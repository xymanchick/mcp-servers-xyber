import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from mcp_server_arxiv.arxiv.config import ArxivApiError, ArxivConfig, ArxivConfigError
from mcp_server_arxiv.arxiv.models import ArxivSearchResult
from mcp_server_arxiv.arxiv.module import (
    _ArxivService,
    _async_download_and_extract_pdf_text,
    get_arxiv_service,
)


class DummyTempDir:
    def __enter__(self):
        return "/tmp/fake"

    def __exit__(self, exc_type, exc_val, exc_tb):
        pass


class TestArxivService:
    @patch("mcp_server_arxiv.arxiv.module.arxiv")
    @patch("mcp_server_arxiv.arxiv.module.fitz")
    def test_init_success(self, mock_fitz, mock_arxiv, arxiv_config):
        mock_arxiv.Client.return_value = MagicMock()

        service = _ArxivService(arxiv_config)

        assert service.config == arxiv_config
        assert service.client is not None
        mock_arxiv.Client.assert_called_once()

    @patch("mcp_server_arxiv.arxiv.module.arxiv", None)
    @patch("mcp_server_arxiv.arxiv.module.fitz")

    def test_init_missing_arxiv_package(self, mock_fitz, arxiv_config):
        with pytest.raises(ArxivConfigError, match="Required package 'arxiv' or 'PyMuPDF' not installed."):
            _ArxivService(arxiv_config)

    @patch("mcp_server_arxiv.arxiv.module.arxiv")
    @patch("mcp_server_arxiv.arxiv.module.fitz", None)
    def test_init_missing_fitz_package(self, mock_arxiv, arxiv_config):
        with pytest.raises(ArxivConfigError, match="Required package 'arxiv' or 'PyMuPDF' not installed."):
            _ArxivService(arxiv_config)


    @pytest.mark.asyncio
    @patch("mcp_server_arxiv.arxiv.module.arxiv")
    @patch("mcp_server_arxiv.arxiv.module.fitz")
    async def test_search_empty_query(self, mock_fitz, mock_arxiv, arxiv_config):
        mock_arxiv.Client.return_value = MagicMock()
        service = _ArxivService(arxiv_config)

        with pytest.raises(ValueError, match="Search query cannot be empty."):
            await service.search("")

    @pytest.mark.asyncio
    @patch("mcp_server_arxiv.arxiv.module.arxiv")
    @patch("mcp_server_arxiv.arxiv.module.fitz")
    @patch("mcp_server_arxiv.arxiv.module._async_download_and_extract_pdf_text")
    @patch("mcp_server_arxiv.arxiv.module.tempfile.TemporaryDirectory")
    @patch("asyncio.get_running_loop")

    async def test_search_success(self, mock_get_loop, mock_temp_dir, mock_download, mock_fitz, mock_arxiv, arxiv_config_custom, multiple_arxiv_results):
        test_results = multiple_arxiv_results[:2]
        
        # Create a proper Result class and make mock objects instances of it
        class DummyResult: 
            pass
        
        # Make the mock objects instances of DummyResult
        for result in test_results:
            result.__class__ = DummyResult
            

        mock_arxiv.Result = DummyResult

        mock_client = MagicMock()
        mock_arxiv.Client.return_value = mock_client


        # Mock search results
        mock_paper1 = DummyResult()
        mock_paper1.title = "Paper 1"
        mock_paper1.authors = [MagicMock(name="Author1")]
        mock_paper1.published = MagicMock(strftime=MagicMock(return_value="2024-01-01"))
        mock_paper1.summary = "Summary 1"
        mock_paper1.get_short_id = MagicMock(return_value="1234.5678v1")
        mock_paper1.pdf_url = "http://arxiv.org/pdf/1234.5678v1.pdf"

        mock_paper2 = DummyResult()
        mock_paper2.title = "Paper 2"
        mock_paper2.authors = [MagicMock(name="Author2")]
        mock_paper2.published = MagicMock(strftime=MagicMock(return_value="2024-01-02"))
        mock_paper2.summary = "Summary 2"
        mock_paper2.get_short_id = MagicMock(return_value="8765.4321v1")
        mock_paper2.pdf_url = "http://arxiv.org/pdf/8765.4321v1.pdf"

        # Mock arxiv.Search and client.results

        mock_search = MagicMock()
        mock_arxiv.Search.return_value = mock_search
        mock_client.results.return_value = iter(test_results)

        async def fake_run_in_executor(executor, func, *args):
            return func(*args)

        mock_loop = MagicMock()
        mock_loop.run_in_executor.side_effect = fake_run_in_executor
        mock_get_loop.return_value = mock_loop

        mock_download.side_effect = [
            ArxivSearchResult(
                title=test_results[0].title,
                authors=[test_results[0].authors[0].name],
                published_date="2021-01-01",
                summary=test_results[0].summary,
                arxiv_id=test_results[0].get_short_id(),
                pdf_url=test_results[0].pdf_url,
                processing_error=None,
            ),
            ArxivSearchResult(
                title=test_results[1].title,
                authors=[test_results[1].authors[0].name],
                published_date="2021-01-02", 
                summary=test_results[1].summary,
                arxiv_id=test_results[1].get_short_id(),
                pdf_url=test_results[1].pdf_url,
                processing_error=None,
            ),
        ]

        service = _ArxivService(arxiv_config_custom)
        results = await service.search("quantum computing")

        assert len(results) == 2
        assert results[0].title == test_results[0].title
        assert results[1].title == test_results[1].title
        assert results[0].processing_error is None
        assert results[1].processing_error is None

    @pytest.mark.asyncio
    @patch("mcp_server_arxiv.arxiv.module.arxiv")
    @patch("mcp_server_arxiv.arxiv.module.fitz")
    @patch("asyncio.get_running_loop")
    async def test_search_arxiv_api_error(self, mock_get_loop, mock_fitz, mock_arxiv, arxiv_config):
        mock_client = MagicMock()
        mock_arxiv.Client.return_value = mock_client
        mock_arxiv.Search.return_value = MagicMock()

        async def fake_run_in_executor(executor, func, *args):
            raise Exception("arxiv error")

        mock_loop = MagicMock()
        mock_loop.run_in_executor.side_effect = fake_run_in_executor
        mock_get_loop.return_value = mock_loop

        service = _ArxivService(arxiv_config)
        with pytest.raises(ArxivApiError):
            await service.search("test")

    @pytest.mark.asyncio
    @patch("mcp_server_arxiv.arxiv.module.arxiv")
    @patch("mcp_server_arxiv.arxiv.module.fitz")
    @patch("asyncio.get_running_loop")
    async def test_search_no_results(self, mock_get_loop, mock_fitz, mock_arxiv):
        config = ArxivConfig()
        mock_client = MagicMock()
        mock_arxiv.Client.return_value = mock_client
        mock_arxiv.Search.return_value = MagicMock()

        async def fake_run_in_executor(executor, func, *args):
            return []

        mock_loop = MagicMock()
        mock_loop.run_in_executor.side_effect = fake_run_in_executor
        mock_get_loop.return_value = mock_loop

        service = _ArxivService(config)
        results = await service.search("no results query")
        assert results == []

    @pytest.mark.asyncio
    @patch("mcp_server_arxiv.arxiv.module.arxiv")
    @patch("mcp_server_arxiv.arxiv.module.fitz")
    @patch(
        "mcp_server_arxiv.arxiv.module._async_download_and_extract_pdf_text",
        new_callable=AsyncMock,
    )
    @patch(
        "mcp_server_arxiv.arxiv.module.tempfile.TemporaryDirectory",
        return_value=DummyTempDir(),
    )
    @patch("asyncio.get_running_loop")
    async def test_search_pdf_processing_error(
        self, mock_get_loop, mock_temp_dir, mock_download, mock_fitz, mock_arxiv
    ):
        config = ArxivConfig(default_max_results=1, default_max_text_length=1000)

        class DummyResult:
            pass

        mock_client = MagicMock()
        mock_arxiv.Client.return_value = mock_client

        mock_arxiv.Result = DummyResult

        mock_paper = DummyResult()
        mock_paper.title = "Paper 1"
        mock_paper.authors = [MagicMock(name="Author1")]
        mock_paper.published = MagicMock(strftime=MagicMock(return_value="2024-01-01"))
        mock_paper.summary = "Summary 1"
        mock_paper.get_short_id = MagicMock(return_value="1234.5678v1")
        mock_paper.pdf_url = "http://arxiv.org/pdf/1234.5678v1.pdf"

        mock_arxiv.Search.return_value = MagicMock()
        mock_client.results.return_value = iter([mock_paper])

        async def fake_run_in_executor(executor, func, *args):
            return func(*args)

        mock_loop = MagicMock()
        mock_loop.run_in_executor.side_effect = fake_run_in_executor
        mock_get_loop.return_value = mock_loop

        mock_download.side_effect = [Exception("PDF error")]

        service = _ArxivService(config)
        results = await service.search("quantum computing")
        assert len(results) == 1
        assert results[0].processing_error is not None
        assert "PDF error" in results[0].processing_error


