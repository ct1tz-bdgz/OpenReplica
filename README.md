# 🙌 OpenReplica

**Code Less, Make More** - A beautiful replica of OpenHands with enhanced UI and full feature parity.

## ✨ Features

- 🤖 **AI-Powered Coding Assistant** - Advanced AI agents that understand and write code
- 🐳 **Secure Docker Runtime** - Isolated execution environment for safe code running
- 💬 **Real-time Chat Interface** - Smooth WebSocket communication with your AI assistant
- 📊 **Beautiful Dashboard** - Modern, intuitive UI that surpasses the original
- 🔧 **Multi-LLM Support** - Works with OpenAI, Anthropic, and other providers
- 🚀 **Fast Performance** - Optimized backend with async operations
- 🎨 **Stunning Design** - Beautiful, responsive interface with smooth animations

## 🚀 Quick Start

### Using Docker (Recommended)

```bash
docker pull openreplica/app:latest

docker run -it --rm --pull=always \
    -e OPENAI_API_KEY=your_key_here \
    -v /var/run/docker.sock:/var/run/docker.sock \
    -v ~/.openreplica-state:/.openreplica-state \
    -p 3000:3000 \
    --add-host host.docker.internal:host-gateway \
    --name openreplica-app \
    openreplica/app:latest
```

Visit [http://localhost:3000](http://localhost:3000) to start coding!

### Local Development

```bash
# Clone the repository
git clone https://github.com/your-username/OpenReplica.git
cd OpenReplica

# Install backend dependencies
pip install -r requirements.txt

# Install frontend dependencies
cd frontend
npm install
cd ..

# Start the application
python -m openreplica.server
```

## 🏗️ Architecture

OpenReplica consists of:

- **Backend**: FastAPI server with AI agent system, Docker runtime, and WebSocket API
- **Frontend**: Modern React/Next.js application with beautiful UI components
- **Runtime**: Secure Docker containers for code execution
- **Database**: SQLAlchemy with support for PostgreSQL, SQLite, and more

## 📖 Documentation

- [Installation Guide](docs/installation.md)
- [Configuration](docs/configuration.md)
- [API Reference](docs/api.md)
- [Development Guide](docs/development.md)

## 🤝 Contributing

We welcome contributions! Please see our [Contributing Guide](CONTRIBUTING.md).

## 📄 License

MIT License - see [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

Inspired by the excellent work of the [OpenHands](https://github.com/All-Hands-AI/OpenHands) team.
