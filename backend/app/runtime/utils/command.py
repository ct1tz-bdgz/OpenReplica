"""
Command utilities for OpenReplica runtime
"""
import os
import shutil
from typing import List, Optional

DEFAULT_MAIN_MODULE = "app.runtime.action_execution_server"


def get_action_execution_server_startup_command(
    working_dir: str = "/workspace",
    port: int = 8000,
    api_key: Optional[str] = None,
    main_module: str = DEFAULT_MAIN_MODULE
) -> List[str]:
    """Get the command to start the action execution server"""
    
    cmd = [
        "python", "-m", main_module,
        "--host", "0.0.0.0",
        "--port", str(port),
        "--working-dir", working_dir,
        "--log-level", "INFO"
    ]
    
    if api_key:
        cmd.extend(["--api-key", api_key])
    
    return cmd


def get_vscode_startup_command(
    working_dir: str = "/workspace",
    port: int = 8080,
    extensions: Optional[List[str]] = None
) -> List[str]:
    """Get the command to start VS Code server"""
    
    cmd = [
        "code-server",
        "--bind-addr", f"0.0.0.0:{port}",
        "--auth", "none",
        "--disable-telemetry",
        "--disable-update-check",
        working_dir
    ]
    
    if extensions:
        for ext in extensions:
            cmd.extend(["--install-extension", ext])
    
    return cmd


def get_jupyter_startup_command(
    working_dir: str = "/workspace",
    port: int = 8888,
    token: Optional[str] = None
) -> List[str]:
    """Get the command to start Jupyter server"""
    
    cmd = [
        "jupyter", "lab",
        "--ip", "0.0.0.0",
        "--port", str(port),
        "--no-browser",
        "--allow-root",
        "--notebook-dir", working_dir
    ]
    
    if token:
        cmd.extend(["--ServerApp.token", token])
    else:
        cmd.extend(["--ServerApp.token", ""])
    
    return cmd


def find_available_tcp_port(start_port: int = 8000, end_port: int = 9000) -> int:
    """Find an available TCP port in the given range"""
    import socket
    
    for port in range(start_port, end_port + 1):
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
                sock.bind(('', port))
                return port
        except OSError:
            continue
    
    raise RuntimeError(f"No available ports in range {start_port}-{end_port}")


def check_docker_available() -> bool:
    """Check if Docker is available"""
    return shutil.which("docker") is not None


def check_command_available(command: str) -> bool:
    """Check if a command is available in PATH"""
    return shutil.which(command) is not None


def get_system_info() -> dict:
    """Get system information"""
    import platform
    import psutil
    
    return {
        "platform": platform.platform(),
        "architecture": platform.architecture(),
        "processor": platform.processor(),
        "python_version": platform.python_version(),
        "cpu_count": psutil.cpu_count(),
        "memory_total": psutil.virtual_memory().total,
        "disk_usage": psutil.disk_usage('/').total if os.path.exists('/') else 0,
        "docker_available": check_docker_available(),
    }


def validate_working_directory(working_dir: str) -> bool:
    """Validate that working directory exists and is writable"""
    try:
        if not os.path.exists(working_dir):
            os.makedirs(working_dir, exist_ok=True)
        
        # Test write access
        test_file = os.path.join(working_dir, ".test_write")
        with open(test_file, 'w') as f:
            f.write("test")
        os.remove(test_file)
        
        return True
    except Exception:
        return False


def setup_runtime_environment(working_dir: str = "/workspace") -> bool:
    """Setup the runtime environment"""
    try:
        # Validate working directory
        if not validate_working_directory(working_dir):
            return False
        
        # Create common directories
        common_dirs = [
            os.path.join(working_dir, "src"),
            os.path.join(working_dir, "tests"),
            os.path.join(working_dir, "docs"),
            os.path.join(working_dir, "tmp"),
            os.path.join(working_dir, ".vscode"),
        ]
        
        for dir_path in common_dirs:
            os.makedirs(dir_path, exist_ok=True)
        
        # Create .gitignore if it doesn't exist
        gitignore_path = os.path.join(working_dir, ".gitignore")
        if not os.path.exists(gitignore_path):
            gitignore_content = """
# Common files to ignore
__pycache__/
*.pyc
*.pyo
*.pyd
.Python
env/
venv/
.env
.venv
pip-log.txt
pip-delete-this-directory.txt
.tox
.coverage
.coverage.*
.cache
nosetests.xml
coverage.xml
*.cover
*.log
.git
.mypy_cache
.pytest_cache
.hypothesis

# IDE files
.vscode/
.idea/
*.swp
*.swo
*~

# OS files
.DS_Store
.DS_Store?
._*
.Spotlight-V100
.Trashes
ehthumbs.db
Thumbs.db

# Temporary files
tmp/
temp/
*.tmp
*.temp
"""
            with open(gitignore_path, 'w') as f:
                f.write(gitignore_content.strip())
        
        return True
        
    except Exception as e:
        print(f"Error setting up runtime environment: {e}")
        return False


def get_default_shell() -> str:
    """Get the default shell for the system"""
    import platform
    
    if platform.system() == "Windows":
        return "powershell.exe"
    else:
        return os.environ.get("SHELL", "/bin/bash")


def escape_shell_argument(arg: str) -> str:
    """Escape a shell argument for safe execution"""
    import shlex
    return shlex.quote(arg)


def build_shell_command(command: List[str]) -> str:
    """Build a shell command from a list of arguments"""
    return " ".join(escape_shell_argument(arg) for arg in command)


def get_environment_variables() -> dict:
    """Get common environment variables for runtime"""
    return {
        "PYTHONUNBUFFERED": "1",
        "PYTHONIOENCODING": "utf-8",
        "DEBIAN_FRONTEND": "noninteractive",
        "TERM": "xterm-256color",
        "SHELL": "/bin/bash",
        "USER": "openreplica",
        "HOME": "/home/openreplica",
    }