@pytest.mark.asyncio
@patch("fitz.open")
async def test_pdf_processing_success(mock_fitz_open, fake_arxiv_result, tmp_path):
    temp_dir = str(tmp_path)
    arxiv_id = fake_arxiv_result.get_short_id()
    pdf_path = tmp_path / f"{arxiv_id}.pdf"

    pdf_path.write_bytes(b"%PDF-1.4 fake")

    def fake_download_pdf(dirpath, filename):
        target = tmp_path / filename
        target.write_bytes(b"%PDF-1.4 downloaded")

    fake_arxiv_result.download_pdf = fake_download_pdf

    fake_page = MagicMock()
    fake_page.get_text.return_value = "Fake page content"
    fake_doc = MagicMock()
    fake_doc.__iter__.return_value = [fake_page]
    fake_doc.close.return_value = None
    mock_fitz_open.return_value = fake_doc

    paper_details = {
        "paper_obj": fake_arxiv_result,
        "arxiv_id": arxiv_id,
        "pdf_url": fake_arxiv_result.pdf_url,
    }

    result: ArxivSearchResult = await _async_download_and_extract_pdf_text(
        paper_details, temp_dir, max_text_length=1000
    )

    assert isinstance(result, ArxivSearchResult)
    assert result.arxiv_id == arxiv_id
    assert "Fake page content" in result.full_text
    assert result.processing_error is None
    assert result.title == fake_arxiv_result.title
    assert "Author One" in result.authors


