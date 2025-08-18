"""
Integration tests for YouTube MCP Server HTTP endpoints

This script tests the actual HTTP endpoints when the server is running.
It requires the server to be started separately.
"""

import asyncio
import json
import time
from datetime import datetime, timedelta
from typing import Any, Dict

import aiohttp


class IntegrationTestResults:
    """Track integration test results"""
    def __init__(self):
        self.passed = 0
        self.failed = 0
        self.errors = []

    def add_result(self, test_name: str, success: bool, error: str = None):
        if success:
            self.passed += 1
            print(f"✅ {test_name}: PASSED")
        else:
            self.failed += 1
            self.errors.append(f"{test_name}: {error}")
            print(f"❌ {test_name}: FAILED - {error}")

    def summary(self):
        total = self.passed + self.failed
        print(f"\n=== Integration Test Summary ===")
        print(f"Total tests: {total}")
        print(f"Passed: {self.passed}")
        print(f"Failed: {self.failed}")
        if self.errors:
            print("\nErrors:")
            for error in self.errors:
                print(f"  - {error}")


class YouTubeServerTester:
    """Test client for YouTube MCP Server HTTP endpoints"""
    
    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url = base_url
        self.results = IntegrationTestResults()
        
    async def test_endpoint(self, session: aiohttp.ClientSession, 
                          data: Dict[str, Any], description: str,
                          expect_error: bool = False, expected_status: int = None):
        """Test an HTTP endpoint"""
        print(f"\n{description}...")
        print(f"Request data: {json.dumps(data, indent=2)}")
        
        try:
            async with session.post(
                f"{self.base_url}/youtube_search_and_transcript",
                json=data,
                headers={"Content-Type": "application/json"}
            ) as response:
                status = response.status
                print(f"Response status: {status}")
                
                try:
                    response_data = await response.json()
                    print("Response data:", json.dumps(response_data, indent=2)[:500] + "...")
                except Exception:
                    response_text = await response.text()
                    print("Response text:", response_text[:500] + "...")
                    response_data = {"text": response_text}
                
                # Check expectations
                if expect_error:
                    if status >= 400:
                        self.results.add_result(description, True)
                    else:
                        self.results.add_result(description, False, 
                                              f"Expected error status but got {status}")
                else:
                    if expected_status and status == expected_status:
                        self.results.add_result(description, True)
                    elif not expected_status and 200 <= status < 300:
                        self.results.add_result(description, True)
                    else:
                        self.results.add_result(description, False, 
                                              f"Unexpected status {status}")
                        
        except Exception as e:
            self.results.add_result(description, False, f"Request failed: {str(e)}")

    async def check_server_health(self, session: aiohttp.ClientSession) -> bool:
        """Check if server is responding"""
        try:
            async with session.get(f"{self.base_url}/health") as response:
                if response.status == 200:
                    print("✅ Server is responding")
                    return True
        except Exception:
            pass
            
        try:
            # Try a simple request to see if server responds
            async with session.post(
                f"{self.base_url}/youtube_search_and_transcript",
                json={"query": "test", "max_results": 1},
                timeout=aiohttp.ClientTimeout(total=5)
            ) as response:
                print(f"✅ Server responded with status {response.status}")
                return True
        except Exception as e:
            print(f"❌ Server not responding: {e}")
            return False

    async def run_tests(self):
        """Run all integration tests"""
        print("=== Starting Integration Tests ===")
        print("Note: Server must be running at", self.base_url)
        
        timeout = aiohttp.ClientTimeout(total=30)
        async with aiohttp.ClientSession(timeout=timeout) as session:
            # Check server health
            if not await self.check_server_health(session):
                print("❌ Server is not running. Please start the server first.")
                print("To start the server: uvicorn mcp_server_youtube.server:app --reload")
                return
            
            # Test 1: Valid request
            await self.test_endpoint(
                session,
                {
                    "query": "Python programming tutorial",
                    "max_results": 3,
                    "transcript_language": "en"
                },
                "1. Testing valid request"
            )
            
            # Test 2: Minimal valid request
            await self.test_endpoint(
                session,
                {
                    "query": "Python programming",
                    "max_results": 2
                },
                "2. Testing minimal valid request"
            )
            
            # Test 3: Empty query (should fail)
            await self.test_endpoint(
                session,
                {
                    "query": "",
                    "max_results": 5
                },
                "3. Testing empty query",
                expect_error=True
            )
            
            # Test 4: Invalid max_results (should fail)
            await self.test_endpoint(
                session,
                {
                    "query": "Python programming",
                    "max_results": 25
                },
                "4. Testing invalid max_results",
                expect_error=True
            )
            
            # Test 5: Invalid language code (should fail)
            await self.test_endpoint(
                session,
                {
                    "query": "Python programming",
                    "max_results": 5,
                    "transcript_language": "xyz123"
                },
                "5. Testing invalid language code",
                expect_error=True
            )
            
            # Test 6: Invalid date format (should fail)
            await self.test_endpoint(
                session,
                {
                    "query": "Python programming",
                    "max_results": 5,
                    "published_after": "2024-01-01"
                },
                "6. Testing invalid date format",
                expect_error=True
            )
            
            # Test 7: Future date (should fail)
            await self.test_endpoint(
                session,
                {
                    "query": "Python programming",
                    "max_results": 5,
                    "published_after": (datetime.now() + timedelta(days=1)).isoformat() + "Z"
                },
                "7. Testing future date",
                expect_error=True
            )
            
            # Test 8: Invalid order_by (should fail)
            await self.test_endpoint(
                session,
                {
                    "query": "Python programming",
                    "max_results": 5,
                    "order_by": "views"
                },
                "8. Testing invalid order_by",
                expect_error=True
            )
            
            # Test 9: Valid language codes
            valid_languages = ["en", "es", "fr"]
            for lang in valid_languages:
                await self.test_endpoint(
                    session,
                    {
                        "query": "Python programming",
                        "max_results": 2,
                        "transcript_language": lang
                    },
                    f"9.{valid_languages.index(lang)+1}. Testing valid language: {lang}"
                )
            
            # Test 10: Valid order_by values
            valid_orders = ["relevance", "date"]
            for order in valid_orders:
                await self.test_endpoint(
                    session,
                    {
                        "query": "Python programming",
                        "max_results": 2,
                        "order_by": order
                    },
                    f"10.{valid_orders.index(order)+1}. Testing valid order_by: {order}"
                )
            
            # Test 11: Edge cases
            await self.test_endpoint(
                session,
                {
                    "query": "a" * 500,  # Max length query
                    "max_results": 1
                },
                "11.1. Testing maximum query length"
            )
            
            await self.test_endpoint(
                session,
                {
                    "query": "Python programming",
                    "max_results": 20  # Max results
                },
                "11.2. Testing maximum max_results"
            )
            
            await self.test_endpoint(
                session,
                {
                    "query": "Python programming",
                    "max_results": 1  # Min results
                },
                "11.3. Testing minimum max_results"
            )
            
            # Test 12: Date range
            await self.test_endpoint(
                session,
                {
                    "query": "Python programming",
                    "max_results": 2,
                    "published_after": "2023-01-01T00:00:00Z",
                    "published_before": "2024-12-31T23:59:59Z"
                },
                "12. Testing date range"
            )
            
            # Test 13: Special characters in query
            special_queries = [
                "Python & JavaScript",
                "How to: Python?",
                "Python (advanced)",
                "C++ vs Python"
            ]
            
            for i, query in enumerate(special_queries, 1):
                await self.test_endpoint(
                    session,
                    {
                        "query": query,
                        "max_results": 2
                    },
                    f"13.{i}. Testing special characters: {query[:20]}..."
                )
            
            # Test 14: Stress test with multiple concurrent requests
            print("\n" + "="*50)
            print("Running concurrent request test...")
            print("="*50)
            
            tasks = []
            for i in range(5):
                task = self.test_endpoint(
                    session,
                    {
                        "query": f"Python tutorial {i}",
                        "max_results": 2
                    },
                    f"14.{i+1}. Concurrent request {i+1}"
                )
                tasks.append(task)
            
            await asyncio.gather(*tasks)
            
        # Show results
        self.results.summary()
        print("\n=== Integration Tests Complete ===")


async def main():
    """Main function to run integration tests"""
    tester = YouTubeServerTester()
    await tester.run_tests()


if __name__ == "__main__":
    asyncio.run(main())
