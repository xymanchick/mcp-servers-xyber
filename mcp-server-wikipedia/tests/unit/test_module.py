from unittest.mock import MagicMock, Mock, patch

import pytest
import wikipediaapi
from mcp_server_wikipedia.wikipedia.config import WikipediaConfig
from mcp_server_wikipedia.wikipedia.models import (ArticleNotFoundError,
                                                   WikipediaAPIError,
                                                   WikipediaConfigError)
from mcp_server_wikipedia.wikipedia.module import (_WikipediaService,
                                                   get_wikipedia_service)


class TestWikipediaServiceInitialization:
    """Test Wikipedia service initialization and configuration."""

    def test_successful_initialization(self, mock_config):
        """Test successful initialization of Wikipedia service."""
        with (
            patch(
                "mcp_server_wikipedia.wikipedia.module.wikipediaapi.Wikipedia"
            ) as mock_wiki_api,
            patch("mcp_server_wikipedia.wikipedia.module.wikipedia") as mock_wiki_lib,
        ):
            mock_wiki_instance = Mock()
            mock_wiki_api.return_value = mock_wiki_instance

            service = _WikipediaService(mock_config)

            # Verify Wikipedia API was initialized with correct parameters
            mock_wiki_api.assert_called_once_with(
                user_agent=mock_config.user_agent,
                language=mock_config.language,
                extract_format=wikipediaapi.ExtractFormat.WIKI,
            )

            # Verify wikipedia library was configured
            mock_wiki_lib.set_lang.assert_called_once_with(mock_config.language)
            mock_wiki_lib.set_user_agent.assert_called_once_with(mock_config.user_agent)

            assert service.config == mock_config
            assert service.wiki == mock_wiki_instance

    def test_initialization_failure(self, mock_config):
        """Test handling of initialization failure."""
        with patch(
            "mcp_server_wikipedia.wikipedia.module.wikipediaapi.Wikipedia"
        ) as mock_wiki_api:
            mock_wiki_api.side_effect = Exception("API initialization failed")

            with pytest.raises(WikipediaConfigError) as exc_info:
                _WikipediaService(mock_config)

            assert "Failed to initialize Wikipedia API" in str(exc_info.value)
            assert exc_info.value.__cause__


class TestWikipediaServiceSearch:
    """Test Wikipedia search functionality."""

    @pytest.mark.asyncio
    async def test_successful_search(self, mock_config):
        """Test successful search with results."""
        with (
            patch(
                "mcp_server_wikipedia.wikipedia.module.wikipediaapi.Wikipedia"
            ) as mock_wiki_api,
            patch("mcp_server_wikipedia.wikipedia.module.wikipedia") as mock_wiki_lib,
        ):
            mock_wiki_instance = Mock()
            mock_wiki_api.return_value = mock_wiki_instance

            search_results = ["Python", "Programming", "Computer Science"]
            mock_wiki_lib.search = Mock(return_value=search_results)
            mock_wiki_lib.set_lang = Mock()
            mock_wiki_lib.set_user_agent = Mock()

            service = _WikipediaService(mock_config)
            result = await service.search("python programming", limit=3)

            mock_wiki_lib.search.assert_called_once_with(
                "python programming", results=3
            )
            assert result == search_results

    @pytest.mark.asyncio
    async def test_search_with_default_limit(self, mock_config):
        """Test search with default limit parameter."""
        with (
            patch(
                "mcp_server_wikipedia.wikipedia.module.wikipediaapi.Wikipedia"
            ) as mock_wiki_api,
            patch("mcp_server_wikipedia.wikipedia.module.wikipedia") as mock_wiki_lib,
        ):
            mock_wiki_instance = Mock()
            mock_wiki_api.return_value = mock_wiki_instance

            mock_wiki_lib.search = Mock(return_value=["Result 1", "Result 2"])
            mock_wiki_lib.set_lang = Mock()
            mock_wiki_lib.set_user_agent = Mock()

            service = _WikipediaService(mock_config)
            await service.search("test query")

            mock_wiki_lib.search.assert_called_once_with("test query", results=10)

    @pytest.mark.asyncio
    async def test_search_empty_query(self, mock_config):
        """Test search with empty query raises ValueError."""
        with (
            patch(
                "mcp_server_wikipedia.wikipedia.module.wikipediaapi.Wikipedia"
            ) as mock_wiki_api,
            patch("mcp_server_wikipedia.wikipedia.module.wikipedia") as mock_wiki_lib,
        ):
            mock_wiki_instance = Mock()
            mock_wiki_api.return_value = mock_wiki_instance
            mock_wiki_lib.set_lang = Mock()
            mock_wiki_lib.set_user_agent = Mock()

            service = _WikipediaService(mock_config)

            with pytest.raises(ValueError) as exc_info:
                await service.search("")

            assert "Search query cannot be empty" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_search_api_error(self, mock_config):
        """Test search API error handling."""
        with (
            patch(
                "mcp_server_wikipedia.wikipedia.module.wikipediaapi.Wikipedia"
            ) as mock_wiki_api,
            patch("mcp_server_wikipedia.wikipedia.module.wikipedia") as mock_wiki_lib,
        ):
            mock_wiki_instance = Mock()
            mock_wiki_api.return_value = mock_wiki_instance

            mock_wiki_lib.search = Mock(side_effect=Exception("Network error"))
            mock_wiki_lib.set_lang = Mock()
            mock_wiki_lib.set_user_agent = Mock()

            service = _WikipediaService(mock_config)

            with pytest.raises(WikipediaAPIError) as exc_info:
                await service.search("test query")

            assert "Wikipedia search failed" in str(exc_info.value)
            assert exc_info.value.__cause__


