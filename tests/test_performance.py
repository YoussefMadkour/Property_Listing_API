"""
Performance tests for the Property Listing API.
Tests search endpoints with large datasets and concurrent requests.
"""

import pytest
import asyncio
import time
import statistics
from typing import List, Dict, Any
from decimal import Decimal
from httpx import AsyncClient
from app.main import app
from app.database import get_db, AsyncSessionLocal
from app.models.property import Property, PropertyType
from app.models.user import User, UserRole
from app.utils.query_optimizer import query_optimizer
from tests.conftest import UserFactory, PropertyFactory
import uuid


class TestPerformanceOptimization:
    """Test performance optimization features and monitoring."""
    
    @pytest.mark.asyncio
    async def test_large_dataset_search_performance(self, async_client: AsyncClient):
        """Test search performance with large dataset."""
        # Create test user
        async with AsyncSessionLocal() as db:
            user_data = UserFactory.create_user_data(
                email="perf_agent@test.com",
                role=UserRole.AGENT
            )
            user = User(**user_data)
            db.add(user)
            await db.commit()
            await db.refresh(user)
            
            # Create large dataset (1000 properties)
            properties = []
            for i in range(1000):
                property_data = PropertyFactory.create_property_data(
                    agent_id=user.id,
                    title=f"Performance Test Property {i}",
                    location=f"Test Location {i % 10}",  # 10 different locations
                    price=Decimal(str(100000 + (i * 1000))),
                    bedrooms=1 + (i % 5),  # 1-5 bedrooms
                    property_type=PropertyType.RENTAL if i % 2 == 0 else PropertyType.SALE
                )
                property_obj = Property(**property_data)
                properties.append(property_obj)
            
            db.add_all(properties)
            await db.commit()
        
        # Test search performance
        search_params = {
            "location": "Test Location 1",
            "min_price": 150000,
            "max_price": 300000,
            "bedrooms": 3,
            "page": 1,
            "page_size": 20
        }
        
        # Measure search performance
        start_time = time.time()
        response = await async_client.get("/api/v1/properties/search", params=search_params)
        execution_time = time.time() - start_time
        
        assert response.status_code == 200
        assert execution_time < 2.0, f"Search took {execution_time:.3f}s, should be under 2s"
        
        data = response.json()
        assert "properties" in data
        assert "total" in data
        assert "page" in data
        
        # Verify results are filtered correctly
        for prop in data["properties"]:
            assert "Test Location 1" in prop["location"]
            assert 150000 <= prop["price"] <= 300000
            assert prop["bedrooms"] == 3
    
    @pytest.mark.asyncio
    async def test_concurrent_search_requests(self, async_client: AsyncClient):
        """Test concurrent search request performance."""
        # Create test data
        async with AsyncSessionLocal() as db:
            user_data = UserFactory.create_user_data(
                email="concurrent_agent@test.com",
                role=UserRole.AGENT
            )
            user = User(**user_data)
            db.add(user)
            await db.commit()
            await db.refresh(user)
            
            # Create 100 properties for testing
            properties = []
            for i in range(100):
                property_data = PropertyFactory.create_property_data(
                    agent_id=user.id,
                    title=f"Concurrent Test Property {i}",
                    location=f"Location {i % 5}",
                    price=Decimal(str(100000 + (i * 5000))),
                    bedrooms=1 + (i % 4)
                )
                property_obj = Property(**property_data)
                properties.append(property_obj)
            
            db.add_all(properties)
            await db.commit()
        
        # Define search scenarios
        search_scenarios = [
            {"location": "Location 0", "page": 1, "page_size": 10},
            {"min_price": 200000, "max_price": 400000, "page": 1, "page_size": 15},
            {"bedrooms": 2, "page": 1, "page_size": 20},
            {"property_type": "rental", "page": 1, "page_size": 25},
            {"location": "Location 1", "bedrooms": 3, "page": 1, "page_size": 10}
        ]
        
        async def perform_search(params: Dict[str, Any]) -> float:
            """Perform a single search and return execution time."""
            start_time = time.time()
            response = await async_client.get("/api/v1/properties/search", params=params)
            execution_time = time.time() - start_time
            assert response.status_code == 200
            return execution_time
        
        # Run concurrent searches
        concurrent_requests = 20
        tasks = []
        
        for i in range(concurrent_requests):
            scenario = search_scenarios[i % len(search_scenarios)]
            tasks.append(perform_search(scenario))
        
        # Execute all requests concurrently
        start_time = time.time()
        execution_times = await asyncio.gather(*tasks)
        total_time = time.time() - start_time
        
        # Analyze performance
        avg_time = statistics.mean(execution_times)
        max_time = max(execution_times)
        p95_time = sorted(execution_times)[int(len(execution_times) * 0.95)]
        
        # Performance assertions
        assert avg_time < 1.0, f"Average response time {avg_time:.3f}s should be under 1s"
        assert max_time < 3.0, f"Max response time {max_time:.3f}s should be under 3s"
        assert p95_time < 2.0, f"95th percentile {p95_time:.3f}s should be under 2s"
        
        print(f"Concurrent performance results:")
        print(f"  Total time: {total_time:.3f}s")
        print(f"  Average time: {avg_time:.3f}s")
        print(f"  Max time: {max_time:.3f}s")
        print(f"  95th percentile: {p95_time:.3f}s")
    
    @pytest.mark.asyncio
    async def test_pagination_performance(self, async_client: AsyncClient):
        """Test pagination performance with large datasets."""
        # Create test data
        async with AsyncSessionLocal() as db:
            user_data = UserFactory.create_user_data(
                email="pagination_agent@test.com",
                role=UserRole.AGENT
            )
            user = User(**user_data)
            db.add(user)
            await db.commit()
            await db.refresh(user)
            
            # Create 500 properties
            properties = []
            for i in range(500):
                property_data = PropertyFactory.create_property_data(
                    agent_id=user.id,
                    title=f"Pagination Test Property {i:03d}",
                    location="Pagination Test Location",
                    price=Decimal(str(100000 + i))
                )
                property_obj = Property(**property_data)
                properties.append(property_obj)
            
            db.add_all(properties)
            await db.commit()
        
        # Test different page sizes and positions
        test_cases = [
            {"page": 1, "page_size": 20},
            {"page": 5, "page_size": 20},
            {"page": 10, "page_size": 20},
            {"page": 1, "page_size": 50},
            {"page": 5, "page_size": 50},
            {"page": 1, "page_size": 100}
        ]
        
        execution_times = []
        
        for case in test_cases:
            start_time = time.time()
            response = await async_client.get(
                "/api/v1/properties/search",
                params={
                    "location": "Pagination Test Location",
                    **case
                }
            )
            execution_time = time.time() - start_time
            execution_times.append(execution_time)
            
            assert response.status_code == 200
            data = response.json()
            
            # Verify pagination works correctly
            expected_items = min(case["page_size"], max(0, data["total"] - (case["page"] - 1) * case["page_size"]))
            assert len(data["properties"]) == expected_items
            
            print(f"Page {case['page']}, size {case['page_size']}: {execution_time:.3f}s")
        
        # Performance assertions
        avg_time = statistics.mean(execution_times)
        max_time = max(execution_times)
        
        assert avg_time < 0.5, f"Average pagination time {avg_time:.3f}s should be under 0.5s"
        assert max_time < 1.0, f"Max pagination time {max_time:.3f}s should be under 1s"
    
    @pytest.mark.asyncio
    async def test_complex_filter_performance(self, async_client: AsyncClient):
        """Test performance with complex filter combinations."""
        # Create test data with varied attributes
        async with AsyncSessionLocal() as db:
            user_data = UserFactory.create_user_data(
                email="complex_filter_agent@test.com",
                role=UserRole.AGENT
            )
            user = User(**user_data)
            db.add(user)
            await db.commit()
            await db.refresh(user)
            
            # Create 300 properties with varied attributes
            properties = []
            locations = ["Downtown", "Suburbs", "Waterfront", "Mountain View", "City Center"]
            
            for i in range(300):
                property_data = PropertyFactory.create_property_data(
                    agent_id=user.id,
                    title=f"Complex Filter Property {i}",
                    location=locations[i % len(locations)],
                    price=Decimal(str(50000 + (i * 2000))),
                    bedrooms=1 + (i % 6),
                    bathrooms=1 + (i % 4),
                    area_sqft=500 + (i * 10),
                    property_type=PropertyType.RENTAL if i % 3 == 0 else PropertyType.SALE
                )
                property_obj = Property(**property_data)
                properties.append(property_obj)
            
            db.add_all(properties)
            await db.commit()
        
        # Test complex filter combinations
        complex_filters = [
            {
                "location": "Downtown",
                "min_price": 100000,
                "max_price": 300000,
                "bedrooms": 2,
                "property_type": "rental"
            },
            {
                "min_price": 200000,
                "max_price": 500000,
                "min_bedrooms": 2,
                "max_bedrooms": 4,
                "min_area": 800,
                "max_area": 1500
            },
            {
                "location": "Waterfront",
                "property_type": "sale",
                "bedrooms": 3,
                "min_price": 300000
            }
        ]
        
        for i, filters in enumerate(complex_filters):
            start_time = time.time()
            response = await async_client.get(
                "/api/v1/properties/search",
                params={**filters, "page": 1, "page_size": 20}
            )
            execution_time = time.time() - start_time
            
            assert response.status_code == 200
            assert execution_time < 1.5, f"Complex filter {i+1} took {execution_time:.3f}s, should be under 1.5s"
            
            data = response.json()
            print(f"Complex filter {i+1}: {execution_time:.3f}s, {data['total']} results")
    
    @pytest.mark.asyncio
    async def test_query_optimizer_integration(self):
        """Test query optimizer functionality."""
        async with AsyncSessionLocal() as db:
            # Test query analysis
            test_query = "SELECT * FROM properties WHERE is_active = true LIMIT 10"
            
            metric = await query_optimizer.analyze_query_performance(
                db, test_query, endpoint="/api/v1/properties"
            )
            
            assert metric.query_hash is not None
            assert metric.execution_time >= 0
            assert metric.timestamp is not None
            assert metric.endpoint == "/api/v1/properties"
            
            # Test index usage verification
            index_stats = await query_optimizer.verify_index_usage(db)
            assert isinstance(index_stats, list)
            
            # Test unused indexes detection
            unused_indexes = await query_optimizer.get_unused_indexes(db)
            assert isinstance(unused_indexes, list)
            
            # Test table statistics
            table_stats = await query_optimizer.analyze_table_statistics(db)
            assert isinstance(table_stats, dict)
            
            # Test performance summary
            summary = query_optimizer.get_query_performance_summary()
            assert "total_queries" in summary
            assert "average_execution_time" in summary
    
    @pytest.mark.asyncio
    async def test_database_connection_pool_monitoring(self):
        """Test database connection pool monitoring."""
        from app.database import get_database_info, monitor_connection_pool
        
        # Test database info retrieval
        db_info = await get_database_info()
        assert "database_version" in db_info
        assert "pool_size" in db_info
        assert "checked_in_connections" in db_info
        assert "checked_out_connections" in db_info
        assert "pool_utilization" in db_info
        
        # Test connection pool monitoring
        pool_status = await monitor_connection_pool()
        assert "status" in pool_status
        assert "pool_size" in pool_status
        assert "utilization_percent" in pool_status
        assert "recommendations" in pool_status
        
        # Verify pool status is valid
        assert pool_status["status"] in ["healthy", "warning", "critical"]
        assert 0 <= pool_status["utilization_percent"] <= 100


