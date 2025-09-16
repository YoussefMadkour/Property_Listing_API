# Integration Tests Documentation

This document describes the comprehensive integration test suite for the Property Listing API.

## Overview

The integration test suite provides end-to-end testing of all API endpoints using a Docker test environment. Tests cover authentication flows, property management, image uploads, search functionality, and complex business scenarios.

## Test Structure

### Test Files

1. **`test_integration_api.py`** - Core API endpoint integration tests
2. **`test_integration_scenarios.py`** - Complex workflow and scenario tests
3. **`test_integration_config.py`** - Test configuration and utilities
4. **`conftest.py`** - Test fixtures and setup

### Test Categories

#### Authentication Tests (`TestAuthenticationEndpoints`)
- User login/logout flows
- JWT token generation and validation
- Token refresh mechanisms
- Authentication error handling
- User role verification

#### Property Management Tests (`TestPropertyManagementEndpoints`)
- CRUD operations for properties
- Property ownership validation
- Admin vs agent permissions
- Property status management
- Bulk operations

#### Image Management Tests (`TestImageManagementEndpoints`)
- Single and multiple image uploads
- Image metadata management
- File storage in Docker volumes
- Image deletion and cleanup
- Primary image designation

#### Search and Filtering Tests (`TestSearchAndFilteringEndpoints`)
- Basic property search
- Advanced filtering combinations
- Pagination and sorting
- Location-based search
- Text search functionality

#### Database Tests (`TestDatabaseCleanupAndIsolation`)
- Transaction isolation
- Concurrent operations
- Database cleanup
- Data consistency

#### Docker Integration Tests (`TestDockerVolumeIntegration`)
- File persistence in volumes
- Cross-container operations
- Storage cleanup

#### Complex Scenarios (`TestCompletePropertyManagementWorkflow`)
- End-to-end agent workflows
- Admin oversight scenarios
- Buyer search journeys
- Multi-step operations

#### Error Handling Tests (`TestErrorHandlingAndEdgeCases`)
- Invalid data handling
- Authorization edge cases
- Concurrent operation conflicts
- Pagination boundary conditions

## Test Environment

### Docker Test Setup

The integration tests use a dedicated Docker test environment:

```yaml
# docker-compose.test.yml
services:
  test_db:
    image: postgres:14-alpine
    environment:
      POSTGRES_DB: property_listings_test
      POSTGRES_USER: postgres
      POSTGRES_PASSWORD: postgres
    ports:
      - "5433:5432"
    tmpfs:
      - /var/lib/postgresql/data  # In-memory for speed

  test_api:
    build: .
    environment:
      DATABASE_URL: postgresql+asyncpg://postgres:postgres@test_db:5432/property_listings_test
      TESTING: true
    volumes:
      - test_uploads_data:/app/test_uploads
    depends_on:
      test_db:
        condition: service_healthy
```

### Environment Variables

Required environment variables for testing:

- `TEST_DATABASE_URL`: PostgreSQL connection string for test database
- `TESTING`: Set to "true" to enable test mode
- `TEST_UPLOAD_DIR`: Directory for test file uploads
- `TEST_JWT_SECRET_KEY`: JWT secret for test tokens

## Running Tests

### Run All Integration Tests

```bash
# Using the test runner script
python run_integration_tests.py

# Using pytest directly
python -m pytest tests/test_integration_api.py -v

# With coverage
python -m pytest tests/test_integration_api.py --cov=app --cov-report=html
```

### Run Specific Test Categories

```bash
# Authentication tests only
python -m pytest tests/test_integration_api.py::TestAuthenticationEndpoints -v

# Property management tests
python -m pytest tests/test_integration_api.py::TestPropertyManagementEndpoints -v

# Image management tests
python -m pytest tests/test_integration_api.py::TestImageManagementEndpoints -v

# Search and filtering tests
python -m pytest tests/test_integration_api.py::TestSearchAndFilteringEndpoints -v

# Complex scenarios
python -m pytest tests/test_integration_scenarios.py -v
```

### Run Tests with Markers

```bash
# Run only authentication-related tests
python -m pytest -m auth -v

# Run only CRUD operation tests
python -m pytest -m crud -v

# Run only Docker-specific tests
python -m pytest -m docker -v

# Run all except slow tests
python -m pytest -m "not slow" -v
```

### Run Tests in Docker

```bash
# Run tests in Docker container
docker-compose -f docker-compose.test.yml up --build test_api

# Run specific test file in Docker
docker-compose -f docker-compose.test.yml run --rm test_api python -m pytest tests/test_integration_api.py -v
```

## Test Data Management

### Test Fixtures

The test suite uses comprehensive fixtures for data setup:

- `test_agent`: Creates a test agent user
- `test_admin`: Creates a test admin user
- `test_property`: Creates a test property
- `test_property_image`: Creates a test property image
- `async_client`: Provides async HTTP client for API calls

### Data Factories

Factory classes create test data with realistic attributes:

```python
# User factory
user = await UserFactory.create_user(
    user_repository,
    email="test@example.com",
    role=UserRole.AGENT
)

# Property factory
property = await PropertyFactory.create_property(
    property_repository,
    agent_id=user.id,
    title="Test Property",
    price=Decimal("1500.00")
)

# Image factory
image = await ImageFactory.create_image(
    image_repository,
    property_id=property.id,
    filename="test.jpg"
)
```

### Test Isolation

Each test runs in an isolated database transaction that is rolled back after completion, ensuring:

