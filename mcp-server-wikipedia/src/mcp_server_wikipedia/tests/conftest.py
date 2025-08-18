import pytest
from unittest.mock import Mock, patch, MagicMock, AsyncMock
from typing import Any, Dict, List
import wikipediaapi
from mcp_server_wikipedia.wikipedia.module import _WikipediaService
from mcp_server_wikipedia.wikipedia import (
    ArticleNotFoundError,
    WikipediaAPIError,
    WikipediaServiceError,
)


@pytest.fixture
def mock_config():
    """Mock Wikipedia configuration."""
    config = Mock()
    config.user_agent = "Test-Agent/1.0"
    config.language = "en"
    return config


@pytest.fixture
def mock_wikipedia_page():
    """Mock Wikipedia page object."""
    page = Mock(spec=wikipediaapi.WikipediaPage)
    page.exists.return_value = True
    page.title = "Test Article"
    page.summary = "This is a test article summary."
    page.text = "This is the full text of the test article."
    page.fullurl = "https://en.wikipedia.org/wiki/Test_Article"
    
    # Mock sections
    section1 = Mock()
    section1.title = "Introduction"
    section2 = Mock()
    section2.title = "History"
    page.sections = [section1, section2]
    
    # Mock links
    page.links = {
        "Related Article 1": Mock(),
        "Related Article 2": Mock(),
        "Related Article 3": Mock()
    }
    
    return page


@pytest.fixture
def mock_wikipedia_service(mock_config, mock_wikipedia_page):
    """Mock Wikipedia service with mocked dependencies."""
    with patch('mcp_server_wikipedia.wikipedia.module.wikipediaapi.Wikipedia') as mock_wiki_api, \
         patch('mcp_server_wikipedia.wikipedia.module.wikipedia') as mock_wiki_lib:
        
        # Mock the wikipediaapi.Wikipedia instance
        mock_wiki_instance = Mock()
        mock_wiki_api.return_value = mock_wiki_instance
        mock_wiki_instance.page.return_value = mock_wikipedia_page
        
        # Mock the wikipedia library functions
        mock_wiki_lib.set_lang = Mock()
        mock_wiki_lib.set_user_agent = Mock()
        mock_wiki_lib.search = Mock(return_value=["Result 1", "Result 2", "Result 3"])
        
        # Create the service instance
        service = _WikipediaService(mock_config)
        
        return service, mock_wiki_instance, mock_wiki_lib


@pytest.fixture
def nonexistent_page_mock():
    """Mock for a non-existent Wikipedia page."""
    page = Mock(spec=wikipediaapi.WikipediaPage)
    page.exists.return_value = False
    return page


@pytest.fixture
def mock_wikipedia_service_simple():
    """Simple mock Wikipedia service for server tests."""
    return AsyncMock()


# === Server Testing Helper Functions ===

async def _test_search_wikipedia(query: str, context: dict) -> dict:
    """Direct implementation of search_wikipedia logic for testing."""
    try:
        service = context["wikipedia_service"]
        results = await service.search(query)
        return {"success": True, "data": results}
    except WikipediaServiceError as e:
        return {"success": False, "error": str(e)}
    except Exception as e:
        return {"success": False, "error": f"Unexpected error: {e}"}


async def _test_get_article(title: str, context: dict) -> dict:
    """Direct implementation of get_article logic for testing."""
    try:
        service = context["wikipedia_service"]
        article = await service.get_article(title)
        return {"success": True, "data": article}
    except ArticleNotFoundError as e:
        return {"success": False, "error": str(e)}
    except WikipediaAPIError as e:
        return {"success": False, "error": f"Wikipedia API error: {e}"}


async def _test_get_summary(title: str, context: dict) -> dict:
    """Direct implementation of get_summary logic for testing."""
    try:
        service = context["wikipedia_service"]
        summary = await service.get_summary(title)
        return {"success": True, "data": summary}
    except ArticleNotFoundError as e:
        return {"success": False, "error": str(e)}
    except WikipediaAPIError as e:
        return {"success": False, "error": f"Wikipedia API error: {e}"}


async def _test_get_sections(title: str, context: dict) -> dict:
    """Direct implementation of get_sections logic for testing."""
    try:
        service = context["wikipedia_service"]
        sections = await service.get_sections(title)
        return {"success": True, "data": sections}
    except ArticleNotFoundError as e:
        return {"success": False, "error": str(e)}
    except WikipediaAPIError as e:
        return {"success": False, "error": f"Wikipedia API error: {e}"}


async def _test_get_links(title: str, limit: int, context: dict) -> dict:
    """Direct implementation of get_links logic for testing."""
    try:
        service = context["wikipedia_service"]
        links = await service.get_links(title, limit)
        return {"success": True, "data": links}
    except ArticleNotFoundError as e:
        return {"success": False, "error": str(e)}
    except WikipediaAPIError as e:
        return {"success": False, "error": f"Wikipedia API error: {e}"}


async def _test_get_related_topics(title: str, limit: int, context: dict) -> dict:
    """Direct implementation of get_related_topics logic for testing."""
    try:
        service = context["wikipedia_service"]
        topics = await service.get_related_topics(title, limit)
        return {"success": True, "data": topics}
    except ArticleNotFoundError as e:
        return {"success": False, "error": str(e)}
    except WikipediaAPIError as e:
        return {"success": False, "error": f"Wikipedia API error: {e}"}