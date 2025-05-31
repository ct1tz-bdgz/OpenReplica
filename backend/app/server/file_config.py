"""
File configuration for OpenReplica matching OpenHands exactly
"""

# Files and directories to ignore when listing workspace files
FILES_TO_IGNORE = {
    # System files
    '.DS_Store',
    'Thumbs.db',
    'desktop.ini',
    
    # Version control
    '.git',
    '.gitignore',
    '.gitmodules',
    '.gitattributes',
    
    # IDE and editor files
    '.vscode',
    '.idea',
    '*.swp',
    '*.swo',
    '*~',
    '.vimrc',
    '.editorconfig',
    
    # Python
    '__pycache__',
    '*.pyc',
    '*.pyo',
    '*.pyd',
    '.Python',
    'build/',
    'develop-eggs/',
    'dist/',
    'downloads/',
    'eggs/',
    '.eggs/',
    'lib/',
    'lib64/',
    'parts/',
    'sdist/',
    'var/',
    'wheels/',
    '*.egg-info/',
    '.installed.cfg',
    '*.egg',
    'MANIFEST',
    
    # Virtual environments
    'env/',
    'venv/',
    'ENV/',
    'env.bak/',
    'venv.bak/',
    '.env',
    '.venv',
    
    # Testing
    '.tox/',
    '.coverage',
    '.coverage.*',
    '.cache',
    'nosetests.xml',
    'coverage.xml',
    '*.cover',
    '.hypothesis/',
    '.pytest_cache/',
    'htmlcov/',
    
    # Documentation
    'docs/_build/',
    '.sphinx-build/',
    
    # Node.js
    'node_modules/',
    'npm-debug.log*',
    'yarn-debug.log*',
    'yarn-error.log*',
    '.npm',
    '.yarn-integrity',
    
    # Logs
    '*.log',
    'logs/',
    
    # OS generated files
    '.DS_Store?',
    '._*',
    '.Spotlight-V100',
    '.Trashes',
    'ehthumbs.db',
    
    # Temporary files
    '*.tmp',
    '*.temp',
    'tmp/',
    'temp/',
    
    # Binary files
    '*.so',
    '*.dylib',
    '*.dll',
    
    # Archives
    '*.zip',
    '*.tar.gz',
    '*.rar',
    
    # Docker
    'Dockerfile',
    '.dockerignore',
    'docker-compose.yml',
    'docker-compose.yaml',
    
    # Runtime specific
    '.openreplica/',
    '.openhands/',
    'runtime_logs/',
}

# Maximum file size for reading (in MB)
MAX_FILE_SIZE_MB = 10

# Allowed file extensions for editing
ALLOWED_EDIT_EXTENSIONS = {
    # Text files
    '.txt', '.md', '.rst', '.rtf',
    
    # Code files
    '.py', '.js', '.ts', '.jsx', '.tsx',
    '.html', '.htm', '.css', '.scss', '.sass', '.less',
    '.json', '.xml', '.yaml', '.yml', '.toml', '.ini',
    '.sh', '.bash', '.zsh', '.fish',
    '.sql', '.graphql', '.gql',
    '.dockerfile', '.dockerignore',
    
    # Configuration files
    '.conf', '.config', '.cfg', '.properties',
    '.env', '.env.example', '.env.local',
    '.gitignore', '.gitattributes',
    
    # Documentation
    '.tex', '.bib', '.wiki',
    
    # Data files
    '.csv', '.tsv', '.jsonl',
    
    # Programming languages
    '.c', '.cpp', '.cc', '.cxx', '.h', '.hpp',
    '.java', '.kt', '.scala',
    '.cs', '.vb', '.fs',
    '.go', '.rs', '.swift',
    '.php', '.rb', '.pl', '.r',
    '.lua', '.vim', '.el',
    '.clj', '.cljs', '.hs',
    '.ml', '.mli', '.ocaml',
    '.dart', '.elm',
    '.jl', '.nim',
    '.zig', '.odin',
    
    # Web technologies
    '.vue', '.svelte', '.astro',
    '.php', '.asp', '.aspx', '.jsp',
    
    # Build files
    'Makefile', 'makefile', '.make',
    'CMakeLists.txt', '.cmake',
    'build.gradle', 'pom.xml',
    'package.json', 'yarn.lock', 'package-lock.json',
    'requirements.txt', 'pyproject.toml', 'setup.py',
    'Cargo.toml', 'Cargo.lock',
    'go.mod', 'go.sum',
    
    # No extension (common for config files)
    '',
}

