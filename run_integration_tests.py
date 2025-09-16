#!/usr/bin/env python3
"""
Integration test runner for Property Listing API.
Runs comprehensive integration tests using Docker test environment.
"""

import os
import sys
import subprocess
import time
import asyncio
from pathlib import Path


def run_command(command: str, cwd: str = None) -> int:
    """Run a shell command and return exit code."""
    print(f"Running: {command}")
    result = subprocess.run(command, shell=True, cwd=cwd)
    return result.returncode


def wait_for_service(host: str, port: int, timeout: int = 30) -> bool:
    """Wait for a service to be available."""
    import socket
    
    start_time = time.time()
    while time.time() - start_time < timeout:
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
                sock.settimeout(1)
                result = sock.connect_ex((host, port))
                if result == 0:
                    return True
        except Exception:
            pass
        time.sleep(1)
    return False


def main():
    """Main test runner function."""
    print("🚀 Starting Property Listing API Integration Tests")
    print("=" * 60)
    
    # Set environment variables for testing
    os.environ["TESTING"] = "true"
    os.environ["TEST_DATABASE_URL"] = "postgresql+asyncpg://postgres:postgres@localhost:5433/property_listings_test"
    
    try:
        # Step 1: Stop any existing test containers
        print("\n📦 Cleaning up existing test containers...")
        run_command("docker-compose -f docker-compose.test.yml down -v")
        
        # Step 2: Start test database
        print("\n🗄️  Starting test database...")
        exit_code = run_command("docker-compose -f docker-compose.test.yml up -d test_db")
        if exit_code != 0:
            print("❌ Failed to start test database")
            return exit_code
        
        # Step 3: Wait for database to be ready
        print("\n⏳ Waiting for test database to be ready...")
        if not wait_for_service("localhost", 5433, timeout=30):
            print("❌ Test database failed to start within timeout")
            return 1
        
        # Give database a bit more time to fully initialize
        time.sleep(5)
        
        # Step 4: Run database migrations
        print("\n🔄 Running database migrations...")
        exit_code = run_command("python migrate.py")
        if exit_code != 0:
            print("❌ Database migrations failed")
            return exit_code
        
        # Step 5: Run integration tests
        print("\n🧪 Running integration tests...")
        
        # Run specific integration test file
        test_commands = [
            "python -m pytest tests/test_integration_api.py -v --tb=short --disable-warnings",
            "python -m pytest tests/test_integration_api.py::TestAuthenticationEndpoints -v --tb=short",
            "python -m pytest tests/test_integration_api.py::TestPropertyManagementEndpoints -v --tb=short",
            "python -m pytest tests/test_integration_api.py::TestImageManagementEndpoints -v --tb=short",
            "python -m pytest tests/test_integration_api.py::TestSearchAndFilteringEndpoints -v --tb=short",
            "python -m pytest tests/test_integration_api.py::TestDatabaseCleanupAndIsolation -v --tb=short",
            "python -m pytest tests/test_integration_api.py::TestDockerVolumeIntegration -v --tb=short"
        ]
        
        # Run all integration tests
        exit_code = run_command("python -m pytest tests/test_integration_api.py -v --tb=short --disable-warnings")
        
        if exit_code == 0:
            print("\n✅ All integration tests passed!")
        else:
            print("\n❌ Some integration tests failed")
            
        # Step 6: Generate test report
        print("\n📊 Generating test coverage report...")
        run_command("python -m pytest tests/test_integration_api.py --cov=app --cov-report=html --cov-report=term")
        
        return exit_code
        
    except KeyboardInterrupt:
        print("\n⚠️  Test run interrupted by user")
        return 1
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        return 1
    finally:
        # Cleanup: Stop test containers
        print("\n🧹 Cleaning up test containers...")
        run_command("docker-compose -f docker-compose.test.yml down -v")


def run_specific_test_class(test_class: str):
    """Run a specific test class."""
    print(f"🧪 Running {test_class} tests...")
    
    # Set environment variables
    os.environ["TESTING"] = "true"
    os.environ["TEST_DATABASE_URL"] = "postgresql+asyncpg://postgres:postgres@localhost:5433/property_listings_test"
    
    try:
        # Start test database
        run_command("docker-compose -f docker-compose.test.yml up -d test_db")
        
        # Wait for database
        if not wait_for_service("localhost", 5433, timeout=30):
            print("❌ Test database failed to start")
            return 1
        
        time.sleep(5)
        
        # Run migrations
        run_command("python migrate.py")
        
        # Run specific test class
        exit_code = run_command(f"python -m pytest tests/test_integration_api.py::{test_class} -v --tb=short")
        
        return exit_code
        
    finally:
        run_command("docker-compose -f docker-compose.test.yml down -v")


if __name__ == "__main__":
    if len(sys.argv) > 1:
        # Run specific test class
        test_class = sys.argv[1]
        exit_code = run_specific_test_class(test_class)
    else:
        # Run all integration tests
        exit_code = main()
    
    sys.exit(exit_code)