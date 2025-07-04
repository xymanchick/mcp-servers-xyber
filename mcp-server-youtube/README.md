# MCP YouTube Server

> **General:** This repository implements an MCP (Model Context Protocol) server for YouTube search and transcript retrieval functionality.
> It allows language models or other agents to easily query YouTube content through a standardized protocol.

> **Documentation:**
> - [API Documentation](docs/api.md)
> - [Installation Guide](docs/installation.md)
> - [Development Guidelines](docs/development.md)
> - [Security Considerations](docs/security.md)

## Overview

This project provides a microservice that exposes YouTube video searching and transcript retrieval functionality through the Model Context Protocol (MCP). It uses the YouTube Data API v3 for searching videos and the `youtube-transcript-api` library for retrieving transcripts.

## Documentation

The complete documentation for this project is available in the [docs](docs/) directory. The following sections provide an overview of key features and usage:

### API Documentation
Detailed API endpoints, request/response formats, and error handling.

### Installation Guide
Step-by-step instructions for setting up and running the server.

### Development Guidelines
Best practices and guidelines for contributing to the project.

### Security Considerations
Important security measures and best practices.

## Input Validation and Error Handling

This server uses Pydantic v2 for robust input validation and structured error handling. All endpoints validate incoming requests and return clear, structured error responses for invalid inputs.

### Request Schema

The `youtube_search_and_transcript` endpoint expects the following request structure:

```python
{
    "request": {
        "query": str,  # Required, min_length=1, max_length=500
        "max_results": int,  # Required, default=5, min=1, max=20
        "transcript_language": str,  # Optional, must be valid ISO 639-1 code
        "published_after": str,  # Optional, ISO 8601 date-time
        "published_before": str,  # Optional, ISO 8601 date-time
        "order_by": str  # Optional, must be one of: 'relevance', 'date', 'viewCount', 'rating'
    }
}
```

### Response Format

The API returns a response with video information and transcript data. When YouTube's anti-bot protection blocks transcript access, the response will include a status message instead of the transcript text.

Example response with status message:
```python
{
    "videos": [
        {
            "video_id": "string",
            "title": "string",
            "channel": "string",
            "published_at": "string",
            "thumbnail": "string",
            "description": "string",
            "transcript": "Transcript available in en but currently blocked by YouTube's anti-bot protection",
            "transcript_language": "en",
            "has_transcript": false
        }
    ]
}
```

### Field Validation Rules

1. **Query**
   - Required field
   - Minimum length: 1 character
   - Maximum length: 500 characters
   - Must not be empty or whitespace only
   - Example: "Python programming tutorial"

2. **Max Results**
   - Required field
   - Default value: 5
   - Minimum value: 1
   - Maximum value: 20
   - Must be a valid integer
   - Example: 5

3. **Transcript Language**
   - Optional field
   - Must be a valid ISO 639-1 language code
   - Supported languages:
     - English (en)
     - Spanish (es)
     - French (fr)
     - German (de)
     - Portuguese (pt)
     - Italian (it)
     - Japanese (ja)
     - Korean (ko)
     - Russian (ru)
     - Chinese (zh)
   - Example: "en"

4. **Published After/Before**
   - Optional fields
   - Must be valid ISO 8601 date-time strings
   - Cannot be in the future
   - Supports both timezone-aware and naive timestamps
   - Naive timestamps are assumed to be UTC
   - Example: "2025-01-01T00:00:00Z" or "2025-01-01T00:00:00+01:00"

5. **Order By**
   - Optional field
   - Must be one of the following values (case-sensitive):
     - "relevance" (default)
     - "date"
     - "viewCount"
     - "rating"
   - Example: "date"

### Validation Error Responses

When validation fails, the server returns a structured error response with HTTP 400 status code:

```json
{
    "error": "Validation failed",
    "details": [
        {
            "field": "query",
            "message": "Query cannot be empty or whitespace only",
            "type": "query_empty"
        }
    ],
    "code": "VALIDATION_ERROR"
    "query": "Python programming tutorial",
    "max_results": 5
}
```

```json
{
    "query": "Machine learning basics",
    "max_results": 3,
    "transcript_language": "en",
    "published_after": "2025-01-01T00:00:00Z",
    "order_by": "relevance"
}
```

### Example Error Responses

```json
{
    "error": {
        "code": "EMPTY_QUERY",
        "message": "Query cannot be empty or whitespace only"
    }
}
```

```json
{
    "error": {
        "code": "INVALID_LANGUAGE",
        "message": "Language code must contain only letters"
    }
}
```

### Performance Considerations

1. **Rate Limiting**
   - The server may implement rate limiting for excessive requests
   - Large queries or result sets may be throttled

2. **Input Size Limits**
   - Maximum query length: 500 characters
   - Maximum results: 20 per request
   - Large payloads may be rejected with HTTP 413 (Payload Too Large)

