"""
Complex integration test scenarios.
Tests end-to-end workflows and business scenarios.
"""

import pytest
import uuid
import asyncio
from decimal import Decimal
from typing import List, Dict, Any

from app.models.user import UserRole
from app.models.property import PropertyType
from tests.conftest import UserFactory, PropertyFactory
from tests.test_integration_config import APITestHelper, TestScenarioRunner, TestDataBuilder


class TestCompletePropertyManagementWorkflow:
    """Test complete property management workflows from start to finish."""
    
    @pytest.mark.asyncio
    async def test_agent_property_management_workflow(
        self, 
        async_client, 
        user_repository, 
        property_repository,
        api_helper: APITestHelper,
        scenario_runner: TestScenarioRunner,
        test_data_builder: TestDataBuilder
    ):
        """Test complete agent workflow: register, create properties, manage listings."""
        # Create agent user
        agent = await UserFactory.create_user(
            user_repository,
            email="workflow_agent@test.com",
            role=UserRole.AGENT
        )
        
        # Agent creates multiple properties
        properties_data = [
            test_data_builder.property_data(
                title="Luxury Villa Dubai",
                location="Dubai Hills",
                price=5000.00,
                bedrooms=4,
                property_type="rental"
            ),
            test_data_builder.property_data(
                title="Downtown Apartment",
                location="Downtown Dubai",
                price=3000.00,
                bedrooms=2,
                property_type="rental"
            ),
            test_data_builder.property_data(
                title="Beach House",
                location="Jumeirah Beach",
                price=800000.00,
                bedrooms=5,
                property_type="sale"
            )
        ]
        
        created_properties = []
        for prop_data in properties_data:
            property_response = await api_helper.create_property(prop_data, agent.email)
            created_properties.append(property_response)
        
        # Verify all properties were created
        assert len(created_properties) == 3
        
        # Agent uploads images for each property
        for prop in created_properties:
            for i in range(2):  # 2 images per property
                await api_helper.upload_image(prop["id"], agent.email, f"image_{i}.jpg")
        
        # Agent views their properties
        headers = await api_helper.login_user(agent.email)
        agent_properties_response = await async_client.get(
            f"/properties/agent/{agent.id}",
            headers=headers
        )
        
        assert agent_properties_response.status_code == 200
        agent_properties_data = agent_properties_response.json()
        assert agent_properties_data["total"] == 3
        
        # Agent updates a property
        property_to_update = created_properties[0]
        update_data = {"title": "Updated Luxury Villa Dubai", "price": 5500.00}
        
        update_response = await async_client.put(
            f"/properties/{property_to_update['id']}",
            json=update_data,
            headers=headers
        )
        
        assert update_response.status_code == 200
        updated_property = update_response.json()
        assert updated_property["title"] == update_data["title"]
        assert float(updated_property["price"]) == update_data["price"]
        
        # Agent deactivates a property
        property_to_deactivate = created_properties[1]
        status_response = await async_client.patch(
            f"/properties/{property_to_deactivate['id']}/status",
            headers=headers
        )
        
        assert status_response.status_code == 200
        deactivated_property = status_response.json()
        assert deactivated_property["is_active"] is False
        
        # Agent gets statistics
        stats_response = await async_client.get("/properties/statistics/summary", headers=headers)
        assert stats_response.status_code == 200
        stats = stats_response.json()
        
        assert stats["total_properties"] == 3
        assert stats["active_properties"] == 2  # One was deactivated
    
    @pytest.mark.asyncio
    async def test_admin_property_oversight_workflow(
        self,
        async_client,
        user_repository,
        property_repository,
        api_helper: APITestHelper,
        test_data_builder: TestDataBuilder
    ):
        """Test admin oversight of all properties and agents."""
        # Create admin user
        admin = await UserFactory.create_user(
            user_repository,
            email="admin@test.com",
            role=UserRole.ADMIN
        )
        
        # Create multiple agents
        agents = []
        for i in range(3):
            agent = await UserFactory.create_user(
                user_repository,
                email=f"agent_{i}@test.com",
                role=UserRole.AGENT
            )
            agents.append(agent)
        
        # Each agent creates properties
        all_properties = []
        for i, agent in enumerate(agents):
            for j in range(2):  # 2 properties per agent
                prop_data = test_data_builder.property_data(
                    title=f"Agent {i} Property {j}",
                    location=f"Location {i}-{j}",
                    price=1000.00 + (i * 500) + (j * 100)
                )
                property_response = await api_helper.create_property(prop_data, agent.email)
                all_properties.append(property_response)
        
        # Admin views all properties
        admin_headers = await api_helper.login_user(admin.email)
        all_properties_response = await async_client.get("/properties", headers=admin_headers)
        
        assert all_properties_response.status_code == 200
        all_properties_data = all_properties_response.json()
        assert all_properties_data["total"] >= 6  # At least 6 properties created
        
        # Admin views specific agent's properties
        target_agent = agents[0]
        agent_properties_response = await async_client.get(
            f"/properties/agent/{target_agent.id}",
            headers=admin_headers
        )
        
        assert agent_properties_response.status_code == 200
        agent_properties_data = agent_properties_response.json()
        assert agent_properties_data["total"] == 2
        
        # Admin can modify any property
        property_to_modify = all_properties[0]
        admin_update_data = {"title": "Admin Modified Property"}
        
        admin_update_response = await async_client.put(
            f"/properties/{property_to_modify['id']}",
            json=admin_update_data,
            headers=admin_headers
        )
        
        assert admin_update_response.status_code == 200
        modified_property = admin_update_response.json()
        assert modified_property["title"] == admin_update_data["title"]
        
        # Admin can delete any property
        property_to_delete = all_properties[1]
        delete_response = await async_client.delete(
            f"/properties/{property_to_delete['id']}",
            headers=admin_headers
        )
        
        assert delete_response.status_code == 204
        
        # Verify property is deleted
        get_deleted_response = await async_client.get(f"/properties/{property_to_delete['id']}")
        assert get_deleted_response.status_code == 404


