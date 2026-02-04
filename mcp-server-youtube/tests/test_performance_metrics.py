"""
Pytest-compatible test file for performance metrics middleware.

This file contains individual test functions that pytest can discover and run.
Each test validates specific aspects of the performance metrics middleware.
"""

import logging
import re
import time
from typing import Dict, List, Tuple, Optional
from collections import defaultdict

import httpx
import pytest

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

BASE_URL = "http://localhost:8000"


class PrometheusMetricsParser:
    """Proper Prometheus metrics parser that handles labels correctly."""
    
    @staticmethod
    def parse_metrics(metrics_text: str) -> Dict[str, list[Tuple[Dict[str, str], float]]]:
        """Parse Prometheus metrics format correctly."""
        metrics = defaultdict(list)
        
        for line in metrics_text.split('\n'):
            line = line.strip()
            if not line or line.startswith('#'):
                continue
            
            if line.startswith('youtube_mcp_'):
                match = re.match(r'^([a-zA-Z_:][a-zA-Z0-9_:]*)(.*?)\s+([+-]?[0-9]*\.?[0-9]+([eE][+-]?[0-9]+)?)$', line)
                if match:
                    metric_name = match.group(1)
                    labels_part = match.group(2)
                    value = float(match.group(3))
                    
                    labels = {}
                    if labels_part.startswith('{') and labels_part.endswith('}'):
                        labels_str = labels_part[1:-1]
                        label_matches = re.findall(r'(\w+)="([^"]*)"', labels_str)
                        labels = dict(label_matches)
                    
                    metrics[metric_name].append((labels, value))
        
        return dict(metrics)
    
    @staticmethod
    def get_metric_value(parsed_metrics: Dict, metric_name: str, labels: Optional[Dict[str, str]] = None) -> float:
        """Get specific metric value by name and labels."""
        if metric_name not in parsed_metrics:
            return 0.0
        
        if labels is None:
            return sum(value for _, value in parsed_metrics[metric_name])
        
        for metric_labels, value in parsed_metrics[metric_name]:
            if all(metric_labels.get(k) == v for k, v in labels.items()):
                return value
        
        return 0.0
    
    @staticmethod
    def get_metric_count(parsed_metrics: Dict, metric_name: str) -> int:
        """Get number of metric entries for a given metric name."""
        return len(parsed_metrics.get(metric_name, []))


@pytest.fixture(scope="session")
async def http_client():
    """HTTP client fixture for making requests."""
    async with httpx.AsyncClient(timeout=30.0) as client:
        yield client


@pytest.fixture(scope="session")
def metrics_parser():
    """Metrics parser fixture."""
    return PrometheusMetricsParser()


@pytest.fixture(scope="session")
async def check_server():
    """Check if server is running before tests."""
    async with httpx.AsyncClient(timeout=5.0) as client:
        try:
            response = await client.get(f"{BASE_URL}/health")
            if response.status_code != 200:
                pytest.skip(f"Server not accessible at {BASE_URL}")
        except Exception:
            pytest.skip(f"Server not running at {BASE_URL}")


@pytest.mark.asyncio
async def test_server_accessibility(http_client, check_server):
    """Test that the server is accessible."""
    response = await http_client.get(f"{BASE_URL}/health")
    assert response.status_code == 200
    logger.info("✓ Server is accessible")


@pytest.mark.asyncio
async def test_metrics_endpoint_exists(http_client, check_server):
    """Test that /metrics endpoint is accessible."""
    response = await http_client.get(f"{BASE_URL}/metrics")
    assert response.status_code == 200
    assert 'youtube_mcp_request_count' in response.text
    assert 'youtube_mcp_request_latency_seconds' in response.text
    assert 'youtube_mcp_error_count' in response.text
    logger.info("✓ Metrics endpoint accessible with expected content")


