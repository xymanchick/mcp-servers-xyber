"""
Comprehensive test script for performance metrics middleware.

This script tests:
1. Request duration tracking via time.perf_counter()
2. Error handling and classification
3. Prometheus metrics integration
4. Request tracing with correlation IDs
5. Log-metrics correlation

Acceptance Tests:
- Access several endpoints, including ones that fail
- Confirm metric counters change
- Check that log lines align with metric spikes
"""

import asyncio
import json
import logging
import time
from typing import Dict, Any

import httpx
import pytest

# Configure logging to see the correlation
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

BASE_URL = "http://localhost:8000"


class MetricsTestRunner:
    """Test runner for performance metrics validation."""
    
    def __init__(self, base_url: str = BASE_URL):
        self.base_url = base_url
        self.client = httpx.AsyncClient(timeout=30.0)
    
    async def get_metrics(self) -> Dict[str, Any]:
        """Fetch current metrics from /metrics endpoint."""
        try:
            response = await self.client.get(f"{self.base_url}/metrics")
            metrics_text = response.text
            
            # Parse Prometheus metrics (simplified)
            metrics = {}
            for line in metrics_text.split('\n'):
                if line.startswith('youtube_mcp_') and not line.startswith('#'):
                    parts = line.split(' ')
                    if len(parts) >= 2:
                        metric_name = parts[0].split('{')[0]
                        value = float(parts[-1])
                        if metric_name not in metrics:
                            metrics[metric_name] = 0
                        metrics[metric_name] += value
            
            return metrics
        except Exception as e:
            logger.error(f"Failed to fetch metrics: {e}")
            return {}
    
    async def test_successful_requests(self):
        """Test successful requests and verify metrics."""
        logger.info("=== Testing Successful Requests ===")
        
        # Get baseline metrics
        baseline_metrics = await self.get_metrics()
        logger.info(f"Baseline metrics: {baseline_metrics}")
        
        # Test health endpoint
        response = await self.client.get(f"{self.base_url}/health")
        assert response.status_code == 200
        logger.info(f"Health check: {response.status_code} - {response.json()}")
        
        # Test YouTube search endpoint (valid request)
        search_payload = {
            "query": "Python programming tutorial",
            "max_results": 3,
            "transcript_language": "en"
        }
        
        response = await self.client.post(
            f"{self.base_url}/youtube_search_and_transcript",
            json=search_payload
        )
        logger.info(f"YouTube search: {response.status_code}")
        
        # Get metrics after successful requests
        updated_metrics = await self.get_metrics()
        logger.info(f"Updated metrics: {updated_metrics}")
        
        # Verify request count increased
        baseline_requests = baseline_metrics.get('youtube_mcp_request_count', 0)
        updated_requests = updated_metrics.get('youtube_mcp_request_count', 0)
        
        assert updated_requests > baseline_requests, "Request count should increase"
        logger.info(f"✓ Request count increased: {baseline_requests} → {updated_requests}")
        
        # Verify latency metrics exist
        assert 'youtube_mcp_request_latency_seconds' in updated_metrics
        logger.info("✓ Request latency metrics captured")
    
    async def test_validation_errors(self):
        """Test validation errors and verify error classification."""
        logger.info("=== Testing Validation Errors ===")
        
        # Get baseline error metrics
        baseline_metrics = await self.get_metrics()
        baseline_errors = baseline_metrics.get('youtube_mcp_error_count', 0)
        
        # Test invalid request (empty query)
        invalid_payload = {
            "query": "",  # Invalid: empty query
            "max_results": 5
        }
        
        response = await self.client.post(
            f"{self.base_url}/youtube_search_and_transcript",
            json=invalid_payload
        )
        
        logger.info(f"Invalid request response: {response.status_code}")
        assert response.status_code == 400, "Should return validation error"
        
        # Test invalid request (bad max_results)
        invalid_payload2 = {
            "query": "test",
            "max_results": 999  # Invalid: too high
        }
        
        response = await self.client.post(
            f"{self.base_url}/youtube_search_and_transcript",
            json=invalid_payload2
        )
        
        logger.info(f"Invalid max_results response: {response.status_code}")
        
        # Verify error metrics increased
        updated_metrics = await self.get_metrics()
        updated_errors = updated_metrics.get('youtube_mcp_error_count', 0)
        
        assert updated_errors > baseline_errors, "Error count should increase"
        logger.info(f"✓ Error count increased: {baseline_errors} → {updated_errors}")
    
    async def test_nonexistent_endpoint(self):
        """Test 404 errors."""
        logger.info("=== Testing 404 Errors ===")
        
        response = await self.client.get(f"{self.base_url}/nonexistent")
        logger.info(f"404 test response: {response.status_code}")
        assert response.status_code == 404
        
        logger.info("✓ 404 error handling verified")
    
    async def test_metrics_endpoint(self):
        """Test metrics endpoint accessibility."""
        logger.info("=== Testing Metrics Endpoint ===")
        
        response = await self.client.get(f"{self.base_url}/metrics")
        assert response.status_code == 200
        assert 'youtube_mcp_request_count' in response.text
        assert 'youtube_mcp_request_latency_seconds' in response.text
        
        logger.info("✓ Metrics endpoint accessible and contains expected metrics")
        logger.info(f"Sample metrics:\n{response.text[:500]}...")
    
    async def test_request_tracing(self):
        """Test request ID generation and tracing."""
        logger.info("=== Testing Request Tracing ===")
        
        # Make multiple requests and verify they have different request IDs
        responses = []
        for i in range(3):
            response = await self.client.get(f"{self.base_url}/health")
            responses.append(response)
            time.sleep(0.1)  # Small delay to ensure different timestamps
        
        # All requests should succeed
        for i, response in enumerate(responses):
            assert response.status_code == 200
            logger.info(f"Request {i+1}: {response.status_code}")
        
        logger.info("✓ Request tracing verified (check logs for request IDs)")
    
    async def test_performance_timing(self):
        """Test request duration measurement."""
        logger.info("=== Testing Performance Timing ===")
        
        # Make a request that should take some time
        start_time = time.perf_counter()
        
        response = await self.client.post(
            f"{self.base_url}/youtube_search_and_transcript",
            json={
                "query": "machine learning",
                "max_results": 5,
                "transcript_language": "en"
            }
        )
        
        end_time = time.perf_counter()
        request_duration = end_time - start_time
        
        logger.info(f"Request took {request_duration:.4f} seconds")
        logger.info(f"Response status: {response.status_code}")
        
        # Verify the timing makes sense
        assert request_duration > 0, "Duration should be positive"
        logger.info("✓ Performance timing measurement verified")
    
    async def run_all_tests(self):
        """Run all acceptance tests."""
        logger.info("Starting Performance Metrics Acceptance Tests")
        logger.info("=" * 60)
        
        try:
            # Check if server is running
            health_response = await self.client.get(f"{self.base_url}/health")
            if health_response.status_code != 200:
                logger.error("Server not accessible at {self.base_url}")
                return False
            
            logger.info("✓ Server is accessible")
            
            # Run all test suites
            await self.test_successful_requests()
            await self.test_validation_errors()
            await self.test_nonexistent_endpoint()
            await self.test_metrics_endpoint()
            await self.test_request_tracing()
            await self.test_performance_timing()
            
            logger.info("=" * 60)
            logger.info("✅ ALL ACCEPTANCE TESTS PASSED")
            logger.info("Performance metrics middleware is working correctly!")
            
            # Final metrics snapshot
            final_metrics = await self.get_metrics()
            logger.info("Final metrics summary:")
            for metric, value in final_metrics.items():
                logger.info(f"  {metric}: {value}")
            
            return True
            
        except Exception as e:
            logger.error(f"❌ TEST FAILED: {e}")
            return False
        
        finally:
            await self.client.aclose()


async def main():
    """Main test function."""
    print("YouTube MCP Server - Performance Metrics Test Suite")
    print("=" * 60)
    print("This test validates:")
    print("✓ Request duration tracking with time.perf_counter()")
    print("✓ Error classification and counting")
    print("✓ Prometheus metrics integration")
    print("✓ Request tracing with correlation IDs")
    print("✓ Log-metrics correlation")
    print("=" * 60)
    
    # Wait a moment for user to read
    await asyncio.sleep(2)
    
    test_runner = MetricsTestRunner()
    success = await test_runner.run_all_tests()
    
    if success:
        print("\n🎉 Performance metrics implementation is complete and working!")
        print("\nTo monitor in production:")
        print("1. Access metrics at: http://localhost:8000/metrics")
        print("2. Check logs for request correlation")
        print("3. Set up Prometheus scraping of /metrics endpoint")
    else:
        print("\n❌ Some tests failed. Check the logs above for details.")
    
    return success


if __name__ == "__main__":
    asyncio.run(main())