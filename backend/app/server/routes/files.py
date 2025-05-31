"""
File management API routes
"""
import os
import shutil
from typing import Dict, Any, List, Optional
from fastapi import APIRouter, HTTPException, UploadFile, File
from pydantic import BaseModel
import mimetypes

from app.core.config import get_settings
from app.core.logging import get_logger

router = APIRouter()
logger = get_logger(__name__)
settings = get_settings()


class FileInfo(BaseModel):
    name: str
    path: str
    size: int
    modified: float
    is_directory: bool
    mime_type: Optional[str] = None


class DirectoryListing(BaseModel):
    path: str
    files: List[FileInfo]
    total_files: int
    total_size: int


class FileContent(BaseModel):
    path: str
    content: str
    encoding: str = "utf-8"
    size: int


class WriteFileRequest(BaseModel):
    path: str
    content: str
    encoding: str = "utf-8"


def get_workspace_path(session_id: str, path: str = "") -> str:
    """Get absolute workspace path for a session"""
    workspace_base = os.path.join(settings.workspace_base, session_id)
    if path:
        # Ensure path is relative and safe
        path = path.lstrip("/")
        full_path = os.path.join(workspace_base, path)
        # Security check - ensure path is within workspace
        if not os.path.abspath(full_path).startswith(os.path.abspath(workspace_base)):
            raise HTTPException(status_code=400, detail="Invalid path")
        return full_path
    return workspace_base


def ensure_workspace_exists(session_id: str) -> str:
    """Ensure workspace directory exists and return path"""
    workspace_path = get_workspace_path(session_id)
    os.makedirs(workspace_path, exist_ok=True)
    return workspace_path


@router.get("/{session_id}/list")
async def list_directory(
    session_id: str, 
    path: str = ""
) -> DirectoryListing:
    """List files and directories in workspace"""
    try:
        full_path = get_workspace_path(session_id, path)
        
        if not os.path.exists(full_path):
            ensure_workspace_exists(session_id)
            if path:  # If specific path doesn't exist
                raise HTTPException(status_code=404, detail="Directory not found")
        
        if not os.path.isdir(full_path):
            raise HTTPException(status_code=400, detail="Path is not a directory")
        
        files = []
        total_size = 0
        
        for item in os.listdir(full_path):
            item_path = os.path.join(full_path, item)
            stat = os.stat(item_path)
            
            is_dir = os.path.isdir(item_path)
            size = 0 if is_dir else stat.st_size
            total_size += size
            
            # Get relative path for response
            relative_path = os.path.join(path, item) if path else item
            
            files.append(FileInfo(
                name=item,
                path=relative_path,
                size=size,
                modified=stat.st_mtime,
                is_directory=is_dir,
                mime_type=None if is_dir else mimetypes.guess_type(item)[0]
            ))
        
        # Sort: directories first, then files, both alphabetically
        files.sort(key=lambda x: (not x.is_directory, x.name.lower()))
        
        return DirectoryListing(
            path=path,
            files=files,
            total_files=len(files),
            total_size=total_size
        )
        
    except Exception as e:
        logger.error("Failed to list directory", error=str(e), session_id=session_id, path=path)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{session_id}/read")
async def read_file(session_id: str, path: str) -> FileContent:
    """Read file content"""
    try:
        full_path = get_workspace_path(session_id, path)
        
        if not os.path.exists(full_path):
            raise HTTPException(status_code=404, detail="File not found")
        
        if os.path.isdir(full_path):
            raise HTTPException(status_code=400, detail="Path is a directory")
        
        # Check file size
        file_size = os.path.getsize(full_path)
        max_size = settings.max_file_size_mb * 1024 * 1024
        if file_size > max_size:
            raise HTTPException(
                status_code=413, 
                detail=f"File too large (max {settings.max_file_size_mb}MB)"
            )
        
        # Try to read as text
        try:
            with open(full_path, 'r', encoding='utf-8') as f:
                content = f.read()
            encoding = 'utf-8'
        except UnicodeDecodeError:
            # Fallback to binary read for non-text files
            with open(full_path, 'rb') as f:
                content = f.read().decode('latin-1')  # Preserve bytes
            encoding = 'binary'
        
        logger.info("File read", session_id=session_id, path=path, size=file_size)
        
        return FileContent(
            path=path,
            content=content,
            encoding=encoding,
            size=file_size
        )
        
    except Exception as e:
        logger.error("Failed to read file", error=str(e), session_id=session_id, path=path)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{session_id}/write")
