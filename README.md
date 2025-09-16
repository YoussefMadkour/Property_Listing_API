# Property Listing API

A comprehensive FastAPI-based backend service for managing property listings, similar to platforms like Dubizzle. The system provides CRUD operations for property management, advanced search and filtering capabilities, image handling, and secure JWT-based authentication.

## Features

- **Property Management**: Create, read, update, and delete property listings
- **Advanced Search**: Filter properties by location, price range, bedrooms, and more
- **Image Upload**: Associate multiple images with property listings
- **Authentication**: JWT-based authentication with role-based access control
- **Performance Optimized**: Database indexing for fast search queries
- **API Documentation**: Auto-generated OpenAPI/Swagger documentation
- **Containerized**: Full Docker support for development and production
- **Health Monitoring**: Built-in health checks and performance monitoring

## Technology Stack

- **Framework**: FastAPI (Python 3.12)
- **Database**: PostgreSQL 14+ with SQLAlchemy 2.0 (async)
- **Authentication**: JWT tokens with bcrypt password hashing
- **Containerization**: Docker & Docker Compose
- **File Storage**: Docker volumes (extensible to cloud storage)
- **Testing**: pytest with async support and Docker test containers
- **Database Migrations**: Alembic
- **API Documentation**: Auto-generated OpenAPI/Swagger

## Quick Start with Docker (Recommended)

### Prerequisites

- Docker 20.10+
- Docker Compose 2.0+

### Docker Setup

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd property-listing-api
   ```

2. **Set up environment variables**
   ```bash
   cp .env.example .env
   # Edit .env with your configuration (optional for development)
   ```

3. **Start the application with Docker Compose**
   ```bash
   # Start all services (API + Database)
   docker-compose up -d
   
   # View logs
   docker-compose logs -f api
   ```

4. **Run database migrations**
   ```bash
   # Run migrations using the migration service
   docker-compose --profile migration up migrate
   ```

5. **Access the application**
   - **API**: http://localhost:8000
   - **Swagger UI**: http://localhost:8000/docs
   - **ReDoc**: http://localhost:8000/redoc
   - **Health Check**: http://localhost:8000/health

### Docker Commands

```bash
# Start services
docker-compose up -d

# Stop services
docker-compose down

# View logs
docker-compose logs -f [service_name]

# Run migrations
docker-compose --profile migration up migrate

# Run tests
docker-compose -f docker-compose.test.yml up --build --abort-on-container-exit

# Rebuild containers
docker-compose up --build

# Clean up volumes (WARNING: This will delete all data)
docker-compose down -v
```

## Local Development Setup (Alternative)

### Prerequisites

- Python 3.12+
- PostgreSQL 14+
- pip or poetry for dependency management

### Installation

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd property-listing-api
   ```

2. **Create and activate virtual environment**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Set up environment variables**
   ```bash
   cp .env.example .env
   # Edit .env with your local PostgreSQL configuration
   ```

5. **Set up PostgreSQL database**
   ```bash
   createdb property_listings
   ```

6. **Run database migrations**
   ```bash
   python migrate.py migrate
   ```

7. **Start the development server**
   ```bash
   uvicorn app.main:app --reload
   ```

The API will be available at `http://localhost:8000`

## API Documentation

### Authentication

All protected endpoints require a JWT token in the Authorization header:
```
Authorization: Bearer <your_jwt_token>
```

#### Login
```bash
curl -X POST "http://localhost:8000/auth/login" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "agent@example.com",
    "password": "password123"
  }'
```

Response:
```json
{
  "access_token": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...",
  "token_type": "bearer",
  "expires_in": 1800
}
```

### Property Management

#### Create Property
```bash
curl -X POST "http://localhost:8000/properties" \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{
    "title": "Beautiful 2BR Apartment",
    "description": "Spacious apartment in downtown area",
    "property_type": "rental",
    "price": 2500.00,
    "bedrooms": 2,
    "bathrooms": 2,
    "area_sqft": 1200,
    "location": "Downtown Dubai",
    "latitude": 25.2048,
    "longitude": 55.2708
  }'
```

#### Search Properties
```bash
# Basic search
curl "http://localhost:8000/properties?page=1&page_size=10"

# Search with filters
curl "http://localhost:8000/properties?location=Dubai&min_price=1000&max_price=5000&bedrooms=2&property_type=rental"
```

#### Get Property Details
```bash
curl "http://localhost:8000/properties/{property_id}"
```

#### Update Property
```bash
curl -X PUT "http://localhost:8000/properties/{property_id}" \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{
    "title": "Updated Property Title",
    "price": 2800.00
  }'
```

#### Delete Property
```bash
curl -X DELETE "http://localhost:8000/properties/{property_id}" \
  -H "Authorization: Bearer <token>"
```

