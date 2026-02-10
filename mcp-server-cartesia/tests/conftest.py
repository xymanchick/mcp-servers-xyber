import os
import tempfile
from unittest.mock import AsyncMock, Mock, patch

import pytest
from fastmcp import Context

# Import Mocking Fixtures


@pytest.fixture(autouse=True)
def mock_langchain_imports():
    with patch.dict(
        "sys.modules",
        {
            "langchain_core.messages": Mock(),
            "langchain_core.tools": Mock(),
            "langchain_mcp_adapters.client": Mock(),
            "langchain_together": Mock(),
            "langgraph.prebuilt": Mock(),
            "dotenv": Mock(),
        },
    ):
        yield


# Environment Variables Fixtures


@pytest.fixture
def env_backup():
    backup = {
        "CARTESIA_API_KEY": os.getenv("CARTESIA_API_KEY"),
        "TOGETHER_API_KEY": os.getenv("TOGETHER_API_KEY"),
        "MCP_CARTESIA_PORT": os.getenv("MCP_CARTESIA_PORT"),
    }
    yield backup
    for key, value in backup.items():
        if value is None:
            os.environ.pop(key, None)
        else:
            os.environ[key] = value


@pytest.fixture
def valid_cartesia_api_key(env_backup):
    api_key = "valid_cartesia_api_key_1234567890"
    os.environ["CARTESIA_API_KEY"] = api_key
    return api_key


@pytest.fixture
def mock_cartesia_config():
    def create_mock_config(api_key="test_key", output_dir=None):
        config = Mock()
        config.api_key = api_key
        config.voice_id = "a38e4e85-e815-43ab-acf1-907c4688dd6c"
        config.model_id = "sonic-2"
        config.output_dir = output_dir or "/tmp/test_audio"
        config._abs_output_dir = output_dir or "/tmp/test_audio"
        config.absolute_output_dir = output_dir or "/tmp/test_audio"
        config.output_format = {
            "container": "wav",
            "encoding": "pcm_f32le",
            "sample_rate": 44100,
        }
        config.output_format_container = "wav"
        config.output_format_encoding = "pcm_f32le"
        config.output_format_sample_rate = 44100
        return config

    return create_mock_config


@pytest.fixture
def valid_together_api_key(env_backup):
    api_key = "valid_together_api_key_1234567890"
    os.environ["TOGETHER_API_KEY"] = api_key
    return api_key


@pytest.fixture
def invalid_cartesia_api_key(env_backup):
    api_key = "your_cartesia_api_key_here"
    os.environ["CARTESIA_API_KEY"] = api_key
    return api_key


@pytest.fixture
def custom_mcp_port(env_backup):
    port = "9999"
    os.environ["MCP_CARTESIA_PORT"] = port
    return port


# Client Mock Fixtures


@pytest.fixture
def mock_llm_model():
    model = Mock()
    model.model = "meta-llama/Meta-Llama-3.1-8B-Instruct-Turbo"
    return model


@pytest.fixture
def mock_chat_together():
    mock_class = Mock()
    mock_instance = Mock()
    mock_instance.model = "meta-llama/Meta-Llama-3.1-8B-Instruct-Turbo"
    mock_class.return_value = mock_instance
    return mock_class


@pytest.fixture
def mock_mcp_client():
    mock_client_instance = AsyncMock()
    mock_context_manager = AsyncMock()
    mock_context_manager.__aenter__ = AsyncMock(return_value=mock_client_instance)
    mock_context_manager.__aexit__ = AsyncMock(return_value=None)

    mock_client = Mock()
    mock_client.return_value = mock_context_manager

    return {
        "client": mock_client,
        "context_manager": mock_context_manager,
        "instance": mock_client_instance,
    }


@pytest.fixture
def mock_cartesia_tool():
    tool = AsyncMock()
    tool.name = "generate_cartesia_tts"
    tool.description = "Generate TTS using Cartesia"
    tool.arun.return_value = (
        "Successfully generated speech and saved to: /app/audio_outputs/test_output.wav"
    )
    return tool


@pytest.fixture
def mock_react_agent():
    agent = AsyncMock()
    mock_response = {"messages": [Mock(content="Agent successfully generated speech")]}
    agent.ainvoke.return_value = mock_response
    return agent


# Test Data Fixtures


@pytest.fixture
def sample_tool_input():
    return {
        "text": "Hello world test",
        "voice": {"id": "a38e4e85-e815-43ab-acf1-907c4688dd6c"},
        "model_id": "sonic-2",
    }


@pytest.fixture
def sample_tool_inputs():
    return [
        {
            "text": "Short text",
            "voice": {"id": "voice-1"},
            "model_id": "sonic-1",
        },
        {
            "text": "Very long text that should be processed correctly by the TTS system",
            "voice": {"id": "voice-2"},
            "model_id": "sonic-2",
        },
        {
            "text": "Text with special characters: @#$%^&*()",
            "voice": {"id": "voice-3"},
            "model_id": "sonic-2",
        },
    ]


@pytest.fixture
def sample_server_responses():
    return {
        "success": [
            "Successfully generated speech and saved to: /app/audio_outputs/test_file.wav",
            'Successfully generated speech and saved to: "/app/audio_outputs/quoted_file.wav"',
            "Successfully generated speech and saved to: /app/audio_outputs/file_with_timestamp_1234567890.wav",
        ],
        "errors": [
            "Error: Invalid API key",
            "Error: Text too long",
            "Error: Voice not found",
            "Connection timeout",
            "",  # Empty response
        ],
    }


# File System Fixtures


@pytest.fixture
def temp_audio_file():
    temp_file = tempfile.NamedTemporaryFile(suffix=".wav", delete=False)
    temp_file.write(b"fake audio data")
    temp_file.close()

    yield temp_file.name

    if os.path.exists(temp_file.name):
        os.unlink(temp_file.name)


# Original Server Test Fixtures


@pytest.fixture
def mock_cartesia_service():
    service = AsyncMock()
    service.generate_speech = AsyncMock(return_value="/tmp/test.wav")
    return service


@pytest.fixture
def mock_context(mock_cartesia_service):
    ctx = AsyncMock(spec=Context)
    ctx.request_context.lifespan_context = {"cartesia_service": mock_cartesia_service}
    return ctx


@pytest.fixture(autouse=True)
def reset_mocks(mock_cartesia_service):
    yield
    mock_cartesia_service.reset_mock()
    mock_cartesia_service.generate_speech.reset_mock()


@pytest.fixture
def mock_cartesia_service_with_error():
    service = AsyncMock()
    service.generate_speech = AsyncMock()
    return service


@pytest.fixture
def mock_context_with_error_service(mock_cartesia_service_with_error):
    ctx = AsyncMock(spec=Context)
    ctx.request_context.lifespan_context = {
        "cartesia_service": mock_cartesia_service_with_error
    }
    return ctx


@pytest.fixture
def sample_voice_with_id():
    return {"id": "test_voice_id", "name": "Test Voice", "language": "en"}


@pytest.fixture
def sample_voice_without_id():
    return {"name": "Test Voice", "language": "en", "gender": "female"}


@pytest.fixture
def sample_text():
    return "Hello world, this is a test message for text-to-speech conversion."


@pytest.fixture
def sample_model_id():
    return "sonic-english"
