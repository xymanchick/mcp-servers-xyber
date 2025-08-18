"""
Performance and load tests for YouTube MCP Server

This script tests the server's performance under various load conditions
and measures response times and resource usage.
"""

import asyncio
import json
import time
from datetime import datetime
from statistics import mean, median
from typing import List, Dict, Any

import aiohttp
import psutil


class PerformanceTestResults:
    """Track performance test results"""
    
    def __init__(self):
        self.results = []
        self.errors = []
        
    def add_result(self, test_name: str, response_time: float, 
                  status: int, success: bool, error: str = None):
        self.results.append({
            'test_name': test_name,
            'response_time': response_time,
            'status': status,
            'success': success,
            'error': error,
            'timestamp': datetime.now()
        })
        
        if not success:
            self.errors.append(f"{test_name}: {error}")
    
    def get_stats(self) -> Dict[str, Any]:
        """Calculate performance statistics"""
        if not self.results:
            return {}
            
        response_times = [r['response_time'] for r in self.results if r['success']]
        success_count = len([r for r in self.results if r['success']])
        total_count = len(self.results)
        
        stats = {
            'total_requests': total_count,
            'successful_requests': success_count,
            'failed_requests': total_count - success_count,
            'success_rate': (success_count / total_count * 100) if total_count > 0 else 0,
            'error_count': len(self.errors)
        }
        
        if response_times:
            stats.update({
                'avg_response_time': mean(response_times),
                'median_response_time': median(response_times),
                'min_response_time': min(response_times),
                'max_response_time': max(response_times),
                'total_time': sum(response_times)
            })
        
        return stats
    
    def print_summary(self):
        """Print test summary"""
        stats = self.get_stats()
        
        print("\n" + "="*60)
        print("PERFORMANCE TEST SUMMARY")
        print("="*60)
        
        print(f"Total Requests: {stats.get('total_requests', 0)}")
        print(f"Successful: {stats.get('successful_requests', 0)}")
        print(f"Failed: {stats.get('failed_requests', 0)}")
        print(f"Success Rate: {stats.get('success_rate', 0):.2f}%")
        
        if 'avg_response_time' in stats:
            print(f"\nResponse Times:")
            print(f"  Average: {stats['avg_response_time']:.3f}s")
            print(f"  Median: {stats['median_response_time']:.3f}s")
            print(f"  Min: {stats['min_response_time']:.3f}s")
            print(f"  Max: {stats['max_response_time']:.3f}s")
            print(f"  Total: {stats['total_time']:.3f}s")
        
        if self.errors:
            print(f"\nErrors ({len(self.errors)}):")
            for error in self.errors[:10]:  # Show first 10 errors
                print(f"  - {error}")
            if len(self.errors) > 10:
                print(f"  ... and {len(self.errors) - 10} more errors")


