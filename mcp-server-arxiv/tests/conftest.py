from datetime import datetime
from unittest.mock import MagicMock

import arxiv
import pytest
from mcp_server_arxiv.server import mcp_server
from mcp_server_arxiv.arxiv.config import ArxivConfig, ArxivApiError, ArxivConfigError
from mcp_server_arxiv.arxiv.models import ArxivSearchResult


@pytest.fixture
def fake_arxiv_result():
    fake = MagicMock(spec=arxiv.Result)
    fake.title = "Fake Paper Title"
    fake.summary = "This is a summary of a fake paper."
    fake.get_short_id.return_value = "1234.5678"
    fake.pdf_url = "https://arxiv.org/pdf/1234.5678.pdf"
    fake.published = datetime(2021, 1, 1)
    fake.authors = [MagicMock(name="Author One"), MagicMock(name="Author Two")]
    fake.authors[0].name = "Author One"
    fake.authors[1].name = "Author Two"
    return fake


@pytest.fixture
def mcp_server_fixture():
    return mcp_server

@pytest.fixture
def arxiv_config():
    return ArxivConfig(
        default_max_results=5,
        default_max_text_length=1000
    )


@pytest.fixture
def arxiv_config_custom():
    return ArxivConfig(
        default_max_results=10,
        default_max_text_length=2000
    )


@pytest.fixture
def mock_arxiv_client():
    mock_client = MagicMock()
    mock_client.search.return_value = iter([])  # Empty search by default
    return mock_client


@pytest.fixture
def multiple_arxiv_results():
    results = []
    for i in range(10):
        fake = MagicMock(spec=arxiv.Result)
        fake.title = f"Fake Paper Title {i+1}"
        fake.summary = f"This is a summary of fake paper {i+1}."
        fake.get_short_id.return_value = f"1234.567{i}"
        fake.pdf_url = f"https://arxiv.org/pdf/1234.567{i}.pdf"
        fake.published = datetime(2021, 1, i+1)
        fake.authors = [MagicMock(name=f"Author {i+1}")]
        fake.authors[0].name = f"Author {i+1}"
        results.append(fake)
    return results


@pytest.fixture
def sample_arxiv_search_result():
    return ArxivSearchResult(
        title="Test Paper",
        authors=["Test Author"],
        published_date="2024-01-01",
        summary="Test summary",
        arxiv_id="1234.5678",
        pdf_url="https://arxiv.org/pdf/1234.5678.pdf",
        full_text="Sample PDF text content"
    )


@pytest.fixture
def mock_pdf_content():
    return "This is sample PDF text content extracted from a research paper."


@pytest.fixture
def arxiv_api_error():
    return ArxivApiError("API request failed", details={"status_code": 500})


@pytest.fixture
def arxiv_config_error():
    return ArxivConfigError("Invalid configuration")
