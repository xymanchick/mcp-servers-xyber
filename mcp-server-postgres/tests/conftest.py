import os
import pytest
from unittest.mock import patch, MagicMock


os.environ.setdefault("POSTGRES_HOST", "localhost")
os.environ.setdefault("POSTGRES_PORT", "5432")
os.environ.setdefault("POSTGRES_USER", "test_user")
os.environ.setdefault("POSTGRES_PASSWORD", "test_password")
os.environ.setdefault("POSTGRES_DATABASE_NAME", "test_db")


patcher_engine = patch('mcp_server_postgres.postgres_client.database.create_async_engine')
patcher_sessionmaker = patch('mcp_server_postgres.postgres_client.database.async_sessionmaker')

mock_engine = patcher_engine.start()
mock_sessionmaker = patcher_sessionmaker.start()

mock_engine.return_value = MagicMock()
mock_sessionmaker.return_value = MagicMock()


@pytest.fixture(scope="session", autouse=True)
def setup_test_env():
    """Set up test environment variables."""
    yield
    patcher_engine.stop()
    patcher_sessionmaker.stop()


@pytest.fixture
def sample_agent():
    agent = MagicMock()
    agent.name = "test_agent"
    agent.uuid = "123e4567-e89b-12d3-a456-426614174000"
    agent.description = {"role": "test", "skills": ["testing"]}
    agent.ticker = "TST"
    agent.user_id = 1
    agent.image_hash = "abc123"
    agent.solana_address = None
    agent.base_address = None
    agent.__str__ = lambda self: f"Agent(name={agent.name}, ticker={agent.ticker})"
    return agent


@pytest.fixture
def mock_postgres_service():
    from mcp_server_postgres.postgres_client import _PostgresService
    service = MagicMock(spec=_PostgresService)
    return service


@pytest.fixture
def mock_server_context():
    from mcp_server_postgres.postgres_client import _PostgresService
    
    mock_db_service = MagicMock(spec=_PostgresService)
    mock_context = MagicMock()
    mock_context.lifespan_context.get.return_value = mock_db_service
    
    return mock_context, mock_db_service


@pytest.fixture
def mock_postgres_config():
    mock_config = MagicMock()
    mock_config.get_db_url.return_value = "postgresql://test:pass@localhost/test_db"
    mock_config.host = "localhost"
    mock_config.port = 5432
    mock_config.user = "test_user"
    mock_config.password = "test_password"
    mock_config.database_name = "test_db"
    return mock_config


@pytest.fixture
def text_content_unknown_tool():
    from mcp.types import TextContent
    return TextContent(type="text", text="Unknown tool: unknown_tool")


@pytest.fixture
def text_content_validation_error():
    from mcp.types import TextContent
    return TextContent(
        type="text", 
        text="Invalid arguments for tool 'get_character_by_name': validation error"
    )


@pytest.fixture
def text_content_database_error():
    from mcp.types import TextContent
    return TextContent(
        type="text", 
        text="Database error occurred while processing tool 'get_character_by_name': Database connection failed"
    )


@pytest.fixture
def text_content_success():
    from mcp.types import TextContent
    return TextContent(
        type="text", 
        text="Agent(name=test_agent, ticker=TST)"
    )
