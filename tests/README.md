# Property Listing API Test Suite

This directory contains comprehensive tests for the Property Listing API, covering models, repositories, services, and integration scenarios.

## Test Structure

### Test Files

- **`conftest.py`** - Test configuration, fixtures, and utilities
- **`test_models.py`** - Unit tests for database models
- **`test_repositories.py`** - Tests for repository layer (data access)
- **`test_services.py`** - Tests for service layer (business logic)
- **`test_error_handling.py`** - Tests for error handling and validation
- **`test_image_upload.py`** - Tests for image upload functionality

### Test Categories

#### 1. Model Tests (`test_models.py`)
- **User Model Tests**
  - User creation and validation
  - Email format validation
  - Password hashing and verification
  - Role-based permissions
  - User dictionary conversion
  
- **Property Model Tests**
  - Property creation and validation
  - Price, bedroom, bathroom, and area validation
  - Coordinate validation
  - Comprehensive validation testing
  - Property dictionary conversion
  
- **PropertyImage Model Tests**
  - Image creation and metadata
  - File size and MIME type validation
  - Image dimension validation
  - Aspect ratio calculation
  - Image dictionary conversion

#### 2. Repository Tests (`test_repositories.py`)
- **Base Repository Tests**
  - CRUD operations (Create, Read, Update, Delete)
  - Pagination and filtering
  - Bulk operations
  - Record counting and existence checks
  
- **User Repository Tests**
  - User creation with validation
  - Email-based authentication
  - Password management
  - Role and status management
  - User statistics and search
  
- **Property Repository Tests**
  - Property creation with validation
  - Advanced search and filtering
  - Location-based searches
  - Agent-specific property management
  - Property statistics
  
- **Image Repository Tests**
  - Image creation and management
  - Property-image associations
  - Primary image handling

#### 3. Service Tests (`test_services.py`)
- **Auth Service Tests**
  - User authentication flows
  - JWT token management
  - Permission validation
  - User management operations
  - Password change operations
  
- **Property Service Tests**
  - Property CRUD with business logic
  - Ownership and permission validation
  - Advanced search functionality
  - Property statistics
  - Featured property management

## Test Configuration

### Database Setup
Tests use a separate PostgreSQL test database to ensure isolation:
- **Test Database**: `property_listings_test`
- **Port**: `5433` (different from main app)
- **Docker Container**: `property_api_test_db`

### Environment Variables
```bash
TEST_DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5433/property_listings_test
TEST_JWT_SECRET_KEY=test-secret-key-for-testing-only
TEST_UPLOAD_DIR=/app/test_uploads
TESTING=true
ENVIRONMENT=testing
```

### Test Fixtures
The test suite includes comprehensive fixtures for:
- **Database Sessions**: Isolated test database sessions
- **Test Users**: Agent, admin, and inactive user fixtures
- **Test Properties**: Active and inactive property fixtures
- **Test Images**: Property image fixtures
- **Repositories**: Pre-configured repository instances
- **Services**: Pre-configured service instances

### Test Factories
Factory classes for creating test data:
- **UserFactory**: Creates test users with various roles and states
- **PropertyFactory**: Creates test properties with different attributes
- **ImageFactory**: Creates test property images with metadata

## Running Tests

### Prerequisites
1. Docker and Docker Compose installed
2. Python 3.12+ with virtual environment
3. All dependencies installed (`pip install -r requirements.txt`)

### Quick Start
```bash
# Run all tests with Docker setup
python run_tests.py

# Run specific test files
python -m pytest tests/test_models.py -v
python -m pytest tests/test_repositories.py -v
python -m pytest tests/test_services.py -v

# Run tests with coverage
python -m pytest tests/ --cov=app --cov-report=html

# Run tests without Docker (assumes DB is running)
python run_tests.py --no-docker
```

### Test Runner Options
```bash
# Keep containers running after tests
python run_tests.py --keep-containers

# Run only migrations
python run_tests.py --migrations-only

# Run specific test patterns
python run_tests.py tests/test_models.py::TestUserModel

# Run with custom pytest arguments
python run_tests.py -- -x --pdb  # Stop on first failure, enter debugger
```

### Manual Database Setup
If you prefer to manage the test database manually:

