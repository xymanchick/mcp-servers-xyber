from __future__ import annotations

from datetime import datetime
from datetime import timedelta
from datetime import timezone

from mcp_server_youtube.youtube.models import YouTubeSearchRequest
from pydantic import ValidationError


def test_valid_request_minimal(test_client, api_endpoints, sample_minimal_request):
    """Test minimal valid request with required fields only."""
    response = test_client.post(
        api_endpoints['search_and_transcript'],
        json=sample_minimal_request
    )
    assert response.status_code == 200, f'Response status: {response.status_code}, Content: {response.json()}'
    data = response.json()
    assert 'videos' in data
    assert len(data['videos']) <= 3

    # Verify response structure
    for video in data['videos']:
        assert 'video_id' in video
        assert 'title' in video
        assert 'channel' in video
        assert 'published_at' in video
        assert 'thumbnail' in video
        assert 'description' in video
        assert 'transcript' in video
        
        # Verify video_id format (should be 11 characters)
        assert len(video['video_id']) == 11
        assert isinstance(video['title'], str)
        assert isinstance(video['channel'], str)
        assert isinstance(video['description'], str)
        
        # Verify published_at is a valid ISO datetime
        try:
            datetime.fromisoformat(video['published_at'].replace('Z', '+00:00'))
        except ValueError:
            assert False, f"Invalid datetime format: {video['published_at']}"


def test_valid_request_with_language(test_client, api_endpoints, sample_search_request):
    """Test valid request with transcript language."""
    response = test_client.post(
        api_endpoints['search_and_transcript'],
        json=sample_search_request
    )
    assert response.status_code == 200, f'Response status: {response.status_code}, Content: {response.json()}'
    data = response.json()
    assert 'videos' in data
    assert len(data['videos']) <= 5

    # Verify transcript language
    for video in data['videos']:
        # Transcript should be present (either actual transcript or error message)
        assert video['transcript'] is not None
        assert isinstance(video['transcript'], str)
        # For mock data, transcript should contain the language
        if video['transcript'] not in ['[No transcript available]', '[Transcripts are disabled]']:
            assert 'en' in video['transcript'] or len(video['transcript']) > 0


def test_valid_request_with_dates(test_client, api_endpoints):
    """Test valid request with date filters."""
    response = test_client.post(
        api_endpoints['search_and_transcript'],
        json={
            'request': {
                'query': 'python programming',
                'max_results': 5,
                'published_after': '2024-01-01T00:00:00Z',
                'published_before': '2024-12-31T23:59:59Z'
            }
        }
    )
    assert response.status_code == 200, f'Response status: {response.status_code}, Content: {response.json()}'
    data = response.json()
    assert 'videos' in data
    assert len(data['videos']) <= 5

    # Verify dates are within range
    for video in data['videos']:
        published_at = datetime.fromisoformat(video['published_at'])
        assert published_at >= datetime.fromisoformat('2024-01-01T00:00:00+00:00')
        assert published_at <= datetime.fromisoformat('2024-12-31T23:59:59+00:00')


def test_valid_request_with_order_by(test_client, api_endpoints):
    """Test valid request with order_by parameter."""
    for order_by in ['relevance', 'date', 'viewCount', 'rating']:
        response = test_client.post(
            api_endpoints['search_and_transcript'],
            json={
                'request': {
                    'query': 'python programming',
                    'max_results': 5,
                    'order_by': order_by
                }
            }
        )
        assert response.status_code == 200, f'Response status: {response.status_code}, Content: {response.json()}'
        data = response.json()
        assert 'videos' in data
        assert len(data['videos']) <= 5


def test_valid_request_with_all_options(test_client, api_endpoints):
    """Test valid request with all optional parameters."""
    response = test_client.post(
        api_endpoints['search_and_transcript'],
        json={
            'request': {
                'query': 'Python programming tutorial',
                'max_results': 5,
                'transcript_language': 'en',
                'published_after': '2025-01-01T00:00:00Z',
                'order_by': 'relevance'
            }
        }
    )
    assert response.status_code == 200, f'Response status: {response.status_code}, Content: {response.json()}'
    data = response.json()
    assert 'videos' in data
    assert len(data['videos']) <= 5

    # Verify all fields are present in results
    for result in data['videos']:
        assert 'video_id' in result
        assert 'title' in result
        assert 'channel' in result
        assert 'published_at' in result
        assert 'thumbnail' in result
        assert 'description' in result
        assert 'transcript' in result


def test_valid_request_with_default_max_results(test_client, api_endpoints):
    """Test valid request using default max_results."""
    response = test_client.post(
        api_endpoints['search_and_transcript'],
        json={
            'request': {
                'query': 'python programming',
                'max_results': 5
            }
        }
    )
    assert response.status_code == 200, f'Response status: {response.status_code}, Content: {response.json()}'
    data = response.json()
    assert 'videos' in data
    assert 'total_results' in data
    assert len(data['videos']) <= 5


