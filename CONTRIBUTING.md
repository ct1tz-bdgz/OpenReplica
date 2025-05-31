# Contributing to OpenReplica

Thank you for your interest in contributing to OpenReplica! This document provides guidelines and instructions for contributing to the project.

## 🚀 Getting Started

### Prerequisites

- **Python 3.9+** - For the backend
- **Node.js 18+** - For the frontend
- **Docker** - For code execution runtime (optional but recommended)
- **Git** - For version control

### Development Setup

1. **Clone the repository**:
   ```bash
   git clone https://github.com/your-username/OpenReplica.git
   cd OpenReplica
   ```

2. **Run the setup script**:
   ```bash
   # On Linux/macOS
   chmod +x start.sh
   ./start.sh
   
   # On Windows
   start.bat
   ```

3. **Add your API keys** to `.env`:
   ```bash
   OPENREPLICA_OPENAI_API_KEY=your_openai_key_here
   OPENREPLICA_ANTHROPIC_API_KEY=your_anthropic_key_here
   ```

## 🏗️ Project Structure

```
OpenReplica/
├── openreplica/           # Python backend
│   ├── core/              # Core configuration and utilities
│   ├── models/            # Database models
│   ├── events/            # Event system
│   ├── llm/               # LLM providers
│   ├── agents/            # AI agents
│   ├── runtime/           # Code execution runtime
│   ├── database/          # Database services
│   └── server/            # FastAPI server
├── frontend/              # React frontend
│   ├── src/
│   │   ├── components/    # React components
│   │   ├── pages/         # Page components
│   │   ├── store/         # State management
│   │   ├── hooks/         # Custom hooks
│   │   └── lib/           # Utilities
│   └── public/            # Static assets
├── tests/                 # Test files
└── docs/                  # Documentation
```

## 🔧 Development Guidelines

### Backend Development

- **Code Style**: Use `black` and `isort` for formatting
- **Type Hints**: Use Python type hints for all functions
- **Async/Await**: Use async patterns for I/O operations
- **Error Handling**: Use custom exceptions from `openreplica.core.exceptions`
- **Logging**: Use structured logging with `openreplica.core.logger`

### Frontend Development

- **Code Style**: Use ESLint and Prettier (configured)
- **TypeScript**: Use TypeScript for all components
- **Components**: Follow the component structure in `components/`
- **State Management**: Use Zustand for global state
- **Styling**: Use Tailwind CSS utility classes

### Testing

- **Backend**: Use `pytest` for testing
  ```bash
  python -m pytest tests/
  ```

- **Frontend**: Use Vitest for testing
  ```bash
  cd frontend && npm test
  ```

### Code Quality

Run the linting tools before submitting:

```bash
# Format backend code
black openreplica/
isort openreplica/

# Lint frontend code
cd frontend && npm run lint
```

## 📝 Pull Request Process

1. **Create a feature branch**:
   ```bash
   git checkout -b feature/your-feature-name
   ```

2. **Make your changes** following the guidelines above

3. **Test your changes**:
   ```bash
   npm run test
   ```

4. **Commit your changes**:
   ```bash
   git add .
   git commit -m "feat: add your feature description"
   ```

5. **Push to your fork**:
   ```bash
   git push origin feature/your-feature-name
   ```

6. **Create a Pull Request** with:
   - Clear description of changes
   - Screenshots for UI changes
   - Test results
   - Breaking change notes (if any)

## 🐛 Bug Reports

When reporting bugs, please include:

- **Environment**: OS, Python version, Node.js version
- **Steps to reproduce** the issue
- **Expected behavior**
- **Actual behavior**
- **Error messages** or logs
- **Screenshots** (for UI issues)

## ✨ Feature Requests

For feature requests, please:

- **Check existing issues** to avoid duplicates
- **Describe the problem** you're trying to solve
- **Propose a solution** with examples
- **Consider alternatives** you've evaluated

## 🎯 Areas for Contribution

We welcome contributions in these areas:

### Backend
- **New LLM Providers**: Add support for more LLM APIs
- **Agent Improvements**: Enhance the AI agent capabilities
- **Runtime Enhancements**: Improve code execution features
- **API Endpoints**: Add new functionality to the REST API
- **Performance**: Optimize database queries and async operations

### Frontend
- **UI Components**: Create reusable, beautiful components
- **Features**: Add new user-facing features
- **Accessibility**: Improve keyboard navigation and screen reader support
- **Mobile**: Enhance mobile responsiveness
- **Themes**: Create new color themes and customizations

### Documentation
- **User Guides**: Write tutorials and how-to guides
- **API Documentation**: Improve API endpoint documentation
- **Code Comments**: Add helpful code comments and docstrings
- **Examples**: Create example projects and use cases

### Testing
- **Unit Tests**: Add test coverage for backend functions
- **Integration Tests**: Test API endpoints and workflows
- **E2E Tests**: Add end-to-end frontend testing
- **Performance Tests**: Add benchmarking and load testing

## 🤝 Community Guidelines

- **Be respectful** and inclusive in all interactions
- **Help others** learn and grow
- **Give constructive feedback** on pull requests
- **Follow the code of conduct**
- **Ask questions** when you need help

## 📄 License

By contributing to OpenReplica, you agree that your contributions will be licensed under the MIT License.

## 🙏 Recognition

All contributors will be recognized in our README and release notes. Thank you for making OpenReplica better!

---

For questions about contributing, please open an issue or reach out to the maintainers.