class TestPerformanceBenchmarks:
    """Benchmark tests for performance regression detection."""
    
    @pytest.mark.asyncio
    async def test_property_creation_benchmark(self, async_client: AsyncClient):
        """Benchmark property creation performance."""
        # Login as agent
        login_response = await async_client.post(
            "/api/v1/auth/login",
            json={"email": "agent@test.com", "password": "testpass123"}
        )
        assert login_response.status_code == 200
        token = login_response.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}
        
        # Benchmark property creation
        creation_times = []
        
        for i in range(10):
            property_data = {
                "title": f"Benchmark Property {i}",
                "description": f"Performance test property {i}",
                "property_type": "rental",
                "price": 150000 + (i * 1000),
                "bedrooms": 2,
                "bathrooms": 1,
                "area_sqft": 1000,
                "location": f"Benchmark Location {i}",
                "latitude": 25.2048 + (i * 0.001),
                "longitude": 55.2708 + (i * 0.001)
            }
            
            start_time = time.time()
            response = await async_client.post(
                "/api/v1/properties",
                json=property_data,
                headers=headers
            )
            creation_time = time.time() - start_time
            creation_times.append(creation_time)
            
            assert response.status_code == 201
        
        # Analyze performance
        avg_creation_time = statistics.mean(creation_times)
        max_creation_time = max(creation_times)
        
        assert avg_creation_time < 0.5, f"Average creation time {avg_creation_time:.3f}s should be under 0.5s"
        assert max_creation_time < 1.0, f"Max creation time {max_creation_time:.3f}s should be under 1s"
        
        print(f"Property creation benchmark:")
        print(f"  Average: {avg_creation_time:.3f}s")
        print(f"  Max: {max_creation_time:.3f}s")
    
    @pytest.mark.asyncio
    async def test_search_response_time_benchmark(self, async_client: AsyncClient):
        """Benchmark search response times under different conditions."""
        search_scenarios = [
            {"name": "Simple location search", "params": {"location": "Test"}},
            {"name": "Price range search", "params": {"min_price": 100000, "max_price": 300000}},
            {"name": "Bedroom filter", "params": {"bedrooms": 2}},
            {"name": "Complex filter", "params": {
                "location": "Test", "min_price": 150000, "max_price": 250000, "bedrooms": 2
            }},
            {"name": "Large page size", "params": {"page_size": 50}},
        ]
        
        benchmark_results = {}
        
        for scenario in search_scenarios:
            times = []
            
            # Run each scenario 5 times
            for _ in range(5):
                start_time = time.time()
                response = await async_client.get(
                    "/api/v1/properties/search",
                    params=scenario["params"]
                )
                execution_time = time.time() - start_time
                times.append(execution_time)
                
                assert response.status_code == 200
            
            avg_time = statistics.mean(times)
            benchmark_results[scenario["name"]] = avg_time
            
            # Performance assertion
            assert avg_time < 1.0, f"{scenario['name']} took {avg_time:.3f}s, should be under 1s"
        
        print("Search benchmark results:")
        for name, time_taken in benchmark_results.items():
            print(f"  {name}: {time_taken:.3f}s")