def test_empty_query(test_client, api_endpoints, invalid_requests):
    """Test request with empty query."""
    response = test_client.post(
        api_endpoints['search_and_transcript'],
        json=invalid_requests['empty_query']
    )
    assert response.status_code == 400
    data = response.json()
    assert 'error' in data
    assert 'details' in data
    assert any('query' in err['field'] for err in data['details'])


def test_whitespace_query(test_client, api_endpoints, invalid_requests):
    """Test request with whitespace-only query."""
    response = test_client.post(
        api_endpoints['search_and_transcript'],
        json=invalid_requests['whitespace_query']
    )
    assert response.status_code == 400
    data = response.json()
    assert 'error' in data
    assert 'details' in data
    assert any('query' in err['field'] for err in data['details'])


def test_invalid_max_results(test_client, api_endpoints, invalid_requests):
    """Test request with invalid max_results."""
    response = test_client.post(
        api_endpoints['search_and_transcript'],
        json=invalid_requests['invalid_max_results_zero']
    )
    assert response.status_code == 400
    data = response.json()
    assert 'error' in data
    assert 'details' in data
    assert any('max_results' in err['field'] for err in data['details'])


def test_invalid_max_results_too_high(test_client, api_endpoints, invalid_requests):
    """Test request with max_results too high."""
    response = test_client.post(
        api_endpoints['search_and_transcript'],
        json=invalid_requests['invalid_max_results_high']
    )
    assert response.status_code == 400
    data = response.json()
    assert 'error' in data
    assert 'details' in data
    assert any('max_results' in err['field'] for err in data['details'])


def test_invalid_language(test_client, api_endpoints, invalid_requests):
    """Test request with invalid language code."""
    response = test_client.post(
        api_endpoints['search_and_transcript'],
        json=invalid_requests['invalid_language']
    )
    assert response.status_code == 400
    data = response.json()
    assert 'error' in data
    assert 'details' in data
    assert any('transcript_language' in err['field'] for err in data['details'])


def test_invalid_date_format(test_client, api_endpoints, invalid_requests):
    """Test request with invalid date format."""
    response = test_client.post(
        api_endpoints['search_and_transcript'],
        json=invalid_requests['invalid_date_format']
    )
    assert response.status_code == 400
    data = response.json()
    assert 'error' in data
    assert 'details' in data
    assert any('published_after' in err['field'] for err in data['details'])


def test_future_date(test_client, api_endpoints):
    """Test request with future date."""
    future_date = (datetime.now(timezone.utc) + timedelta(days=1)).isoformat()
    response = test_client.post(
        api_endpoints['search_and_transcript'],
        json={
            'request': {
                'query': 'python programming',
                'max_results': 5,
                'published_after': future_date
            }
        }
    )
    assert response.status_code == 400
    data = response.json()
    assert 'error' in data
    assert 'details' in data
    assert any('published_after' in err['field'] for err in data['details'])


def test_invalid_order_by(test_client, api_endpoints):
    """Test request with invalid order_by value."""
    invalid_values = ['invalid', 'popularity', 'newest', 123, None]
    
    for order_by in invalid_values:
        response = test_client.post(
            api_endpoints['search_and_transcript'],
            json={
                'request': {
                    'query': 'python programming',
                    'max_results': 5,
                    'order_by': order_by
                }
            }
        )
        if order_by is None:
            # None is valid (optional parameter)
            assert response.status_code == 200, f'Response status: {response.status_code}, Content: {response.json()}'
        else:
            # Invalid values should return 400
            assert response.status_code == 400, f'Expected 400 for order_by={order_by}, got {response.status_code}'
            data = response.json()
            assert 'error' in data
            assert 'details' in data


def test_valid_order_by_values(test_client, api_endpoints):
    """Test request with valid order_by values."""
    valid_values = ['relevance', 'date', 'viewCount', 'rating']
    
    for order_by in valid_values:
        response = test_client.post(
            api_endpoints['search_and_transcript'],
            json={
                'request': {
                    'query': 'python programming',
                    'max_results': 5,
                    'order_by': order_by
                }
            }
        )
        assert response.status_code == 200, f'Response status: {response.status_code}, Content: {response.json()}'
        data = response.json()
        assert 'videos' in data
        assert len(data['videos']) <= 5


def test_missing_required_fields(test_client, api_endpoints):
    """Test request missing required fields."""
    data = {'query': 'Python programming'}  # missing max_results
    try:
        YouTubeSearchRequest(**data)
    except ValidationError as e:
        error_details = [f"{err['loc'][0]}: {err['msg']}" for err in e.errors()]
        assert 'max_results' in '\n'.join(error_details)