# Binary file extensions to exclude from text operations
BINARY_EXTENSIONS = {
    # Images
    '.jpg', '.jpeg', '.png', '.gif', '.bmp', '.svg', '.webp', '.ico',
    '.tiff', '.tif', '.psd', '.ai', '.eps',
    
    # Audio
    '.mp3', '.wav', '.flac', '.aac', '.ogg', '.m4a', '.wma',
    
    # Video
    '.mp4', '.avi', '.mkv', '.mov', '.wmv', '.flv', '.webm', '.m4v',
    
    # Archives
    '.zip', '.tar', '.gz', '.bz2', '.xz', '.7z', '.rar',
    
    # Executables
    '.exe', '.msi', '.dmg', '.pkg', '.deb', '.rpm',
    '.app', '.bin', '.run',
    
    # Libraries
    '.so', '.dll', '.dylib', '.a', '.lib',
    
    # Documents
    '.pdf', '.doc', '.docx', '.xls', '.xlsx', '.ppt', '.pptx',
    '.odt', '.ods', '.odp',
    
    # Fonts
    '.ttf', '.otf', '.woff', '.woff2', '.eot',
    
    # Database
    '.db', '.sqlite', '.sqlite3', '.mdb',
    
    # Compiled
    '.pyc', '.pyo', '.class', '.o', '.obj',
}


def is_file_ignored(file_path: str) -> bool:
    """Check if a file should be ignored"""
    import os
    
    file_name = os.path.basename(file_path)
    
    # Check exact matches
    if file_name in FILES_TO_IGNORE:
        return True
    
    # Check directory matches
    path_parts = file_path.split(os.sep)
    for part in path_parts:
        if part in FILES_TO_IGNORE:
            return True
    
    # Check if it's a hidden file (starts with .)
    if file_name.startswith('.') and file_name not in {'.env', '.gitignore', '.gitattributes'}:
        return True
    
    return False


def is_binary_file(file_path: str) -> bool:
    """Check if a file is binary based on extension"""
    import os
    
    _, ext = os.path.splitext(file_path.lower())
    return ext in BINARY_EXTENSIONS


def is_editable_file(file_path: str) -> bool:
    """Check if a file can be edited"""
    import os
    
    if is_binary_file(file_path):
        return False
    
    _, ext = os.path.splitext(file_path.lower())
    file_name = os.path.basename(file_path)
    
    # Allow files with allowed extensions
    if ext in ALLOWED_EDIT_EXTENSIONS:
        return True
    
    # Allow common config files without extensions
    config_files = {
        'Makefile', 'makefile', 'Dockerfile', 'Procfile',
        'LICENSE', 'README', 'CHANGELOG', 'CONTRIBUTING',
        'AUTHORS', 'CREDITS', 'INSTALL', 'NEWS', 'TODO'
    }
    
    if file_name in config_files:
        return True
    
    return False


def get_file_type(file_path: str) -> str:
    """Get file type category"""
    import os
    
    if is_binary_file(file_path):
        return 'binary'
    
    _, ext = os.path.splitext(file_path.lower())
    
    # Programming languages
    code_extensions = {
        '.py': 'python',
        '.js', '.jsx': 'javascript',
        '.ts', '.tsx': 'typescript',
        '.html', '.htm': 'html',
        '.css', '.scss', '.sass': 'css',
        '.json': 'json',
        '.xml': 'xml',
        '.yaml', '.yml': 'yaml',
        '.md': 'markdown',
        '.sh', '.bash': 'shell',
        '.sql': 'sql',
        '.c', '.h': 'c',
        '.cpp', '.cc', '.cxx', '.hpp': 'cpp',
        '.java': 'java',
        '.go': 'go',
        '.rs': 'rust',
        '.php': 'php',
        '.rb': 'ruby',
        '.swift': 'swift',
    }
    
    return code_extensions.get(ext, 'text')