@pytest.mark.asyncio
async def test_prometheus_metrics_parsing(http_client, metrics_parser, check_server):
    """Test that Prometheus metrics can be parsed correctly."""
    response = await http_client.get(f"{BASE_URL}/metrics")
    assert response.status_code == 200
    
    parsed_metrics = metrics_parser.parse_metrics(response.text)
    assert len(parsed_metrics) > 0, "Should have parseable metrics"
    
    # Verify expected metric types exist
    expected_metrics = [
        'youtube_mcp_request_count',
        'youtube_mcp_request_latency_seconds',
        'youtube_mcp_error_count',
        'youtube_mcp_error_count_total'
    ]
    
    for metric in expected_metrics:
        assert any(metric in name for name in parsed_metrics.keys()), f"Should have {metric} metrics"
    
    logger.info(f"✓ Parsed {len(parsed_metrics)} metric types successfully")


@pytest.mark.asyncio
async def test_request_counting(http_client, metrics_parser, check_server):
    """Test that requests are counted properly."""
    # Get baseline metrics
    response = await http_client.get(f"{BASE_URL}/metrics")
    baseline_metrics = metrics_parser.parse_metrics(response.text)
    baseline_count = metrics_parser.get_metric_value(baseline_metrics, 'youtube_mcp_request_count')
    
    # Make a test request
    await http_client.get(f"{BASE_URL}/health")
    
    # Check updated metrics
    response = await http_client.get(f"{BASE_URL}/metrics")
    updated_metrics = metrics_parser.parse_metrics(response.text)
    updated_count = metrics_parser.get_metric_value(updated_metrics, 'youtube_mcp_request_count')
    
    assert updated_count > baseline_count, f"Request count should increase: {baseline_count} -> {updated_count}"
    logger.info(f"✓ Request counting works: {baseline_count} → {updated_count}")


@pytest.mark.asyncio
async def test_request_latency_tracking(http_client, metrics_parser, check_server):
    """Test that request latency is tracked."""
    # Get baseline metrics
    response = await http_client.get(f"{BASE_URL}/metrics")
    baseline_metrics = metrics_parser.parse_metrics(response.text)
    baseline_latency_count = metrics_parser.get_metric_count(baseline_metrics, 'youtube_mcp_request_latency_seconds')
    
    # Make a test request
    start_time = time.perf_counter()
    await http_client.get(f"{BASE_URL}/health")
    end_time = time.perf_counter()
    client_duration = end_time - start_time
    
    # Check updated metrics
    response = await http_client.get(f"{BASE_URL}/metrics")
    updated_metrics = metrics_parser.parse_metrics(response.text)
    updated_latency_count = metrics_parser.get_metric_count(updated_metrics, 'youtube_mcp_request_latency_seconds')
    
    assert updated_latency_count > baseline_latency_count, "Latency metrics should increase"
    assert client_duration > 0, "Client duration should be positive"
    
    # Verify histogram buckets exist
    latency_metrics = updated_metrics.get('youtube_mcp_request_latency_seconds', [])
    bucket_count = sum(1 for labels, _ in latency_metrics if 'le' in labels)
    assert bucket_count > 0, "Should have histogram buckets"
    
    logger.info(f"✓ Latency tracking works: {updated_latency_count - baseline_latency_count} new measurements")


@pytest.mark.asyncio
async def test_error_classification_404(http_client, metrics_parser, check_server):
    """Test 404 error classification."""
    # Make request to non-existent endpoint
    response = await http_client.get(f"{BASE_URL}/nonexistent")
    assert response.status_code == 404
    
    # Check error metrics
    metrics_response = await http_client.get(f"{BASE_URL}/metrics")
    metrics = metrics_parser.parse_metrics(metrics_response.text)
    
    not_found_errors = metrics_parser.get_metric_value(
        metrics,
        'youtube_mcp_error_count',
        {'error_type': 'not_found_error'}
    )
    assert not_found_errors > 0, "Should have not_found_error metrics"
    logger.info(f"✓ 404 error classification: {not_found_errors} occurrences")


