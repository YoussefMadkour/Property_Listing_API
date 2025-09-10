# Property Listing API

A comprehensive FastAPI-based backend service for managing property listings, similar to platforms like Dubizzle. The system provides CRUD operations for property management, advanced search and filtering capabilities, image handling, and secure JWT-based authentication.

## Features

- **Property Management**: Create, read, update, and delete property listings
- **Advanced Search**: Filter properties by location, price range, bedrooms, and more
- **Image Upload**: Associate multiple images with property listings
- **Authentication**: JWT-based authentication with role-based access control
- **Performance Optimized**: Database indexing for fast search queries
- **API Documentation**: Auto-generated OpenAPI/Swagger documentation

## Technology Stack

- **Framework**: FastAPI
- **Database**: PostgreSQL with SQLAlchemy ORM
- **Authentication**: JWT tokens
- **File Storage**: Local filesystem (extensible to cloud storage)
- **Testing**: pytest with async support

## Quick Start

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
   # Edit .env with your configuration
   ```

5. **Set up PostgreSQL database**
   ```bash
   createdb property_listing_db
   ```

6. **Run database migrations** (when implemented)
   ```bash
   alembic upgrade head
   ```

7. **Start the development server**
   ```bash
   uvicorn app.main:app --reload
   ```

The API will be available at `http://localhost:8000`

### API Documentation

- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

## Project Structure

```
property-listing-api/
├── app/
│   ├── __init__.py
│   ├── main.py                 # FastAPI application entry point
│   ├── config.py              # Configuration management
│   ├── models/                # SQLAlchemy models
│   ├── schemas/               # Pydantic schemas
│   ├── repositories/          # Data access layer
│   ├── services/              # Business logic layer
│   ├── routers/               # API route handlers
│   └── utils/                 # Utility functions
├── tests/                     # Test suite
├── uploads/                   # File storage directory
├── requirements.txt           # Python dependencies
└── README.md
```

## Development

### Running Tests
```bash
pytest
```

### Code Formatting
```bash
black app/ tests/
isort app/ tests/
```

### Type Checking
```bash
mypy app/
```

## Configuration

The application uses Pydantic settings for configuration management. Key settings include:

- **Database URL**: PostgreSQL connection string
- **JWT Settings**: Secret key, algorithm, token expiration
- **File Upload**: Directory, size limits, allowed types
- **API Settings**: CORS origins, pagination defaults

See `.env.example` for all available configuration options.

## License

This project is licensed under the MIT License.