class TestWikipediaServicePageRetrieval:
    """Test Wikipedia page retrieval functionality."""

    def test_get_page_existing(self, mock_wikipedia_service, mock_wikipedia_page):
        """Test getting an existing page."""
        service, mock_wiki_instance, _ = mock_wikipedia_service

        mock_wiki_instance.page.return_value = mock_wikipedia_page

        result = service._get_page("Test Article")

        mock_wiki_instance.page.assert_called_once_with("Test Article")
        assert result == mock_wikipedia_page

    def test_get_page_not_found(self, mock_wikipedia_service, nonexistent_page_mock):
        """Test getting a non-existent page."""
        service, mock_wiki_instance, _ = mock_wikipedia_service

        mock_wiki_instance.page.return_value = nonexistent_page_mock

        with pytest.raises(ArticleNotFoundError) as exc_info:
            service._get_page("Non-existent Article")

        assert exc_info.value.title == "Non-existent Article"
        assert "not found" in str(exc_info.value)


class TestWikipediaServiceGetArticle:
    """Test get_article functionality."""

    @pytest.mark.asyncio
    async def test_get_article_success(
        self, mock_wikipedia_service, mock_wikipedia_page
    ):
        """Test successful article retrieval."""
        service, mock_wiki_instance, _ = mock_wikipedia_service
        mock_wiki_instance.page.return_value = mock_wikipedia_page

        result = await service.get_article("Test Article")

        expected = {
            "title": "Test Article",
            "summary": "This is a test article summary.",
            "text": "This is the full text of the test article.",
            "url": "https://en.wikipedia.org/wiki/Test_Article",
            "sections": ["Introduction", "History"],
            "links": ["Related Article 1", "Related Article 2", "Related Article 3"],
        }

        assert result == expected

    @pytest.mark.asyncio
    async def test_get_article_not_found(
        self, mock_wikipedia_service, nonexistent_page_mock
    ):
        """Test article retrieval for non-existent article."""
        service, mock_wiki_instance, _ = mock_wikipedia_service
        mock_wiki_instance.page.return_value = nonexistent_page_mock

        with pytest.raises(ArticleNotFoundError):
            await service.get_article("Non-existent Article")


