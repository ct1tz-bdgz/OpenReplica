#!/bin/bash

# OpenReplica Startup Script
# This script sets up and starts the complete OpenReplica system

set -e

echo "🙌 Welcome to OpenReplica - Code Less, Make More!"
echo "=================================================="

# Check if Python is installed
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3.9+ is required but not found. Please install Python first."
    exit 1
fi

# Check Python version
python_version=$(python3 --version 2>&1 | awk '{print $2}')
echo "✅ Found Python $python_version"

# Check if Node.js is installed
if ! command -v node &> /dev/null; then
    echo "❌ Node.js 18+ is required but not found. Please install Node.js first."
    exit 1
fi

# Check Node version
node_version=$(node --version)
echo "✅ Found Node.js $node_version"

# Check if Docker is running
if ! docker info > /dev/null 2>&1; then
    echo "⚠️  Docker is not running. Some features may not work."
    echo "   Please start Docker for full code execution capabilities."
else
    echo "✅ Docker is running"
fi

echo ""
echo "🔧 Setting up OpenReplica..."

# Create virtual environment if it doesn't exist
if [ ! -d ".venv" ]; then
    echo "📦 Creating Python virtual environment..."
    python3 -m venv .venv
fi

# Activate virtual environment
echo "🔗 Activating virtual environment..."
source .venv/bin/activate

# Install Python dependencies
echo "📥 Installing Python dependencies..."
pip install -q --upgrade pip
pip install -q -r requirements.txt

# Install frontend dependencies
echo "📥 Installing frontend dependencies..."
cd frontend
npm install --silent
cd ..

# Create .env file if it doesn't exist
if [ ! -f ".env" ]; then
    echo "⚙️  Creating environment configuration..."
    cat > .env << EOL
# OpenReplica Configuration
OPENREPLICA_DEBUG=true
OPENREPLICA_HOST=0.0.0.0
OPENREPLICA_PORT=3000

# Database
OPENREPLICA_DATABASE_URL=sqlite:///./openreplica.db

# LLM Configuration (Add your API keys here)
# OPENREPLICA_OPENAI_API_KEY=your_openai_key_here
# OPENREPLICA_ANTHROPIC_API_KEY=your_anthropic_key_here
OPENREPLICA_DEFAULT_LLM_PROVIDER=openai
OPENREPLICA_LLM_MODEL=gpt-4

# Docker Runtime
OPENREPLICA_DOCKER_ENABLED=true
OPENREPLICA_RUNTIME_IMAGE=python:3.11-slim

# Workspaces
OPENREPLICA_WORKSPACE_BASE=./workspaces
EOL
    echo "📝 Created .env file. Please add your API keys to use AI features."
fi

# Create workspaces directory
mkdir -p workspaces

# Initialize database
echo "🗄️  Initializing database..."
python -c "
import asyncio
from openreplica.database.connection import init_db
asyncio.run(init_db())
print('Database initialized successfully!')
"

echo ""
echo "🚀 Starting OpenReplica..."
echo ""
echo "📍 The application will be available at:"
echo "   Frontend: http://localhost:3000"
echo "   API Docs: http://localhost:3000/api/docs"
echo ""
echo "⏹️  Press Ctrl+C to stop the application"
echo ""

# Start both backend and frontend
if command -v concurrently &> /dev/null; then
    npm run dev
else
    echo "Installing concurrently for development..."
    npm install -g concurrently
    npm run dev
fi
