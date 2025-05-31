"""
Action execution server for OpenReplica runtime
Runs inside containers and executes actions received from the backend
"""
import argparse
import asyncio
import base64
import json
import logging
import mimetypes
import os
import shutil
import sys
import tempfile
import time
import traceback
from contextlib import asynccontextmanager
from pathlib import Path
from zipfile import ZipFile

from fastapi import Depends, FastAPI, HTTPException, Request, UploadFile
from fastapi.exceptions import RequestValidationError
from fastapi.responses import FileResponse, JSONResponse
from fastapi.security import APIKeyHeader
from pydantic import BaseModel
from starlette.background import BackgroundTask
from starlette.exceptions import HTTPException as StarletteHTTPException
from uvicorn import run

from app.core.logger import get_logger
from app.events.action import (
    Action,
    CmdRunAction,
    FileEditAction,
    FileReadAction,
    FileWriteAction,
)
from app.events.observation import (
    CmdOutputObservation,
    ErrorObservation,
    FileEditObservation,
    FileReadObservation,
    FileWriteObservation,
    Observation,
)
from app.events.serialization import event_from_dict, event_to_dict

logger = get_logger(__name__)


class ActionRequest(BaseModel):
    action: dict


SESSION_API_KEY = os.environ.get('SESSION_API_KEY')
api_key_header = APIKeyHeader(name='X-Session-API-Key', auto_error=False)


def verify_api_key(api_key: str = Depends(api_key_header)):
    if SESSION_API_KEY and api_key != SESSION_API_KEY:
        raise HTTPException(status_code=403, detail='Invalid API Key')
    return api_key


