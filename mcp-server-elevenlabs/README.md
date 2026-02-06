# ElevenLabs MCP Server
> **General:** An MCP (Model Context Protocol) server for ElevenLabs Text-to-Speech generation.

## Capabilities

### 1. **API-Only Endpoints** (`/api`)

| Method | Endpoint       | Description               |
| :----- | :------------- | :------------------------ |
| `GET`  | `/api/health`  | Health check              |

### 2. **Hybrid Endpoints** (`/hybrid`)

These are exposed as both REST endpoints and MCP tools.

| Method/Tool                | Description                                  |
| :------------------------- | :------------------------------------------- |
| `elevenlabs_generate_voice`| Generate an MP3 audio file from text         |

### 3. **Downloads**

| Method | Endpoint                    | Description               |
| :----- | :-------------------------- | :------------------------ |
| `GET`  | `/hybrid/audio/{filename}`  | Download generated audio  |

## API Documentation

Once the server is running:

- **Swagger UI**: `http://localhost:8000/docs`
- **MCP endpoint**: `http://localhost:8000/mcp`

## Requirements

- **Python 3.12+**
- **UV** (dependency management)
- **Docker** (optional)
- **ElevenLabs API Key**

## Setup

```bash
# path: ./mcp-servers/mcp-server-elevenlabs/
uv sync
```

## Configuration

Create a `.env` file (see `.example.env`):

```env
ELEVENLABS_API_KEY=your_api_key
ELEVENLABS_VOICE_ID=optional_default_voice_id
ELEVENLABS_MODEL_ID=optional_default_model_id
LOGGING_LEVEL=INFO
```

## Running the Server

### Locally

```bash
# Basic run
uv run --python 3.12 python -m mcp_server_elevenlabs

# Or use the helper script
./scripts/start-server.sh
```

### Using Docker

```bash
# Build the image
docker build -t mcp-server-elevenlabs .

# Run the container (mount media dir for persistence)
docker run --rm -it -p 8000:8000 -v $(pwd)/voice:/app/media/voice mcp-server-elevenlabs
```

## Project Structure

```
mcp-server-elevenlabs/
├── src/
│   └── mcp_server_elevenlabs/
│       ├── __main__.py              # Entry point (uvicorn)
│       ├── app.py                   # Application factory (REST + MCP)
│       ├── config.py                # Settings (.env support)
│       ├── logging_config.py        # Uvicorn logging configuration
│       ├── schemas.py               # Pydantic request/response models
│       ├── api_routers/             # API-only routes (REST)
│       ├── hybrid_routers/          # Hybrid routes (REST + MCP)
│       ├── mcp_routers/             # MCP-only routes (optional)
│       └── elevenlabs/              # Business logic layer
├── scripts/
├── Dockerfile
├── pyproject.toml
├── tool_pricing.yaml
└── uv.lock
```
