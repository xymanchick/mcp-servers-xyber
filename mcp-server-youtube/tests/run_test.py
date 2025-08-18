"""
Comprehensive test runner for YouTube MCP Server

This script runs a comprehensive test suite for the YouTube MCP Server,
including unit tests, integration tests, validation tests, and performance tests.

Features:
- Automatic server lifecycle management
- Health checks before running tests
- Support for running without server (unit tests only)
- Quick mode for fast feedback
- Detailed test reporting with emojis
- Graceful error handling and cleanup
- Timeout protection for all tests

Usage:
    python3 tests/run_test.py                 # Full test suite
    python3 tests/run_test.py --no-server     # Unit tests only
    python3 tests/run_test.py --quick         # Quick tests only
    python3 tests/run_test.py --help          # Show help

Test Types:
- Unit tests: Fast tests that don't require external dependencies
- Validation tests: API validation and contract tests  
- Integration tests: End-to-end tests requiring running server
- Retry logic tests: Tests for retry and error handling
- Manual tests: Interactive or complex scenario tests
- Performance tests: Load and performance testing

Requirements:
- pytest installed
- mcp_server_youtube module available
- Optional: requests library for health checks (falls back to urllib)
"""

from __future__ import annotations

import logging
import subprocess
import sys
import time
from typing import Optional

# Try to import requests, if not available, use urllib
try:
    import requests
    HAS_REQUESTS = True
except ImportError:
    import urllib.request
    import urllib.error
    HAS_REQUESTS = False


# Configure logging with better formatting
class ColoredFormatter(logging.Formatter):
    """Colored log formatter."""
    
    COLOR_CODES = {
        'DEBUG': '\033[36m',     # Cyan
        'INFO': '\033[32m',      # Green  
        'WARNING': '\033[33m',   # Yellow
        'ERROR': '\033[31m',     # Red
        'CRITICAL': '\033[35m',  # Magenta
    }
    RESET_CODE = '\033[0m'

    def format(self, record):
        log_color = self.COLOR_CODES.get(record.levelname, self.RESET_CODE)
        record.levelname = f"{log_color}{record.levelname}{self.RESET_CODE}"
        return super().format(record)


# Set up colored logging
handler = logging.StreamHandler()
handler.setFormatter(ColoredFormatter('%(levelname)s:%(name)s:%(message)s'))
logging.basicConfig(level=logging.INFO, handlers=[handler])
logger = logging.getLogger(__name__)


def check_server_health(host: str = "localhost", port: int = 8000, timeout: int = 30) -> bool:
    """Check if the server is responding to health checks."""
    url = f"http://{host}:{port}/health"
    start_time = time.time()
    
    while time.time() - start_time < timeout:
        try:
            if HAS_REQUESTS:
                response = requests.get(url, timeout=5)
                if response.status_code == 200:
                    logger.info("Server is healthy and responding")
                    return True
            else:
                # Fallback to urllib if requests is not available
                with urllib.request.urlopen(url, timeout=5) as response:
                    if response.status == 200:
                        logger.info("Server is healthy and responding")
                        return True
        except (requests.exceptions.RequestException if HAS_REQUESTS else urllib.error.URLError):
            pass
        except Exception:
            pass
        time.sleep(1)
    
    logger.error(f"Server health check failed after {timeout} seconds")
    return False