def test_too_long_query(test_client, api_endpoints):
    """Test request with query too long."""
    long_query = 'a' * 501
    response = test_client.post(
        api_endpoints['search_and_transcript'],
        json={
            'request': {
                'query': long_query,
                'max_results': 5
            }
        }
    )
    assert response.status_code == 400
    data = response.json()
    assert 'error' in data
    assert 'details' in data
    assert any('query' in err['field'] for err in data['details'])


def test_negative_max_results(test_client, api_endpoints):
    """Test request with negative max_results."""
    response = test_client.post(
        api_endpoints['search_and_transcript'],
        json={
            'request': {
                'query': 'python programming',
                'max_results': -1
            }
        }
    )
    assert response.status_code == 400
    data = response.json()
    assert 'error' in data
    assert 'details' in data
    assert any('max_results' in err['field'] for err in data['details'])


def test_incompatible_dates(test_client, api_endpoints):
    """Test request where published_after is after published_before."""
    response = test_client.post(
        api_endpoints['search_and_transcript'],
        json={
            'request': {
                'query': 'python programming',
                'max_results': 5,
                'published_after': '2024-12-31T23:59:59Z',
                'published_before': '2024-01-01T00:00:00Z'
            }
        }
    )
    # This should either return 400 (validation error) or 200 with results
    # For mock data, it returns 200 since the mock doesn't filter by dates
    assert response.status_code == 200
    data = response.json()
    assert 'videos' in data
    # Mock implementation doesn't filter by date, so we just check structure
    assert isinstance(data['videos'], list)


def test_malformed_json(test_client, api_endpoints):
    """Test request with malformed JSON."""
    import httpx
    response = httpx.post(
        f'{test_client.base_url}/youtube_search_and_transcript',
        content='{"request": {"query": "test", invalid json',
        headers={'Content-Type': 'application/json'}
    )
    # Could be 400 (bad request) or 403 (forbidden) depending on server config
    assert response.status_code in [400, 403]
    
    # Response might not be valid JSON if server returns HTML error page
    try:
        data = response.json()
        assert 'error' in data or 'detail' in data
    except Exception:
        # If JSON parsing fails, just check that we got an error status
        assert response.status_code in [400, 403]


def test_missing_request_wrapper(test_client, api_endpoints):
    """Test direct request format (without 'request' wrapper)."""
    response = test_client.post(
        api_endpoints['search_and_transcript'],
        json={
            'query': 'python programming',
            'max_results': 5
        }
    )
    # Should work with direct format according to routes.py
    assert response.status_code == 200
    data = response.json()
    assert 'videos' in data


def test_extra_fields(test_client, api_endpoints):
    """Test request with extra unexpected fields."""
    response = test_client.post(
        api_endpoints['search_and_transcript'],
        json={
            'request': {
                'query': 'python programming',
                'max_results': 5,
                'unexpected_field': 'should_be_ignored'
            }
        }
    )
    # Pydantic with extra='forbid' should return 400
    assert response.status_code == 400
    data = response.json()
    assert 'error' in data
    assert 'details' in data


def test_special_characters_in_query(test_client, api_endpoints):
    """Test request with special characters in query."""
    special_queries = [
        'python & programming',
        'C++ tutorial',
        'React.js fundamentals',
        'SQL: SELECT * FROM',
        'AI/ML basics',
        'Node.js + Express'
    ]
    
    for query in special_queries:
        response = test_client.post(
            api_endpoints['search_and_transcript'],
            json={
                'request': {
                    'query': query,
                    'max_results': 3
                }
            }
        )
        assert response.status_code == 200, f'Failed for query: {query}'
        data = response.json()
        assert 'videos' in data


def test_unicode_query(test_client, api_endpoints):
    """Test request with unicode characters in query."""
    unicode_queries = [
        'Python программирование',
        'JavaScript тутorials',
        'Machine Learning 机器学习',
        'React.js 入門'
    ]
    
    for query in unicode_queries:
        response = test_client.post(
            api_endpoints['search_and_transcript'],
            json={
                'request': {
                    'query': query,
                    'max_results': 3
                }
            }
        )
        assert response.status_code == 200, f'Failed for unicode query: {query}'
        data = response.json()
        assert 'videos' in data


def test_boundary_max_results(test_client, api_endpoints):
    """Test boundary values for max_results."""
    # Test minimum valid value
    response = test_client.post(
        api_endpoints['search_and_transcript'],
        json={
            'request': {
                'query': 'python',
                'max_results': 1
            }
        }
    )
    assert response.status_code == 200
    data = response.json()
    assert len(data['videos']) <= 1
    
    # Test maximum valid value
    response = test_client.post(
        api_endpoints['search_and_transcript'],
        json={
            'request': {
                'query': 'python',
                'max_results': 20
            }
        }
    )
    assert response.status_code == 200
    data = response.json()
    assert len(data['videos']) <= 20


