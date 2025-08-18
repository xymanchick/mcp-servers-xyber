import asyncio
import logging

from unittest.mock import MagicMock, AsyncMock, patch
import pytest
import aiohttp
from mcp_server_tavily.tavily.module import (
    _TavilyService, 
    get_tavily_service,
    is_retryable_tavily_error,
    _ainvoke_with_retry
)
from mcp_server_tavily.tavily.config import TavilyConfig, TavilyConfigError
from mcp_server_tavily.tavily.models import TavilySearchResult

def test_is_retryable_tavily_error_429():
    error = Exception("Error 429: Too Many Requests")
    assert is_retryable_tavily_error(error) is True


def test_is_retryable_tavily_error_5xx():
    error = Exception("Error 500: Internal Server Error")
    assert is_retryable_tavily_error(error) is True
    
    error = Exception("Error 503: Service Unavailable")
    assert is_retryable_tavily_error(error) is True


def test_is_retryable_tavily_error_4xx_not_429():
    error = Exception("Error 400: Bad Request")
    assert is_retryable_tavily_error(error) is False
    
    error = Exception("Error 404: Not Found")
    assert is_retryable_tavily_error(error) is False


def test_is_retryable_tavily_error_no_match():
    error = Exception("Some generic error")
    assert is_retryable_tavily_error(error) is False
    
    error = Exception("Network error")
    assert is_retryable_tavily_error(error) is False


@pytest.mark.asyncio
async def test_ainvoke_with_retry_success(mock_tavily_tool, mock_result, mock_sleep):
    mock_tavily_tool.ainvoke.return_value = mock_result
    
    result = await _ainvoke_with_retry(mock_tavily_tool, "test query")
    
    assert result == mock_result
    assert mock_tavily_tool.ainvoke.call_count == 1


@pytest.mark.asyncio
async def test_ainvoke_with_retry_timeout_then_success(mock_tavily_tool, mock_result, mock_sleep):
    mock_tavily_tool.ainvoke.side_effect = [asyncio.TimeoutError(), mock_result]
    
    result = await _ainvoke_with_retry(mock_tavily_tool, "test query")
    
    assert result == mock_result
    assert mock_tavily_tool.ainvoke.call_count == 2


@pytest.mark.asyncio
async def test_ainvoke_with_retry_client_error_then_success(mock_tavily_tool, mock_result, mock_sleep):
    mock_tavily_tool.ainvoke.side_effect = [aiohttp.ClientError(), mock_result]
    
    result = await _ainvoke_with_retry(mock_tavily_tool, "test query")
    
    assert result == mock_result
    assert mock_tavily_tool.ainvoke.call_count == 2


def test_tavily_service_init(mock_config):
    service = _TavilyService(mock_config)
    assert service.config == mock_config


@patch('mcp_server_tavily.tavily.module.TavilySearch')
def test_create_tavily_tool_success(mock_tavily_search, mock_config):
    service = _TavilyService(mock_config)
    mock_tool = MagicMock()
    mock_tavily_search.return_value = mock_tool
    
    result = service._create_tavily_tool()
    
    mock_tavily_search.assert_called_once_with(
        api_key=mock_config.api_key,
        max_results=mock_config.max_results,
        topic=mock_config.topic,
        search_depth=mock_config.search_depth,
        include_answer=mock_config.include_answer,
        include_raw_content=mock_config.include_raw_content,
        include_images=mock_config.include_images,
    )
    assert result == mock_tool


@patch('mcp_server_tavily.tavily.module.TavilySearch')
def test_create_tavily_tool_with_max_results_override(mock_tavily_search, mock_config):
    service = _TavilyService(mock_config)
    mock_tool = MagicMock()
    mock_tavily_search.return_value = mock_tool
    
    result = service._create_tavily_tool(max_results=10)
    
    mock_tavily_search.assert_called_once_with(
        api_key=mock_config.api_key,
        max_results=10,  # overridden value
        topic=mock_config.topic,
        search_depth=mock_config.search_depth,
        include_answer=mock_config.include_answer,
        include_raw_content=mock_config.include_raw_content,
        include_images=mock_config.include_images,
    )
    assert result == mock_tool


@patch('mcp_server_tavily.tavily.module.TavilySearch')
def test_create_tavily_tool_exception(mock_tavily_search, mock_config):
    service = _TavilyService(mock_config)
    mock_tavily_search.side_effect = Exception("Test error")
    
    with pytest.raises(TavilyConfigError, match="Error creating TavilySearch tool"):
        service._create_tavily_tool()


@pytest.mark.asyncio
async def test_search_empty_query(mock_config):
    service = _TavilyService(mock_config)
    
    with pytest.raises(ValueError, match="Search query cannot be empty"):
        await service.search("")