### Image Management

#### Upload Property Images
```bash
curl -X POST "http://localhost:8000/properties/{property_id}/images" \
  -H "Authorization: Bearer <token>" \
  -F "file=@/path/to/image.jpg"
```

#### Get Property Images
```bash
curl "http://localhost:8000/properties/{property_id}/images"
```

#### Delete Image
```bash
curl -X DELETE "http://localhost:8000/images/{image_id}" \
  -H "Authorization: Bearer <token>"
```

### Response Examples

#### Property Response
```json
{
  "id": "123e4567-e89b-12d3-a456-426614174000",
  "title": "Beautiful 2BR Apartment",
  "description": "Spacious apartment in downtown area",
  "property_type": "rental",
  "price": 2500.00,
  "bedrooms": 2,
  "bathrooms": 2,
  "area_sqft": 1200,
  "location": "Downtown Dubai",
  "latitude": 25.2048,
  "longitude": 55.2708,
  "agent_id": "456e7890-e89b-12d3-a456-426614174001",
  "created_at": "2024-01-15T10:30:00Z",
  "updated_at": "2024-01-15T10:30:00Z",
  "images": [
    {
      "id": "789e0123-e89b-12d3-a456-426614174002",
      "filename": "living_room.jpg",
      "file_path": "/uploads/properties/123e4567-e89b-12d3-a456-426614174000/living_room.jpg",
      "file_size": 2048576,
      "mime_type": "image/jpeg",
      "upload_date": "2024-01-15T10:35:00Z",
      "is_primary": true
    }
  ]
}
```

#### Search Results Response
```json
{
  "items": [
    {
      "id": "123e4567-e89b-12d3-a456-426614174000",
      "title": "Beautiful 2BR Apartment",
      "price": 2500.00,
      "bedrooms": 2,
      "location": "Downtown Dubai",
      "images": []
    }
  ],
  "total": 150,
  "page": 1,
  "page_size": 10,
  "total_pages": 15
}
```

#### Error Response
```json
{
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "Validation failed",
    "details": [
      {
        "field": "price",
        "message": "Price must be greater than 0"
      }
    ]
  }
}
```

## Project Structure

```
property-listing-api/
├── app/
│   ├── __init__.py
│   ├── main.py                 # FastAPI application entry point
│   ├── config.py              # Configuration management
│   ├── database.py            # Database connection and session management
│   ├── models/                # SQLAlchemy models
│   │   ├── __init__.py
│   │   ├── property.py        # Property model
│   │   ├── user.py           # User model
│   │   └── image.py          # PropertyImage model
│   ├── schemas/               # Pydantic schemas for request/response
│   │   ├── __init__.py
│   │   ├── property.py       # Property schemas
│   │   ├── user.py          # User schemas
│   │   ├── auth.py          # Authentication schemas
│   │   ├── image.py         # Image schemas
│   │   └── error.py         # Error response schemas
│   ├── repositories/          # Data access layer
│   │   ├── __init__.py
│   │   ├── base.py          # Base repository class
│   │   ├── property.py      # Property repository
│   │   ├── user.py          # User repository
│   │   └── image.py         # Image repository
│   ├── services/              # Business logic layer
│   │   ├── __init__.py
│   │   ├── property.py      # Property service
│   │   ├── auth.py          # Authentication service
│   │   ├── image.py         # Image service
│   │   └── error_handler.py # Error handling service
│   ├── routers/               # API route handlers
│   │   ├── __init__.py
│   │   ├── properties.py    # Property endpoints
│   │   ├── auth.py          # Authentication endpoints
│   │   ├── images.py        # Image endpoints
│   │   └── monitoring.py    # Health and monitoring endpoints
│   ├── middleware/            # Custom middleware
│   │   ├── __init__.py
│   │   ├── performance.py   # Performance monitoring
│   │   └── validation.py    # Request validation
│   └── utils/                 # Utility functions
│       ├── __init__.py
│       ├── auth.py          # Authentication utilities
│       ├── dependencies.py  # FastAPI dependencies
│       ├── exceptions.py    # Custom exceptions
│       ├── validators.py    # Data validators
│       ├── file_utils.py    # File handling utilities
│       └── query_optimizer.py # Database query optimization
├── tests/                     # Test suite
│   ├── __init__.py
│   ├── conftest.py           # Test configuration and fixtures
│   ├── test_models.py        # Model tests
│   ├── test_repositories.py  # Repository tests
│   ├── test_services.py      # Service tests
│   ├── test_integration_*.py # Integration tests
│   └── test_performance.py   # Performance tests
├── alembic/                   # Database migrations
│   ├── versions/             # Migration files
│   ├── env.py               # Alembic environment
│   └── script.py.mako       # Migration template
├── uploads/                   # File storage directory (Docker volume)
├── docker-compose.yml         # Development Docker configuration
├── docker-compose.test.yml    # Test Docker configuration
├── docker-compose.prod.yml    # Production Docker configuration
├── Dockerfile                 # Container definition
├── requirements.txt           # Python dependencies
├── .env.example              # Environment variables template
├── alembic.ini               # Alembic configuration
├── migrate.py                # Migration runner script
└── README.md
```