class TestPropertySearchAndDiscoveryWorkflows:
    """Test property search and discovery user journeys."""
    
    @pytest.mark.asyncio
    async def test_buyer_property_search_journey(
        self,
        async_client,
        user_repository,
        property_repository,
        api_helper: APITestHelper,
        scenario_runner: TestScenarioRunner,
        test_data_builder: TestDataBuilder
    ):
        """Test complete buyer search journey with various filters."""
        # Create agent and properties
        agent = await UserFactory.create_user(
            user_repository,
            email="search_agent@test.com",
            role=UserRole.AGENT
        )
        
        # Create diverse properties for searching
        properties_data = [
            # Rental properties
            test_data_builder.property_data(
                title="Modern Studio Downtown",
                location="Downtown Dubai",
                price=1200.00,
                bedrooms=0,
                bathrooms=1,
                area_sqft=500,
                property_type="rental"
            ),
            test_data_builder.property_data(
                title="Family Apartment Marina",
                location="Dubai Marina",
                price=2500.00,
                bedrooms=3,
                bathrooms=2,
                area_sqft=1200,
                property_type="rental"
            ),
            test_data_builder.property_data(
                title="Luxury Penthouse JBR",
                location="Jumeirah Beach Residence",
                price=8000.00,
                bedrooms=4,
                bathrooms=3,
                area_sqft=2500,
                property_type="rental"
            ),
            # Sale properties
            test_data_builder.property_data(
                title="Cozy Villa Suburbs",
                location="Arabian Ranches",
                price=1200000.00,
                bedrooms=4,
                bathrooms=3,
                area_sqft=2000,
                property_type="sale"
            ),
            test_data_builder.property_data(
                title="Investment Apartment",
                location="Business Bay",
                price=800000.00,
                bedrooms=2,
                bathrooms=2,
                area_sqft=900,
                property_type="sale"
            )
        ]
        
        created_properties = []
        for prop_data in properties_data:
            property_response = await api_helper.create_property(prop_data, agent.email)
            created_properties.append(property_response)
        
        # Buyer Journey 1: Looking for rental under 3000 AED
        rental_search = await api_helper.search_properties({
            "property_type": "rental",
            "max_price": 3000,
            "sort_by": "price",
            "sort_order": "asc"
        })
        
        assert rental_search["total"] >= 2
        for prop in rental_search["properties"]:
            assert prop["property_type"] == "rental"
            assert float(prop["price"]) <= 3000
        
        # Verify sorting
        prices = [float(prop["price"]) for prop in rental_search["properties"]]
        assert prices == sorted(prices)
        
        # Buyer Journey 2: Looking for family home (3+ bedrooms)
        family_search = await api_helper.search_properties({
            "bedrooms": 3,
            "sort_by": "area_sqft",
            "sort_order": "desc"
        })
        
        assert family_search["total"] >= 2
        for prop in family_search["properties"]:
            assert prop["bedrooms"] >= 3
        
        # Buyer Journey 3: Location-specific search
        marina_search = await api_helper.search_properties({
            "location": "Marina"
        })
        
        assert marina_search["total"] >= 1
        for prop in marina_search["properties"]:
            assert "Marina" in prop["location"]
        
        # Buyer Journey 4: Investment property search (sale, under 1M)
        investment_search = await api_helper.search_properties({
            "property_type": "sale",
            "max_price": 1000000,
            "min_area": 800
        })
        
        assert investment_search["total"] >= 1
        for prop in investment_search["properties"]:
            assert prop["property_type"] == "sale"
            assert float(prop["price"]) <= 1000000
            assert prop["area_sqft"] >= 800
        
        # Buyer Journey 5: Nearby properties search
        nearby_response = await async_client.get(
            "/properties/nearby/location?latitude=25.2048&longitude=55.2708&radius_km=10"
        )
        
        assert nearby_response.status_code == 200
        nearby_properties = nearby_response.json()
        assert isinstance(nearby_properties, list)
    
    @pytest.mark.asyncio
    async def test_advanced_search_combinations(
        self,
        async_client,
        user_repository,
        property_repository,
        api_helper: APITestHelper,
        test_data_builder: TestDataBuilder
    ):
        """Test complex search filter combinations."""
        # Create agent and diverse properties
        agent = await UserFactory.create_user(
            user_repository,
            email="advanced_search_agent@test.com",
            role=UserRole.AGENT
        )
        
        # Create properties with specific attributes for testing
        test_properties = [
            {
                "title": "Affordable Studio Central",
                "location": "Dubai Downtown",
                "price": 1000.00,
                "bedrooms": 0,
                "bathrooms": 1,
                "area_sqft": 400,
                "property_type": "rental"
            },
            {
                "title": "Mid-range Apartment Marina",
                "location": "Dubai Marina",
                "price": 2000.00,
                "bedrooms": 2,
                "bathrooms": 2,
                "area_sqft": 1000,
                "property_type": "rental"
            },
            {
                "title": "Luxury Penthouse JBR",
                "location": "Jumeirah Beach Residence",
                "price": 5000.00,
                "bedrooms": 3,
                "bathrooms": 3,
                "area_sqft": 2000,
                "property_type": "rental"
            },
            {
                "title": "Premium Villa Emirates Hills",
                "location": "Emirates Hills",
                "price": 2000000.00,
                "bedrooms": 5,
                "bathrooms": 4,
                "area_sqft": 4000,
                "property_type": "sale"
            }
        ]
        
        for prop_data in test_properties:
            await api_helper.create_property(prop_data, agent.email)
        
        # Test 1: Multiple filters - rental, 2+ bedrooms, under 3000, in Marina/JBR
        complex_search_1 = await api_helper.search_properties({
            "property_type": "rental",
            "bedrooms": 2,
            "max_price": 3000,
            "query": "Marina"
        })
        
        assert complex_search_1["total"] >= 1
        for prop in complex_search_1["properties"]:
            assert prop["property_type"] == "rental"
            assert prop["bedrooms"] >= 2
            assert float(prop["price"]) <= 3000
            assert "Marina" in prop["location"] or "Marina" in prop["title"]
        
        # Test 2: Area and price combination
        area_price_search = await api_helper.search_properties({
            "min_area": 1000,
            "max_area": 3000,
            "min_price": 1500,
            "max_price": 6000
        })
        
        for prop in area_price_search["properties"]:
            assert 1000 <= prop["area_sqft"] <= 3000
            assert 1500 <= float(prop["price"]) <= 6000
        
        # Test 3: Bathroom and bedroom combination
        room_search = await api_helper.search_properties({
            "bedrooms": 2,
            "bathrooms": 2
        })
        
        for prop in room_search["properties"]:
            assert prop["bedrooms"] >= 2
            assert prop["bathrooms"] >= 2
        
        # Test 4: Text search with filters
        text_filter_search = await api_helper.search_properties({
            "query": "Luxury",
            "property_type": "rental",
            "min_price": 3000
        })
        
        for prop in text_filter_search["properties"]:
            assert "Luxury" in prop["title"] or "Luxury" in prop["description"]
            assert prop["property_type"] == "rental"
            assert float(prop["price"]) >= 3000