class YouTubePerformanceTester:
    """Performance tester for YouTube MCP Server"""
    
    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url = base_url
        self.results = PerformanceTestResults()
        
    async def make_request(self, session: aiohttp.ClientSession, 
                          data: Dict[str, Any], test_name: str) -> None:
        """Make a single request and record performance"""
        start_time = time.time()
        
        try:
            async with session.post(
                f"{self.base_url}/youtube_search_and_transcript",
                json=data,
                headers={"Content-Type": "application/json"}
            ) as response:
                response_time = time.time() - start_time
                status = response.status
                
                # Try to read response
                try:
                    await response.json()
                    success = 200 <= status < 300
                    error = None if success else f"HTTP {status}"
                except Exception as e:
                    success = False
                    error = f"Response parsing error: {e}"
                    
                self.results.add_result(test_name, response_time, status, success, error)
                
        except Exception as e:
            response_time = time.time() - start_time
            self.results.add_result(test_name, response_time, 0, False, str(e))
    
    async def check_server_health(self, session: aiohttp.ClientSession) -> bool:
        """Check if server is responding"""
        try:
            async with session.post(
                f"{self.base_url}/youtube_search_and_transcript",
                json={"query": "test", "max_results": 1},
                timeout=aiohttp.ClientTimeout(total=5)
            ) as response:
                return True
        except Exception:
            return False
    
    async def test_single_requests(self, session: aiohttp.ClientSession):
        """Test individual request performance"""
        print("\n" + "="*50)
        print("Testing individual request performance...")
        print("="*50)
        
        test_cases = [
            {
                "data": {"query": "Python programming", "max_results": 5},
                "name": "Basic request"
            },
            {
                "data": {"query": "Python programming", "max_results": 1},
                "name": "Minimal request"
            },
            {
                "data": {
                    "query": "Python programming tutorial", 
                    "max_results": 10,
                    "transcript_language": "en",
                    "order_by": "relevance"
                },
                "name": "Complex request"
            },
            {
                "data": {"query": "a" * 500, "max_results": 5},
                "name": "Long query"
            },
            {
                "data": {"query": "Python 编程教程", "max_results": 3},
                "name": "Unicode query"
            }
        ]
        
        for test_case in test_cases:
            print(f"Testing {test_case['name']}...")
            for i in range(3):  # 3 requests per test case
                await self.make_request(
                    session, 
                    test_case["data"], 
                    f"{test_case['name']} #{i+1}"
                )
                await asyncio.sleep(0.1)  # Small delay between requests
    
    async def test_concurrent_requests(self, session: aiohttp.ClientSession):
        """Test concurrent request performance"""
        print("\n" + "="*50)
        print("Testing concurrent request performance...")
        print("="*50)
        
        # Test with different concurrency levels
        concurrency_levels = [5, 10, 20]
        
        for concurrent_count in concurrency_levels:
            print(f"\nTesting {concurrent_count} concurrent requests...")
            
            tasks = []
            start_time = time.time()
            
            for i in range(concurrent_count):
                data = {
                    "query": f"Python tutorial {i % 5}",  # Vary queries slightly
                    "max_results": 2 + (i % 3)  # Vary result count
                }
                task = self.make_request(
                    session, 
                    data, 
                    f"Concurrent-{concurrent_count} #{i+1}"
                )
                tasks.append(task)
            
            # Execute all requests concurrently
            await asyncio.gather(*tasks)
            
            total_time = time.time() - start_time
            print(f"Completed {concurrent_count} requests in {total_time:.3f}s")
            print(f"Average time per request: {total_time/concurrent_count:.3f}s")
    
    async def test_sustained_load(self, session: aiohttp.ClientSession):
        """Test sustained load over time"""
        print("\n" + "="*50)
        print("Testing sustained load (30 requests over 15 seconds)...")
        print("="*50)
        
        duration = 15  # seconds
        request_count = 30
        interval = duration / request_count
        
        start_time = time.time()
        
        for i in range(request_count):
            data = {
                "query": f"Programming tutorial {i % 10}",
                "max_results": 2 + (i % 4)
            }
            
            await self.make_request(
                session, 
                data, 
                f"Sustained load #{i+1}"
            )
            
            # Calculate next request time
            next_request_time = start_time + (i + 1) * interval
            sleep_time = max(0, next_request_time - time.time())
            if sleep_time > 0:
                await asyncio.sleep(sleep_time)
        
        total_time = time.time() - start_time
        print(f"Completed sustained load test in {total_time:.3f}s")
    
    async def test_error_handling_performance(self, session: aiohttp.ClientSession):
        """Test performance with invalid requests"""
        print("\n" + "="*50)
        print("Testing error handling performance...")
        print("="*50)
        
        error_cases = [
            {
                "data": {"query": "", "max_results": 5},
                "name": "Empty query error"
            },
            {
                "data": {"query": "test", "max_results": 25},
                "name": "Invalid max_results error"
            },
            {
                "data": {"query": "test", "transcript_language": "invalid"},
                "name": "Invalid language error"
            },
            {
                "data": {"query": "test", "published_after": "invalid-date"},
                "name": "Invalid date error"
            }
        ]
        
        for error_case in error_cases:
            print(f"Testing {error_case['name']}...")
            for i in range(3):  # 3 requests per error case
                await self.make_request(
                    session, 
                    error_case["data"], 
                    f"{error_case['name']} #{i+1}"
                )
                await asyncio.sleep(0.05)
    
    def monitor_system_resources(self):
        """Monitor system resource usage"""
        try:
            cpu_percent = psutil.cpu_percent(interval=1)
            memory = psutil.virtual_memory()
            
            print(f"\nSystem Resources:")
            print(f"  CPU Usage: {cpu_percent:.1f}%")
            print(f"  Memory Usage: {memory.percent:.1f}%")
            print(f"  Available Memory: {memory.available / 1024**3:.2f} GB")
            
        except Exception as e:
            print(f"Could not monitor system resources: {e}")
    
    async def run_performance_tests(self):
        """Run all performance tests"""
        print("=== Starting Performance Tests ===")
        print("Note: Server must be running at", self.base_url)
        
        # Monitor initial system state
        self.monitor_system_resources()
        
        timeout = aiohttp.ClientTimeout(total=60)  # Longer timeout for load tests
        connector = aiohttp.TCPConnector(limit=100)  # Allow more concurrent connections
        
        async with aiohttp.ClientSession(timeout=timeout, connector=connector) as session:
            # Check server health
            if not await self.check_server_health(session):
                print("❌ Server is not running. Please start the server first.")
                return
            
            print("✅ Server is responding")
            
            # Run test suites
            await self.test_single_requests(session)
            await self.test_concurrent_requests(session)
            await self.test_sustained_load(session)
            await self.test_error_handling_performance(session)
            
            # Monitor final system state
            self.monitor_system_resources()
        
        # Show results
        self.results.print_summary()
        
        # Performance recommendations
        stats = self.results.get_stats()
        if 'avg_response_time' in stats:
            avg_time = stats['avg_response_time']
            if avg_time > 5.0:
                print("\n⚠️  WARNING: Average response time is high (>5s)")
                print("   Consider optimizing server performance or API rate limits")
            elif avg_time > 2.0:
                print("\n⚡ INFO: Average response time is moderate (>2s)")
                print("   This is typical for YouTube API requests")
            else:
                print("\n🚀 GOOD: Average response time is fast (<2s)")
        
        if stats.get('success_rate', 0) < 95:
            print("\n⚠️  WARNING: Success rate is below 95%")
            print("   Check server logs for errors and API limits")
        elif stats.get('success_rate', 0) < 99:
            print("\n⚡ INFO: Success rate is good but could be improved")
        else:
            print("\n✅ EXCELLENT: Success rate is above 99%")


async def main():
    """Main function to run performance tests"""
    tester = YouTubePerformanceTester()
    await tester.run_performance_tests()


if __name__ == "__main__":
    print("Performance Test Suite for YouTube MCP Server")
    print("This will run various load and performance tests.")
    print("Make sure the server is running before starting tests.")
    print("-" * 60)
    
    asyncio.run(main())
