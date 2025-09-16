# Performance Optimization and Monitoring

This document describes the performance optimization and monitoring features implemented in the Property Listing API.

## Overview

The API includes comprehensive performance optimization and monitoring capabilities to ensure optimal performance under high load conditions. These features include:

- Database query optimization and monitoring
- Connection pool management and monitoring
- Performance testing suite
- Real-time performance metrics
- Index usage verification
- Automated performance recommendations

## Features Implemented

### 1. Database Query Optimization (`app/utils/query_optimizer.py`)

The `QueryOptimizer` class provides comprehensive query performance monitoring:

- **Query Performance Analysis**: Uses `EXPLAIN ANALYZE` to measure query execution times
- **Slow Query Detection**: Automatically identifies and logs queries exceeding thresholds
- **Index Usage Monitoring**: Tracks database index usage statistics
- **Performance Metrics Collection**: Stores query metrics for analysis
- **Optimization Recommendations**: Provides actionable optimization suggestions

#### Usage Example:
```python
from app.utils.query_optimizer import query_optimizer

# Analyze query performance
metric = await query_optimizer.analyze_query_performance(
    db, "SELECT * FROM properties WHERE location = 'Dubai'", 
    endpoint="/api/v1/properties/search"
)

# Get performance summary
summary = query_optimizer.get_query_performance_summary()
```

### 2. Enhanced Database Connection Pooling (`app/database.py`)

Optimized connection pool configuration for high-performance scenarios:

- **Increased Pool Size**: 20 base connections with 30 overflow capacity
- **Connection Recycling**: 30-minute connection lifecycle for freshness
- **Performance Monitoring**: Real-time pool utilization tracking
- **PostgreSQL Optimization**: Tuned server settings for performance

#### Key Configuration:
```python
engine = create_async_engine(
    settings.database_url,
    pool_size=20,           # Base pool size
    max_overflow=30,        # Additional connections
    pool_recycle=1800,      # 30-minute recycling
    pool_pre_ping=True,     # Connection validation
    # ... additional optimizations
)
```

### 3. Performance Monitoring Endpoints (`app/routers/monitoring.py`)

Admin-only endpoints for real-time performance monitoring:

- **`GET /api/v1/monitoring/health`**: Basic health check
- **`GET /api/v1/monitoring/database`**: Database performance metrics
- **`GET /api/v1/monitoring/query-performance`**: Query performance analysis
- **`GET /api/v1/monitoring/performance-summary`**: Comprehensive system overview

#### Example Response:
```json
{
  "database_info": {
    "pool_utilization": 45.2,
    "cache_hit_ratio": 95.8,
    "active_connections": 12
  },
  "query_performance": {
    "average_execution_time": 0.125,
    "slow_query_percentage": 2.1,
    "total_queries": 1547
  }
}
```

### 4. Performance Testing Suite (`tests/test_performance.py`)

Comprehensive performance tests covering:

- **Large Dataset Performance**: Tests with 1000+ properties
- **Concurrent Request Handling**: Simulates multiple simultaneous users
- **Search Performance**: Validates search response times under load
- **Pagination Efficiency**: Tests pagination with large datasets
- **Complex Filter Performance**: Multi-criteria search optimization

#### Running Performance Tests:
```bash
# Run all performance tests
python -m pytest tests/test_performance.py -v

# Run specific test
python -m pytest tests/test_performance.py::TestPerformanceOptimization::test_large_dataset_search_performance -v

# Run with performance test runner
./run_performance_tests.py
```

### 5. Database Index Verification (`verify_indexes.py`)

Automated script to verify database index health:

- **Index Existence Verification**: Ensures all required indexes are present
- **Usage Statistics**: Monitors which indexes are being used
- **Unused Index Detection**: Identifies potentially unnecessary indexes
- **Optimization Recommendations**: Suggests index improvements

#### Running Index Verification:
```bash
./verify_indexes.py
```

### 6. Enhanced Property Repository Query Monitoring

The property repository now includes automatic query performance monitoring:

```python
# Automatic query monitoring in search operations
await query_optimizer.analyze_query_performance(
    self.db, query_str, endpoint="/api/v1/properties/search"
)
```

## Performance Benchmarks

### Target Performance Metrics

- **Search Response Time**: < 2 seconds for datasets up to 10,000 properties
- **Concurrent Users**: Support 95% of requests under 3 seconds with 20+ concurrent users
- **Database Cache Hit Ratio**: > 90%
- **Connection Pool Utilization**: 50-80% under normal load

### Test Results

The performance tests validate:

1. **Large Dataset Search**: ✅ < 2s response time with 1000 properties
2. **Concurrent Requests**: ✅ Average < 1s, 95th percentile < 2s
3. **Pagination Performance**: ✅ < 0.5s average, < 1s maximum
4. **Complex Filters**: ✅ < 1.5s for multi-criteria searches

