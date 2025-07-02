import pytest
from fastapi.testclient import TestClient
from mcp_server_youtube.main import app
from mcp_server_youtube.schemas import YouTubeSearchRequest
from datetime import datetime, timezone, timedelta
from pydantic import ValidationError

client = TestClient(app)


def test_valid_request_minimal():
    """Test minimal valid request with required fields only."""
    response = client.post(
        "/mcp/youtube_search_and_transcript",
        json={
            "request": {
                "query": "python programming",
                "max_results": 3
            }
        }
    )
    assert response.status_code == 200, f"Response status: {response.status_code}, Content: {response.json()}"
    data = response.json()
    assert "results" in data
    assert len(data["results"]) <= 3
    
    # Verify response structure
    for result in data["results"]:
        assert "video_id" in result
        assert "title" in result
        assert "channel" in result
        assert "published_at" in result
        assert "thumbnail" in result
        assert "description" in result
        assert "transcript" in result

def test_valid_request_with_language():
    """Test valid request with transcript language."""
    response = client.post(
        "/mcp/youtube_search_and_transcript",
        json={
            "request": {
                "query": "python programming",
                "max_results": 5,
                "transcript_language": "en"
            }
        }
    )
    assert response.status_code == 200, f"Response status: {response.status_code}, Content: {response.json()}"
    data = response.json()
    assert "results" in data
    assert len(data["results"]) <= 5

def test_valid_request_with_dates():
    """Test valid request with date filters."""
    response = client.post(
        "/mcp/youtube_search_and_transcript",
        json={
            "request": {
                "query": "python programming",
                "max_results": 5,
                "published_after": "2025-01-01T00:00:00Z",
                "published_before": "2025-12-31T23:59:59Z"
            }
        }
    )
    assert response.status_code == 200, f"Response status: {response.status_code}, Content: {response.json()}"
    data = response.json()
    assert "results" in data
    assert len(data["results"]) <= 5

def test_valid_request_with_order_by():
    """Test valid request with order_by parameter."""
    for order_by in ["relevance", "date", "viewCount", "rating"]:
        response = client.post(
            "/mcp/youtube_search_and_transcript",
            json={
                "request": {
                    "query": "python programming",
                    "max_results": 5,
                    "order_by": order_by
                }
            }
        )
        assert response.status_code == 200, f"Response status: {response.status_code}, Content: {response.json()}"
        data = response.json()
        assert "results" in data
        assert len(data["results"]) <= 5

def test_valid_request_with_all_options():
    """Test valid request with all optional parameters."""
    response = client.post(
        "/mcp/youtube_search_and_transcript",
        json={
            "request": {
                "query": "python programming",
                "max_results": 10,
                "transcript_language": "en",
                "published_after": "2025-01-01T00:00:00Z",
                "published_before": "2025-12-31T23:59:59Z",
                "order_by": "relevance"
            }
        }
    )
    assert response.status_code == 200, f"Response status: {response.status_code}, Content: {response.json()}"
    data = response.json()
    assert "results" in data
    assert len(data["results"]) <= 10
    
    # Verify all fields are present in results
    for result in data["results"]:
        assert "video_id" in result
        assert "title" in result
        assert "channel" in result
        assert "published_at" in result
        assert "thumbnail" in result
        assert "description" in result
        assert "transcript" in result

def test_valid_request_with_default_max_results():
    """Test valid request using default max_results."""
    response = client.post(
        "/mcp/youtube_search_and_transcript",
        json={
            "request": {
                "query": "python programming",
                "max_results": 5
            }
        }
    )
    assert response.status_code == 200, f"Response status: {response.status_code}, Content: {response.json()}"
    data = response.json()
    assert "results" in data
    assert len(data["results"]) <= 5


def test_empty_query():
    """Test request with empty query."""
    response = client.post(
        "/mcp/youtube_search_and_transcript",
        json={
            "request": {
                "query": "",
                "max_results": 5
            }
        }
    )
    assert response.status_code == 400
    data = response.json()
    assert "error" in data
    assert "details" in data
    assert any("query" in err["field"] for err in data["details"])


