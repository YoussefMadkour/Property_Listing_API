#!/usr/bin/env python3
"""
Database migration script with Docker integration.
Handles database migrations, seeding, and Docker container management.
"""

import asyncio
import os
import sys
import subprocess
import argparse
import logging
from pathlib import Path
from typing import Optional

# Add the app directory to the Python path
sys.path.insert(0, str(Path(__file__).parent))

from app.config import settings
from app.database import engine, test_engine, Base, AsyncSessionLocal, TestAsyncSessionLocal
from app.models.user import User, UserRole
from app.models.property import Property
from app.models.image import PropertyImage

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class MigrationManager:
    """Manages database migrations with Docker integration."""
    
    def __init__(self):
        self.docker_compose_file = "docker-compose.yml"
        self.test_docker_compose_file = "docker-compose.test.yml"
    
    def run_command(self, command: list, check: bool = True) -> subprocess.CompletedProcess:
        """Run a shell command and return the result."""
        logger.info(f"Running command: {' '.join(command)}")
        try:
            result = subprocess.run(
                command,
                check=check,
                capture_output=True,
                text=True
            )
            if result.stdout:
                logger.info(f"Command output: {result.stdout}")
            return result
        except subprocess.CalledProcessError as e:
            logger.error(f"Command failed: {e}")
            if e.stderr:
                logger.error(f"Error output: {e.stderr}")
            raise
    
    def is_docker_running(self) -> bool:
        """Check if Docker is running."""
        try:
            result = self.run_command(["docker", "info"], check=False)
            return result.returncode == 0
        except FileNotFoundError:
            logger.error("Docker is not installed or not in PATH")
            return False
    
    def start_database_container(self, test: bool = False) -> None:
        """Start the database container using Docker Compose."""
        if not self.is_docker_running():
            raise RuntimeError("Docker is not running. Please start Docker first.")
        
        compose_file = self.test_docker_compose_file if test else self.docker_compose_file
        
        if not Path(compose_file).exists():
            raise FileNotFoundError(f"Docker Compose file not found: {compose_file}")
        
        logger.info(f"Starting database container using {compose_file}")
        
        # Start only the database service
        self.run_command([
            "docker-compose",
            "-f", compose_file,
            "up", "-d", "db"
        ])
        
        # Wait for database to be ready
        logger.info("Waiting for database to be ready...")
        self.run_command([
            "docker-compose",
            "-f", compose_file,
            "exec", "-T", "db",
            "pg_isready", "-U", "postgres"
        ])
        
        logger.info("Database container is ready")
    
    def stop_database_container(self, test: bool = False) -> None:
        """Stop the database container."""
        compose_file = self.test_docker_compose_file if test else self.docker_compose_file
        
        logger.info(f"Stopping database container using {compose_file}")
        self.run_command([
            "docker-compose",
            "-f", compose_file,
            "down"
        ])
    
    def create_migration(self, message: str) -> None:
        """Create a new Alembic migration."""
        logger.info(f"Creating migration: {message}")
        
        # Ensure database is running
        self.start_database_container()
        
        try:
            # Create the migration
            self.run_command([
                "alembic", "revision", "--autogenerate", "-m", message
            ])
            logger.info("Migration created successfully")
        except Exception as e:
            logger.error(f"Failed to create migration: {e}")
            raise
    
    def run_migrations(self, test: bool = False) -> None:
        """Run pending migrations."""
        logger.info("Running database migrations")
        
        # Start appropriate database container
        self.start_database_container(test=test)
        
        try:
            # Set environment for test database if needed
            env = os.environ.copy()
            if test:
                env["TESTING"] = "true"
            
            # Run migrations
            self.run_command(["alembic", "upgrade", "head"], check=True)
            logger.info("Migrations completed successfully")
        except Exception as e:
            logger.error(f"Failed to run migrations: {e}")
            raise
    
    def rollback_migration(self, revision: str = "-1") -> None:
        """Rollback to a specific migration."""
        logger.info(f"Rolling back to revision: {revision}")
        
        # Ensure database is running
        self.start_database_container()
        
        try:
            self.run_command(["alembic", "downgrade", revision])
            logger.info("Rollback completed successfully")
        except Exception as e:
            logger.error(f"Failed to rollback migration: {e}")
            raise
    
    def show_migration_history(self) -> None:
        """Show migration history."""
        logger.info("Showing migration history")
        
        try:
            self.run_command(["alembic", "history", "--verbose"])
        except Exception as e:
            logger.error(f"Failed to show migration history: {e}")
            raise
    
    def show_current_revision(self) -> None:
        """Show current database revision."""
        logger.info("Showing current database revision")
        
        # Ensure database is running
        self.start_database_container()
        
        try:
            self.run_command(["alembic", "current", "--verbose"])
        except Exception as e:
            logger.error(f"Failed to show current revision: {e}")
            raise
    
    async def seed_database(self, test: bool = False) -> None:
        """Seed the database with initial data."""
        logger.info("Seeding database with initial data")
        
        # Use appropriate session factory
        session_factory = TestAsyncSessionLocal if test else AsyncSessionLocal
        
        if not session_factory:
            raise RuntimeError("Database session factory not configured")
        
        async with session_factory() as session:
            try:
                # Check if admin user already exists
                from sqlalchemy import select
                result = await session.execute(
                    select(User).where(User.email == "admin@example.com")
                )
                existing_admin = result.scalar_one_or_none()
                
                if existing_admin:
                    logger.info("Admin user already exists, skipping seed")
                    return
                
                # Create admin user
                admin_user = User(
                    email="admin@example.com",
                    full_name="System Administrator",
                    role=UserRole.ADMIN,
                    is_active=True
                )
                admin_user.set_password("admin123456")  # Change this in production
                
                session.add(admin_user)
                await session.commit()
                
                logger.info("Database seeded successfully")
                logger.info("Admin user created:")
                logger.info("  Email: admin@example.com")
                logger.info("  Password: admin123456")
                logger.info("  Role: admin")
                logger.warning("Please change the admin password in production!")
                
            except Exception as e:
                await session.rollback()
                logger.error(f"Failed to seed database: {e}")
                raise
    
    async def reset_database(self, test: bool = False) -> None:
        """Reset the database by dropping and recreating all tables."""
        logger.warning("Resetting database - all data will be lost!")
        
        if not test and not settings.is_development:
            raise RuntimeError("Database reset is only allowed in development or test mode")
        
        # Use appropriate engine
        target_engine = test_engine if test else engine
        
        if not target_engine:
            raise RuntimeError("Database engine not configured")
        
        async with target_engine.begin() as conn:
            # Drop all tables
            await conn.run_sync(Base.metadata.drop_all)
            logger.info("All tables dropped")
            
            # Create all tables
            await conn.run_sync(Base.metadata.create_all)
            logger.info("All tables created")
        
        # Seed with initial data
        await self.seed_database(test=test)
        
        logger.info("Database reset completed")