class TestImageManagementWorkflows:
    """Test complete image management workflows."""
    
    @pytest.mark.asyncio
    async def test_property_image_lifecycle(
        self,
        async_client,
        user_repository,
        property_repository,
        api_helper: APITestHelper,
        test_data_builder: TestDataBuilder
    ):
        """Test complete image management lifecycle for a property."""
        # Create agent and property
        agent = await UserFactory.create_user(
            user_repository,
            email="image_agent@test.com",
            role=UserRole.AGENT
        )
        
        property_data = test_data_builder.property_data(
            title="Property with Images",
            location="Test Location"
        )
        property_response = await api_helper.create_property(property_data, agent.email)
        property_id = property_response["id"]
        
        # Upload multiple images
        uploaded_images = []
        for i in range(5):
            image_response = await api_helper.upload_image(
                property_id, 
                agent.email, 
                f"property_image_{i}.jpg"
            )
            uploaded_images.append(image_response["image"])
        
        # Verify all images were uploaded
        property_images_response = await async_client.get(f"/images/property/{property_id}")
        assert property_images_response.status_code == 200
        
        property_images_data = property_images_response.json()
        assert property_images_data["total"] == 5
        
        # Set one image as primary
        headers = await api_helper.login_user(agent.email)
        target_image_id = uploaded_images[2]["id"]
        
        primary_response = await async_client.post(
            f"/images/{target_image_id}/set-primary",
            headers=headers
        )
        
        assert primary_response.status_code == 200
        primary_image = primary_response.json()
        assert primary_image["is_primary"] is True
        
        # Update image metadata
        update_data = {"display_order": 1}
        update_response = await async_client.put(
            f"/images/{target_image_id}",
            json=update_data,
            headers=headers
        )
        
        assert update_response.status_code == 200
        updated_image = update_response.json()
        assert updated_image["display_order"] == 1
        
        # Download image file
        download_response = await async_client.get(f"/images/{target_image_id}/file")
        assert download_response.status_code == 200
        assert download_response.headers["content-type"] == "image/jpeg"
        
        # Delete one image
        image_to_delete = uploaded_images[0]["id"]
        delete_response = await async_client.delete(f"/images/{image_to_delete}", headers=headers)
        assert delete_response.status_code == 204
        
        # Verify image was deleted
        get_deleted_response = await async_client.get(f"/images/{image_to_delete}")
        assert get_deleted_response.status_code == 404
        
        # Verify property now has 4 images
        final_images_response = await async_client.get(f"/images/property/{property_id}")
        final_images_data = final_images_response.json()
        assert final_images_data["total"] == 4
    
    @pytest.mark.asyncio
    async def test_bulk_image_operations(
        self,
        async_client,
        user_repository,
        property_repository,
        api_helper: APITestHelper,
        test_data_builder: TestDataBuilder
    ):
        """Test bulk image upload and management operations."""
        # Create agent and property
        agent = await UserFactory.create_user(
            user_repository,
            email="bulk_image_agent@test.com",
            role=UserRole.AGENT
        )
        
        property_data = test_data_builder.property_data(
            title="Bulk Image Property",
            location="Test Location"
        )
        property_response = await api_helper.create_property(property_data, agent.email)
        property_id = property_response["id"]
        
        # Bulk upload multiple images
        from PIL import Image as PILImage
        import io
        
        headers = await api_helper.login_user(agent.email)
        
        # Create multiple test image files
        image_files = []
        for i in range(3):
            image = PILImage.new('RGB', (800, 600), color=['red', 'green', 'blue'][i])
            image_bytes = io.BytesIO()
            image.save(image_bytes, format='JPEG')
            image_bytes.seek(0)
            image_files.append(("files", (f"bulk_image_{i}.jpg", image_bytes, "image/jpeg")))
        
        # Upload multiple images at once
        bulk_upload_response = await async_client.post(
            f"/images/property/{property_id}/upload-multiple",
            files=image_files,
            headers=headers
        )
        
        assert bulk_upload_response.status_code == 201
        bulk_upload_data = bulk_upload_response.json()
        
        assert bulk_upload_data["success"] is True
        assert bulk_upload_data["uploaded_count"] == 3
        assert len(bulk_upload_data["images"]) == 3
        
        # Verify all images are associated with the property
        property_images_response = await async_client.get(f"/images/property/{property_id}")
        property_images_data = property_images_response.json()
        assert property_images_data["total"] == 3


