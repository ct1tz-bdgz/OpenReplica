"""Docker-based runtime for secure code execution."""

import os
import asyncio
import tempfile
from typing import Dict, Any, Optional
import docker
from docker.models.containers import Container
from openreplica.core.config import settings
from openreplica.core.exceptions import RuntimeError
from openreplica.core.logger import logger


class DockerRuntime:
    """Docker-based runtime for secure code execution."""
    
    def __init__(self):
        self.client = docker.from_env()
        self.containers: Dict[str, Container] = {}  # session_id -> container
        
    async def create_container(self, session_id: str, workspace_path: str) -> Container:
        """Create a new Docker container for a session."""
        try:
            # Ensure workspace directory exists
            os.makedirs(workspace_path, exist_ok=True)
            
            container = self.client.containers.run(
                image=settings.runtime_image,
                command="sleep infinity",  # Keep container alive
                detach=True,
                name=f"openreplica-{session_id}",
                volumes={
                    workspace_path: {"bind": "/workspace", "mode": "rw"}
                },
                working_dir="/workspace",
                mem_limit=settings.max_container_memory,
                network_mode="none",  # Disable network access for security
                remove=True,  # Auto-remove when stopped
                environment={
                    "PYTHONPATH": "/workspace",
                    "HOME": "/workspace"
                }
            )
            
            self.containers[session_id] = container
            logger.info("Created Docker container", session_id=session_id, container_id=container.id[:12])
            
            return container
            
        except Exception as e:
            logger.error("Failed to create Docker container", session_id=session_id, error=str(e))
            raise RuntimeError(f"Failed to create container: {str(e)}")
            
    async def execute_code(
        self, 
        session_id: str, 
        code: str, 
        language: str = "python",
        timeout: int = None
    ) -> Dict[str, Any]:
        """Execute code in the Docker container."""
        if timeout is None:
            timeout = settings.sandbox_timeout
            
        container = self.containers.get(session_id)
        if not container:
            raise RuntimeError(f"No container found for session {session_id}")
            
        try:
            # Prepare the execution command based on language
            if language.lower() == "python":
                # Create a temporary file with the code
                with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
                    f.write(code)
                    temp_file = f.name
                    
                # Copy file to container and execute
                container.put_archive("/workspace", open(temp_file, 'rb').read())
                cmd = f"python {os.path.basename(temp_file)}"
                
            elif language.lower() in ["javascript", "js", "node"]:
                with tempfile.NamedTemporaryFile(mode='w', suffix='.js', delete=False) as f:
                    f.write(code)
                    temp_file = f.name
                    
                container.put_archive("/workspace", open(temp_file, 'rb').read())
                cmd = f"node {os.path.basename(temp_file)}"
                
            elif language.lower() == "bash":
                cmd = code
                
            else:
                raise RuntimeError(f"Unsupported language: {language}")
                
            # Execute the command
            exec_result = container.exec_run(
                cmd=cmd,
                timeout=timeout,
                demux=True
            )
            
            stdout = exec_result.output[0].decode() if exec_result.output[0] else ""
            stderr = exec_result.output[1].decode() if exec_result.output[1] else ""
            
            output = stdout
            if stderr:
                output += f"\n--- STDERR ---\n{stderr}"
                
            success = exec_result.exit_code == 0
            
            # Clean up temporary file
            if language.lower() in ["python", "javascript", "js", "node"]:
                os.unlink(temp_file)
                
            logger.info("Code execution completed", 
                       session_id=session_id,
                       language=language,
                       success=success,
                       exit_code=exec_result.exit_code)
            
            return {
                "output": output,
                "success": success,
                "exit_code": exec_result.exit_code,
                "language": language
            }
            
        except Exception as e:
            logger.error("Code execution failed", session_id=session_id, error=str(e))
            return {
                "output": f"Execution error: {str(e)}",
                "success": False,
                "exit_code": -1,
                "language": language
            }
            
    async def write_file(self, session_id: str, filepath: str, content: str):
        """Write a file in the container workspace."""
        container = self.containers.get(session_id)
        if not container:
            raise RuntimeError(f"No container found for session {session_id}")
            
        try:
            # Create directory structure if needed
            dir_path = os.path.dirname(filepath)
            if dir_path:
                container.exec_run(f"mkdir -p {dir_path}")
                
            # Write the file
            with tempfile.NamedTemporaryFile(mode='w', delete=False) as f:
                f.write(content)
                temp_file = f.name
                
            # Copy file to container
            with open(temp_file, 'rb') as f:
                container.put_archive(os.path.dirname(filepath) or "/workspace", f.read())
                
            os.unlink(temp_file)
            
            logger.info("File written", session_id=session_id, filepath=filepath)
            
        except Exception as e:
            logger.error("File write failed", session_id=session_id, filepath=filepath, error=str(e))
            raise RuntimeError(f"Failed to write file: {str(e)}")
            
    async def read_file(self, session_id: str, filepath: str) -> str:
        """Read a file from the container workspace."""
        container = self.containers.get(session_id)
        if not container:
            raise RuntimeError(f"No container found for session {session_id}")
            
        try:
            # Read the file
            exec_result = container.exec_run(f"cat {filepath}")
            
            if exec_result.exit_code != 0:
                raise RuntimeError(f"File not found or cannot be read: {filepath}")
                
            content = exec_result.output.decode()
            logger.info("File read", session_id=session_id, filepath=filepath)
            
            return content
            
        except Exception as e:
            logger.error("File read failed", session_id=session_id, filepath=filepath, error=str(e))
            raise RuntimeError(f"Failed to read file: {str(e)}")
            
    async def list_files(self, session_id: str, directory: str = "/workspace") -> list[str]:
        """List files in a directory."""
        container = self.containers.get(session_id)
        if not container:
            raise RuntimeError(f"No container found for session {session_id}")
            
        try:
            exec_result = container.exec_run(f"find {directory} -type f")
            
            if exec_result.exit_code != 0:
                return []
                
            files = exec_result.output.decode().strip().split('\n')
            return [f for f in files if f]
            
        except Exception as e:
            logger.error("File listing failed", session_id=session_id, error=str(e))
            return []
            
    async def cleanup_container(self, session_id: str):
        """Clean up and remove the container for a session."""
        container = self.containers.get(session_id)
        if container:
            try:
                container.stop(timeout=10)
                del self.containers[session_id]
                logger.info("Container cleaned up", session_id=session_id)
            except Exception as e:
                logger.error("Container cleanup failed", session_id=session_id, error=str(e))