## Development

### Running Tests

#### With Docker (Recommended)
```bash
# Run all tests
docker-compose -f docker-compose.test.yml up --build --abort-on-container-exit

# Run specific test file
docker-compose -f docker-compose.test.yml run --rm test pytest tests/test_models.py -v

# Run with coverage
docker-compose -f docker-compose.test.yml run --rm test pytest --cov=app --cov-report=html
```

#### Local Testing
```bash
# Run all tests
python run_tests.py

# Run specific tests
pytest tests/test_models.py -v

# Run integration tests
python run_integration_tests.py

# Run performance tests
python run_performance_tests.py
```

### Database Migrations

#### With Docker
```bash
# Create new migration
docker-compose run --rm api alembic revision --autogenerate -m "Description"

# Run migrations
docker-compose --profile migration up migrate

# Rollback migration
docker-compose run --rm api alembic downgrade -1
```

#### Local Development
```bash
# Create new migration
alembic revision --autogenerate -m "Description"

# Run migrations
python migrate.py migrate

# Rollback migration
alembic downgrade -1
```

### Code Quality

```bash
# Format code
black app/ tests/
isort app/ tests/

# Type checking
mypy app/

# Linting
flake8 app/ tests/
```

## Configuration

The application uses Pydantic settings for configuration management. All settings can be configured via environment variables.

### Environment Variables

#### Application Settings
- `APP_NAME`: Application name (default: "Property Listing API")
- `APP_VERSION`: Application version (default: "1.0.0")
- `ENVIRONMENT`: Environment (development/staging/production)
- `DEBUG`: Enable debug mode (default: false)

#### Database Settings
- `DATABASE_URL`: PostgreSQL connection string
- `POSTGRES_DB`: Database name
- `POSTGRES_USER`: Database user
- `POSTGRES_PASSWORD`: Database password
- `POSTGRES_HOST`: Database host
- `POSTGRES_PORT`: Database port

#### JWT Settings
- `JWT_SECRET_KEY`: Secret key for JWT tokens (must be 32+ characters)
- `JWT_ALGORITHM`: JWT algorithm (default: HS256)
- `ACCESS_TOKEN_EXPIRE_MINUTES`: Token expiration time (default: 30)

#### File Upload Settings
- `UPLOAD_DIR`: Upload directory path
- `MAX_FILE_SIZE`: Maximum file size in bytes (default: 10MB)
- `ALLOWED_FILE_TYPES`: Comma-separated list of allowed MIME types

#### API Settings
- `API_V1_PREFIX`: API version prefix (default: /api/v1)
- `CORS_ORIGINS`: Comma-separated list of allowed origins
- `DEFAULT_PAGE_SIZE`: Default pagination size (default: 20)
- `MAX_PAGE_SIZE`: Maximum pagination size (default: 100)

See `.env.example` for all available configuration options.

## Deployment

### Production Deployment with Docker

1. **Set up production environment file**
   ```bash
   cp .env.example .env.prod
   # Edit .env.prod with production values
   ```

2. **Deploy with production configuration**
   ```bash
   docker-compose -f docker-compose.prod.yml up -d
   ```

3. **Run database migrations**
   ```bash
   docker-compose -f docker-compose.prod.yml --profile migration up migrate
   ```

### Health Checks

The application includes built-in health checks:

- **Health endpoint**: `GET /health`
- **Database health**: `GET /health/db`
- **Docker health checks**: Configured in docker-compose files

### Monitoring

Performance monitoring is available through:

- **Metrics endpoint**: `GET /metrics`
- **Performance logs**: Structured logging with request timing
- **Database query optimization**: Built-in query performance monitoring

## Troubleshooting

### Common Issues

#### Docker Issues
```bash
# Clean up containers and volumes
docker-compose down -v
docker system prune -f

# Rebuild containers
docker-compose up --build
```

#### Database Connection Issues
```bash
# Check database logs
docker-compose logs db

# Test database connection
docker-compose exec db psql -U postgres -d property_listings -c "SELECT 1;"
```

#### Permission Issues
```bash
# Fix upload directory permissions
sudo chown -R $USER:$USER uploads/
chmod 755 uploads/
```

## License

This project is licensed under the MIT License.