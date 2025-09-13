# Database Foundation Setup

This document describes the database foundation and migration system for the Property Listing API.

## Overview

The database foundation includes:
- **SQLAlchemy 2.0** with async support for PostgreSQL
- **Alembic** for database migrations with Docker compatibility
- **Connection pooling** optimized for containerized environments
- **Base model** with common fields (id, created_at, updated_at)

## Components

### 1. Database Configuration (`app/config.py`)
- Environment-based configuration using Pydantic Settings
- Docker-compatible database URLs
- Separate test database configuration
- Connection pooling settings

### 2. Database Connection (`app/database.py`)
- Async SQLAlchemy engine with optimized connection pooling
- Base model class with UUID primary keys and timestamps
- Database session management with dependency injection
- Connection testing and monitoring utilities

### 3. Migration System (`alembic/`)
- Alembic configuration for Docker environments
- Async migration support
- Auto-generated migration file naming with timestamps
- Environment-aware migration execution

## Usage

### Local Development (without Docker)

1. **Test database connection:**
   ```bash
   python test_db_connection.py
   ```

2. **Check Alembic configuration:**
   ```bash
   python -c "from alembic.config import Config; Config('alembic.ini')"
   ```

### Docker Environment

1. **Start containers:**
   ```bash
   docker-compose up -d
   ```

2. **Test database connection:**
   ```bash
   python migrate.py test
   ```

3. **Create initial migration:**
   ```bash
   python migrate.py revision "Initial migration"
   ```

4. **Apply migrations:**
   ```bash
   python migrate.py upgrade
   ```

5. **Check migration status:**
   ```bash
   python migrate.py current
   ```

## Migration Commands

The `migrate.py` script provides Docker-compatible migration commands:

- `python migrate.py test` - Test database connection
- `python migrate.py init` - Initialize database with current models
- `python migrate.py revision "message"` - Create new migration
- `python migrate.py upgrade [target]` - Apply migrations
- `python migrate.py downgrade [target]` - Rollback migrations
- `python migrate.py current` - Show current migration
- `python migrate.py history` - Show migration history

## Database Schema

### Base Model Fields
All models inherit from `Base` and include:
- `id`: UUID primary key with automatic generation
- `created_at`: Timestamp with timezone (auto-set on creation)
- `updated_at`: Timestamp with timezone (auto-updated on modification)

### Connection Pooling
Optimized for Docker containers:
- **Pool size**: 10 connections
- **Max overflow**: 20 additional connections
- **Pool recycle**: 3600 seconds (1 hour)
- **Pool timeout**: 30 seconds
- **Pre-ping**: Enabled for connection validation

## Environment Variables

### Required for Docker:
- `POSTGRES_DB`: Database name
- `POSTGRES_USER`: Database user
- `POSTGRES_PASSWORD`: Database password
- `POSTGRES_HOST`: Database host (usually "db" in Docker)
- `POSTGRES_PORT`: Database port (usually 5432)

### Optional:
- `DATABASE_URL`: Complete database URL (overrides individual components)
- `TEST_POSTGRES_*`: Test database configuration

## Testing

The database foundation includes comprehensive testing utilities:

1. **Connection testing**: Verify database connectivity
2. **Pool monitoring**: Check connection pool status
3. **Migration testing**: Validate migration scripts
4. **Async operation testing**: Ensure async compatibility

## Docker Integration

The system is designed for Docker Compose environments:

1. **Service dependencies**: API service depends on database service
2. **Volume mounting**: Persistent data storage
3. **Network isolation**: Secure container communication
4. **Health checks**: Database readiness verification

## Performance Considerations

1. **Connection pooling**: Optimized for concurrent requests
2. **Async operations**: Non-blocking database operations
3. **Index strategy**: Prepared for search optimization
4. **Query monitoring**: Built-in performance tracking

## Security Features

1. **Connection validation**: Pre-ping enabled
2. **Credential management**: Environment-based configuration
3. **SQL injection protection**: SQLAlchemy ORM usage
4. **Connection encryption**: PostgreSQL SSL support

## Troubleshooting

### Common Issues:

1. **Connection refused**: Check if PostgreSQL container is running
2. **Permission denied**: Verify database credentials
3. **Migration conflicts**: Use `alembic history` to check migration state
4. **Pool exhaustion**: Monitor connection pool metrics

### Debug Commands:

```bash
# Check container status
docker-compose ps

# View database logs
docker-compose logs db

# Connect to database directly
docker-compose exec db psql -U postgres -d property_listings

# Check migration status
python migrate.py current
```

## Next Steps

After completing this database foundation setup:

1. Create data models (User, Property, PropertyImage)
2. Set up repository layer for data access
3. Implement service layer with business logic
4. Create API endpoints with database integration
5. Add comprehensive testing suite