```bash
# Start test database
docker-compose -f docker-compose.test.yml up -d test_db

# Run migrations
DATABASE_URL="postgresql+asyncpg://postgres:postgres@localhost:5433/property_listings_test" \
python -m alembic upgrade head

# Run tests
python -m pytest tests/ -v

# Stop test database
docker-compose -f docker-compose.test.yml down
```

## Test Coverage

The test suite aims for comprehensive coverage:

### Model Coverage
- ✅ All model fields and relationships
- ✅ Validation methods and business rules
- ✅ Model properties and computed fields
- ✅ Error handling for invalid data

### Repository Coverage
- ✅ All CRUD operations
- ✅ Complex queries and filtering
- ✅ Pagination and sorting
- ✅ Database constraints and relationships
- ✅ Error handling for database operations

### Service Coverage
- ✅ Business logic validation
- ✅ Authentication and authorization
- ✅ Permission checking
- ✅ Error handling and exceptions
- ✅ Integration between services

### Target Metrics
- **Code Coverage**: 90%+ for critical business logic
- **Test Count**: 100+ comprehensive test cases
- **Performance**: All tests complete in under 30 seconds

## Test Data Management

### Test Isolation
- Each test gets a fresh database session
- Transactions are rolled back after each test
- No test data persists between test runs

### Test Data Factories
Use factories for consistent test data creation:

```python
# Create test user
user = await UserFactory.create_user(
    user_repository,
    email="test@example.com",
    role=UserRole.AGENT
)

# Create test property
property_obj = await PropertyFactory.create_property(
    property_repository,
    agent_id=user.id,
    title="Test Property",
    price=Decimal("1500.00")
)
```

### Assertions
Use provided assertion helpers for consistent testing:

```python
# Compare users
assert_user_equal(user1, user2, check_password=True)

# Compare properties
assert_property_equal(prop1, prop2)

# Compare images
assert_image_equal(img1, img2)
```

## Debugging Tests

### Common Issues
1. **Database Connection**: Ensure test database is running on port 5433
2. **Migration Errors**: Run migrations manually if needed
3. **Import Errors**: Check Python path and virtual environment
4. **Async Issues**: Ensure proper async/await usage

### Debug Commands
```bash
# Run single test with verbose output
python -m pytest tests/test_models.py::TestUserModel::test_user_creation -v -s

# Run with debugger on failure
python -m pytest tests/ --pdb

# Run with detailed traceback
python -m pytest tests/ --tb=long

# Check test setup
python test_setup.py
```

### Logging
Tests include detailed logging for debugging:
- Repository operations
- Service business logic
- Authentication flows
- Error conditions

## Continuous Integration

The test suite is designed for CI/CD integration:

### GitHub Actions Example
```yaml
name: Tests
on: [push, pull_request]
jobs:
  test:
    runs-on: ubuntu-latest
    services:
      postgres:
        image: postgres:14
        env:
          POSTGRES_PASSWORD: postgres
          POSTGRES_DB: property_listings_test
        options: >-
          --health-cmd pg_isready
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5
    steps:
      - uses: actions/checkout@v2
      - name: Set up Python
        uses: actions/setup-python@v2
        with:
          python-version: 3.12
      - name: Install dependencies
        run: pip install -r requirements.txt
      - name: Run tests
        run: python run_tests.py --no-docker
```

## Contributing

When adding new tests:

1. **Follow Naming Conventions**: `test_*` for functions, `Test*` for classes
2. **Use Fixtures**: Leverage existing fixtures and factories
3. **Test Edge Cases**: Include both success and failure scenarios
4. **Document Complex Tests**: Add docstrings for complex test logic
5. **Maintain Coverage**: Ensure new code is properly tested

### Test Checklist
- [ ] Unit tests for new models/methods
- [ ] Repository tests for new database operations
- [ ] Service tests for new business logic
- [ ] Integration tests for new API endpoints
- [ ] Error handling tests for new exceptions
- [ ] Performance tests for complex operations

## Performance Testing

For performance-critical operations:

```python
import time
import pytest

@pytest.mark.slow
async def test_large_property_search_performance():
    """Test search performance with large dataset."""
    start_time = time.time()
    
    # Create large dataset
    for i in range(1000):
        await PropertyFactory.create_property(...)
    
    # Perform search
    results = await property_service.search_properties(...)
    
    end_time = time.time()
    assert end_time - start_time < 2.0  # Should complete in under 2 seconds
```

Run performance tests separately:
```bash
python -m pytest tests/ -m slow -v
```