@pytest.mark.asyncio
async def test_search_none_query(mock_config):
    service = _TavilyService(mock_config)
    
    with pytest.raises(ValueError, match="Search query cannot be empty"):
        await service.search(None)


@pytest.mark.asyncio
async def test_search_empty_results(mock_config, mocker):
    service = _TavilyService(mock_config)
    mock_tavily_tool = AsyncMock()
    mock_tavily_tool.ainvoke.return_value = None
    
    mocker.patch.object(service, "_create_tavily_tool", return_value=mock_tavily_tool)
    
    results = await service.search("test query")
    
    assert len(results) == 1
    assert results[0].title == "No Results"
    assert results[0].url == "#"
    assert results[0].content == "No results were found for this search query."


@pytest.mark.asyncio
async def test_search_error_response(mock_config, mocker):
    service = _TavilyService(mock_config)
    mock_tavily_tool = AsyncMock()
    mock_tavily_tool.ainvoke.return_value = "error"
    
    mocker.patch.object(service, "_create_tavily_tool", return_value=mock_tavily_tool)
    
    results = await service.search("test query")
    
    assert len(results) == 1
    assert results[0].title == "Search Error"
    assert results[0].url == "#"
    assert "API returned an error" in results[0].content


@pytest.mark.asyncio
async def test_search_string_response(mock_config, mocker):
    service = _TavilyService(mock_config)
    mock_tavily_tool = AsyncMock()
    mock_tavily_tool.ainvoke.return_value = "Some search result text"
    
    mocker.patch.object(service, "_create_tavily_tool", return_value=mock_tavily_tool)
    
    results = await service.search("test query")
    
    assert len(results) == 1
    assert results[0].title == "Search Result"
    assert results[0].url == "#"
    assert results[0].content == "Some search result text"


@pytest.mark.asyncio
async def test_search_dict_response_with_results(mock_config, mocker):
    service = _TavilyService(mock_config)
    mock_tavily_tool = AsyncMock()
    mock_response = {
        "results": [
            {"title": "Result 1", "url": "http://example.com/1", "content": "Content 1"},
            {"title": "Result 2", "url": "http://example.com/2", "content": "Content 2"}
        ]
    }
    mock_tavily_tool.ainvoke.return_value = mock_response
    
    mocker.patch.object(service, "_create_tavily_tool", return_value=mock_tavily_tool)
    
    results = await service.search("test query")
    
    assert len(results) == 2
    assert results[0].title == "Result 1"
    assert results[0].url == "http://example.com/1"
    assert results[0].content == "Content 1"
    assert results[1].title == "Result 2"
    assert results[1].url == "http://example.com/2"
    assert results[1].content == "Content 2"


@pytest.mark.asyncio
async def test_search_dict_response_with_answer_only(mock_config, mocker):
    service = _TavilyService(mock_config)
    mock_tavily_tool = AsyncMock()
    mock_response = {"answer": "This is the answer to your question"}
    mock_tavily_tool.ainvoke.return_value = mock_response
    
    mocker.patch.object(service, "_create_tavily_tool", return_value=mock_tavily_tool)
    
    results = await service.search("test query")
    
    assert len(results) == 1
    assert results[0].title == "Search Answer"
    assert results[0].url == "#"
    assert results[0].content == "This is the answer to your question"


@pytest.mark.asyncio
async def test_search_dict_response_empty_results(mock_config, mocker):
    service = _TavilyService(mock_config)
    mock_tavily_tool = AsyncMock()
    mock_response = {"results": []}
    mock_tavily_tool.ainvoke.return_value = mock_response
    
    mocker.patch.object(service, "_create_tavily_tool", return_value=mock_tavily_tool)
    
    results = await service.search("test query")
    
    assert len(results) == 1
    assert results[0].title == "No Results"
    assert results[0].url == "#"
    assert results[0].content == "No search results found."


@pytest.mark.asyncio
async def test_search_dict_response_with_non_dict_results(mock_config, mocker):
    service = _TavilyService(mock_config)
    mock_tavily_tool = AsyncMock()
    mock_response = {
        "results": [
            {"title": "Valid Result", "url": "http://example.com", "content": "Valid content"},
            "Non-dict result",  # This should be handled as a non-dict item
            123  # Another non-dict item
        ]
    }
    mock_tavily_tool.ainvoke.return_value = mock_response
    
    mocker.patch.object(service, "_create_tavily_tool", return_value=mock_tavily_tool)
    
    results = await service.search("test query")
    
    assert len(results) == 3
    assert results[0].title == "Valid Result"
    assert results[0].url == "http://example.com"
    assert results[0].content == "Valid content"
    assert results[1].title == "Search Result 2"
    assert results[1].url == "#"
    assert results[1].content == "Non-dict result"
    assert results[2].title == "Search Result 3"
    assert results[2].url == "#"
    assert results[2].content == "123"


