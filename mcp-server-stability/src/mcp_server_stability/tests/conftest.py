from unittest.mock import Mock

import pytest


@pytest.fixture
def sample_api_key():
    return "sk-test-api-key-12345"


@pytest.fixture
def sample_url():
    return "https://api.stability.ai/v2beta/stable-image/generate/core"


@pytest.fixture
def mock_stability_config(sample_api_key, sample_url):
    config = Mock()
    config.api_key = sample_api_key
    config.url = sample_url
    return config


@pytest.fixture
def sample_generation_params():
    return {"prompt": "A beautiful landscape", "width": 512, "height": 512}


@pytest.fixture
def mock_successful_response():
    response = Mock()
    response.is_success = True
    response.status_code = 200
    response.content = b"fake_image_data"
    return response


@pytest.fixture
def mock_error_response():
    response = Mock()
    response.is_success = False
    response.status_code = 400
    response.text = "Bad Request"
    return response
