<div align="center">

# 🤝 Contributing to MCP Servers

*Thank you for contributing to the MCP Servers project!*

🚀 This guide will help you set up your development environment and understand our workflow.

</div>

---

## 🛠️ Development Setup

### 🎯 Quick Start

**1️⃣ Navigate to the service you want to work on:**
```bash
cd mcp-server-{service-name}
```

**2️⃣ Install dependencies:**
```bash
uv sync
```

**3️⃣ Set up development tools (recommended):**
```bash
# Copy the pre-commit template
cp ../.pre-commit-config.template.yaml .pre-commit-config.yaml

# Install pre-commit hooks
uv run pre-commit install
```

**4️⃣ Configure your environment:**
```bash
cp .env.example .env
# Edit .env with your API keys and configuration
```

**5️⃣ Verify everything works:**
```bash
uv run pytest                    # Run tests
uv run pre-commit run --all-files # Check code quality
```

---

## 📐 Repository Structure & Code Quality

### 📁 Standard Service Structure
```
mcp-server-{name}/
├── src/
│   └── mcp_server_{name}/
│       ├── __init__.py
│       ├── __main__.py          # Entry point
│       ├── server.py            # MCP server implementation
│       ├── logging_config.py    # Logging setup
│       └── {name}/              # Service-specific logic
│           ├── __init__.py
│           ├── config.py        # Configuration management
│           ├── module.py        # Main business logic
│           └── models.py        # Data models (if needed)
├── tests/                       # Test files
├── Dockerfile                   # Multi-stage build (dev & prod)
├── pyproject.toml              # Dependencies & tool config
├── uv.lock                     # Locked dependencies
├── README.md                   # Service documentation
└── .env.example                # Environment template
```
#### ⚙️ Configuration Management
- Store all config in `{service}/config.py`
- Place credentials or sensitive data only in .env and NEVER COMMIT IT
- Use environment variables with `.env.example` template
- Validate configuration with Pydantic `BaseSettings`

#### 🚨 Error Handling
- Create service-specific exception hierarchies
- Log errors with sufficient context for debugging
- Handle external API failures gracefully with retries
- Provide helpful error messages to users

#### 🧪 Testing Strategy
- Use `pytest` with fixtures for common setup patterns
- Mock all external API calls and dependencies
- Test both success and failure scenarios
- Include integration tests for critical workflows


#### 📊 Code Quality Standards

```bash
# 🔄 Run all quality checks (recommended)
uv run pre-commit run --all-files

# 🖐️ Or run individually
uv run ruff check .              # Linting
uv run ruff format .             # Code formatting
uv run mypy .                    # Type checking
uv run pytest                    # Run tests
```

---

## 🔧 Working on the Repository

### 🐳 Docker Development

All services include **multi-stage Dockerfiles** with development targets:

```bash
# 🔄 Develop with hot-reload and debugging
docker-compose -f docker-compose.debug.yml up mcp_server_{name}
```

### ➕ Adding a New Service

**1️⃣ Create and set up the service:**
```bash
# Create directory
mkdir mcp-server-{name}
cd mcp-server-{name}
```

**2️⃣ Copy file structure from mcp-server-template:**
- ❓ Customize every file inside according to hints
- 📦 Customize `pyproject.toml` with service dependencies

**3️⃣ Add to root integration:**
```yaml
# Add to docker-compose.yml
mcp_server_{name}:
  build:
    context: ./mcp-server-{name}
    dockerfile: Dockerfile
  # ... rest of configuration
```

**4️⃣ Documentation:**
- 📝 Update root README.md with service description
- 📚 Create comprehensive service README.md
- 🏷️ Add to services table with emoji and use case

---

## 🤝 Contributing Back

### 📝 Pull Request Guidelines

🎯 **Scope**: Focus on a single service unless making cross-cutting changes
🧪 **Testing**: Include tests for new functionality and verify existing tests pass
📚 **Documentation**: Update README.md files and add clear docstrings
✅ **Quality**: Ensure all pre-commit checks pass
🐳 **Docker**: Verify both development and production builds work
📖 **Description**: Clearly explain what the change does and why it's needed

### 🆘 Getting Help

💡 **Service-specific questions**: Check individual service READMEs
👀 **Code patterns**: Review existing services for established patterns
🐛 **Issues**: Open a GitHub issue for architecture or workflow questions
📞 **Quick help**: Look at similar implementations in other services

---

<div align="center">

**🙏 Thank you for contributing! 🙏**

*Every contribution helps make this project better for everyone.*

</div>
