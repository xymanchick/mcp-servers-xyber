# YouTube Search and Transcript API Documentation

## Overview

This API provides functionality to search YouTube videos and retrieve their transcripts. It uses the YouTube Data API v3 and YouTube Transcript API to fetch video information and transcripts respectively.

## API Endpoints

### 1. YouTube Search and Transcript

**Endpoint:** `POST /youtube_search_and_transcript`

**Description:** Search YouTube videos and retrieve their transcripts.

**Request Body:**
```json
{
    "request": {
        "query": "string",  // Search query (1-500 characters)
        "max_results": 5,   // Maximum number of results (1-20)
        "transcript_language": "en",  // Language code for transcript
        "published_after": "2025-01-01T00:00:00Z",  // ISO format date
        "published_before": "2025-12-31T23:59:59Z",  // ISO format date
        "order_by": "relevance"  // Sort order (relevance, date, viewCount, rating)
    }
}
```

**Response:**
```json
{
    "videos": [
        {
            "video_id": "string",
            "title": "string",
            "channel": "string",
            "published_at": "string",
            "thumbnail": "string",
            "description": "string",
            "transcript": "string | status message",
            "transcript_language": "string | null",
            "has_transcript": boolean
        }
    ]
}
```

**Transcript Status Messages:**
- When YouTube's anti-bot protection blocks transcript access, the response will include a status message instead of the transcript text.
- Status messages indicate why the transcript couldn't be retrieved and include the language code if available.
- Example status messages:
  - "Transcript available in en but currently blocked by YouTube's anti-bot protection"
  - "Transcripts disabled by video creator"
  - "Video unavailable"
  - "No transcripts available"
  - "Error accessing transcript: [error message]"

### 2. Server-Sent Events (SSE)

**Endpoint:** `GET /sse`

**Description:** Real-time updates for YouTube search results.

**Query Parameters:**
- `query`: Search query string

**Response:** Server-Sent Events stream with updates

## Error Responses

All endpoints return appropriate HTTP status codes with error details:

- **400 Bad Request:** Validation errors or malformed requests
  ```json
  {
      "error": "Validation failed",
      "details": [
          {
              "field": "string",
              "message": "string",
              "type": "string"
          }
      ],
      "code": "VALIDATION_ERROR"
  }
  ```

- **500 Internal Server Error:** Server-side errors
  ```json
  {
      "error": "An unexpected error occurred",
      "code": "SERVER_ERROR"
  }
  ```

## Supported Languages

The API supports the following languages for transcripts:
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

## Rate Limits

- Maximum 50 requests per minute
- Maximum 10,000 requests per day
- Maximum 20 results per search

## Security

- All endpoints require proper authentication
- Input validation using Pydantic schemas
- Rate limiting implemented
- Secure handling of YouTube API credentials

## Development Guidelines

### Setup

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Set environment variables:
```
YOUTUBE_API_KEY=your_api_key_here
```

3. Run the server:
```bash
python -m mcp_server_youtube
```

### Testing

The API includes comprehensive unit tests for:
- Input validation
- Error handling
- API endpoints
- Transcript retrieval

Run tests using:
```bash
pytest tests/
```

## Contributing

1. Fork the repository
2. Create your feature branch
3. Commit your changes
4. Push to the branch
5. Create a Pull Request

## License

This project is proprietary and confidential. Unauthorized disclosure or distribution is strictly prohibited.