3. **Error Handling**
   - All validation errors return HTTP 400 (Bad Request)
   - Malformed inputs return HTTP 400 with specific error codes
   - Server errors return HTTP 500 with error details
    "max_results": int = 3,  # Optional, range: 1-20
    "transcript_language": str = "en"  # Optional, supported languages: en, es, fr, de, pt, it, ja, ko, ru, zh
}
```

### Validation Rules

#### Query Validation
- Must be a non-empty string (1-500 characters)
- Cannot contain only whitespace
- Must not exceed 500 characters

#### Results Validation
- Must be an integer between 1 and 20
- Default value is 3
- Cannot be less than 1 or greater than 20

#### Language Validation
- Must be a valid ISO 639-1 or ISO 639-2 language code
- Supported languages:
  - English (en)
  - Spanish (es)
  - French (fr)
  - German (de)
  - Portuguese (pt)
  - Italian (it)
  - Japanese (ja)
  - Korean (ko)
  - Russian (ru)
  - Chinese (zh)

### Response Schema

All successful responses will follow this structure:

```python
{
    "title": str,  # Video title (1-500 chars)
    "description": str,  # Video description (optional, max 5000 chars)
    "publish_date": datetime,  # ISO 8601 format
    "transcript": str,  # Transcript text (optional, max 100,000 chars)
    "video_url": str,  # Valid YouTube video URL
    "thumbnail_url": str,  # Valid YouTube thumbnail URL
    "channel_name": str,  # Channel name (1-100 chars)
    "channel_url": str,  # Valid YouTube channel URL
    "view_count": int,  # Number of views (optional, 0-1,000,000,000)
    "like_count": int,  # Number of likes (optional, 0-1,000,000,000)
    "duration": str  # ISO 8601 duration format (e.g., PT1H23M45S)
}
```

### Error Handling

Invalid requests will return a 400 Bad Request error with a descriptive message. Common validation errors include:

- "Query cannot be empty or whitespace only"
- "Query cannot exceed 500 characters"
- "Language code must be between 2 and 5 characters"
- "Invalid language code"
- "Max results must be between 1 and 20"

### Example Valid Request

```json
{
    "query": "Python programming tutorial",
    "max_results": 5,
    "transcript_language": "en"
}
```

### Example Error Response

```json
{
    "error": "Invalid input: Query cannot be empty or whitespace only",
    "status_code": 400
}
```

## MCP Tools:

1. `youtube_search_and_transcript`
    - **Description:** Searches YouTube for videos and retrieves their transcripts
    - **Input:**
        - `query` (string, required): The search query string for YouTube videos
        - `max_results` (integer, optional, default: 3, min: 1, max: 20): Maximum number of video results
        - `transcript_language` (string, optional, default: 'en'): Desired transcript language code
    - **Output:** A string containing formatted results with video details and transcripts


## Requirements

- Python 3.12+
- uv (for dependency management)
- Docker (optional, for containerization)
- YouTube Data API Key

## Setup

1. **Clone the Repository**:
   ```bash
   git clone <repository-url>
   cd mcp-server-youtube
   ```

2. **Create `.env` File**:
   ```dotenv
   YOUTUBE_API_KEY="YOUR_YOUTUBE_API_KEY_HERE"
   MCP_YOUTUBE_HOST="127.0.0.1"
   MCP_YOUTUBE_PORT=8000
   LOGGING_LEVEL="info"
   ```

3. **Install Dependencies**:
   ```bash
   uv sync .
   ```

## Running the Server

### Locally

```bash
# Basic run
python -m mcp_server_youtube

# Custom port and host
python -m mcp_server_youtube --host 0.0.0.0 --port 8000
```

### Using Docker

```bash
# Build the image
docker build -t mcp-server-youtube .

# Run the container
docker run --rm -it -p 8000:8000 --env-file .env mcp-server-youtube
```

## Example Client

This example demonstrates using the YouTube service with a LangGraph ReAct agent:

```python
import os
import asyncio
from dotenv import load_dotenv
from langchain_mcp_adapters.client import MultiServerMCPClient
from langgraph.prebuilt import create_react_agent
from langchain_openai import ChatOpenAI

async def main():
    # Load environment variables
    load_dotenv()

    # Initialize LLM
    model = ChatOpenAI(model="gpt-4")

    # Connect to MCP server
    async with MultiServerMCPClient({
        "youtube_search_and_transcript": {
            "url": "http://localhost:8000/sse",
            "transport": "sse",
        }
    }) as client:
        # Get available tools
        tools = client.get_tools()

        # Create ReAct agent
        agent = create_react_agent(model, tools)

        # Example query
        response = await agent.ainvoke({
            "messages": [{
                "role": "user",
                "content": "Find recent videos about quantum computing breakthroughs"
            }]
        })

        print(response["messages"][-1].content)

if __name__ == "__main__":
    asyncio.run(main())
```

## Project Structure

```
mcp-server-youtube/
├── src/
│   └── mcp_server_youtube/
│       └── youtube/
│           ├── __init__.py
│           ├── config.py
│           ├── module.py
│       ├── __init__.py
│       ├── __main__.py
│       ├── logging_config.py
│       ├── server.py
├── .env.example
├── .gitignore
├── Dockerfile
├── LICENSE
├── pyproject.toml
├── README.md
└── uv.lock
```

## Contributing

1. Fork the repository
2. Create your feature branch
3. Commit your changes
4. Push to the branch
5. Create a Pull Request

## License

MIT