def start_server() -> Optional[subprocess.Popen]:
    """Start the server in a separate process."""
    logger.info("Starting YouTube MCP server...")
    
    try:
        server_process = subprocess.Popen(
            [sys.executable, '-m', 'mcp_server_youtube'],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        
        # Wait for server to start and check health
        if check_server_health():
            logger.info("Server started successfully")
            return server_process
        else:
            logger.error("Server failed to start properly")
            if server_process.poll() is None:
                server_process.terminate()
                server_process.wait(timeout=5)
            return None
            
    except Exception as e:
        logger.error(f"Failed to start server: {e}")
        return None


def stop_server(server_process: subprocess.Popen) -> None:
    """Stop the server process gracefully."""
    if server_process is None:
        return
        
    logger.info("Stopping server...")
    try:
        server_process.terminate()
        server_process.wait(timeout=10)
        logger.info("Server stopped successfully")
    except subprocess.TimeoutExpired:
        logger.warning("Server didn't stop gracefully, forcing termination")
        server_process.kill()
        server_process.wait()



def run_manual_tests() -> tuple[bool, float]:
    """Run manual tests."""
    import os
    start_time = time.time()
    
    if not os.path.exists('tests/manual_test.py'):
        logger.warning("Manual test file not found, skipping...")
        return True, time.time() - start_time
    
    logger.info("Running manual tests...")
    try:
        result = subprocess.run(
            [sys.executable, 'tests/manual_test.py'], 
            check=True,
            capture_output=True,
            text=True,
            timeout=300  # 5 minutes timeout
        )
        logger.info("Manual tests completed successfully")
        return True, time.time() - start_time
    except subprocess.CalledProcessError as e:
        logger.error(f"Manual tests failed with exit code {e.returncode}")
        if e.stderr:
            logger.error(f"Error output: {e.stderr}")
        return False, time.time() - start_time
    except subprocess.TimeoutExpired:
        logger.error("Manual tests timed out")
        return False, time.time() - start_time
    except Exception as e:
        logger.error(f"Unexpected error running manual tests: {e}")
        return False, time.time() - start_time



def run_automated_tests() -> tuple[bool, float]:
    """Run automated tests using pytest."""
    import os
    start_time = time.time()
    
    if not os.path.exists('tests/validation_test.py'):
        logger.warning("Validation test file not found, skipping...")
        return True, time.time() - start_time
    
    logger.info("Running automated tests...")
    try:
        result = subprocess.run(
            ['pytest', 'tests/validation_test.py', '-v', '--tb=short'], 
            check=True,
            capture_output=True,
            text=True,
            timeout=300  # 5 minutes timeout
        )
        logger.info("Automated tests completed successfully")
        return True, time.time() - start_time
    except subprocess.CalledProcessError as e:
        logger.error(f"Automated tests failed with exit code {e.returncode}")
        if e.stderr:
            logger.error(f"Error output: {e.stderr}")
        return False, time.time() - start_time
    except subprocess.TimeoutExpired:
        logger.error("Automated tests timed out")
        return False, time.time() - start_time
    except Exception as e:
        logger.error(f"Unexpected error running automated tests: {e}")
        return False, time.time() - start_time


def run_integration_tests() -> tuple[bool, float]:
    """Run integration tests."""
    import os
    start_time = time.time()
    
    if not os.path.exists('tests/integration_test.py'):
        logger.warning("Integration test file not found, skipping...")
        return True, time.time() - start_time
    
    logger.info("Running integration tests...")
    try:
        result = subprocess.run(
            [sys.executable, 'tests/integration_test.py'], 
            check=True,
            capture_output=True,
            text=True,
            timeout=300  # 5 minutes timeout
        )
        logger.info("Integration tests completed successfully")
        return True, time.time() - start_time
    except subprocess.CalledProcessError as e:
        logger.error(f"Integration tests failed with exit code {e.returncode}")
        if e.stderr:
            logger.error(f"Error output: {e.stderr}")
        return False, time.time() - start_time
    except subprocess.TimeoutExpired:
        logger.error("Integration tests timed out")
        return False, time.time() - start_time
    except Exception as e:
        logger.error(f"Unexpected error running integration tests: {e}")
        return False, time.time() - start_time


def run_performance_tests() -> tuple[bool, float]:
    """Run performance tests."""
    import os
    start_time = time.time()
    
    if not os.path.exists('tests/performance_test.py'):
        logger.warning("Performance test file not found, skipping...")
        return True, time.time() - start_time
    
    logger.info("Running performance tests...")
    try:
        result = subprocess.run(
            [sys.executable, 'tests/performance_test.py'], 
            check=True,
            capture_output=True,
            text=True,
            timeout=600  # 10 minutes timeout for performance tests
        )
        logger.info("Performance tests completed successfully")
        return True, time.time() - start_time
    except subprocess.CalledProcessError as e:
        logger.error(f"Performance tests failed with exit code {e.returncode}")
        if e.stderr:
            logger.error(f"Error output: {e.stderr}")
        return False, time.time() - start_time
    except subprocess.TimeoutExpired:
        logger.error("Performance tests timed out")
        return False, time.time() - start_time
    except Exception as e:
        logger.error(f"Unexpected error running performance tests: {e}")
        return False, time.time() - start_time


def run_retry_logic_tests() -> tuple[bool, float]:
    """Run retry logic tests."""
    import os
    start_time = time.time()
    
    if not os.path.exists('tests/retry_logic_test.py'):
        logger.warning("Retry logic test file not found, skipping...")
        return True, time.time() - start_time
    
    logger.info("Running retry logic tests...")
    try:
        result = subprocess.run(
            [sys.executable, 'tests/retry_logic_test.py'], 
            check=True,
            capture_output=True,
            text=True,
            timeout=300  # 5 minutes timeout
        )
        logger.info("Retry logic tests completed successfully")
        return True, time.time() - start_time
    except subprocess.CalledProcessError as e:
        logger.error(f"Retry logic tests failed with exit code {e.returncode}")
        if e.stderr:
            logger.error(f"Error output: {e.stderr}")
        return False, time.time() - start_time
    except subprocess.TimeoutExpired:
        logger.error("Retry logic tests timed out")
        return False, time.time() - start_time
    except Exception as e:
        logger.error(f"Unexpected error running retry logic tests: {e}")
        return False, time.time() - start_time


def run_unit_tests() -> tuple[bool, float]:
    """Run unit tests using pytest."""
    import os
    start_time = time.time()
    
    test_files = ['tests/test_module.py', 'tests/test_server.py']
    existing_files = [f for f in test_files if os.path.exists(f)]
    
    if not existing_files:
        logger.warning("No unit test files found, skipping...")
        return True, time.time() - start_time
    
    logger.info("Running unit tests...")
    try:
        cmd = ['pytest'] + existing_files + ['-v', '--tb=short']
        result = subprocess.run(
            cmd,
            check=True,
            capture_output=True,
            text=True,
            timeout=300  # 5 minutes timeout
        )
        logger.info("Unit tests completed successfully")
        return True, time.time() - start_time
    except subprocess.CalledProcessError as e:
        logger.error(f"Unit tests failed with exit code {e.returncode}")
        if e.stderr:
            logger.error(f"Error output: {e.stderr}")
        return False, time.time() - start_time
    except subprocess.TimeoutExpired:
        logger.error("Unit tests timed out")
        return False, time.time() - start_time
    except Exception as e:
        logger.error(f"Unexpected error running unit tests: {e}")
        return False, time.time() - start_time


def check_dependencies() -> bool:
    """Check if all required dependencies are available."""
    logger.info("Checking dependencies...")
    
    missing_deps = []
    
    # Check pytest
    try:
        subprocess.run(['pytest', '--version'], check=True, capture_output=True)
    except (subprocess.CalledProcessError, FileNotFoundError):
        missing_deps.append('pytest')
    
    # Check if server module can be imported
    try:
        subprocess.run([sys.executable, '-c', 'import mcp_server_youtube'], check=True, capture_output=True)
    except subprocess.CalledProcessError:
        missing_deps.append('mcp_server_youtube module')
    
    if missing_deps:
        logger.error(f"Missing dependencies: {', '.join(missing_deps)}")

        return False
    
    logger.info("All dependencies are available")
    return True


def check_test_files() -> bool:
    """Check if all test files exist."""
    import os
    
    test_files = [
        'tests/manual_test.py',
        'tests/validation_test.py',
        'tests/integration_test.py',
        'tests/performance_test.py',
        'tests/retry_logic_test.py',
        'tests/test_module.py',
        'tests/test_server.py'
    ]
    
    missing_files = []
    for test_file in test_files:
        if not os.path.exists(test_file):
            missing_files.append(test_file)
    
    if missing_files:
        logger.warning(f"Missing test files: {', '.join(missing_files)}")
        logger.warning("Some tests will be skipped")
    
    return len(missing_files) == 0


def main():
    """Main function to run all tests."""
    import argparse
    
    parser = argparse.ArgumentParser(description='Run YouTube MCP Server test suite')
    parser.add_argument('--no-server', action='store_true', 
                       help='Run tests without starting the server (unit/validation tests only)')
    parser.add_argument('--quick', action='store_true',
                       help='Run only quick tests (unit and validation)')
    parser.add_argument('--test-type', choices=['unit', 'validation', 'integration', 'manual', 'performance', 'retry_logic'],
                       help='Run only specific test type')
    parser.add_argument('--verbose', '-v', action='store_true',
                       help='Show detailed output from test commands')
    parser.add_argument('--list', action='store_true',
                       help='List available test files and exit')
    
    args = parser.parse_args()
    
    if args.list:
        list_test_files()
        return True
    
    # Set logging level based on verbose flag
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    logger.info("Starting comprehensive test suite...")
    
    # Pre-flight checks
    if not check_dependencies():
        logger.error("Dependency check failed. Exiting.")
        sys.exit(1)
    
    check_test_files()  # Just warn, don't exit
    
    server_process = None
    if not args.no_server and args.test_type not in ['unit', 'validation']:
        # Start server
        server_process = start_server()
        if server_process is None:
            logger.warning("Failed to start server. Running tests that don't require server...")
            args.no_server = True


    try:
        # Run all test suites
        test_results = {}
        test_times = {}
        total_start_time = time.time()
        
        # Determine which tests to run
        if args.test_type:
            # Run only specific test type
            if args.test_type == 'unit':
                success, duration = run_unit_tests()
                test_results['unit'] = success
                test_times['unit'] = duration
            elif args.test_type == 'validation':
                success, duration = run_automated_tests()
                test_results['validation'] = success
                test_times['validation'] = duration
            elif args.test_type == 'integration':
                success, duration = run_integration_tests()
                test_results['integration'] = success
                test_times['integration'] = duration
            elif args.test_type == 'manual':
                success, duration = run_manual_tests()
                test_results['manual'] = success
                test_times['manual'] = duration
            elif args.test_type == 'performance':
                success, duration = run_performance_tests()
                test_results['performance'] = success
                test_times['performance'] = duration
            elif args.test_type == 'retry_logic':
                success, duration = run_retry_logic_tests()
                test_results['retry_logic'] = success
                test_times['retry_logic'] = duration
        else:
            # Always run unit tests (fastest and don't require server)
            success, duration = run_unit_tests()
            test_results['unit'] = success
            test_times['unit'] = duration
            
            # Always run validation tests (may work without server depending on implementation)
            success, duration = run_automated_tests()
            test_results['validation'] = success
            test_times['validation'] = duration
            
            if not args.no_server and not args.quick:
                # Run integration tests (require server)
                success, duration = run_integration_tests()
                test_results['integration'] = success
                test_times['integration'] = duration
                
                # Run retry logic tests
                success, duration = run_retry_logic_tests()
                test_results['retry_logic'] = success
                test_times['retry_logic'] = duration
                
                # Run manual tests
                success, duration = run_manual_tests()
                test_results['manual'] = success
                test_times['manual'] = duration
                
                # Run performance tests last (slowest)
                success, duration = run_performance_tests()
                test_results['performance'] = success
                test_times['performance'] = duration
            elif args.no_server:
                logger.info("Skipping server-dependent tests (use --no-server to run without server)")
            elif args.quick:
                logger.info("Quick mode: running only unit and validation tests")

        total_duration = time.time() - total_start_time

        # Print detailed summary
        logger.info("\n" + "="*70)
        logger.info("COMPREHENSIVE TEST SUMMARY")
        logger.info("="*70)
        
        total_tests = len(test_results)
        passed_tests = sum(1 for success in test_results.values() if success)
        
        for test_type, success in test_results.items():
            status = '✅ PASSED' if success else '❌ FAILED'
            duration = test_times.get(test_type, 0)
            logger.info(f"{test_type.replace('_', ' ').title():15} : {status} ({duration:.2f}s)")

        logger.info("-" * 70)
        logger.info(f"Total: {passed_tests}/{total_tests} test suites passed in {total_duration:.2f}s")
        
        # Check if all tests passed
        all_passed = all(test_results.values())
        if all_passed:
            logger.info("🎉 All test suites passed successfully!")
        else:
            logger.error(f"⚠️  {total_tests - passed_tests} test suite(s) failed!")
        
        # Show mode information
        if args.test_type:
            logger.info(f"Mode: Single test type ({args.test_type})")
        elif args.no_server:
            logger.info("Mode: No-server tests only")
        elif args.quick:
            logger.info("Mode: Quick tests only")
        else:
            logger.info("Mode: Full test suite")
            
        return all_passed


    except KeyboardInterrupt:
        logger.warning("Test execution interrupted by user")
        return False
    except Exception as e:
        logger.error(f"Unexpected error during test execution: {e}")
        return False
        
    finally:
        # Always stop the server if it was started
        if server_process:
            stop_server(server_process)


def list_test_files():
    """List all available test files and their status."""
    import os
    
    test_files = [
        ('tests/manual_test.py', 'Manual tests'),
        ('tests/validation_test.py', 'Validation tests'),
        ('tests/integration_test.py', 'Integration tests'),
        ('tests/performance_test.py', 'Performance tests'),
        ('tests/retry_logic_test.py', 'Retry logic tests'),
        ('tests/test_module.py', 'Unit tests (module)'),
        ('tests/test_server.py', 'Unit tests (server)')
    ]
    
    print("\nAvailable test files:")
    print("=" * 50)
    
    for file_path, description in test_files:
        exists = "✅" if os.path.exists(file_path) else "❌"
        print(f"{exists} {file_path:25} - {description}")
    
    print("\nTest types you can run individually:")
    print("- unit         : Unit tests")
    print("- validation   : Validation tests")
    print("- integration  : Integration tests")
    print("- manual       : Manual tests")
    print("- performance  : Performance tests")
    print("- retry_logic  : Retry logic tests")
    print("\nExample: python3 tests/run_test.py --test-type unit")


if __name__ == '__main__':
    success = main()
    sys.exit(0 if success else 1)