async def write_file(session_id: str, request: WriteFileRequest) -> Dict[str, Any]:
    """Write content to file"""
    try:
        full_path = get_workspace_path(session_id, request.path)
        
        # Ensure parent directory exists
        os.makedirs(os.path.dirname(full_path), exist_ok=True)
        
        # Check file extension
        _, ext = os.path.splitext(request.path)
        if ext and ext not in settings.allowed_file_extensions:
            raise HTTPException(
                status_code=400, 
                detail=f"File extension {ext} not allowed"
            )
        
        # Write file
        with open(full_path, 'w', encoding=request.encoding) as f:
            f.write(request.content)
        
        file_size = os.path.getsize(full_path)
        
        logger.info("File written", session_id=session_id, path=request.path, size=file_size)
        
        return {
            "message": "File written successfully",
            "path": request.path,
            "size": file_size
        }
        
    except Exception as e:
        logger.error("Failed to write file", error=str(e), session_id=session_id, path=request.path)
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/{session_id}/delete")
async def delete_file(session_id: str, path: str) -> Dict[str, str]:
    """Delete file or directory"""
    try:
        full_path = get_workspace_path(session_id, path)
        
        if not os.path.exists(full_path):
            raise HTTPException(status_code=404, detail="File or directory not found")
        
        if os.path.isdir(full_path):
            shutil.rmtree(full_path)
        else:
            os.remove(full_path)
        
        logger.info("File deleted", session_id=session_id, path=path)
        
        return {"message": f"{'Directory' if os.path.isdir(full_path) else 'File'} deleted successfully"}
        
    except Exception as e:
        logger.error("Failed to delete file", error=str(e), session_id=session_id, path=path)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{session_id}/upload")
async def upload_file(
    session_id: str,
    file: UploadFile = File(...),
    path: str = ""
) -> Dict[str, Any]:
    """Upload a file to workspace"""
    try:
        # Check file size
        content = await file.read()
        max_size = settings.max_file_size_mb * 1024 * 1024
        if len(content) > max_size:
            raise HTTPException(
                status_code=413,
                detail=f"File too large (max {settings.max_file_size_mb}MB)"
            )
        
        # Determine file path
        file_path = os.path.join(path, file.filename) if path else file.filename
        full_path = get_workspace_path(session_id, file_path)
        
        # Ensure parent directory exists
        os.makedirs(os.path.dirname(full_path), exist_ok=True)
        
        # Write file
        with open(full_path, 'wb') as f:
            f.write(content)
        
        logger.info("File uploaded", session_id=session_id, filename=file.filename, size=len(content))
        
        return {
            "message": "File uploaded successfully",
            "filename": file.filename,
            "path": file_path,
            "size": len(content)
        }
        
    except Exception as e:
        logger.error("Failed to upload file", error=str(e), session_id=session_id)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{session_id}/create-directory")
async def create_directory(
    session_id: str,
    path: str
) -> Dict[str, str]:
    """Create a new directory"""
    try:
        full_path = get_workspace_path(session_id, path)
        
        if os.path.exists(full_path):
            raise HTTPException(status_code=409, detail="Directory already exists")
        
        os.makedirs(full_path, exist_ok=True)
        
        logger.info("Directory created", session_id=session_id, path=path)
        
        return {"message": "Directory created successfully"}
        
    except Exception as e:
        logger.error("Failed to create directory", error=str(e), session_id=session_id, path=path)
        raise HTTPException(status_code=500, detail=str(e))