def main():
    """Main CLI interface for migration management."""
    parser = argparse.ArgumentParser(description="Database migration management with Docker")
    subparsers = parser.add_subparsers(dest="command", help="Available commands")
    
    # Create migration command
    create_parser = subparsers.add_parser("create", help="Create a new migration")
    create_parser.add_argument("message", help="Migration message")
    
    # Migrate command
    migrate_parser = subparsers.add_parser("migrate", help="Run pending migrations")
    migrate_parser.add_argument("--test", action="store_true", help="Run on test database")
    
    # Rollback command
    rollback_parser = subparsers.add_parser("rollback", help="Rollback migrations")
    rollback_parser.add_argument("revision", nargs="?", default="-1", help="Revision to rollback to")
    
    # History command
    subparsers.add_parser("history", help="Show migration history")
    
    # Current command
    subparsers.add_parser("current", help="Show current revision")
    
    # Seed command
    seed_parser = subparsers.add_parser("seed", help="Seed database with initial data")
    seed_parser.add_argument("--test", action="store_true", help="Seed test database")
    
    # Reset command
    reset_parser = subparsers.add_parser("reset", help="Reset database (development only)")
    reset_parser.add_argument("--test", action="store_true", help="Reset test database")
    reset_parser.add_argument("--confirm", action="store_true", help="Confirm database reset")
    
    # Start/stop database commands
    start_parser = subparsers.add_parser("start-db", help="Start database container")
    start_parser.add_argument("--test", action="store_true", help="Start test database")
    
    stop_parser = subparsers.add_parser("stop-db", help="Stop database container")
    stop_parser.add_argument("--test", action="store_true", help="Stop test database")
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return
    
    manager = MigrationManager()
    
    try:
        if args.command == "create":
            manager.create_migration(args.message)
        
        elif args.command == "migrate":
            manager.run_migrations(test=args.test)
        
        elif args.command == "rollback":
            manager.rollback_migration(args.revision)
        
        elif args.command == "history":
            manager.show_migration_history()
        
        elif args.command == "current":
            manager.show_current_revision()
        
        elif args.command == "seed":
            asyncio.run(manager.seed_database(test=args.test))
        
        elif args.command == "reset":
            if not args.confirm:
                print("Database reset requires --confirm flag")
                return
            asyncio.run(manager.reset_database(test=args.test))
        
        elif args.command == "start-db":
            manager.start_database_container(test=args.test)
        
        elif args.command == "stop-db":
            manager.stop_database_container(test=args.test)
        
    except Exception as e:
        logger.error(f"Command failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()