"""
File utilities for OpenReplica runtime
"""
import os
import shutil
from typing import List, Optional
from pathlib import Path

from app.core.logging import get_logger

logger = get_logger(__name__)


def read_lines(file_path: str, start_line: int = 1, end_line: Optional[int] = None) -> List[str]:
    """Read lines from a file"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()
        
        # Convert to 0-indexed
        start_idx = max(0, start_line - 1)
        end_idx = len(lines) if end_line is None else min(len(lines), end_line)
        
        return lines[start_idx:end_idx]
        
    except Exception as e:
        logger.error(f"Error reading lines from {file_path}: {e}")
        return []


def insert_lines(file_path: str, new_lines: List[str], insert_line: int) -> bool:
    """Insert lines into a file at specified line number"""
    try:
        # Read existing content
        if os.path.exists(file_path):
            with open(file_path, 'r', encoding='utf-8') as f:
                existing_lines = f.readlines()
        else:
            existing_lines = []
        
        # Convert to 0-indexed
        insert_idx = max(0, insert_line - 1)
        
        # Insert new lines
        for i, line in enumerate(new_lines):
            if not line.endswith('\n'):
                line += '\n'
            existing_lines.insert(insert_idx + i, line)
        
        # Write back to file
        with open(file_path, 'w', encoding='utf-8') as f:
            f.writelines(existing_lines)
        
        return True
        
    except Exception as e:
        logger.error(f"Error inserting lines into {file_path}: {e}")
        return False


def write_file(file_path: str, content: str, encoding: str = 'utf-8') -> bool:
    """Write content to a file"""
    try:
        # Ensure directory exists
        os.makedirs(os.path.dirname(file_path), exist_ok=True)
        
        with open(file_path, 'w', encoding=encoding) as f:
            f.write(content)
        
        return True
        
    except Exception as e:
        logger.error(f"Error writing to {file_path}: {e}")
        return False


def read_file(file_path: str, encoding: str = 'utf-8') -> Optional[str]:
    """Read content from a file"""
    try:
        with open(file_path, 'r', encoding=encoding) as f:
            return f.read()
            
    except UnicodeDecodeError:
        # Try with different encodings
        for alt_encoding in ['latin-1', 'cp1252', 'iso-8859-1']:
            try:
                with open(file_path, 'r', encoding=alt_encoding) as f:
                    return f.read()
            except UnicodeDecodeError:
                continue
        
        # If all encodings fail, read as binary and decode with errors='replace'
        try:
            with open(file_path, 'rb') as f:
                return f.read().decode('utf-8', errors='replace')
        except Exception as e:
            logger.error(f"Error reading {file_path}: {e}")
            return None
            
    except Exception as e:
        logger.error(f"Error reading {file_path}: {e}")
        return None


def copy_file(src: str, dst: str) -> bool:
    """Copy a file"""
    try:
        # Ensure destination directory exists
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        
        shutil.copy2(src, dst)
        return True
        
    except Exception as e:
        logger.error(f"Error copying {src} to {dst}: {e}")
        return False


def move_file(src: str, dst: str) -> bool:
    """Move a file"""
    try:
        # Ensure destination directory exists
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        
        shutil.move(src, dst)
        return True
        
    except Exception as e:
        logger.error(f"Error moving {src} to {dst}: {e}")
        return False


def delete_file(file_path: str) -> bool:
    """Delete a file or directory"""
    try:
        if os.path.isfile(file_path):
            os.remove(file_path)
        elif os.path.isdir(file_path):
            shutil.rmtree(file_path)
        else:
            logger.warning(f"Path does not exist: {file_path}")
            return False
            
        return True
        
    except Exception as e:
        logger.error(f"Error deleting {file_path}: {e}")
        return False


def create_directory(dir_path: str) -> bool:
    """Create a directory"""
    try:
        os.makedirs(dir_path, exist_ok=True)
        return True
        
    except Exception as e:
        logger.error(f"Error creating directory {dir_path}: {e}")
        return False


def list_files(dir_path: str, recursive: bool = False, show_hidden: bool = False) -> List[dict]:
    """List files in a directory"""
    try:
        files = []
        
        if recursive:
            for root, dirs, filenames in os.walk(dir_path):
                # Filter hidden directories if needed
                if not show_hidden:
                    dirs[:] = [d for d in dirs if not d.startswith('.')]
                
                for filename in filenames:
                    if not show_hidden and filename.startswith('.'):
                        continue
                        
                    file_path = os.path.join(root, filename)
                    rel_path = os.path.relpath(file_path, dir_path)
                    stat = os.stat(file_path)
                    
                    files.append({
                        'name': filename,
                        'path': rel_path,
                        'size': stat.st_size,
                        'modified': stat.st_mtime,
                        'is_directory': False,
                        'permissions': oct(stat.st_mode)[-3:],
                    })
                
                for dirname in dirs:
                    if not show_hidden and dirname.startswith('.'):
                        continue
                        
                    dir_full_path = os.path.join(root, dirname)
                    rel_path = os.path.relpath(dir_full_path, dir_path)
                    stat = os.stat(dir_full_path)
                    
                    files.append({
                        'name': dirname,
                        'path': rel_path,
                        'size': 0,
                        'modified': stat.st_mtime,
                        'is_directory': True,
                        'permissions': oct(stat.st_mode)[-3:],
                    })
        else:
            for item in os.listdir(dir_path):
                if not show_hidden and item.startswith('.'):
                    continue
                    
                item_path = os.path.join(dir_path, item)
                stat = os.stat(item_path)
                
                files.append({
                    'name': item,
                    'path': item,
                    'size': stat.st_size if os.path.isfile(item_path) else 0,
                    'modified': stat.st_mtime,
                    'is_directory': os.path.isdir(item_path),
                    'permissions': oct(stat.st_mode)[-3:],
                })
        
        return files
        
    except Exception as e:
        logger.error(f"Error listing files in {dir_path}: {e}")
        return []


def get_file_info(file_path: str) -> Optional[dict]:
    """Get information about a file"""
    try:
        if not os.path.exists(file_path):
            return None
            
        stat = os.stat(file_path)
        
        return {
            'name': os.path.basename(file_path),
            'path': file_path,
            'size': stat.st_size,
            'modified': stat.st_mtime,
            'created': stat.st_ctime,
            'is_directory': os.path.isdir(file_path),
            'is_file': os.path.isfile(file_path),
            'permissions': oct(stat.st_mode)[-3:],
            'owner': stat.st_uid,
            'group': stat.st_gid,
        }
        
    except Exception as e:
        logger.error(f"Error getting file info for {file_path}: {e}")
        return None


def search_files(directory: str, pattern: str, case_sensitive: bool = False, file_pattern: str = "*") -> List[dict]:
    """Search for text in files"""
    try:
        import re
        import fnmatch
        
        results = []
        
        # Compile regex pattern
        flags = 0 if case_sensitive else re.IGNORECASE
        regex = re.compile(pattern, flags)
        
        for root, dirs, files in os.walk(directory):
            for filename in files:
                # Check if file matches file pattern
                if not fnmatch.fnmatch(filename, file_pattern):
                    continue
                    
                file_path = os.path.join(root, filename)
                
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        for line_num, line in enumerate(f, 1):
                            if regex.search(line):
                                results.append({
                                    'file': os.path.relpath(file_path, directory),
                                    'line': line_num,
                                    'content': line.strip(),
                                    'match': pattern
                                })
                except (UnicodeDecodeError, PermissionError):
                    # Skip binary files or files we can't read
                    continue
        
        return results
        
    except Exception as e:
        logger.error(f"Error searching files: {e}")
        return []


def get_mime_type(file_path: str) -> str:
    """Get MIME type of a file"""
    try:
        import mimetypes
        mime_type, _ = mimetypes.guess_type(file_path)
        return mime_type or 'application/octet-stream'
    except Exception:
        return 'application/octet-stream'


def is_text_file(file_path: str) -> bool:
    """Check if a file is a text file"""
    try:
        mime_type = get_mime_type(file_path)
        return mime_type.startswith('text/') or mime_type in [
            'application/json',
            'application/xml',
            'application/javascript',
            'application/x-python-code',
        ]
    except Exception:
        return False


def is_binary_file(file_path: str) -> bool:
    """Check if a file is binary"""
    try:
        with open(file_path, 'rb') as f:
            chunk = f.read(1024)
            return b'\0' in chunk
    except Exception:
        return False


def get_file_extension(file_path: str) -> str:
    """Get file extension"""
    return Path(file_path).suffix.lower()


def get_file_size_human(size_bytes: int) -> str:
    """Convert file size to human readable format"""
    if size_bytes == 0:
        return "0 B"
    
    size_names = ["B", "KB", "MB", "GB", "TB"]
    i = 0
    while size_bytes >= 1024 and i < len(size_names) - 1:
        size_bytes /= 1024.0
        i += 1
    
    return f"{size_bytes:.1f} {size_names[i]}"
