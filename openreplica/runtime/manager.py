"""Runtime manager for OpenReplica."""

from typing import Dict, Any, Optional
from openreplica.runtime.docker_runtime import DockerRuntime
from openreplica.core.config import settings
from openreplica.core.exceptions import RuntimeError
from openreplica.core.logger import logger


class RuntimeManager:
    """Manages runtime environments for code execution."""
    
    def __init__(self):
        self.docker_runtime = DockerRuntime() if settings.docker_enabled else None
        self.workspaces: Dict[str, str] = {}  # session_id -> workspace_path
        
    async def create_workspace(self, session_id: str, workspace_path: Optional[str] = None) -> str:
        """Create a workspace for a session."""
        if workspace_path is None:
            workspace_path = f"{settings.workspace_base}/{session_id}"
            
        self.workspaces[session_id] = workspace_path
        
        if self.docker_runtime:
            await self.docker_runtime.create_container(session_id, workspace_path)
            
        logger.info("Workspace created", session_id=session_id, workspace_path=workspace_path)
        return workspace_path
        
    async def execute_code(
        self, 
        session_id: str, 
        code: str, 
        language: str = "python",
        workspace_path: Optional[str] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """Execute code in the runtime environment."""
        if session_id not in self.workspaces:
            if workspace_path:
                await self.create_workspace(session_id, workspace_path)
            else:
                raise RuntimeError(f"No workspace found for session {session_id}")
                
        if not self.docker_runtime:
            raise RuntimeError("Docker runtime not available")
            
        return await self.docker_runtime.execute_code(session_id, code, language, **kwargs)
        
    async def write_file(self, session_id: str, filepath: str, content: str):
        """Write a file in the workspace."""
        if session_id not in self.workspaces:
            raise RuntimeError(f"No workspace found for session {session_id}")
            
        if self.docker_runtime:
            await self.docker_runtime.write_file(session_id, filepath, content)
        else:
            # Fallback to local file system
            import os
            import aiofiles
            
            full_path = os.path.join(self.workspaces[session_id], filepath)
            os.makedirs(os.path.dirname(full_path), exist_ok=True)
            
            async with aiofiles.open(full_path, 'w') as f:
                await f.write(content)
                
    async def read_file(self, session_id: str, filepath: str) -> str:
        """Read a file from the workspace."""
        if session_id not in self.workspaces:
            raise RuntimeError(f"No workspace found for session {session_id}")
            
        if self.docker_runtime:
            return await self.docker_runtime.read_file(session_id, filepath)
        else:
            # Fallback to local file system
            import os
            import aiofiles
            
            full_path = os.path.join(self.workspaces[session_id], filepath)
            
            async with aiofiles.open(full_path, 'r') as f:
                return await f.read()
                
    async def list_files(self, session_id: str, directory: str = ".") -> list[str]:
        """List files in a directory."""
        if session_id not in self.workspaces:
            raise RuntimeError(f"No workspace found for session {session_id}")
            
        if self.docker_runtime:
            return await self.docker_runtime.list_files(session_id, directory)
        else:
            # Fallback to local file system
            import os
            
            workspace_path = self.workspaces[session_id]
            full_path = os.path.join(workspace_path, directory)
            
            if not os.path.exists(full_path):
                return []
                
            files = []
            for root, dirs, filenames in os.walk(full_path):
                for filename in filenames:
                    rel_path = os.path.relpath(os.path.join(root, filename), workspace_path)
                    files.append(rel_path)
                    
            return files
            
    async def cleanup_workspace(self, session_id: str):
        """Clean up workspace for a session."""
        if session_id in self.workspaces:
            if self.docker_runtime:
                await self.docker_runtime.cleanup_container(session_id)
                
            del self.workspaces[session_id]
            logger.info("Workspace cleaned up", session_id=session_id)
            
    def get_workspace_path(self, session_id: str) -> Optional[str]:
        """Get the workspace path for a session."""
        return self.workspaces.get(session_id)


# Global runtime manager instance
runtime_manager = RuntimeManager()
