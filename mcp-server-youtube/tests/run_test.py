from __future__ import annotations

import subprocess
import sys
import time
from threading import Thread


def run_server():
    """Start the server in a separate process."""
    server_process = subprocess.Popen(
        [sys.executable, "-m", "mcp_server_youtube"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    # Wait for server to start
    time.sleep(2)
    return server_process


def run_manual_tests():
    """Run manual tests."""
    print("\n=== Running Manual Tests ===")
    try:
        subprocess.run([sys.executable, "tests/manual_test.py"], check=True)
    except subprocess.CalledProcessError as e:
        print(f"\nManual tests failed with error: {e}")
        return False
    return True


def run_automated_tests():
    """Run automated tests using pytest."""
    print("\n=== Running Automated Tests ===")
    try:
        subprocess.run(["pytest", "tests/validation_test.py", "-v"], check=True)
    except subprocess.CalledProcessError as e:
        print(f"\nAutomated tests failed with error: {e}")
        return False
    return True


def main():
    """Main function to run all tests."""
    print("Starting test suite...")

    # Start server in a separate thread
    server_thread = Thread(target=run_server)
    server_thread.start()
    time.sleep(2)  # Give server time to start

    # Run tests
    manual_success = run_manual_tests()
    auto_success = run_automated_tests()

    # Stop the server
    print("\nStopping server...")
    server_thread.join(timeout=2)

    # Print summary
    print("\n=== Test Summary ===")
    print(f"Manual tests: {'PASSED' if manual_success else 'FAILED'}")
    print(f"Automated tests: {'PASSED' if auto_success else 'FAILED'}")

    if not manual_success or not auto_success:
        sys.exit(1)


if __name__ == "__main__":
    main()