class ActionExecutionServer:
    """Server that executes actions inside runtime containers"""
    
    def __init__(self, working_dir: str = "/workspace", api_key: str = None):
        self.working_dir = working_dir
        self.api_key = api_key
        self.bash_session = None
        self.jupyter_session = None
        
        # Ensure working directory exists
        os.makedirs(working_dir, exist_ok=True)
        os.chdir(working_dir)
        
        self.app = self._create_app()
    
    def _create_app(self) -> FastAPI:
        """Create FastAPI application"""
        
        @asynccontextmanager
        async def lifespan(app: FastAPI):
            # Startup
            logger.info(f"Action execution server starting in {self.working_dir}")
            yield
            # Shutdown
            logger.info("Action execution server shutting down")
        
        app = FastAPI(
            title="OpenReplica Action Execution Server",
            lifespan=lifespan
        )
        
        @app.exception_handler(StarletteHTTPException)
        async def http_exception_handler(request: Request, exc: StarletteHTTPException):
            return JSONResponse(
                status_code=exc.status_code,
                content={"error": exc.detail}
            )
        
        @app.exception_handler(RequestValidationError)
        async def validation_exception_handler(request: Request, exc: RequestValidationError):
            return JSONResponse(
                status_code=422,
                content={"error": "Validation error", "details": exc.errors()}
            )
        
        @app.get("/")
        async def root():
            return {"status": "OpenReplica Action Execution Server"}
        
        @app.get("/health")
        async def health():
            return {
                "status": "healthy",
                "working_dir": self.working_dir,
                "cwd": os.getcwd()
            }
        
        @app.post("/execute_action")
        async def execute_action(
            request: ActionRequest,
            api_key: str = Depends(verify_api_key)
        ):
            """Execute an action and return observation"""
            try:
                # Convert dict to action object
                action = event_from_dict(request.action)
                
                # Execute the action
                observation = await self._execute_action(action)
                
                # Convert observation back to dict
                return event_to_dict(observation)
                
            except Exception as e:
                logger.error(f"Error executing action: {e}")
                traceback.print_exc()
                return event_to_dict(ErrorObservation(
                    content=str(e),
                    message=f"Error executing action: {e}"
                ))
        
        @app.get("/files")
        async def list_files(path: str = "."):
            """List files in directory"""
            try:
                full_path = os.path.join(self.working_dir, path)
                if not os.path.exists(full_path):
                    raise HTTPException(status_code=404, detail="Path not found")
                
                files = []
                for item in os.listdir(full_path):
                    item_path = os.path.join(full_path, item)
                    stat = os.stat(item_path)
                    files.append({
                        "name": item,
                        "is_directory": os.path.isdir(item_path),
                        "size": stat.st_size,
                        "modified": stat.st_mtime
                    })
                
                return {"files": files}
                
            except Exception as e:
                raise HTTPException(status_code=500, detail=str(e))
        
        @app.get("/file/{path:path}")
        async def read_file(path: str):
            """Read file content"""
            try:
                full_path = os.path.join(self.working_dir, path)
                if not os.path.exists(full_path):
                    raise HTTPException(status_code=404, detail="File not found")
                
                if os.path.isdir(full_path):
                    raise HTTPException(status_code=400, detail="Path is a directory")
                
                # Check if binary file
                try:
                    with open(full_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                    return {"content": content, "encoding": "utf-8"}
                except UnicodeDecodeError:
                    # Binary file, return base64 encoded
                    with open(full_path, 'rb') as f:
                        content = base64.b64encode(f.read()).decode('ascii')
                    return {"content": content, "encoding": "base64"}
                
            except Exception as e:
                raise HTTPException(status_code=500, detail=str(e))
        
        @app.post("/file/{path:path}")
        async def write_file(path: str, request: dict):
            """Write file content"""
            try:
                full_path = os.path.join(self.working_dir, path)
                content = request.get("content", "")
                encoding = request.get("encoding", "utf-8")
                
                # Ensure directory exists
                os.makedirs(os.path.dirname(full_path), exist_ok=True)
                
                if encoding == "base64":
                    # Decode base64 content
                    content_bytes = base64.b64decode(content)
                    with open(full_path, 'wb') as f:
                        f.write(content_bytes)
                else:
                    with open(full_path, 'w', encoding=encoding) as f:
                        f.write(content)
                
                return {"success": True, "path": path}
                
            except Exception as e:
                raise HTTPException(status_code=500, detail=str(e))
        
        @app.delete("/file/{path:path}")
        async def delete_file(path: str):
            """Delete file or directory"""
            try:
                full_path = os.path.join(self.working_dir, path)
                if not os.path.exists(full_path):
                    raise HTTPException(status_code=404, detail="Path not found")
                
                if os.path.isdir(full_path):
                    shutil.rmtree(full_path)
                else:
                    os.remove(full_path)
                
                return {"success": True, "path": path}
                
            except Exception as e:
                raise HTTPException(status_code=500, detail=str(e))
        
        @app.post("/upload")
        async def upload_file(file: UploadFile, path: str = ""):
            """Upload file to container"""
            try:
                upload_path = os.path.join(self.working_dir, path, file.filename)
                os.makedirs(os.path.dirname(upload_path), exist_ok=True)
                
                with open(upload_path, 'wb') as f:
                    content = await file.read()
                    f.write(content)
                
                return {"success": True, "path": upload_path, "filename": file.filename}
                
            except Exception as e:
                raise HTTPException(status_code=500, detail=str(e))
        
        return app
    
    async def _execute_action(self, action: Action) -> Observation:
        """Execute an action and return observation"""
        
        if isinstance(action, CmdRunAction):
            return await self._execute_cmd_action(action)
        elif isinstance(action, FileReadAction):
            return await self._execute_file_read_action(action)
        elif isinstance(action, FileWriteAction):
            return await self._execute_file_write_action(action)
        elif isinstance(action, FileEditAction):
            return await self._execute_file_edit_action(action)
        else:
            return ErrorObservation(
                content=f"Unsupported action type: {type(action).__name__}",
                message=f"Action type {type(action).__name__} is not supported"
            )
    
    async def _execute_cmd_action(self, action: CmdRunAction) -> CmdOutputObservation:
        """Execute command action"""
        try:
            # Initialize bash session if needed
            if self.bash_session is None:
                from app.runtime.utils.bash import BashSession
                self.bash_session = BashSession()
            
            # Execute command
            exit_code, output = self.bash_session.execute(action.command)
            
            return CmdOutputObservation(
                content=output,
                command=action.command,
                exit_code=exit_code
            )
            
        except Exception as e:
            return CmdOutputObservation(
                content=str(e),
                command=action.command,
                exit_code=-1
            )
    
    async def _execute_file_read_action(self, action: FileReadAction) -> FileReadObservation:
        """Execute file read action"""
        try:
            file_path = os.path.join(self.working_dir, action.path)
            
            if not os.path.exists(file_path):
                return FileReadObservation(
                    content="",
                    path=action.path,
                    error=f"File not found: {action.path}"
                )
            
            # Read file content
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
            except UnicodeDecodeError:
                # Try with different encodings
                for encoding in ['latin-1', 'cp1252']:
                    try:
                        with open(file_path, 'r', encoding=encoding) as f:
                            content = f.read()
                        break
                    except UnicodeDecodeError:
                        continue
                else:
                    # Read as binary and decode with errors='replace'
                    with open(file_path, 'rb') as f:
                        content = f.read().decode('utf-8', errors='replace')
            
            return FileReadObservation(
                content=content,
                path=action.path
            )
            
        except Exception as e:
            return FileReadObservation(
                content="",
                path=action.path,
                error=str(e)
            )
    
    async def _execute_file_write_action(self, action: FileWriteAction) -> FileWriteObservation:
        """Execute file write action"""
        try:
            file_path = os.path.join(self.working_dir, action.path)
            
            # Ensure directory exists
            os.makedirs(os.path.dirname(file_path), exist_ok=True)
            
            # Write file content
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(action.content)
            
            return FileWriteObservation(
                content=f"File written successfully: {action.path}",
                path=action.path
            )
            
        except Exception as e:
            return FileWriteObservation(
                content=f"Error writing file: {e}",
                path=action.path,
                error=str(e)
            )
    
    async def _execute_file_edit_action(self, action: FileEditAction) -> FileEditObservation:
        """Execute file edit action"""
        try:
            file_path = os.path.join(self.working_dir, action.path)
            
            if not os.path.exists(file_path):
                return FileEditObservation(
                    content=f"File not found: {action.path}",
                    path=action.path,
                    error=f"File not found: {action.path}"
                )
            
            # Read current content
            with open(file_path, 'r', encoding='utf-8') as f:
                current_content = f.read()
            
            # Apply edit based on edit type
            if hasattr(action, 'new_str') and hasattr(action, 'old_str'):
                # String replacement
                if action.old_str in current_content:
                    new_content = current_content.replace(action.old_str, action.new_str)
                else:
                    return FileEditObservation(
                        content=f"String not found in file: {action.old_str}",
                        path=action.path,
                        error=f"String not found: {action.old_str}"
                    )
            else:
                # Full content replacement
                new_content = getattr(action, 'content', current_content)
            
            # Write new content
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(new_content)
            
            return FileEditObservation(
                content=f"File edited successfully: {action.path}",
                path=action.path
            )
            
        except Exception as e:
            return FileEditObservation(
                content=f"Error editing file: {e}",
                path=action.path,
                error=str(e)
            )


def main():
    """Main entry point for action execution server"""
    parser = argparse.ArgumentParser(description="OpenReplica Action Execution Server")
    parser.add_argument("--host", default="0.0.0.0", help="Host to bind to")
    parser.add_argument("--port", type=int, default=8000, help="Port to bind to")
    parser.add_argument("--working-dir", default="/workspace", help="Working directory")
    parser.add_argument("--api-key", help="API key for authentication")
    parser.add_argument("--log-level", default="INFO", help="Log level")
    
    args = parser.parse_args()
    
    # Setup logging
    logging.basicConfig(
        level=getattr(logging, args.log_level.upper()),
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Create server
    server = ActionExecutionServer(
        working_dir=args.working_dir,
        api_key=args.api_key
    )
    
    # Run server
    run(
        server.app,
        host=args.host,
        port=args.port,
        log_level=args.log_level.lower()
    )


if __name__ == "__main__":
    main()