@pytest.mark.asyncio
@patch("fitz.open")
async def test_pdf_processing_empty_text(mock_fitz_open, fake_arxiv_result, tmp_path):
    temp_dir = str(tmp_path)
    arxiv_id = fake_arxiv_result.get_short_id()
    pdf_path = tmp_path / f"{arxiv_id}.pdf"
    pdf_path.write_bytes(b"%PDF-1.4")

    def fake_download_pdf(dirpath, filename):
        (tmp_path / filename).write_bytes(b"%PDF-1.4")

    fake_arxiv_result.download_pdf = fake_download_pdf

    fake_page = MagicMock()
    fake_page.get_text.return_value = ""
    fake_doc = MagicMock()
    fake_doc.__iter__.return_value = [fake_page]
    fake_doc.close.return_value = None
    mock_fitz_open.return_value = fake_doc

    paper_details = {
        "paper_obj": fake_arxiv_result,
        "arxiv_id": arxiv_id,
        "pdf_url": fake_arxiv_result.pdf_url,
    }

    result = await _async_download_and_extract_pdf_text(paper_details, temp_dir, None)

    assert result.full_text == "[Could not extract text content from PDF]"
    assert result.processing_error is None



class TestGetArxivService:
    @patch("mcp_server_arxiv.arxiv.module.ArxivConfig")
    @patch("mcp_server_arxiv.arxiv.module._ArxivService")
    @patch("mcp_server_arxiv.arxiv.module.logger")
    def test_get_arxiv_service_success(self, mock_logger, mock_arxiv_service_class, mock_config_class):
        get_arxiv_service.cache_clear()
        
        mock_config = MagicMock()
        mock_config_class.return_value = mock_config
        
        mock_service = MagicMock()
        mock_arxiv_service_class.return_value = mock_service

        result = get_arxiv_service()

        assert result == mock_service
        mock_config_class.assert_called_once()
        mock_arxiv_service_class.assert_called_once_with(config=mock_config)
        mock_logger.info.assert_called_once_with(
            "_ArxivService instance created successfully via get_arxiv_service."
        )

    @patch("mcp_server_arxiv.arxiv.module.ArxivConfig")
    @patch("mcp_server_arxiv.arxiv.module._ArxivService")
    @patch("mcp_server_arxiv.arxiv.module.logger")
    def test_get_arxiv_service_singleton_behavior(self, mock_logger, mock_arxiv_service_class, mock_config_class):
        get_arxiv_service.cache_clear()
        
        mock_config = MagicMock()
        mock_config_class.return_value = mock_config
        
        mock_service = MagicMock()
        mock_arxiv_service_class.return_value = mock_service

        result1 = get_arxiv_service()
        result2 = get_arxiv_service()

        assert result1 == result2
        assert result1 is result2
        mock_config_class.assert_called_once()
        mock_arxiv_service_class.assert_called_once_with(config=mock_config)

    @patch("mcp_server_arxiv.arxiv.module.ArxivConfig")
    @patch("mcp_server_arxiv.arxiv.module.logger")
    def test_get_arxiv_service_config_error(self, mock_logger, mock_config_class):
        get_arxiv_service.cache_clear()
        
        config_error = ArxivConfigError("Configuration validation failed")
        mock_config_class.side_effect = config_error

        with pytest.raises(ArxivConfigError, match="Configuration validation failed"):
            get_arxiv_service()

        mock_logger.error.assert_called_once()
        error_call = mock_logger.error.call_args[0][0]
        assert "FATAL: Failed to initialize _ArxivService" in error_call
        assert "Configuration validation failed" in error_call

    @patch("mcp_server_arxiv.arxiv.module.ArxivConfig")
    @patch("mcp_server_arxiv.arxiv.module._ArxivService")
    @patch("mcp_server_arxiv.arxiv.module.logger")
    def test_get_arxiv_service_service_init_error(self, mock_logger, mock_arxiv_service_class, mock_config_class):
        get_arxiv_service.cache_clear()
        
        mock_config = MagicMock()
        mock_config_class.return_value = mock_config
        
        service_error = ArxivConfigError("Required packages not installed")
        mock_arxiv_service_class.side_effect = service_error

        with pytest.raises(ArxivConfigError, match="Required packages not installed"):
            get_arxiv_service()

        mock_logger.error.assert_called_once()
        error_call = mock_logger.error.call_args[0][0]
        assert "FATAL: Failed to initialize _ArxivService" in error_call

    @patch("mcp_server_arxiv.arxiv.module.ArxivConfig")
    @patch("mcp_server_arxiv.arxiv.module._ArxivService")
    @patch("mcp_server_arxiv.arxiv.module.logger")
    def test_get_arxiv_service_unexpected_error(self, mock_logger, mock_arxiv_service_class, mock_config_class):
        get_arxiv_service.cache_clear()
        
        mock_config = MagicMock()
        mock_config_class.return_value = mock_config
        
        unexpected_error = RuntimeError("Unexpected runtime error")
        mock_arxiv_service_class.side_effect = unexpected_error

        with pytest.raises(ArxivConfigError, match="Unexpected error during _ArxivService initialization"):
            get_arxiv_service()

        mock_logger.error.assert_called_once()
        error_call = mock_logger.error.call_args[0][0]
        assert "FATAL: Unexpected error initializing _ArxivService" in error_call

    def teardown_method(self):
        get_arxiv_service.cache_clear()


