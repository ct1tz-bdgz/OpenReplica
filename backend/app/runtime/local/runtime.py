"""
Local runtime implementation for OpenReplica
Provides local execution environment for development and testing
"""
import asyncio
import os
import shutil
import subprocess
import time
from typing import Dict, Any, Optional, List
import tempfile
import stat

from app.runtime.base import Runtime, RuntimeConfig, CommandResult
from app.events.action import Action, ActionType
from app.events.observation import Observation, create_observation, ObservationType
from app.core.logging import get_logger

logger = get_logger(__name__)


class LocalRuntime(Runtime):
    """Local runtime environment for development and testing"""
    
    def __init__(self, config: RuntimeConfig):
        super().__init__(config)
        self.workspace_path = None
        self.processes: Dict[str, subprocess.Popen] = {}
        
    async def start(self, session_id: str) -> None:
        """Start local runtime environment"""
        self.session_id = session_id
        
        try:
            # Create workspace directory
            base_workspace = self.config.workspace_dir
            if not os.path.isabs(base_workspace):
                base_workspace = os.path.abspath(base_workspace)
            
            self.workspace_path = os.path.join(base_workspace, session_id)
            os.makedirs(self.workspace_path, exist_ok=True)
            
            # Set permissions
            os.chmod(self.workspace_path, 0o755)
            
            # Setup environment
            await self._setup_workspace()
            
            self.is_running = True
            logger.info(f"Local runtime started for session {session_id}")
            
        except Exception as e:
            logger.error(f"Failed to start local runtime: {e}")
            raise RuntimeError(f"Local runtime failed to start: {e}")
    
    async def stop(self) -> None:
        """Stop local runtime environment"""
        try:
            # Terminate all running processes
            for proc_id, process in self.processes.items():
                try:
                    process.terminate()
                    # Wait up to 5 seconds for graceful shutdown
                    try:
                        process.wait(timeout=5)
                    except subprocess.TimeoutExpired:
                        process.kill()
                        process.wait()
                    logger.info(f"Terminated process {proc_id}")
                except Exception as e:
                    logger.warning(f"Failed to terminate process {proc_id}: {e}")
            
            self.processes.clear()
            self.is_running = False
            
            logger.info(f"Local runtime stopped for session {self.session_id}")
            
        except Exception as e:
            logger.error(f"Error stopping local runtime: {e}")
    
    async def execute_action(self, action: Action) -> Observation:
        """Execute an action in the local environment"""
        if not self.is_running:
            return create_observation(
                ObservationType.ERROR,
                error_message="Runtime not running",
                success=False
            )
        
        try:
            if action.action_type == ActionType.RUN:
                return await self._handle_run_action(action)
            elif action.action_type == ActionType.WRITE:
                return await self._handle_write_action(action)
            elif action.action_type == ActionType.READ:
                return await self._handle_read_action(action)
            elif action.action_type == ActionType.EDIT:
                return await self._handle_edit_action(action)
            elif action.action_type == ActionType.DELETE:
                return await self._handle_delete_action(action)
            elif action.action_type == ActionType.CREATE_DIRECTORY:
                return await self._handle_create_directory_action(action)
            elif action.action_type == ActionType.SEARCH:
                return await self._handle_search_action(action)
            else:
                return create_observation(
                    ObservationType.ERROR,
                    error_message=f"Unsupported action type: {action.action_type}",
                    success=False
                )
                
        except Exception as e:
            logger.error(f"Action execution failed: {e}")
            return create_observation(
                ObservationType.ERROR,
                error_message=str(e),
                success=False
            )
    
    async def _handle_run_action(self, action: Action) -> Observation:
        """Handle RUN action"""
        command = getattr(action, 'command', '')
        working_dir = getattr(action, 'working_dir', self.workspace_path)
        timeout = getattr(action, 'timeout', self.config.timeout)
        background = getattr(action, 'background', False)
        
        if background:
            return await self._run_command_background(command, working_dir)
        else:
            result = await self.run_command(command, working_dir, timeout)
            
            return create_observation(
                ObservationType.COMMAND_RESULT,
                command=command,
                exit_code=result.exit_code,
                stdout=result.stdout,
                stderr=result.stderr,
                working_dir=working_dir,
                execution_time=result.execution_time,
                success=result.success
            )
    
    async def _handle_write_action(self, action: Action) -> Observation:
        """Handle WRITE action"""
        path = getattr(action, 'path', '')
        content = getattr(action, 'content', '')
        encoding = getattr(action, 'encoding', 'utf-8')
        
        try:
            await self.write_file(path, content, encoding)
            
            file_path = self._resolve_path(path)
            file_size = os.path.getsize(file_path)
            
            return create_observation(
                ObservationType.FILE_WRITTEN,
                path=path,
                size=file_size,
                success=True
            )
            
        except Exception as e:
            return create_observation(
                ObservationType.ERROR,
                error_message=f"Failed to write file {path}: {e}",
                success=False
            )
    
    async def _handle_read_action(self, action: Action) -> Observation:
        """Handle READ action"""
        path = getattr(action, 'path', '')
        start_line = getattr(action, 'start_line', None)
        end_line = getattr(action, 'end_line', None)
        
        try:
            content = await self.read_file(path)
            
            # Handle line range if specified
            if start_line is not None:
                lines = content.split('\n')
                start_idx = max(0, start_line - 1)  # Convert to 0-indexed
                end_idx = len(lines) if end_line is None else min(len(lines), end_line)
                content = '\n'.join(lines[start_idx:end_idx])
            
            return create_observation(
                ObservationType.FILE_READ,
                path=path,
                content=content,
                encoding='utf-8',
                size=len(content.encode('utf-8')),
                success=True
            )
            
        except Exception as e:
            return create_observation(
                ObservationType.ERROR,
                error_message=f"Failed to read file {path}: {e}",
                success=False
            )
    
    async def run_command(self, command: str, working_dir: str = None, timeout: int = None) -> CommandResult:
        """Run a command in the local environment"""
        working_dir = working_dir or self.workspace_path
        timeout = timeout or self.config.timeout
        
        start_time = time.time()
        
        try:
            # Prepare environment
            env = {**os.environ, **self.config.environment}
            
            # Run command
            process = await asyncio.create_subprocess_shell(
                command,
                cwd=working_dir,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                env=env
            )
            
            try:
                stdout, stderr = await asyncio.wait_for(
                    process.communicate(), 
                    timeout=timeout
                )
                exit_code = process.returncode
            except asyncio.TimeoutError:
                process.kill()
                await process.wait()
                stdout, stderr = b"", b"Command timed out"
                exit_code = -1
            
            execution_time = time.time() - start_time
            
            return CommandResult(
                command=command,
                exit_code=exit_code,
                stdout=stdout.decode('utf-8', errors='replace'),
                stderr=stderr.decode('utf-8', errors='replace'),
                execution_time=execution_time,
                pid=process.pid,
                working_dir=working_dir
            )
            
        except Exception as e:
            execution_time = time.time() - start_time
            return CommandResult(
                command=command,
                exit_code=-1,
                stdout="",
                stderr=str(e),
                execution_time=execution_time,
                working_dir=working_dir
            )
    
    async def read_file(self, path: str) -> str:
        """Read file content"""
        file_path = self._resolve_path(path)
        
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"File not found: {path}")
        
        if not os.path.isfile(file_path):
            raise ValueError(f"Path is not a file: {path}")
        
        # Check file size
        file_size = os.path.getsize(file_path)
        if file_size > self.config.max_file_size:
            raise ValueError(f"File too large: {file_size} bytes")
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                return f.read()
        except UnicodeDecodeError:
            # Try with different encodings
            for encoding in ['latin-1', 'cp1252', 'iso-8859-1']:
                try:
                    with open(file_path, 'r', encoding=encoding) as f:
                        return f.read()
                except UnicodeDecodeError:
                    continue
            
            # If all encodings fail, read as binary and decode with errors='replace'
            with open(file_path, 'rb') as f:
                return f.read().decode('utf-8', errors='replace')
    
    async def write_file(self, path: str, content: str, encoding: str = 'utf-8') -> None:
        """Write content to file"""
        file_path = self._resolve_path(path)
        
        # Check file extension
        _, ext = os.path.splitext(path)
        if ext and ext not in self.config.allowed_extensions:
            raise ValueError(f"File extension not allowed: {ext}")
        
        # Ensure directory exists
        os.makedirs(os.path.dirname(file_path), exist_ok=True)
        
        try:
            with open(file_path, 'w', encoding=encoding) as f:
                f.write(content)
        except Exception as e:
            raise RuntimeError(f"Failed to write file: {e}")
    
    async def list_files(self, path: str = ".") -> List[Dict[str, Any]]:
        """List files in directory"""
        dir_path = self._resolve_path(path)
        
        if not os.path.exists(dir_path):
            raise FileNotFoundError(f"Directory not found: {path}")
        
        if not os.path.isdir(dir_path):
            raise ValueError(f"Path is not a directory: {path}")
        
        files = []
        try:
            for item in os.listdir(dir_path):
                item_path = os.path.join(dir_path, item)
                stat_info = os.stat(item_path)
                
                files.append({
                    'name': item,
                    'path': os.path.relpath(item_path, self.workspace_path),
                    'size': stat_info.st_size,
                    'modified': stat_info.st_mtime,
                    'is_directory': os.path.isdir(item_path),
                    'permissions': stat.filemode(stat_info.st_mode),
                    'owner': str(stat_info.st_uid),
                    'group': str(stat_info.st_gid)
                })
            
            return files
            
        except Exception as e:
            raise RuntimeError(f"Failed to list directory: {e}")
    
    def _resolve_path(self, path: str) -> str:
        """Resolve relative path to absolute path within workspace"""
        if os.path.isabs(path):
            # Ensure path is within workspace
            abs_path = os.path.normpath(path)
            if not abs_path.startswith(self.workspace_path):
                raise ValueError(f"Path outside workspace: {path}")
            return abs_path
        else:
            # Relative path
            abs_path = os.path.normpath(os.path.join(self.workspace_path, path))
            if not abs_path.startswith(self.workspace_path):
                raise ValueError(f"Path outside workspace: {path}")
            return abs_path
    
    async def _setup_workspace(self) -> None:
        """Setup the workspace environment"""
        # Create common directories
        common_dirs = [
            "src",
            "tests",
            "docs",
            ".vscode",
            "tmp"
        ]
        
        for dir_name in common_dirs:
            dir_path = os.path.join(self.workspace_path, dir_name)
            os.makedirs(dir_path, exist_ok=True)
        
        # Create a README file
        readme_content = f"""# OpenReplica Workspace

Session ID: {self.session_id}
Created: {time.strftime('%Y-%m-%d %H:%M:%S')}

This is your AI-powered development workspace. You can:
- Write and edit code
- Execute commands
- Browse files
- Chat with AI assistants

Happy coding!
"""
        
        readme_path = os.path.join(self.workspace_path, "README.md")
        with open(readme_path, 'w') as f:
            f.write(readme_content)
    
    async def _run_command_background(self, command: str, working_dir: str) -> Observation:
        """Run command in background"""
        try:
            # Prepare environment
            env = {**os.environ, **self.config.environment}
            
            # Start background process
            process = await asyncio.create_subprocess_shell(
                command,
                cwd=working_dir,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                env=env
            )
            
            # Store process for later management
            proc_id = f"bg_{len(self.processes)}_{int(time.time())}"
            self.processes[proc_id] = process
            
            return create_observation(
                ObservationType.SUCCESS,
                message=f"Background process started: {command} (PID: {process.pid})",
                data={"process_id": proc_id, "pid": process.pid},
                success=True
            )
            
        except Exception as e:
            return create_observation(
                ObservationType.ERROR,
                error_message=f"Failed to start background process: {e}",
                success=False
            )
