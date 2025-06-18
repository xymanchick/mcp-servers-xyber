import pytest
from unittest.mock import patch, MagicMock
from mcp_server_arxiv.arxiv.module import _async_download_and_extract_pdf_text
from mcp_server_arxiv.arxiv.models import ArxivSearchResult
import urllib.error
from tenacity import RetryError
import arxiv
from pymupdf import Document
import re
import os
from reportlab.pdfgen import canvas


def mock_download_pdf_side_effect(*args, **kwargs):
    """Mock implementation of urllib's urlretrieve function."""
    temp_dir = kwargs.get("dirpath", ".")
    safe_filename = kwargs.get("filename", "mock_paper.pdf")
    pdf_path = os.path.join(temp_dir, safe_filename)
    # Create a mock PDF file for testing
    c = canvas.Canvas(pdf_path)
    c.drawString(100, 750, "Extracted text from PDF")
    c.save()


@pytest.fixture
def mock_paper_details():
    """Fixture for mock paper details."""
    return {
        "paper_obj": MagicMock(),
        "arxiv_id": "1234.56789",
        "pdf_url": "http://arxiv.org/pdf/1234.56789.pdf",
    }


@pytest.fixture
def mock_temp_dir():
    """Fixture for temporary directory."""
    return os.path.join(os.getcwd(), "mcp-server-arxiv", "tests", "data")


def mock_download_side_effect_http_error(*args, **kwargs):
    """Simulate an HTTP error during PDF download."""
    raise urllib.error.HTTPError(
        url="http://arxiv.org/pdf/1234.56789.pdf",
        code=500,
        msg="Internal Server Error",
        hdrs=None,
        fp=None,
    )


def mock_download_side_effect_do_nothing(*args, **kwargs):
    pass


def mock_download_side_effect_urllib_error(*args, **kwargs):
    """Simulate a URLError during PDF download."""
    raise urllib.error.URLError("Network error")


def mock_download_side_effect_success(*args, **kwargs):
    """Simulate a successful PDF download."""
    return ArxivSearchResult(
        arxiv_id="1234.56789",
        pdf_url="http://arxiv.org/pdf/1234.56789.pdf",
        full_text="",
        processing_error=None,
        title="Mock Paper Title",
        authors=["Author One", "Author Two"],
        published_date="2023-10-01",
        summary="This is a mock summary of the paper.",
    )


def mock_download_side_effect_timeout(*args, **kwargs):
    """Simulate a timeout error during PDF download."""
    raise urllib.error.URLError("Timeout error")


# @patch("mcp_server_arxiv.arxiv.module.arxiv.Result.download_pdf")
@pytest.mark.asyncio
async def test_async_download_and_extract_pdf_text_successful_download(
    #
    mock_paper_details,
    mock_temp_dir,
):
    """Test successful PDF download and text extraction."""

    # mock_download_pdf.side_effect = mock_download_pdf_side_effect
    mock_paper_details["paper_obj"].download_pdf.side_effect = (
        mock_download_pdf_side_effect
    )
    result = await _async_download_and_extract_pdf_text(
        mock_paper_details, mock_temp_dir, max_text_length=1000
    )

    assert isinstance(result, ArxivSearchResult)
    assert result.processing_error is None
    assert result.full_text == "Extracted text from PDF"


@patch("mcp_server_arxiv.arxiv.module.arxiv.Result.download_pdf")
@patch("mcp_server_arxiv.arxiv.module.fitz.open")
@pytest.mark.asyncio
async def test_async_download_and_extract_pdf_text_retry_logic(
    mock_download_pdf, mock_fitz_open, mock_paper_details, mock_temp_dir, caplog
):
    """Test retry logic for transient errors during PDF download."""
    # Simulate transient errors during download
    mock_download_pdf.side_effect = mock_download_side_effect_timeout

    with pytest.raises(RetryError):
        result = await _async_download_and_extract_pdf_text(
            mock_paper_details, mock_temp_dir, max_text_length=1000
        )

        assert isinstance(result, ArxivSearchResult)
        assert "Timeout error" in result.processing_error

    # Check that retries are logged
    assert len(re.findall(r"ERROR", caplog.text)) > 4