@pytest.mark.asyncio
async def test_search_list_response_strings(mock_config, mocker):
    service = _TavilyService(mock_config)
    mock_tavily_tool = AsyncMock()
    mock_response = ["Result 1 content", "Result 2 content"]
    mock_tavily_tool.ainvoke.return_value = mock_response
    
    mocker.patch.object(service, "_create_tavily_tool", return_value=mock_tavily_tool)
    
    results = await service.search("test query")
    
    assert len(results) == 2
    assert results[0].title == "Search Result 1"
    assert results[0].content == "Result 1 content"
    assert results[1].title == "Search Result 2"
    assert results[1].content == "Result 2 content"


@pytest.mark.asyncio
async def test_search_list_response_objects_with_attributes(mock_config, mocker):
    """Test search handles list response with objects having title, url, content."""
    service = _TavilyService(mock_config)
    mock_tavily_tool = AsyncMock()
    
    # Create mock objects with attributes
    mock_result1 = MagicMock()
    mock_result1.title = "Object Result 1"
    mock_result1.url = "http://example.com/obj1"
    mock_result1.content = "Object content 1"
    
    mock_result2 = MagicMock()
    mock_result2.title = "Object Result 2"  
    mock_result2.url = "http://example.com/obj2"
    mock_result2.content = "Object content 2"
    
    mock_response = [mock_result1, mock_result2]
    mock_tavily_tool.ainvoke.return_value = mock_response
    
    mocker.patch.object(service, "_create_tavily_tool", return_value=mock_tavily_tool)
    
    results = await service.search("test query")
    
    assert len(results) == 2
    assert results[0].title == "Object Result 1"
    assert results[0].url == "http://example.com/obj1"
    assert results[0].content == "Object content 1"


@pytest.mark.asyncio
async def test_search_list_response_document_objects(mock_config, mocker):
    service = _TavilyService(mock_config)
    mock_tavily_tool = AsyncMock()
    
    # Create mock Document objects with proper hasattr behavior
    mock_doc1 = MagicMock()
    mock_doc1.page_content = "Document content 1"
    mock_doc1.metadata = {"title": "Doc Title 1", "source": "http://doc1.com"}
    # Remove attributes that would make it look like TavilySearchResult
    del mock_doc1.title
    del mock_doc1.url
    del mock_doc1.content
    
    mock_doc2 = MagicMock()
    mock_doc2.page_content = "Document content 2"
    mock_doc2.metadata = {"source": "http://doc2.com"}  # No title
    del mock_doc2.title
    del mock_doc2.url
    del mock_doc2.content
    
    mock_response = [mock_doc1, mock_doc2]
    mock_tavily_tool.ainvoke.return_value = mock_response
    
    mocker.patch.object(service, "_create_tavily_tool", return_value=mock_tavily_tool)
    
    results = await service.search("test query")
    
    assert len(results) == 2
    assert results[0].title == "Doc Title 1"
    assert results[0].url == "http://doc1.com"
    assert results[0].content == "Document content 1"
    assert results[1].title == "Search Result 2"  # Default title
    assert results[1].url == "http://doc2.com"
    assert results[1].content == "Document content 2"


@pytest.mark.asyncio
async def test_search_list_response_unknown_objects(mock_config, mocker):
    """Test search handles list response with unknown object types."""
    service = _TavilyService(mock_config)
    mock_tavily_tool = AsyncMock()
    
    # Create objects without expected attributes
    mock_obj1 = MagicMock()
    del mock_obj1.title  # Remove title attribute
    del mock_obj1.url    # Remove url attribute
    del mock_obj1.content # Remove content attribute
    del mock_obj1.page_content # Remove page_content attribute
    del mock_obj1.metadata # Remove metadata attribute
    
    mock_response = [mock_obj1, "some string"]
    mock_tavily_tool.ainvoke.return_value = mock_response
    
    mocker.patch.object(service, "_create_tavily_tool", return_value=mock_tavily_tool)
    
    results = await service.search("test query")
    
    assert len(results) == 2
    assert results[0].title == "Search Result 1"
    assert results[0].url == "#"
    assert str(mock_obj1) in results[0].content  # Should be str representation
    assert results[1].content == "some string"


@pytest.mark.asyncio 
async def test_search_unexpected_response_type(mock_config, mocker):
    service = _TavilyService(mock_config)
    mock_tavily_tool = AsyncMock()
    mock_response = 12345  # Unexpected type
    mock_tavily_tool.ainvoke.return_value = mock_response
    
    mocker.patch.object(service, "_create_tavily_tool", return_value=mock_tavily_tool)
    
    results = await service.search("test query")
    
    assert len(results) == 1
    assert results[0].title == "Search Result"
    assert results[0].url == "#"
    assert results[0].content == "12345"