## Database Indexes

### Required Indexes for Optimal Performance

The system requires these indexes for optimal search performance:

#### Properties Table:
- `idx_properties_location_price`: Composite index for location + price searches
- `idx_properties_bedrooms_price`: Composite index for bedroom + price filters
- `idx_properties_search_optimization`: Comprehensive search index
- `idx_properties_coordinates`: Geographic coordinate index
- Individual indexes on: `location`, `price`, `bedrooms`, `property_type`, `is_active`

#### Users Table:
- Unique index on `email`
- Standard indexes on `id`, `created_at`, `updated_at`

#### Property Images Table:
- Foreign key index on `property_id`
- Standard indexes on `id`, `created_at`, `updated_at`

## Monitoring and Alerting

### Real-time Monitoring

The system provides real-time monitoring through:

1. **Performance Middleware**: Tracks request timing and system resources
2. **Query Optimizer**: Monitors database query performance
3. **Connection Pool Monitor**: Tracks database connection health
4. **Health Check Endpoints**: Provides system status information

### Key Metrics to Monitor

- **Response Times**: Average, 95th percentile, maximum
- **Database Performance**: Query execution times, cache hit ratio
- **Connection Pool**: Utilization percentage, connection leaks
- **Error Rates**: Failed requests, database errors
- **System Resources**: CPU usage, memory consumption

### Alerting Thresholds

- **Critical**: Average response time > 3s, pool utilization > 90%
- **Warning**: Average response time > 1s, pool utilization > 75%
- **Info**: Slow queries detected, unused indexes found

## Optimization Recommendations

### Database Optimization

1. **Index Maintenance**: Regular `VACUUM ANALYZE` operations
2. **Query Optimization**: Use `EXPLAIN ANALYZE` for slow queries
3. **Connection Pooling**: Monitor and tune pool sizes based on load
4. **Cache Configuration**: Optimize PostgreSQL shared_buffers

### Application Optimization

1. **Pagination**: Always use pagination for large result sets
2. **Selective Loading**: Use `selectinload` for relationships
3. **Query Batching**: Combine multiple queries where possible
4. **Caching**: Implement Redis caching for frequently accessed data

### Infrastructure Optimization

1. **Horizontal Scaling**: Deploy multiple API instances
2. **Read Replicas**: Use read replicas for search-heavy workloads
3. **Load Balancing**: Distribute requests across instances
4. **CDN**: Use CDN for static assets and images

## Usage Examples

### Monitoring Performance in Production

```python
# Get current performance metrics
from app.routers.monitoring import get_performance_summary

summary = await get_performance_summary(current_admin_user)
print(f"System health: {summary['system_health']}")
print(f"Average query time: {summary['performance_metrics']['queries']['average_execution_time']}")
```

### Running Performance Tests

```bash
# Full performance test suite
./run_performance_tests.py

# Specific test pattern
./run_performance_tests.py --test-pattern "concurrent"

# Skip environment setup (if already running)
./run_performance_tests.py --skip-setup --skip-cleanup
```

### Verifying Database Indexes

```bash
# Check all indexes
./verify_indexes.py

# Generate SQL for missing indexes
./verify_indexes.py | grep "CREATE INDEX"
```

## Troubleshooting

### Common Performance Issues

1. **Slow Search Queries**
   - Check if required indexes exist
   - Verify query execution plans
   - Consider adding composite indexes

2. **High Connection Pool Utilization**
   - Increase pool size or max_overflow
   - Check for connection leaks
   - Monitor long-running queries

3. **Memory Usage Issues**
   - Review query result set sizes
   - Implement proper pagination
   - Monitor connection pool settings

### Performance Debugging

1. **Enable Query Logging**: Set `echo=True` in database engine
2. **Use EXPLAIN ANALYZE**: Analyze slow query execution plans
3. **Monitor System Resources**: Check CPU and memory usage
4. **Review Application Logs**: Look for performance warnings

## Future Enhancements

### Planned Improvements

1. **Redis Caching**: Implement caching layer for frequently accessed data
2. **Query Result Caching**: Cache search results for common queries
3. **Database Sharding**: Implement horizontal database scaling
4. **Advanced Monitoring**: Integration with monitoring tools (Prometheus, Grafana)
5. **Auto-scaling**: Automatic scaling based on performance metrics

### Performance Testing Enhancements

1. **Load Testing**: Integration with tools like Locust or k6
2. **Stress Testing**: Test system limits and failure points
3. **Endurance Testing**: Long-running performance validation
4. **Regression Testing**: Automated performance regression detection

## Conclusion

The Property Listing API includes comprehensive performance optimization and monitoring capabilities designed to ensure optimal performance under high load conditions. The combination of database optimization, query monitoring, performance testing, and real-time metrics provides a robust foundation for scalable property listing operations.

Regular monitoring and optimization using the provided tools will help maintain optimal performance as the system scales.