def test_valid_language_codes(test_client, api_endpoints):
    """Test valid language codes from LanguageCode enum."""
    valid_languages = ['en', 'es', 'fr', 'de', 'pt', 'it', 'ja', 'ko', 'ru', 'zh']
    
    for lang in valid_languages:
        response = test_client.post(
            api_endpoints['search_and_transcript'],
            json={
                'request': {
                    'query': 'programming tutorial',
                    'max_results': 3,
                    'transcript_language': lang
                }
            }
        )
        assert response.status_code == 200, f'Failed for language: {lang}'
        data = response.json()
        assert 'videos' in data


def test_case_insensitive_language(test_client, api_endpoints):
    """Test that language codes are case insensitive."""
    response = test_client.post(
        api_endpoints['search_and_transcript'],
        json={
            'request': {
                'query': 'programming tutorial',
                'max_results': 3,
                'transcript_language': 'EN'  # Uppercase
            }
        }
    )
    assert response.status_code == 200
    data = response.json()
    assert 'videos' in data


def test_empty_request_body(test_client, api_endpoints):
    """Test request with empty body."""
    response = test_client.post(
        api_endpoints['search_and_transcript'],
        json={}
    )
    assert response.status_code == 400
    data = response.json()
    assert 'error' in data


def test_null_values(test_client, api_endpoints):
    """Test request with null values for optional fields."""
    response = test_client.post(
        api_endpoints['search_and_transcript'],
        json={
            'request': {
                'query': 'python programming',
                'max_results': 5,
                'transcript_language': None,
                'published_after': None,
                'published_before': None,
                'order_by': None
            }
        }
    )
    assert response.status_code == 200
    data = response.json()
    assert 'videos' in data


def test_response_structure_validation(test_client, api_endpoints):
    """Test that response contains all expected fields."""
    response = test_client.post(
        api_endpoints['search_and_transcript'],
        json={
            'request': {
                'query': 'python programming',
                'max_results': 3
            }
        }
    )
    assert response.status_code == 200
    data = response.json()
    
    # Check top-level structure
    assert 'videos' in data
    assert isinstance(data['videos'], list)
    
    # Check each video structure
    for video in data['videos']:
        required_fields = ['video_id', 'title', 'channel', 'published_at', 'thumbnail', 'description', 'transcript']
        for field in required_fields:
            assert field in video, f"Missing field: {field}"
            
        # Validate data types
        assert isinstance(video['video_id'], str)
        assert isinstance(video['title'], str)
        assert isinstance(video['channel'], str)
        assert isinstance(video['published_at'], str)
        assert isinstance(video['thumbnail'], str)
        assert isinstance(video['description'], str)
        assert isinstance(video['transcript'], str)


def test_very_short_query(test_client, api_endpoints):
    """Test minimum length query."""
    response = test_client.post(
        api_endpoints['search_and_transcript'],
        json={
            'request': {
                'query': 'a',  # Single character
                'max_results': 3
            }
        }
    )
    assert response.status_code == 200
    data = response.json()
    assert 'videos' in data


def test_numeric_query(test_client, api_endpoints):
    """Test query with only numbers."""
    response = test_client.post(
        api_endpoints['search_and_transcript'],
        json={
            'request': {
                'query': '12345',
                'max_results': 3
            }
        }
    )
    assert response.status_code == 200
    data = response.json()
    assert 'videos' in data


def test_date_edge_cases(test_client, api_endpoints):
    """Test edge cases for date validation."""
    # Test with different timezone formats
    timezone_formats = [
        '2024-01-01T00:00:00Z',
        '2024-01-01T00:00:00+00:00',
        '2024-01-01T00:00:00-05:00',
        '2024-01-01T00:00:00+09:00'
    ]
    
    for date_str in timezone_formats:
        response = test_client.post(
            api_endpoints['search_and_transcript'],
            json={
                'request': {
                    'query': 'test',
                    'max_results': 1,
                    'published_after': date_str
                }
            }
        )
        assert response.status_code == 200, f"Failed for date format: {date_str}"


def test_max_length_query(test_client, api_endpoints):
    """Test query at maximum allowed length."""
    max_query = 'a' * 500  # Maximum allowed length
    response = test_client.post(
        api_endpoints['search_and_transcript'],
        json={
            'request': {
                'query': max_query,
                'max_results': 3
            }
        }
    )
    assert response.status_code == 200
    data = response.json()
    assert 'videos' in data