@pytest.mark.asyncio
async def test_error_classification_validation(http_client, metrics_parser, check_server):
    """Test validation error classification."""
    # Make invalid request
    response = await http_client.post(
        f"{BASE_URL}/youtube_search_and_transcript",
        json={"query": ""}  # Invalid: empty query
    )
    assert response.status_code == 400
    
    # Check error metrics
    metrics_response = await http_client.get(f"{BASE_URL}/metrics")
    metrics = metrics_parser.parse_metrics(metrics_response.text)
    
    validation_errors = metrics_parser.get_metric_value(
        metrics,
        'youtube_mcp_error_count',
        {'error_type': 'validation_error'}
    )
    assert validation_errors > 0, "Should have validation_error metrics"
    logger.info(f"✓ Validation error classification: {validation_errors} occurrences")


@pytest.mark.asyncio
async def test_request_method_labeling(http_client, metrics_parser, check_server):
    """Test that requests are labeled with correct HTTP methods."""
    # Make GET request
    await http_client.get(f"{BASE_URL}/health")
    
    # Make POST request
    await http_client.post(
        f"{BASE_URL}/youtube_search_and_transcript",
        json={"query": "test", "max_results": 1}
    )
    
    # Check metrics have correct method labels
    response = await http_client.get(f"{BASE_URL}/metrics")
    metrics = metrics_parser.parse_metrics(response.text)
    
    get_requests = metrics_parser.get_metric_value(
        metrics,
        'youtube_mcp_request_count',
        {'method': 'GET', 'path': '/health'}
    )
    
    post_requests = metrics_parser.get_metric_value(
        metrics,
        'youtube_mcp_request_count',
        {'method': 'POST', 'path': '/youtube_search_and_transcript'}
    )
    
    assert get_requests > 0, "Should have GET request metrics"
    assert post_requests > 0, "Should have POST request metrics"
    logger.info(f"✓ Method labeling: GET={get_requests}, POST={post_requests}")


@pytest.mark.asyncio
async def test_user_agent_tracking(http_client, metrics_parser, check_server):
    """Test request tracing with different user agents."""
    user_agents = ["TestBot/1.0", "TestBot/2.0", "TestBot/3.0"]
    
    baseline_response = await http_client.get(f"{BASE_URL}/metrics")
    baseline_metrics = metrics_parser.parse_metrics(baseline_response.text)
    baseline_health = metrics_parser.get_metric_value(
        baseline_metrics,
        'youtube_mcp_request_count',
        {'method': 'GET', 'path': '/health'}
    )
    
    # Make requests with different user agents
    for user_agent in user_agents:
        headers = {"User-Agent": user_agent}
        response = await http_client.get(f"{BASE_URL}/health", headers=headers)
        assert response.status_code == 200
    
    # Verify all requests were tracked
    updated_response = await http_client.get(f"{BASE_URL}/metrics")
    updated_metrics = metrics_parser.parse_metrics(updated_response.text)
    updated_health = metrics_parser.get_metric_value(
        updated_metrics,
        'youtube_mcp_request_count',
        {'method': 'GET', 'path': '/health'}
    )
    
    assert updated_health >= baseline_health + len(user_agents), "Should track all requests"
    logger.info(f"✓ User agent tracking: {updated_health - baseline_health} new requests")


@pytest.mark.asyncio
async def test_total_error_counting(http_client, metrics_parser, check_server):
    """Test that total error count is maintained."""
    baseline_response = await http_client.get(f"{BASE_URL}/metrics")
    baseline_metrics = metrics_parser.parse_metrics(baseline_response.text)
    baseline_total_errors = metrics_parser.get_metric_value(baseline_metrics, 'youtube_mcp_error_count_total')
    
    # Generate errors
    await http_client.get(f"{BASE_URL}/nonexistent")  # 404
    await http_client.post(f"{BASE_URL}/youtube_search_and_transcript", json={"query": ""})  # 400
    
    # Check total error count increased
    updated_response = await http_client.get(f"{BASE_URL}/metrics")
    updated_metrics = metrics_parser.parse_metrics(updated_response.text)
    updated_total_errors = metrics_parser.get_metric_value(updated_metrics, 'youtube_mcp_error_count_total')
    
    assert updated_total_errors > baseline_total_errors, "Total error count should increase"
    logger.info(f"✓ Total error counting: {baseline_total_errors} → {updated_total_errors}")
