#!/usr/bin/env python3
"""
Migration management script for Docker environment.
Provides commands to run Alembic migrations in containerized PostgreSQL.
"""

import subprocess
import sys
import os
from typing import List, Optional


def run_command(command: List[str], cwd: Optional[str] = None) -> int:
    """Run a command and return the exit code."""
    print(f"Running: {' '.join(command)}")
    try:
        result = subprocess.run(command, cwd=cwd, check=False)
        return result.returncode
    except Exception as e:
        print(f"Error running command: {e}")
        return 1


def check_docker_compose():
    """Check if Docker Compose is available."""
    try:
        subprocess.run(["docker-compose", "--version"], 
                      capture_output=True, check=True)
        return "docker-compose"
    except (subprocess.CalledProcessError, FileNotFoundError):
        try:
            subprocess.run(["docker", "compose", "version"], 
                          capture_output=True, check=True)
            return "docker compose"
        except (subprocess.CalledProcessError, FileNotFoundError):
            print("Error: Docker Compose not found!")
            return None


def main():
    """Main migration management function."""
    if len(sys.argv) < 2:
        print("Usage: python migrate.py <command> [args...]")
        print("Commands:")
        print("  init        - Initialize database (create tables)")
        print("  revision    - Create a new migration")
        print("  upgrade     - Apply migrations")
        print("  downgrade   - Rollback migrations")
        print("  current     - Show current migration")
        print("  history     - Show migration history")
        print("  test        - Test database connection")
        return 1
    
    command = sys.argv[1]
    args = sys.argv[2:] if len(sys.argv) > 2 else []
    
    # Check Docker Compose availability
    docker_compose = check_docker_compose()
    if not docker_compose:
        return 1
    
    docker_cmd = docker_compose.split()
    
    if command == "test":
        # Test database connection
        print("Testing database connection...")
        return run_command([
            *docker_cmd, "exec", "api", 
            "python", "test_db_connection.py"
        ])
    
    elif command == "init":
        # Initialize database with current models
        print("Initializing database...")
        return run_command([
            *docker_cmd, "exec", "api", 
            "python", "-c", 
            "import asyncio; from app.database import create_tables; asyncio.run(create_tables())"
        ])
    
    elif command == "revision":
        # Create new migration
        message = args[0] if args else "Auto-generated migration"
        print(f"Creating new migration: {message}")
        return run_command([
            *docker_cmd, "exec", "api", 
            "alembic", "revision", "--autogenerate", "-m", message
        ])
    
    elif command == "upgrade":
        # Apply migrations
        target = args[0] if args else "head"
        print(f"Upgrading to: {target}")
        return run_command([
            *docker_cmd, "exec", "api", 
            "alembic", "upgrade", target
        ])
    
    elif command == "downgrade":
        # Rollback migrations
        target = args[0] if args else "-1"
        print(f"Downgrading to: {target}")
        return run_command([
            *docker_cmd, "exec", "api", 
            "alembic", "downgrade", target
        ])
    
    elif command == "current":
        # Show current migration
        print("Current migration:")
        return run_command([
            *docker_cmd, "exec", "api", 
            "alembic", "current"
        ])
    
    elif command == "history":
        # Show migration history
        print("Migration history:")
        return run_command([
            *docker_cmd, "exec", "api", 
            "alembic", "history"
        ])
    
    else:
        print(f"Unknown command: {command}")
        return 1


if __name__ == "__main__":
    sys.exit(main())