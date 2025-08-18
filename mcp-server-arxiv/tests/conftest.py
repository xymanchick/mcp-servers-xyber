from datetime import datetime
from unittest.mock import MagicMock

import arxiv
import pytest
from mcp_server_arxiv.server import mcp_server


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