def test_whitespace_query():
    """Test request with whitespace-only query."""
    response = client.post(
        "/mcp/youtube_search_and_transcript",
        json={
            "request": {
                "query": "   ",
                "max_results": 5
            }
        }
    )
    assert response.status_code == 400
    data = response.json()
    assert "error" in data
    assert "details" in data
    assert any("query" in err["field"] for err in data["details"])


def test_invalid_max_results():
    """Test request with invalid max_results."""
    response = client.post(
        "/mcp/youtube_search_and_transcript",
        json={
            "request": {
                "query": "python programming",
                "max_results": 0
            }
        }
    )
    assert response.status_code == 400
    data = response.json()
    assert "error" in data
    assert "details" in data
    assert any("max_results" in err["field"] for err in data["details"])


def test_invalid_max_results_too_high():
    """Test request with max_results too high."""
    response = client.post(
        "/mcp/youtube_search_and_transcript",
        json={
            "request": {
                "query": "python programming",
                "max_results": 25
            }
        }
    )
    assert response.status_code == 400
    data = response.json()
    assert "error" in data
    assert "details" in data
    assert any("max_results" in err["field"] for err in data["details"])


def test_invalid_language():
    """Test request with invalid language code."""
    response = client.post(
        "/mcp/youtube_search_and_transcript",
        json={
            "request": {
                "query": "python programming",
                "max_results": 5,
                "transcript_language": "xyz"
            }
        }
    )
    assert response.status_code == 400
    data = response.json()
    assert "error" in data
    assert "details" in data
    assert any("transcript_language" in err["field"] for err in data["details"])


def test_invalid_date_format():
    """Test request with invalid date format."""
    response = client.post(
        "/mcp/youtube_search_and_transcript",
        json={
            "request": {
                "query": "python programming",
                "max_results": 5,
                "published_after": "2025-01-01"
            }
        }
    )
    assert response.status_code == 400
    data = response.json()
    assert "error" in data
    assert "details" in data
    assert any("published_after" in err["field"] for err in data["details"])


def test_future_date():
    """Test request with future date."""
    future_date = (datetime.now(timezone.utc) + timedelta(days=1)).isoformat()
    response = client.post(
        "/mcp/youtube_search_and_transcript",
        json={
            "request": {
                "query": "python programming",
                "max_results": 5,
                "published_after": future_date
            }
        }
    )
    assert response.status_code == 400
    data = response.json()
    assert "error" in data
    assert "details" in data
    assert any("published_after" in err["field"] for err in data["details"])


def test_invalid_order_by():
    """Test request with invalid order_by value."""
    response = client.post(
        "/mcp/youtube_search_and_transcript",
        json={
            "request": {
                "query": "python programming",
                "max_results": 5,
                "order_by": "invalid"
            }
        }
    )
    assert response.status_code == 400
    data = response.json()
    assert "error" in data
    assert "details" in data
    assert any("order_by" in err["field"] for err in data["details"])


def test_missing_required_fields():
    """Test request missing required fields."""
    data = {"query": "Python programming"}  # missing max_results
    try:
        YouTubeSearchRequest(**data)
    except ValidationError as e:
        error_details = [f"{err['loc'][0]}: {err['msg']}" for err in e.errors()]
        assert "max_results" in "\n".join(error_details)


def test_too_long_query():
    """Test request with query too long."""
    long_query = "a" * 501
    response = client.post(
        "/mcp/youtube_search_and_transcript",
        json={
            "request": {
                "query": long_query,
                "max_results": 5
            }
        }
    )
    assert response.status_code == 400
    data = response.json()
    assert "error" in data
    assert "details" in data
    assert any("query" in err["field"] for err in data["details"])


def test_negative_max_results():
    """Test request with negative max_results."""
    response = client.post(
        "/mcp/youtube_search_and_transcript",
        json={
            "request": {
                "query": "python programming",
                "max_results": -1
            }
        }
    )
    assert response.status_code == 400
    data = response.json()
    assert "error" in data
    assert "details" in data
    assert any("max_results" in err["field"] for err in data["details"])
