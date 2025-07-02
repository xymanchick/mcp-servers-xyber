# Installation Guide

## Prerequisites

- Python 3.10 or higher
- pip package manager
- Virtual environment (recommended)
- YouTube Data API v3 credentials

## Installation Steps

### 1. Create Virtual Environment

```bash
# Create virtual environment
python -m venv .venv

# Activate virtual environment
source .venv/bin/activate  # On Unix/macOS
.venv\Scripts\activate     # On Windows
```

### 2. Install Dependencies

```bash
# Install project dependencies
pip install -r requirements.txt
```

### 3. Configure Environment

Create a `.env` file in the project root with the following content:

```
YOUTUBE_API_KEY=your_api_key_here
```

### 4. Run the Server

```bash
# Run the development server
python -m mcp_server_youtube

# The server will start on http://0.0.0.0:8000
```

## Development Setup

### 1. Install Development Dependencies

```bash
pip install -r requirements-dev.txt
```

### 2. Run Tests

```bash
pytest tests/
```

### 3. Run Linting

```bash
pre-commit run --all-files
```

## Docker Setup

### Build Docker Image

```bash
docker build -t mcp-server-youtube .
```

### Run Docker Container

```bash
docker run -d -p 8000:8000 -e YOUTUBE_API_KEY=your_api_key_here mcp-server-youtube
```

## Troubleshooting

### Common Issues

1. **Missing API Key**
   - Ensure `YOUTUBE_API_KEY` is set in environment variables
   - Check API key permissions in Google Cloud Console

2. **Rate Limit Exceeded**
   - Wait for the rate limit to reset
   - Consider implementing caching for frequent requests

3. **Validation Errors**
   - Check request payload against API documentation
   - Ensure all required fields are present
   - Verify field types and constraints

### Logging

The server logs are located in:
- `logs/server.log` - Main server logs
- `logs/error.log` - Error logs
- `logs/access.log` - Access logs

## Security Considerations

1. **API Key Security**
   - Never commit API keys to version control
   - Use environment variables or secure vaults
   - Rotate API keys periodically

2. **Input Validation**
   - All inputs are validated using Pydantic schemas
   - Never trust user input without validation
   - Implement proper error handling

3. **Rate Limiting**
   - Implement rate limiting to prevent abuse
   - Monitor API usage patterns
   - Set appropriate limits based on usage
