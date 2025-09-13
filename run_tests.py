#!/usr/bin/env python3
"""
Test runner script for the property listing API.
Handles Docker container setup and test execution.
"""

import os
import sys
import subprocess
import time
import argparse
from pathlib import Path


def run_command(command, cwd=None, check=True):
    """Run a shell command and return the result."""
    print(f"Running: {command}")
    try:
        result = subprocess.run(
            command,
            shell=True,
            cwd=cwd,
            check=check,
            capture_output=True,
            text=True
        )
        if result.stdout:
            print(result.stdout)
        if result.stderr:
            print(result.stderr, file=sys.stderr)
        return result
    except subprocess.CalledProcessError as e:
        print(f"Command failed with exit code {e.returncode}")
        if e.stdout:
            print(e.stdout)
        if e.stderr:
            print(e.stderr, file=sys.stderr)
        raise


def wait_for_db(max_attempts=30, delay=2):
    """Wait for the test database to be ready."""
    print("Waiting for test database to be ready...")
    
    for attempt in range(max_attempts):
        try:
            # Try to connect to the test database
            result = run_command(
                "docker exec property_api_test_db pg_isready -U postgres -d property_listings_test",
                check=False
            )
            if result.returncode == 0:
                print("Test database is ready!")
                return True
        except Exception:
            pass
        
        print(f"Attempt {attempt + 1}/{max_attempts} - Database not ready, waiting {delay}s...")
        time.sleep(delay)
    
    print("Test database failed to become ready!")
    return False


def setup_test_environment():
    """Set up the test environment."""
    print("Setting up test environment...")
    
    # Create test uploads directory
    test_uploads_dir = Path("test_uploads")
    test_uploads_dir.mkdir(exist_ok=True)
    
    # Set test environment variables
    os.environ.update({
        "TESTING": "true",
        "ENVIRONMENT": "testing",
        "TEST_DATABASE_URL": "postgresql+asyncpg://postgres:postgres@localhost:5433/property_listings_test",
        "TEST_JWT_SECRET_KEY": "test-secret-key-for-testing-only",
        "TEST_UPLOAD_DIR": str(test_uploads_dir.absolute())
    })


def start_test_containers():
    """Start the test database container."""
    print("Starting test containers...")
    
    # Stop any existing test containers
    run_command("docker-compose -f docker-compose.test.yml down", check=False)
    
    # Start test database
    run_command("docker-compose -f docker-compose.test.yml up -d test_db")
    
    # Wait for database to be ready
    if not wait_for_db():
        raise RuntimeError("Test database failed to start")


def stop_test_containers():
    """Stop and clean up test containers."""
    print("Stopping test containers...")
    run_command("docker-compose -f docker-compose.test.yml down", check=False)


def run_migrations():
    """Run database migrations for tests."""
    print("Running test database migrations...")
    
    # Set database URL for migrations
    os.environ["DATABASE_URL"] = "postgresql+asyncpg://postgres:postgres@localhost:5433/property_listings_test"
    
    try:
        # Run migrations
        run_command("python -m alembic upgrade head")
        print("Migrations completed successfully!")
    except Exception as e:
        print(f"Migration failed: {e}")
        raise


def run_tests(test_args=None):
    """Run the test suite."""
    print("Running tests...")
    
    # Build pytest command
    cmd_parts = ["python", "-m", "pytest"]
    
    if test_args:
        cmd_parts.extend(test_args)
    else:
        # Default test arguments
        cmd_parts.extend([
            "tests/",
            "-v",
            "--tb=short",
            "--cov=app",
            "--cov-report=term-missing",
            "--cov-report=html:htmlcov"
        ])
    
    command = " ".join(cmd_parts)
    
    try:
        result = run_command(command)
        return result.returncode == 0
    except subprocess.CalledProcessError as e:
        print(f"Tests failed with exit code: {e.returncode}")
        return False


def main():
    """Main test runner function."""
    parser = argparse.ArgumentParser(description="Run tests for the property listing API")
    parser.add_argument(
        "--no-docker",
        action="store_true",
        help="Skip Docker container setup (assume database is already running)"
    )
    parser.add_argument(
        "--keep-containers",
        action="store_true",
        help="Keep test containers running after tests"
    )
    parser.add_argument(
        "--migrations-only",
        action="store_true",
        help="Only run migrations, don't run tests"
    )
    parser.add_argument(
        "test_args",
        nargs="*",
        help="Additional arguments to pass to pytest"
    )
    
    args = parser.parse_args()
    
    try:
        # Setup test environment
        setup_test_environment()
        
        # Start containers if needed
        if not args.no_docker:
            start_test_containers()
        
        # Run migrations
        run_migrations()
        
        if args.migrations_only:
            print("Migrations completed. Exiting.")
            return 0
        
        # Run tests
        success = run_tests(args.test_args)
        
        if success:
            print("\n✅ All tests passed!")
            return 0
        else:
            print("\n❌ Some tests failed!")
            return 1
    
    except KeyboardInterrupt:
        print("\n⚠️  Tests interrupted by user")
        return 1
    
    except Exception as e:
        print(f"\n❌ Test runner failed: {e}")
        return 1
    
    finally:
        # Clean up containers unless requested to keep them
        if not args.no_docker and not args.keep_containers:
            stop_test_containers()


if __name__ == "__main__":
    sys.exit(main())