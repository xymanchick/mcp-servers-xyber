import logging

import pytest
from mcp_server_qdrant.server import mcp_server as mcp_server_instance


# disable FastMCP error logging
@pytest.fixture(autouse=True)
def disable_all_logging():
    logging.disable(logging.ERROR)
    yield
    logging.disable(logging.NOTSET)


@pytest.fixture
def mcp_server():
    return mcp_server_instance
