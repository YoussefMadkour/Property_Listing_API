# Database Migration Guide

This guide explains how to use the database migration system with Docker integration for the Property Listing API.

## Overview

The migration system uses Alembic for database schema management and includes Docker integration for containerized environments. It supports:

- Creating and running migrations
- Database seeding with initial data
- Rollback functionality
- Docker Compose integration
- Test database management

## Migration Script Usage

The `migrate.py` script provides a comprehensive CLI for database management:

### Basic Commands

```bash
# Create a new migration
python migrate.py create "Description of changes"

# Run pending migrations
python migrate.py migrate

# Run migrations on test database
python migrate.py migrate --test

# Rollback to previous migration
python migrate.py rollback

# Rollback to specific revision
python migrate.py rollback <revision_id>

# Show current database revision
python migrate.py current

# Show migration history
python migrate.py history

# Seed database with initial data
python migrate.py seed

# Seed test database
python migrate.py seed --test

# Reset database (development only)
python migrate.py reset --confirm

# Reset test database
python migrate.py reset --test --confirm
```

### Database Container Management

```bash
# Start database container
python migrate.py start-db

# Start test database container
python migrate.py start-db --test

# Stop database container
python migrate.py stop-db

# Stop test database container
python migrate.py stop-db --test
```

## Docker Compose Integration

### Running Migrations with Docker Compose

The system includes a dedicated migration service in Docker Compose:

```bash
# Run migrations using Docker Compose
docker-compose --profile migration run --rm migrate

# Create a new migration
docker-compose --profile migration run --rm migrate python migrate.py create "New migration"

# Seed the database
docker-compose --profile migration run --rm migrate python migrate.py seed

# Show current revision
docker-compose --profile migration run --rm migrate python migrate.py current

# Rollback migration
docker-compose --profile migration run --rm migrate python migrate.py rollback
```

### Environment Setup

1. Copy the environment template:
```bash
cp .env.example .env
```

2. Update the `.env` file with your configuration:
```env
# Database Configuration
DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5434/property_listings
POSTGRES_DB=property_listings
POSTGRES_USER=postgres
POSTGRES_PASSWORD=postgres
POSTGRES_HOST=localhost
POSTGRES_PORT=5434

# JWT Configuration
JWT_SECRET_KEY=your-secret-key-change-in-production-must-be-at-least-32-characters-long
```

## Migration Workflow

### 1. Development Workflow

1. **Start the database:**
```bash
python migrate.py start-db
```

2. **Make model changes** in `app/models/`

3. **Create migration:**
```bash
python migrate.py create "Add new field to User model"
```

4. **Review the generated migration** in `alembic/versions/`

5. **Run the migration:**
```bash
python migrate.py migrate
```

6. **Verify the changes:**
```bash
python migrate.py current
```

### 2. Production Deployment

1. **Build and deploy containers:**
```bash
docker-compose up -d db
```

2. **Run migrations:**
```bash
docker-compose --profile migration run --rm migrate
```

3. **Start the application:**
```bash
docker-compose up -d api
```

### 3. Testing Workflow

1. **Start test database:**
```bash
python migrate.py start-db --test
```

2. **Run migrations on test database:**
```bash
python migrate.py migrate --test
```

3. **Seed test data:**
```bash
python migrate.py seed --test
```

4. **Run tests:**
```bash
pytest
```

5. **Reset test database when needed:**
```bash
python migrate.py reset --test --confirm
```

## Database Schema

### Current Tables

1. **users** - User accounts with authentication
   - `id` (UUID, Primary Key)
   - `email` (String, Unique)
   - `hashed_password` (String)
   - `full_name` (String)
   - `role` (Enum: AGENT, ADMIN)
   - `is_active` (Boolean)
   - `created_at`, `updated_at` (Timestamps)

2. **properties** - Property listings
   - `id` (UUID, Primary Key)
   - `title` (String)
   - `description` (Text)
   - `property_type` (Enum: RENTAL, SALE)
   - `price` (Decimal)
   - `bedrooms`, `bathrooms` (Integer)
   - `area_sqft` (Integer)
   - `location` (String)
   - `latitude`, `longitude` (Decimal, Optional)
   - `is_active` (Boolean)
   - `agent_id` (UUID, Foreign Key to users)
   - `created_at`, `updated_at` (Timestamps)

3. **property_images** - Property image metadata
   - `id` (UUID, Primary Key)
   - `property_id` (UUID, Foreign Key to properties)
   - `filename` (String)
   - `file_path` (String, Unique)
   - `file_size` (Integer)
   - `mime_type` (String)
   - `width`, `height` (Integer, Optional)
   - `is_primary` (Boolean)
   - `display_order` (Integer)
   - `upload_date` (Timestamp)
   - `created_at`, `updated_at` (Timestamps)

### Database Indexes

The system includes optimized indexes for:
- User email lookups
- Property search by location, price, bedrooms
- Property filtering by type and status
- Image management and retrieval
- Composite indexes for complex queries

## Initial Data Seeding

The system automatically creates an admin user during seeding:

- **Email:** admin@example.com
- **Password:** admin123456
- **Role:** admin

**⚠️ Important:** Change the admin password in production!

## Troubleshooting

### Common Issues

1. **Port conflicts:**
   - The database runs on port 5434 to avoid conflicts
   - Update your connection strings accordingly

2. **Permission errors:**
   - Ensure Docker has proper permissions
   - Check file ownership in mounted volumes

3. **Migration conflicts:**
   - Use `python migrate.py history` to check migration status
   - Resolve conflicts manually if needed
   - Use rollback functionality to revert problematic migrations

4. **Container connectivity:**
   - Ensure containers are on the same network
   - Check Docker Compose network configuration

### Debugging

1. **Check container logs:**
```bash
docker-compose logs db
docker-compose logs api
```

2. **Connect to database directly:**
```bash
docker-compose exec db psql -U postgres -d property_listings
```

3. **Inspect migration status:**
```bash
python migrate.py current
python migrate.py history
```

## Best Practices

1. **Always backup before migrations** in production
2. **Test migrations** on a copy of production data
3. **Review generated migrations** before applying
4. **Use descriptive migration messages**
5. **Keep migrations small and focused**
6. **Document breaking changes**
7. **Use the rollback feature** to test migration reversibility

## Security Considerations

1. **Change default passwords** in production
2. **Use strong JWT secrets**
3. **Limit database access** to necessary services
4. **Use environment variables** for sensitive configuration
5. **Enable SSL/TLS** for database connections in production
6. **Regular security updates** for container images

## Performance Optimization

1. **Database indexes** are automatically created for common queries
2. **Connection pooling** is configured for optimal performance
3. **Async operations** reduce blocking in the application
4. **Proper foreign key constraints** ensure data integrity
5. **Composite indexes** optimize complex search queries

## Monitoring and Maintenance

1. **Monitor migration execution time**
2. **Track database size growth**
3. **Regular index maintenance**
4. **Monitor connection pool usage**
5. **Log migration activities**
6. **Set up alerts** for migration failures

For more information, see the main README.md file and the API documentation.