@echo off
REM OpenReplica Startup Script for Windows
REM This script sets up and starts the complete OpenReplica system

echo 🙌 Welcome to OpenReplica - Code Less, Make More!
echo ==================================================

REM Check if Python is installed
python --version >nul 2>&1
if errorlevel 1 (
    echo ❌ Python 3.9+ is required but not found. Please install Python first.
    pause
    exit /b 1
)

echo ✅ Found Python
python --version

REM Check if Node.js is installed
node --version >nul 2>&1
if errorlevel 1 (
    echo ❌ Node.js 18+ is required but not found. Please install Node.js first.
    pause
    exit /b 1
)

echo ✅ Found Node.js
node --version

REM Check if Docker is running
docker info >nul 2>&1
if errorlevel 1 (
    echo ⚠️  Docker is not running. Some features may not work.
    echo    Please start Docker for full code execution capabilities.
) else (
    echo ✅ Docker is running
)

echo.
echo 🔧 Setting up OpenReplica...

REM Create virtual environment if it doesn't exist
if not exist ".venv" (
    echo 📦 Creating Python virtual environment...
    python -m venv .venv
)

REM Activate virtual environment
echo 🔗 Activating virtual environment...
call .venv\Scripts\activate.bat

REM Install Python dependencies
echo 📥 Installing Python dependencies...
pip install -q --upgrade pip
pip install -q -r requirements.txt

REM Install frontend dependencies
echo 📥 Installing frontend dependencies...
cd frontend
npm install --silent
cd ..

REM Create .env file if it doesn't exist
if not exist ".env" (
    echo ⚙️  Creating environment configuration...
    (
        echo # OpenReplica Configuration
        echo OPENREPLICA_DEBUG=true
        echo OPENREPLICA_HOST=0.0.0.0
        echo OPENREPLICA_PORT=3000
        echo.
        echo # Database
        echo OPENREPLICA_DATABASE_URL=sqlite:///./openreplica.db
        echo.
        echo # LLM Configuration ^(Add your API keys here^)
        echo # OPENREPLICA_OPENAI_API_KEY=your_openai_key_here
        echo # OPENREPLICA_ANTHROPIC_API_KEY=your_anthropic_key_here
        echo OPENREPLICA_DEFAULT_LLM_PROVIDER=openai
        echo OPENREPLICA_LLM_MODEL=gpt-4
        echo.
        echo # Docker Runtime
        echo OPENREPLICA_DOCKER_ENABLED=true
        echo OPENREPLICA_RUNTIME_IMAGE=python:3.11-slim
        echo.
        echo # Workspaces
        echo OPENREPLICA_WORKSPACE_BASE=./workspaces
    ) > .env
    echo 📝 Created .env file. Please add your API keys to use AI features.
)

REM Create workspaces directory
if not exist "workspaces" mkdir workspaces

REM Initialize database
echo 🗄️  Initializing database...
python -c "import asyncio; from openreplica.database.connection import init_db; asyncio.run(init_db()); print('Database initialized successfully!')"

echo.
echo 🚀 Starting OpenReplica...
echo.
echo 📍 The application will be available at:
echo    Frontend: http://localhost:3000
echo    API Docs: http://localhost:3000/api/docs
echo.
echo ⏹️  Press Ctrl+C to stop the application
echo.

REM Start both backend and frontend
npm run dev
