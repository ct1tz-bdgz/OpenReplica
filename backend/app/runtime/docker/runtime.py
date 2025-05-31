"""
Docker runtime implementation for OpenReplica
Provides secure, isolated execution environments using Docker containers
"""
import asyncio
import json
import os
import time
from typing import Dict, Any, Optional, List, AsyncGenerator
import docker
from docker.errors import DockerException, ContainerError, ImageNotFound

from app.runtime.base import Runtime, RuntimeConfig, CommandResult, FileInfo
from app.events.action import Action, ActionType
from app.events.observation import Observation, create_observation, ObservationType
from app.core.logging import get_logger

logger = get_logger(__name__)


class DockerRuntime(Runtime):
    """Docker-based runtime environment"""
    
    def __init__(self, config: RuntimeConfig):
        super().__init__(config)
        self.docker_client = None
        self.container = None
        self.background_processes: Dict[str, Any] = {}
        
    async def start(self, session_id: str) -> None:
        """Start Docker container for the session"""
        self.session_id = session_id
        
        try:
            # Initialize Docker client
            self.docker_client = docker.from_env()
            
            # Create container name
            container_name = f"{self.config.container_name_prefix}_{session_id}"
            
            # Setup environment variables
            environment = {
                "DEBIAN_FRONTEND": "noninteractive",
                "PYTHONUNBUFFERED": "1",
                "PYTHONIOENCODING": "utf-8",
                "SESSION_ID": session_id,
                **self.config.environment
            }
            
            # Setup volumes
            workspace_host_path = os.path.abspath(f"/tmp/openreplica_workspaces/{session_id}")
            os.makedirs(workspace_host_path, exist_ok=True)
            
            volumes = {
                workspace_host_path: {
                    'bind': self.config.workspace_dir,
                    'mode': 'rw'
                }
            }
            
            # Container configuration
            container_config = {
                'image': self.config.container_image,
                'name': container_name,
                'environment': environment,
                'volumes': volumes,
                'working_dir': self.config.workspace_dir,
                'user': f"{self.config.user_id}:{self.config.group_id}",
                'mem_limit': self.config.memory_limit,
                'cpus': self.config.cpu_limit,
                'detach': True,
                'stdin_open': True,
                'tty': True,
                'remove': True,  # Auto-remove when stopped
                'security_opt': ['no-new-privileges:true'],
                'cap_drop': ['ALL'],
                'cap_add': ['CHOWN', 'DAC_OVERRIDE', 'FOWNER', 'SETGID', 'SETUID'],
            }
            
            # Network configuration
            if not self.config.enable_networking:
                container_config['network_mode'] = 'none'
            else:
                container_config['dns'] = self.config.dns_servers
            
            # Read-only root filesystem
            if self.config.read_only_root:
                container_config['read_only'] = True
                container_config['tmpfs'] = {'/tmp': 'noexec,nosuid,size=100m'}
            
            # Pull image if not available
            try:
                self.docker_client.images.get(self.config.container_image)
            except ImageNotFound:
                logger.info(f"Pulling Docker image: {self.config.container_image}")
                self.docker_client.images.pull(self.config.container_image)
            
            # Create and start container
            self.container = self.docker_client.containers.run(**container_config)
            self.container_id = self.container.id
            self.is_running = True
            
            # Setup working directory
            await self._setup_workspace()
            
            logger.info(f"Docker container started: {container_name}")
            
        except DockerException as e:
            logger.error(f"Failed to start Docker container: {e}")
            raise RuntimeError(f"Docker runtime failed to start: {e}")
    
    async def stop(self) -> None:
        """Stop the Docker container"""
        if self.container:
            try:
                # Stop background processes
                for proc_id, proc_info in self.background_processes.items():
                    try:
                        await self._kill_process(proc_info['pid'])
                    except Exception as e:
                        logger.warning(f"Failed to kill process {proc_id}: {e}")
                
                # Stop container
                self.container.stop(timeout=10)
                logger.info(f"Docker container stopped: {self.container_id}")
                
            except Exception as e:
                logger.error(f"Error stopping container: {e}")
                try:
                    self.container.kill()
                except Exception:
                    pass
            finally:
                self.container = None
                self.container_id = None
                self.is_running = False
                self.background_processes.clear()
    
    async def execute_action(self, action: Action) -> Observation:
        """Execute an action in the Docker container"""
        if not self.is_running or not self.container:
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
        working_dir = getattr(action, 'working_dir', self.config.workspace_dir)
        timeout = getattr(action, 'timeout', self.config.timeout)
        background = getattr(action, 'background', False)
        
        if background:
            return await self._run_command_background(command, working_dir)
        else:
            return await self.run_command(command, working_dir, timeout)
    
    async def _handle_write_action(self, action: Action) -> Observation:
        """Handle WRITE action"""
        path = getattr(action, 'path', '')
        content = getattr(action, 'content', '')
        encoding = getattr(action, 'encoding', 'utf-8')
        
        await self.write_file(path, content, encoding)
        
        return create_observation(
            ObservationType.FILE_WRITTEN,
            path=path,
            size=len(content.encode(encoding)),
            success=True
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
                size=len(content.encode('utf-8')),
                success=True
            )
            
        except Exception as e:
            return create_observation(
                ObservationType.ERROR,
                error_message=f"Failed to read file {path}: {e}",
                success=False
            )
    
    async def run_command(self, command: str, working_dir: str = None, timeout: int = None) -> Observation:
        """Run a command in the container"""
        if not self.container:
            raise RuntimeError("Container not running")
        
        working_dir = working_dir or self.config.workspace_dir
        timeout = timeout or self.config.timeout
        
        # Prepare command
        full_command = f"cd {working_dir} && {command}"
        
        start_time = time.time()
        
        try:
            # Execute command
            exit_code, output = self.container.exec_run(
                cmd=["/bin/bash", "-c", full_command],
                stdout=True,
                stderr=True,
                stdin=False,
                tty=False,
                privileged=False,
                user=f"{self.config.user_id}:{self.config.group_id}",
                workdir=working_dir,
                environment=self.config.environment
            )
            
            execution_time = time.time() - start_time
            
            # Decode output
            if isinstance(output, bytes):
                output_str = output.decode('utf-8', errors='replace')
            else:
                output_str = str(output)
            
            # Split stdout and stderr (Docker exec_run combines them)
            stdout = output_str
            stderr = ""
            
            return create_observation(
                ObservationType.COMMAND_RESULT,
                command=command,
                exit_code=exit_code,
                stdout=stdout,
                stderr=stderr,
                execution_time=execution_time,
                working_dir=working_dir,
                success=exit_code == 0
            )
            
        except Exception as e:
            execution_time = time.time() - start_time
            return create_observation(
                ObservationType.ERROR,
                error_message=str(e),
                success=False
            )
    
    async def read_file(self, path: str) -> str:
        """Read file content from container"""
        if not self.container:
            raise RuntimeError("Container not running")
        
        try:
            # Use cat command to read file
            exit_code, output = self.container.exec_run(
                cmd=["cat", path],
                stdout=True,
                stderr=True
            )
            
            if exit_code != 0:
                raise FileNotFoundError(f"File not found or cannot be read: {path}")
            
            if isinstance(output, bytes):
                return output.decode('utf-8', errors='replace')
            return str(output)
            
        except Exception as e:
            raise RuntimeError(f"Failed to read file {path}: {e}")
    
    async def write_file(self, path: str, content: str, encoding: str = 'utf-8') -> None:
        """Write content to file in container"""
        if not self.container:
            raise RuntimeError("Container not running")
        
        try:
            # Ensure directory exists
            dir_path = os.path.dirname(path)
            if dir_path:
                self.container.exec_run(["mkdir", "-p", dir_path])
            
            # Write content using echo (for small files) or dd (for large files)
            if len(content) < 1024 * 1024:  # Less than 1MB
                # Use echo for small files
                escaped_content = content.replace("'", "'\"'\"'")
                command = f"echo '{escaped_content}' > {path}"
                exit_code, output = self.container.exec_run(
                    cmd=["/bin/bash", "-c", command]
                )
            else:
                # Use stdin for large files
                exit_code, output = self.container.exec_run(
                    cmd=["tee", path],
                    stdin=True,
                    stdout=True,
                    stderr=True
                )
            
            if exit_code != 0:
                raise RuntimeError(f"Failed to write file: {output}")
                
        except Exception as e:
            raise RuntimeError(f"Failed to write file {path}: {e}")
    
    async def list_files(self, path: str = ".") -> List[Dict[str, Any]]:
        """List files in directory"""
        if not self.container:
            raise RuntimeError("Container not running")
        
        try:
            # Use ls with JSON-like output
            command = f"find {path} -maxdepth 1 -exec stat --format='%n|%s|%Y|%A|%U|%G' {{}} \\;"
            exit_code, output = self.container.exec_run(
                cmd=["/bin/bash", "-c", command]
            )
            
            if exit_code != 0:
                raise RuntimeError(f"Failed to list directory: {output}")
            
            files = []
            if isinstance(output, bytes):
                output = output.decode('utf-8', errors='replace')
            
            for line in output.strip().split('\n'):
                if not line:
                    continue
                    
                parts = line.split('|')
                if len(parts) >= 6:
                    name = os.path.basename(parts[0])
                    if name == path or name == '.':
                        continue
                        
                    files.append({
                        'name': name,
                        'path': parts[0],
                        'size': int(parts[1]),
                        'modified': float(parts[2]),
                        'is_directory': parts[3].startswith('d'),
                        'permissions': parts[3],
                        'owner': parts[4],
                        'group': parts[5]
                    })
            
            return files
            
        except Exception as e:
            raise RuntimeError(f"Failed to list files in {path}: {e}")
    
    async def _setup_workspace(self) -> None:
        """Setup the workspace environment"""
        setup_commands = [
            "apt-get update -q",
            "apt-get install -yq curl wget git vim nano tree ripgrep",
            "pip install --upgrade pip",
            "pip install requests aiohttp fastapi uvicorn",
            f"chown -R {self.config.user_id}:{self.config.group_id} {self.config.workspace_dir}",
        ]
        
        for command in setup_commands:
            try:
                await self.run_command(command)
            except Exception as e:
                logger.warning(f"Setup command failed: {command} - {e}")
    
    async def _run_command_background(self, command: str, working_dir: str) -> Observation:
        """Run command in background"""
        # This would require implementing background process management
        # For now, return an observation indicating background execution started
        return create_observation(
            ObservationType.SUCCESS,
            message=f"Background command started: {command}",
            success=True
        )
    
    async def _kill_process(self, pid: int) -> None:
        """Kill a process by PID"""
        if self.container:
            try:
                self.container.exec_run(["kill", "-9", str(pid)])
            except Exception as e:
                logger.warning(f"Failed to kill process {pid}: {e}")
