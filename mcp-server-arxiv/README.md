# MCP Server - Arxiv Search

This service provides an MCP-compliant server interface with a tool to search and retrieve papers from the [Arxiv](https://arxiv.org/) preprint repository. It is designed for use in multi-tool agent systems, but can also be run standalone.

---

## Features

- **MCP Tool:** `arxiv_search` for querying arXiv, downloading PDFs, and extracting text.
- **Async & Fast:** Uses async I/O and parallel PDF processing for speed.
- **Configurable:** Environment variables (via `.env` or system) control search/result limits.
- **Docker Support:** Ready-to-use Dockerfile for containerized deployment.
- **Client Example:** Shows how to use the server from Python, including with LangChain MCP adapters.
- **Modern Python:** Requires Python 3.11+ for async features.

---

## Directory Structure

```
mcp-server-arxiv/
├── src/mcp_server_arxiv/
│   ├── server.py         # Main MCP server, exposes the tool, handles requests
│   ├── __main__.py       # Entrypoint for running the server
│   ├── logging_config.py # Logging setup
│   └── arxiv/
│       ├── module.py     # Core logic for searching, downloading, extracting
│       ├── models.py     # Data models (e.g., ArxivSearchResult)
│       └── config.py     # Configuration and error classes
├── tests/                # Unit tests for server and module
│   ├── conftest.py       # Pytest configuration and fixtures
│   ├── test_server.py    # Tests for the MCP server functionality
│   └── test_module.py    # Tests for the arxiv module functionality
├── pyproject.toml        # Dependencies and build config
├── Dockerfile            # Containerization support
├── LICENSE               # MIT License
├── .gitignore            # Files/directories excluded from version control
└── README.md
```

---

## .gitignore and Excluded Files
---

## Requirements

- Python 3.11+
- No API key required (Arxiv is free to use)
- [uv](https://github.com/astral-sh/uv) (recommended for dependency management)

---

## Setup

1. **Clone the Repository:**
   - Place this directory within your `mcp-servers` project or clone it standalone.
2. **Create Environment File:**
   - Copy `.env.example` to `.env` and edit as needed (see Configuration section).
3. **Install Dependencies:**
   - It's recommended to use a virtual environment. Navigate to the `mcp-server-arxiv` directory.

   ```bash
   # Using uv (recommended)
   uv venv
   source .venv/bin/activate
   uv pip install -e .[dev]
   # Or using pip + venv
   # python -m venv .venv
   # source .venv/bin/activate
   # pip install -e .[dev]
   ```

---

## Running the Server

Ensure your virtual environment is activated and the `.env` file is present and configured.

```bash
# Run with default host (0.0.0.0) and port (8006)
python -m mcp_server_arxiv

# Run on a specific host/port
python -m mcp_server_arxiv --host 127.0.0.1 --port 8006
```

### Docker Support

```bash
# Build the Docker image
docker build -t mcp-server-arxiv .

# Run the container
docker run --rm -it -p 8006:8006 --env-file .env mcp-server-arxiv
```

---

## Running Tests and Coverage
The project includes a comprehensive suite of unit tests covering core functionality in module.py and server.py.

Tests mock external dependencies to ensure reliability and speed.

To run all tests with coverage and see detailed reports:
```bash
cd mcp-server-arxiv
pytest -v --color=yes --cov=mcp_server_arxiv --cov-report=term-missing --cov-fail-under=70

```
- This will fail if coverage is below 70%.
- Coverage reports show which lines are uncovered.

---
## API Usage

The server provides the following MCP tool:

- **Tool:** `arxiv_search`
  - **Parameters:**
    - `query` (str, required): Search query string
    - `max_results` (int, optional): Maximum number of results to return (default: 5, max: 50)
    - `max_text_length` (int, optional): Maximum characters of extracted text per paper (default: unlimited, min: 100)

**Example tool call input:**
```json
{
  "name": "arxiv_search",
  "arguments": {
    "query": "quantum entanglement communication",
    "max_results": 2,
    "max_text_length": 1500
  }
}
```

**Example output (truncated):**
```
--- Paper 1 ---
Title: Quantum Entanglement in Communication
Authors: Alice Smith, Bob Jones
Published: 2023-01-15
ArXiv ID: 2301.12345v1
PDF URL: https://arxiv.org/pdf/2301.12345v1
Summary: This paper explores...
Full Text Preview: [First 200 chars of extracted PDF text...]

--- Paper 2 ---
...
```

---

## Configuration

- Uses environment variables with the prefix `ARXIV_` (e.g., `ARXIV_DEFAULT_MAX_RESULTS`).
- Reads from `.env` file if present.
- Main config options:
  - `ARXIV_DEFAULT_MAX_RESULTS` (default: 5)
  - `ARXIV_DEFAULT_MAX_TEXT_LENGTH` (optional, min 100 chars)
- Dockerfile sets defaults for `MCP_ARXIV_PORT` and `MCP_ARXIV_HOST`.

---


## Troubleshooting

- **Missing dependencies:** Ensure you have Python 3.11+ and all dependencies installed (`uv pip install -e .[dev]`).
- **Docker networking:** If running the server in Docker, use `host.docker.internal` as the host for local clients.
- **PDF extraction errors:** Some arXiv PDFs may be image-based or malformed; errors are reported in the `processing_error` field of results.
- **Environment variables:** Double-check your `.env` file and variable names (see Configuration section).
- **.gitignore:** Review and update `.gitignore` if you add new generated or sensitive files.
- **uv.lock:** Commit this file if you want reproducible builds; otherwise, it can be regenerated.

---

## License

This project is licensed under the MIT License.
