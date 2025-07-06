<div align="center">

<!--![MCP Servers Collection](image_placeholder) -->

# 🔌 MCP Servers Collection

*Production-ready [Model Context Protocol](https://modelcontextprotocol.io/introduction) servers with standardized architecture*

[![Docker](https://img.shields.io/badge/Docker-Ready-blue?logo=docker)](https://docker.com)
[![MCP](https://img.shields.io/badge/MCP-Compatible-green)](https://modelcontextprotocol.io)
[![Python](https://img.shields.io/badge/Python-3.12+-yellow?logo=python)](https://python.org)

</div>

## 🎯 **Why Choose Our MCP Servers?**

**Skip the learning curve** - Once you understand one server, you can instantly work with any of them. **Standardized architecture** across all the services states consistent patterns, predictable deployment, and maintainable code.

### 💡 **Built for Modern Development**

🏗️ **Self-contained** → Each server manages its own dependencies and configuration

🚀 **Production-ready** → Multi-stage Docker builds with optimized layer caching

⚡ **Full protocol support** → streamable_http, sse and stdio transports for maximum flexibility

📐 **Best practices built-in** → Comprehensive testing, linting, and error handling

### 🎯 **Perfect For**

**Teams** → Maintain consistency across your entire MCP infrastructure

**Developers** → Focus on business logic, not boilerplate setup

**Production** → Deploy with confidence using proven patterns

**Custom development** → Use our template to create new servers in minutes


## 🛠️ Available Servers

| Service | Description | Use Case |
|---------|-------------|----------|
| 📚 **arxiv** | Searches and retrieves academic papers | Research & academia |
| 🎙️ **cartesia** | Text-to-speech using Cartesia API | Voice synthesis |
| 🎨 **imgen** | Image generation via Google Vertex AI | Creative content |
| 🗄️ **postgres** | Database operations with PostgreSQL | Data storage |
| 🔍 **qdrant** | Vector database operations | Semantic search |
| 🎭 **stability** | Image generation via Stability AI SDXL | AI artwork |
| 🌐 **tavily** | Web search using Tavily API | Information gathering |
| 💬 **telegram** | Posts messages to Telegram channels | Messaging & notifications |
| 🐦 **twitter** | Twitter/X API interactions | Social media |
| 📖 **wikipedia** | Wikipedia article search & retrieval | Knowledge base |
| 📺 **youtube** | YouTube video transcript extraction | Content analysis |



## 🚀 Quick Start

### 📋 Prerequisites

- 🐳 Docker and Docker Compose
- ⚙️ Service-specific `.env` setup (see individual service READMEs)

### 🏃‍♂️ Running Services

```bash
# 🐙 Using Docker Compose (recommended)
docker-compose up -d                        # All services
docker-compose up mcp-server-youtube -d     # Specific service

# 🐳 Using Docker directly
cd mcp-server-youtube
docker build -t mcp-server-youtube .
docker run -p 8000:8000 --env-file .env mcp-server-youtube
```

---

## 🤝 Contributing

See [`CONTRIBUTING.md`](./CONTRIBUTING.md) for detailed development guidelines.

<div align="center">

**🌟 Star this repo if you find it useful! 🌟**

</div>