@patch('mcp_server_tavily.tavily.module.TavilyConfig')
def test_get_tavily_service_success(mock_config_class):
    mock_config = MagicMock()
    mock_config_class.return_value = mock_config
    
    get_tavily_service.cache_clear()
    
    service = get_tavily_service()
    
    assert isinstance(service, _TavilyService)
    assert service.config == mock_config
    mock_config_class.assert_called_once()


@patch('mcp_server_tavily.tavily.module.TavilyConfig')
def test_get_tavily_service_singleton(mock_config_class):
    mock_config = MagicMock()
    mock_config_class.return_value = mock_config
    
    get_tavily_service.cache_clear()
    
    service1 = get_tavily_service()
    service2 = get_tavily_service()
    
    assert service1 is service2  # Same instance
    assert mock_config_class.call_count == 1  # Config created only once


@patch('mcp_server_tavily.tavily.module.TavilyConfig')
def test_get_tavily_service_config_error(mock_config_class):
    mock_config_class.side_effect = TavilyConfigError("Config error")
    
    get_tavily_service.cache_clear()
    
    with pytest.raises(TavilyConfigError, match="Config error"):
        get_tavily_service()


@pytest.mark.asyncio
async def test_search_retries_on_timeout(mock_config, mocker, caplog, mock_result, mock_sleep):
    tavily_service = _TavilyService(mock_config)
    mock_tavily_tool = AsyncMock()

    mock_tavily_tool.ainvoke.side_effect = [asyncio.TimeoutError(), mock_result]

    mocker.patch.object(
        tavily_service, "_create_tavily_tool", return_value=mock_tavily_tool
    )
    caplog.set_level(logging.WARNING)

    response = await tavily_service.search("Test")

    assert response[0].title == "Test"
    assert mock_tavily_tool.ainvoke.call_count == 2

    # Check that each failed call yields a warning
    logs = [rec for rec in caplog.records if rec.levelno == logging.WARNING]
    assert len(logs) == 1
    assert "TimeoutError" in str(logs[0].message)


@pytest.mark.asyncio
async def test_search_retries_on_recoverable_http_error(mock_config, mocker, mock_result, mock_sleep):
    tavily_service = _TavilyService(mock_config)
    mock_tavily_tool = AsyncMock()

    mock_tavily_tool.ainvoke.side_effect = [
        Exception("Error 429: Too Many Requests"),
        Exception("Error 500: Internal Server Error"),
        Exception("Error 501: Internal Server Error"),
        mock_result,
    ]

    mocker.patch.object(
        tavily_service, "_create_tavily_tool", return_value=mock_tavily_tool
    )

    response = await tavily_service.search("Test")

    assert response[0].title == "Test"
    assert mock_tavily_tool.ainvoke.call_count == 4


@pytest.mark.asyncio
async def test_search_fails_on_client_error(mock_config, mocker, mock_result, mock_sleep):
    tavily_service = _TavilyService(mock_config)
    mock_tavily_tool = AsyncMock()

    mock_tavily_tool.ainvoke.side_effect = [aiohttp.ClientError(), mock_result]

    mocker.patch.object(
        tavily_service, "_create_tavily_tool", return_value=mock_tavily_tool
    )

    response = await tavily_service.search("Test")

    assert response[0].title == "Test"
    assert mock_tavily_tool.ainvoke.call_count == 2


@pytest.mark.asyncio
async def test_search_fails_on_unrecoverable_http_error(mock_config, mocker, mock_result, mock_sleep):
    tavily_service = _TavilyService(mock_config)
    mock_tavily_tool = AsyncMock()

    mock_tavily_tool.ainvoke.side_effect = [
        Exception("Error 400: Bad Request"),
        mock_result,
    ]

    mocker.patch.object(
        tavily_service, "_create_tavily_tool", return_value=mock_tavily_tool
    )

    response = await tavily_service.search("Test")

    assert response[0].title == "Search Error"
    assert mock_tavily_tool.ainvoke.call_count == 1


@pytest.mark.asyncio
async def test_search_fails_after_five_attempts(mock_config, mocker, mock_sleep):
    tavily_service = _TavilyService(mock_config)
    mock_tavily_tool = AsyncMock()

    mock_tavily_tool.ainvoke.side_effect = aiohttp.ClientError("Persistent Failure")

    mocker.patch.object(
        tavily_service, "_create_tavily_tool", return_value=mock_tavily_tool
    )

    response = await tavily_service.search("Test")

    assert response[0].title == "Search Error"
    assert mock_tavily_tool.ainvoke.call_count == 5