class TestWikipediaServiceGetSummary:
    """Test get_summary functionality."""

    @pytest.mark.asyncio
    async def test_get_summary_success(
        self, mock_wikipedia_service, mock_wikipedia_page
    ):
        """Test successful summary retrieval."""
        service, mock_wiki_instance, _ = mock_wikipedia_service
        mock_wiki_instance.page.return_value = mock_wikipedia_page

        result = await service.get_summary("Test Article")

        assert result == "This is a test article summary."

    @pytest.mark.asyncio
    async def test_get_summary_not_found(
        self, mock_wikipedia_service, nonexistent_page_mock
    ):
        """Test summary retrieval for non-existent article."""
        service, mock_wiki_instance, _ = mock_wikipedia_service
        mock_wiki_instance.page.return_value = nonexistent_page_mock

        with pytest.raises(ArticleNotFoundError):
            await service.get_summary("Non-existent Article")


class TestWikipediaServiceGetSections:
    """Test get_sections functionality."""

    @pytest.mark.asyncio
    async def test_get_sections_success(
        self, mock_wikipedia_service, mock_wikipedia_page
    ):
        """Test successful sections retrieval."""
        service, mock_wiki_instance, _ = mock_wikipedia_service
        mock_wiki_instance.page.return_value = mock_wikipedia_page

        result = await service.get_sections("Test Article")

        assert result == ["Introduction", "History"]

    @pytest.mark.asyncio
    async def test_get_sections_empty(self, mock_wikipedia_service):
        """Test sections retrieval for article with no sections."""
        service, mock_wiki_instance, _ = mock_wikipedia_service

        page_no_sections = Mock(spec=wikipediaapi.WikipediaPage)
        page_no_sections.exists.return_value = True
        page_no_sections.sections = []
        mock_wiki_instance.page.return_value = page_no_sections

        result = await service.get_sections("Article No Sections")

        assert result == []

    @pytest.mark.asyncio
    async def test_get_sections_not_found(
        self, mock_wikipedia_service, nonexistent_page_mock
    ):
        """Test sections retrieval for non-existent article."""
        service, mock_wiki_instance, _ = mock_wikipedia_service
        mock_wiki_instance.page.return_value = nonexistent_page_mock

        with pytest.raises(ArticleNotFoundError):
            await service.get_sections("Non-existent Article")


class TestWikipediaServiceGetLinks:
    """Test get_links functionality."""

    @pytest.mark.asyncio
    async def test_get_links_success(self, mock_wikipedia_service, mock_wikipedia_page):
        """Test successful links retrieval."""
        service, mock_wiki_instance, _ = mock_wikipedia_service
        mock_wiki_instance.page.return_value = mock_wikipedia_page

        result = await service.get_links("Test Article")

        expected_links = ["Related Article 1", "Related Article 2", "Related Article 3"]
        assert result == expected_links

    @pytest.mark.asyncio
    async def test_get_links_empty(self, mock_wikipedia_service):
        """Test links retrieval for article with no links."""
        service, mock_wiki_instance, _ = mock_wikipedia_service

        page_no_links = Mock(spec=wikipediaapi.WikipediaPage)
        page_no_links.exists.return_value = True
        page_no_links.links = {}
        mock_wiki_instance.page.return_value = page_no_links

        result = await service.get_links("Article No Links")

        assert result == []

    @pytest.mark.asyncio
    async def test_get_links_not_found(
        self, mock_wikipedia_service, nonexistent_page_mock
    ):
        """Test links retrieval for non-existent article."""
        service, mock_wiki_instance, _ = mock_wikipedia_service
        mock_wiki_instance.page.return_value = nonexistent_page_mock

        with pytest.raises(ArticleNotFoundError):
            await service.get_links("Non-existent Article")