class TestErrorHandlingAndEdgeCases:
    """Test error handling and edge cases in integration scenarios."""
    
    @pytest.mark.asyncio
    async def test_concurrent_property_operations(
        self,
        async_client,
        user_repository,
        api_helper: APITestHelper,
        test_data_builder: TestDataBuilder
    ):
        """Test concurrent operations on the same property."""
        # Create agent
        agent = await UserFactory.create_user(
            user_repository,
            email="concurrent_agent@test.com",
            role=UserRole.AGENT
        )
        
        # Create property
        property_data = test_data_builder.property_data(
            title="Concurrent Test Property",
            price=2000.00
        )
        property_response = await api_helper.create_property(property_data, agent.email)
        property_id = property_response["id"]
        
        headers = await api_helper.login_user(agent.email)
        
        # Perform concurrent updates
        async def update_property(update_data: Dict[str, Any]):
            return await async_client.put(
                f"/properties/{property_id}",
                json=update_data,
                headers=headers
            )
        
        # Run concurrent updates
        update_tasks = [
            update_property({"title": "Concurrent Update 1"}),
            update_property({"price": 2100.00}),
            update_property({"description": "Updated description"})
        ]
        
        responses = await asyncio.gather(*update_tasks, return_exceptions=True)
        
        # At least one update should succeed
        successful_updates = [r for r in responses if hasattr(r, 'status_code') and r.status_code == 200]
        assert len(successful_updates) >= 1
        
        # Verify final property state is consistent
        final_property_response = await async_client.get(f"/properties/{property_id}")
        assert final_property_response.status_code == 200
    
    @pytest.mark.asyncio
    async def test_invalid_data_handling(
        self,
        async_client,
        user_repository,
        api_helper: APITestHelper
    ):
        """Test handling of various invalid data scenarios."""
        # Create agent
        agent = await UserFactory.create_user(
            user_repository,
            email="invalid_data_agent@test.com",
            role=UserRole.AGENT
        )
        
        headers = await api_helper.login_user(agent.email)
        
        # Test invalid property data scenarios
        invalid_scenarios = [
            {
                "name": "negative_price",
                "data": {
                    "title": "Test Property",
                    "description": "Test",
                    "property_type": "rental",
                    "price": -100.00,
                    "bedrooms": 2,
                    "bathrooms": 1,
                    "area_sqft": 1000,
                    "location": "Test"
                },
                "expected_status": 422
            },
            {
                "name": "invalid_property_type",
                "data": {
                    "title": "Test Property",
                    "description": "Test",
                    "property_type": "invalid_type",
                    "price": 1000.00,
                    "bedrooms": 2,
                    "bathrooms": 1,
                    "area_sqft": 1000,
                    "location": "Test"
                },
                "expected_status": 422
            },
            {
                "name": "missing_required_fields",
                "data": {
                    "title": "Test Property"
                    # Missing required fields
                },
                "expected_status": 422
            },
            {
                "name": "zero_area",
                "data": {
                    "title": "Test Property",
                    "description": "Test",
                    "property_type": "rental",
                    "price": 1000.00,
                    "bedrooms": 2,
                    "bathrooms": 1,
                    "area_sqft": 0,
                    "location": "Test"
                },
                "expected_status": 422
            }
        ]
        
        for scenario in invalid_scenarios:
            response = await async_client.post(
                "/properties",
                json=scenario["data"],
                headers=headers
            )
            
            assert response.status_code == scenario["expected_status"], \
                f"Scenario {scenario['name']} failed: expected {scenario['expected_status']}, got {response.status_code}"
    
    @pytest.mark.asyncio
    async def test_authorization_edge_cases(
        self,
        async_client,
        user_repository,
        property_repository,
        api_helper: APITestHelper,
        test_data_builder: TestDataBuilder
    ):
        """Test authorization edge cases and security scenarios."""
        # Create multiple agents
        agent1 = await UserFactory.create_user(
            user_repository,
            email="auth_agent1@test.com",
            role=UserRole.AGENT
        )
        
        agent2 = await UserFactory.create_user(
            user_repository,
            email="auth_agent2@test.com",
            role=UserRole.AGENT
        )
        
        # Agent1 creates a property
        property_data = test_data_builder.property_data(
            title="Agent1 Property",
            location="Test Location"
        )
        property_response = await api_helper.create_property(property_data, agent1.email)
        property_id = property_response["id"]
        
        # Agent2 tries to modify Agent1's property (should fail)
        agent2_headers = await api_helper.login_user(agent2.email)
        
        unauthorized_update = await async_client.put(
            f"/properties/{property_id}",
            json={"title": "Unauthorized Update"},
            headers=agent2_headers
        )
        
        assert unauthorized_update.status_code == 403
        
        # Agent2 tries to delete Agent1's property (should fail)
        unauthorized_delete = await async_client.delete(
            f"/properties/{property_id}",
            headers=agent2_headers
        )
        
        assert unauthorized_delete.status_code == 403
        
        # Verify property is unchanged
        property_check = await async_client.get(f"/properties/{property_id}")
        assert property_check.status_code == 200
        property_data = property_check.json()
        assert property_data["title"] == "Agent1 Property"  # Original title
    
    @pytest.mark.asyncio
    async def test_pagination_edge_cases(
        self,
        async_client,
        user_repository,
        property_repository,
        api_helper: APITestHelper,
        test_data_builder: TestDataBuilder
    ):
        """Test pagination edge cases and boundary conditions."""
        # Create agent and multiple properties
        agent = await UserFactory.create_user(
            user_repository,
            email="pagination_agent@test.com",
            role=UserRole.AGENT
        )
        
        # Create 25 properties for pagination testing
        for i in range(25):
            property_data = test_data_builder.property_data(
                title=f"Pagination Test Property {i:02d}",
                price=1000.00 + (i * 100),
                location=f"Location {i}"
            )
            await api_helper.create_property(property_data, agent.email)
        
        # Test various pagination scenarios
        pagination_tests = [
            {"page": 1, "page_size": 10, "expected_count": 10},
            {"page": 2, "page_size": 10, "expected_count": 10},
            {"page": 3, "page_size": 10, "expected_count": 5},  # Remaining properties
            {"page": 1, "page_size": 50, "expected_count": 25},  # All properties
            {"page": 1, "page_size": 5, "expected_count": 5},   # Small page size
        ]
        
        for test_case in pagination_tests:
            response = await async_client.get(
                f"/properties?page={test_case['page']}&page_size={test_case['page_size']}"
            )
            
            assert response.status_code == 200
            data = response.json()
            
            assert len(data["properties"]) == test_case["expected_count"]
            assert data["page"] == test_case["page"]
            assert data["page_size"] == test_case["page_size"]
            assert data["total"] >= 25
        
        # Test invalid pagination parameters
        invalid_pagination_tests = [
            {"page": 0, "page_size": 10},      # Invalid page
            {"page": -1, "page_size": 10},     # Negative page
            {"page": 1, "page_size": 0},       # Invalid page size
            {"page": 1, "page_size": -5},      # Negative page size
            {"page": 1, "page_size": 1000},    # Too large page size
        ]
        
        for test_case in invalid_pagination_tests:
            response = await async_client.get(
                f"/properties?page={test_case['page']}&page_size={test_case['page_size']}"
            )
            
            # Should either return 422 for validation error or handle gracefully
            assert response.status_code in [200, 422]