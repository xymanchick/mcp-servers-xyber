"""
Manual test script for YouTube MCP Server

This script provides examples of how to test the server's functionality,
including validation of input parameters and error handling.
"""

import json
import time
from datetime import datetime, timedelta

import requests

# Base URL for the server
BASE_URL = "http://localhost:8000"

print("=== Starting Manual Tests ===")


def test_endpoint(data: dict, description: str):
    """Helper function to test an endpoint"""
    print(f"\n{description}...")
    print(f"Request data: {json.dumps(data, indent=2)}")

    try:
        # MCP endpoint requires wrapping in request key
        response = requests.post(
            f"{BASE_URL}/youtube_search_and_transcript",
            json={"request": data},
            headers={"Content-Type": "application/json"},
        )

        print(f"Response status: {response.status_code}")
        try:
            response_data = response.json()
            print("Response data:", json.dumps(response_data, indent=2))

            # Check for validation errors
            if "error" in response_data:
                print("Error details:", response_data["error"])
        except json.JSONDecodeError:
            print("Response text:", response.text)

    except requests.exceptions.RequestException as e:
        print(f"Request failed: {str(e)}")


# 1. Test valid request
test_endpoint(
    {
        "query": "Python programming tutorial",
        "max_results": 5,
        "transcript_language": "en",
        "published_after": "2025-01-01T00:00:00Z",
        "order_by": "relevance",
    },
    "1. Testing valid request",
)

# 2. Test empty query
test_endpoint({"query": "", "max_results": 5}, "2. Testing empty query")

# 3. Test invalid max_results
test_endpoint(
    {
        "query": "Python programming",
        "max_results": 25,  # exceeds max limit of 20
    },
    "3. Testing invalid max_results",
)

# 4. Test invalid language code
test_endpoint(
    {
        "query": "Python programming",
        "max_results": 5,
        "transcript_language": "xyz123",  # invalid language code
    },
    "4. Testing invalid language code",
)

# 5. Test invalid date format
test_endpoint(
    {
        "query": "Python programming",
        "max_results": 5,
        "published_after": "2025-01-01",  # missing time component
    },
    "5. Testing invalid date format",
)

# 6. Test invalid order_by value
test_endpoint(
    {
        "query": "Python programming",
        "max_results": 5,
        "order_by": "views",  # invalid sort order
    },
    "6. Testing invalid order_by value",
)

# 7. Test future date
test_endpoint(
    {
        "query": "Python programming",
        "max_results": 5,
        "published_after": (datetime.now() + timedelta(days=1)).isoformat() + "Z",
    },
    "7. Testing future date",
)

# 8. Test whitespace-only query
test_endpoint({"query": "   ", "max_results": 5}, "8. Testing whitespace-only query")

print("\n=== Tests Complete ===")
print(
    "Note: All invalid requests should return 400 status code with descriptive error messages"
)