class TestWikipediaServiceGetRelatedTopics:
    """Test get_related_topics functionality."""

    @pytest.mark.asyncio
    async def test_get_related_topics_success(
        self, mock_wikipedia_service, mock_wikipedia_page
    ):
        """Test successful related topics retrieval."""
        service, mock_wiki_instance, _ = mock_wikipedia_service
        mock_wiki_instance.page.return_value = mock_wikipedia_page

        result = await service.get_related_topics("Test Article", limit=2)

        expected_topics = ["Related Article 1", "Related Article 2"]
        assert result == expected_topics

    @pytest.mark.asyncio
    async def test_get_related_topics_default_limit(self, mock_wikipedia_service):
        """Test related topics retrieval with default limit."""
        service, mock_wiki_instance, _ = mock_wikipedia_service

        # Create a page with many links
        page_many_links = Mock(spec=wikipediaapi.WikipediaPage)
        page_many_links.exists.return_value = True
        page_many_links.links = {f"Link {i}": Mock() for i in range(25)}
        mock_wiki_instance.page.return_value = page_many_links

        result = await service.get_related_topics("Article Many Links")

        # Should return only 20 items (default limit)
        assert len(result) == 20

    @pytest.mark.asyncio
    async def test_get_related_topics_not_found(
        self, mock_wikipedia_service, nonexistent_page_mock
    ):
        """Test related topics retrieval for non-existent article."""
        service, mock_wiki_instance, _ = mock_wikipedia_service
        mock_wiki_instance.page.return_value = nonexistent_page_mock

        with pytest.raises(ArticleNotFoundError):
            await service.get_related_topics("Non-existent Article")


class TestGetWikipediaService:
    """Test the factory function for getting Wikipedia service instance."""

    def test_get_wikipedia_service_singleton(self):
        """Test that get_wikipedia_service returns the same instance (singleton)."""
        with (
            patch(
                "mcp_server_wikipedia.wikipedia.module.wikipediaapi.Wikipedia"
            ) as mock_wiki_api,
            patch("mcp_server_wikipedia.wikipedia.module.wikipedia") as mock_wiki_lib,
            patch(
                "mcp_server_wikipedia.wikipedia.module.WikipediaConfig"
            ) as mock_config_class,
        ):
            mock_config = Mock()
            mock_config_class.return_value = mock_config
            mock_wiki_instance = Mock()
            mock_wiki_api.return_value = mock_wiki_instance

            # Clear the cache first
            get_wikipedia_service.cache_clear()

            # Get service twice
            service1 = get_wikipedia_service()
            service2 = get_wikipedia_service()

            # Should be the same instance due to lru_cache
            assert service1 is service2

            # Config should only be created once
            assert mock_config_class.call_count == 1

    def test_get_wikipedia_service_configuration(self):
        """Test that get_wikipedia_service properly configures the service."""
        with (
            patch(
                "mcp_server_wikipedia.wikipedia.module.wikipediaapi.Wikipedia"
            ) as mock_wiki_api,
            patch("mcp_server_wikipedia.wikipedia.module.wikipedia") as mock_wiki_lib,
            patch(
                "mcp_server_wikipedia.wikipedia.module.WikipediaConfig"
            ) as mock_config_class,
        ):
            mock_config = Mock()
            mock_config.user_agent = "Test-Agent"
            mock_config.language = "en"
            mock_config_class.return_value = mock_config

            mock_wiki_instance = Mock()
            mock_wiki_api.return_value = mock_wiki_instance

            # Clear the cache first
            get_wikipedia_service.cache_clear()

            service = get_wikipedia_service()

            # Verify the service was configured with the mock config
            assert service.config == mock_config
            assert service.wiki == mock_wiki_instance

    def test_get_wikipedia_service_cache_clear(self):
        """Test that cache can be cleared and service is recreated."""
        with (
            patch(
                "mcp_server_wikipedia.wikipedia.module.wikipediaapi.Wikipedia"
            ) as mock_wiki_api,
            patch("mcp_server_wikipedia.wikipedia.module.wikipedia") as mock_wiki_lib,
            patch(
                "mcp_server_wikipedia.wikipedia.module.WikipediaConfig"
            ) as mock_config_class,
        ):
            mock_config = Mock()
            mock_config_class.return_value = mock_config
            mock_wiki_instance = Mock()
            mock_wiki_api.return_value = mock_wiki_instance

            # Clear the cache first
            get_wikipedia_service.cache_clear()

            # Get service, clear cache, get service again
            service1 = get_wikipedia_service()
            get_wikipedia_service.cache_clear()
            service2 = get_wikipedia_service()

            # Should be different instances after cache clear
            assert service1 is not service2

            # Config should be created twice (once for each instance)
            assert mock_config_class.call_count == 2