- No test data pollution between tests
- Consistent test environment
- Fast test execution
- Reliable test results

## API Test Helpers

### Authentication Helper

```python
async def get_auth_headers(async_client, user):
    """Get authentication headers for API requests."""
    login_data = {"email": user.email, "password": "testpassword123"}
    response = await async_client.post("/auth/login", json=login_data)
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}
```

### Property Creation Helper

```python
async def create_test_property(async_client, user, property_data):
    """Create a property via API."""
    headers = await get_auth_headers(async_client, user)
    response = await async_client.post("/properties", json=property_data, headers=headers)
    return response.json()
```

### Image Upload Helper

```python
async def upload_test_image(async_client, property_id, user):
    """Upload a test image to a property."""
    headers = await get_auth_headers(async_client, user)
    image_file = create_test_image_file()
    files = {"file": ("test.jpg", image_file, "image/jpeg")}
    response = await async_client.post(f"/images/property/{property_id}/upload", files=files, headers=headers)
    return response.json()
```

## Test Scenarios

### Complete Agent Workflow

Tests the full agent experience:

1. Agent registration/login
2. Property creation with details
3. Image uploads (multiple images)
4. Property updates and modifications
5. Property status management
6. Property deletion

### Buyer Search Journey

Tests the property search experience:

1. Basic property listing
2. Location-based filtering
3. Price range filtering
4. Property type filtering
5. Combined filter searches
6. Pagination through results
7. Nearby property search

### Admin Management Workflow

Tests admin capabilities:

1. View all properties across agents
2. Modify any property
3. Delete any property
4. View agent-specific properties
5. System-wide statistics

### Image Management Lifecycle

Tests complete image handling:

1. Single image upload
2. Multiple image upload
3. Image metadata updates
4. Primary image designation
5. Image file downloads
6. Image deletion
7. Cleanup on property deletion

## Error Handling Tests

### Authentication Errors
- Invalid credentials
- Expired tokens
- Missing authentication
- Inactive user accounts

### Authorization Errors
- Cross-agent property access
- Insufficient permissions
- Role-based restrictions

### Validation Errors
- Invalid property data
- Missing required fields
- Data type mismatches
- Business rule violations

### System Errors
- Database connection issues
- File upload failures
- Concurrent operation conflicts

## Performance Considerations

### Test Optimization

- Use in-memory database for speed
- Parallel test execution where safe
- Minimal test data creation
- Efficient cleanup procedures

### Load Testing Scenarios

- Concurrent user operations
- Bulk data operations
- Large file uploads
- Complex search queries

## Continuous Integration

### GitHub Actions Integration

```yaml
name: Integration Tests
on: [push, pull_request]
jobs:
  integration-tests:
    runs-on: ubuntu-latest
    services:
      postgres:
        image: postgres:14
        env:
          POSTGRES_PASSWORD: postgres
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
      - name: Run integration tests
        run: python run_integration_tests.py
```

### Test Reporting

- Coverage reports generated in HTML format
- Test results exported to JUnit XML
- Performance metrics collected
- Failure screenshots for debugging

## Troubleshooting

### Common Issues

1. **Database Connection Failures**
   - Ensure test database is running
   - Check connection string format
   - Verify database credentials

2. **Docker Volume Issues**
   - Clear Docker volumes between runs
   - Check volume mount permissions
   - Verify upload directory exists

3. **Authentication Failures**
   - Check JWT secret configuration
   - Verify token expiration settings
   - Ensure user fixtures are created

4. **Test Isolation Problems**
   - Verify transaction rollback
   - Check fixture scope settings
   - Clear any global state

### Debug Mode

Run tests with debug output:

```bash
# Verbose output with debug info
python -m pytest tests/test_integration_api.py -v -s --tb=long

# With database query logging
TEST_DB_ECHO=true python -m pytest tests/test_integration_api.py -v

# With request/response logging
python -m pytest tests/test_integration_api.py -v --log-cli-level=DEBUG
```

## Best Practices

### Test Writing Guidelines

1. **Test Independence**: Each test should be independent and not rely on other tests
2. **Clear Assertions**: Use descriptive assertion messages
3. **Realistic Data**: Use realistic test data that matches production scenarios
4. **Error Testing**: Test both success and failure scenarios
5. **Documentation**: Document complex test scenarios and edge cases

### Performance Guidelines

1. **Minimize Database Calls**: Use efficient queries and batch operations
2. **Reuse Fixtures**: Share common test data through fixtures
3. **Parallel Execution**: Design tests to run in parallel safely
4. **Resource Cleanup**: Always clean up resources after tests

### Maintenance Guidelines

1. **Regular Updates**: Keep tests updated with API changes
2. **Coverage Monitoring**: Maintain high test coverage
3. **Performance Monitoring**: Track test execution times
4. **Documentation**: Keep test documentation current

## Future Enhancements

### Planned Improvements

1. **Load Testing**: Add comprehensive load testing scenarios
2. **Security Testing**: Add security-focused integration tests
3. **API Versioning**: Test API version compatibility
4. **Mobile API**: Add mobile-specific API endpoint tests
5. **Real-time Features**: Test WebSocket and real-time functionality

### Test Infrastructure

1. **Test Data Seeding**: Automated test data generation
2. **Visual Testing**: Screenshot comparison for UI components
3. **Contract Testing**: API contract validation
4. **Chaos Testing**: Fault injection and resilience testing