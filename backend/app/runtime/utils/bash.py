"""
Bash session management for OpenReplica runtime
"""
import asyncio
import os
import subprocess
import threading
import time
from typing import Optional, Tuple
import pty
import select

from app.core.logging import get_logger

logger = get_logger(__name__)


class BashSession:
    """Manages a persistent bash session for command execution"""
    
    def __init__(self, working_dir: str = "/workspace"):
        self.working_dir = working_dir
        self.process: Optional[subprocess.Popen] = None
        self.master_fd: Optional[int] = None
        self.slave_fd: Optional[int] = None
        self._lock = threading.Lock()
        self._started = False
        
    def start(self) -> None:
        """Start the bash session"""
        with self._lock:
            if self._started:
                return
                
            try:
                # Create a pseudo-terminal
                self.master_fd, self.slave_fd = pty.openpty()
                
                # Start bash process
                self.process = subprocess.Popen(
                    ['/bin/bash', '--login', '-i'],
                    stdin=self.slave_fd,
                    stdout=self.slave_fd,
                    stderr=self.slave_fd,
                    cwd=self.working_dir,
                    env=os.environ.copy(),
                    preexec_fn=os.setsid,
                    close_fds=True
                )
                
                # Close slave fd in parent process
                os.close(self.slave_fd)
                self.slave_fd = None
                
                # Set working directory
                self._send_command_raw(f"cd {self.working_dir}")
                time.sleep(0.1)  # Allow command to execute
                
                self._started = True
                logger.info(f"Bash session started in {self.working_dir}")
                
            except Exception as e:
                logger.error(f"Failed to start bash session: {e}")
                self._cleanup()
                raise
    
    def execute(self, command: str, timeout: float = 30.0) -> Tuple[int, str]:
        """Execute a command and return exit code and output"""
        if not self._started:
            self.start()
            
        with self._lock:
            try:
                # Clear any existing output
                self._read_available_output()
                
                # Send command with unique markers
                start_marker = f"__START_COMMAND_{int(time.time())}__"
                end_marker = f"__END_COMMAND_{int(time.time())}__"
                
                command_line = f"echo '{start_marker}'; {command}; echo \"__EXIT_CODE_$?__\"; echo '{end_marker}'"
                self._send_command_raw(command_line)
                
                # Read output until end marker
                output = self._read_until_marker(end_marker, timeout)
                
                # Parse output and exit code
                exit_code, clean_output = self._parse_command_output(output, start_marker, end_marker)
                
                return exit_code, clean_output
                
            except Exception as e:
                logger.error(f"Error executing command '{command}': {e}")
                return -1, str(e)
    
    def _send_command_raw(self, command: str) -> None:
        """Send raw command to bash session"""
        if self.master_fd is None:
            raise RuntimeError("Bash session not started")
            
        command_bytes = (command + '\n').encode('utf-8')
        os.write(self.master_fd, command_bytes)
    
    def _read_available_output(self) -> str:
        """Read any available output without blocking"""
        if self.master_fd is None:
            return ""
            
        output = ""
        try:
            while True:
                ready, _, _ = select.select([self.master_fd], [], [], 0.1)
                if not ready:
                    break
                    
                data = os.read(self.master_fd, 4096)
                if not data:
                    break
                    
                output += data.decode('utf-8', errors='replace')
        except (OSError, ValueError):
            pass
            
        return output
    
    def _read_until_marker(self, end_marker: str, timeout: float) -> str:
        """Read output until end marker is found"""
        if self.master_fd is None:
            raise RuntimeError("Bash session not started")
            
        output = ""
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            try:
                ready, _, _ = select.select([self.master_fd], [], [], 0.1)
                if ready:
                    data = os.read(self.master_fd, 4096)
                    if data:
                        chunk = data.decode('utf-8', errors='replace')
                        output += chunk
                        
                        if end_marker in output:
                            break
                else:
                    # Check if process is still alive
                    if self.process and self.process.poll() is not None:
                        break
                        
            except (OSError, ValueError) as e:
                logger.warning(f"Error reading from bash session: {e}")
                break
        
        return output
    
    def _parse_command_output(self, output: str, start_marker: str, end_marker: str) -> Tuple[int, str]:
        """Parse command output to extract exit code and clean output"""
        try:
            # Find start and end markers
            start_idx = output.find(start_marker)
            end_idx = output.find(end_marker)
            
            if start_idx == -1 or end_idx == -1:
                return -1, output
            
            # Extract content between markers
            content = output[start_idx + len(start_marker):end_idx]
            
            # Find exit code
            exit_code = 0
            exit_code_marker = "__EXIT_CODE_"
            exit_code_idx = content.rfind(exit_code_marker)
            
            if exit_code_idx != -1:
                exit_code_line = content[exit_code_idx:]
                try:
                    exit_code_str = exit_code_line.split('__')[2]  # Extract number between __ markers
                    exit_code = int(exit_code_str)
                    # Remove exit code line from content
                    content = content[:exit_code_idx]
                except (IndexError, ValueError):
                    pass
            
            # Clean up the output
            clean_output = content.strip()
            
            # Remove ANSI escape sequences
            import re
            ansi_escape = re.compile(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])')
            clean_output = ansi_escape.sub('', clean_output)
            
            return exit_code, clean_output
            
        except Exception as e:
            logger.warning(f"Error parsing command output: {e}")
            return -1, output
    
    def stop(self) -> None:
        """Stop the bash session"""
        with self._lock:
            self._cleanup()
            self._started = False
    
    def _cleanup(self) -> None:
        """Clean up resources"""
        try:
            if self.process:
                self.process.terminate()
                try:
                    self.process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    self.process.kill()
                self.process = None
                
            if self.master_fd is not None:
                os.close(self.master_fd)
                self.master_fd = None
                
            if self.slave_fd is not None:
                os.close(self.slave_fd)
                self.slave_fd = None
                
        except Exception as e:
            logger.warning(f"Error during cleanup: {e}")
    
    def __del__(self):
        """Destructor to ensure cleanup"""
        self._cleanup()


class AsyncBashSession:
    """Async wrapper around BashSession"""
    
    def __init__(self, working_dir: str = "/workspace"):
        self.bash_session = BashSession(working_dir)
        self._executor = None
    
    async def start(self) -> None:
        """Start the async bash session"""
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(self._executor, self.bash_session.start)
    
    async def execute(self, command: str, timeout: float = 30.0) -> Tuple[int, str]:
        """Execute command asynchronously"""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            self._executor, 
            self.bash_session.execute, 
            command, 
            timeout
        )
    
    async def stop(self) -> None:
        """Stop the async bash session"""
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(self._executor, self.bash_session.stop)


# Global bash session for the action execution server
_global_bash_session: Optional[BashSession] = None


def get_global_bash_session(working_dir: str = "/workspace") -> BashSession:
    """Get or create the global bash session"""
    global _global_bash_session
    
    if _global_bash_session is None:
        _global_bash_session = BashSession(working_dir)
        _global_bash_session.start()
    
    return _global_bash_session


def execute_bash_command(command: str, working_dir: str = "/workspace", timeout: float = 30.0) -> Tuple[int, str]:
    """Execute a bash command using the global session"""
    session = get_global_bash_session(working_dir)
    return session.execute(command, timeout)
