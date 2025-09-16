# API Documentation

Complete API documentation for the Property Listing API with examples and usage patterns.

## Table of Contents

- [Overview](#overview)
- [Authentication](#authentication)
- [Property Management](#property-management)
- [Image Management](#image-management)
- [Search and Filtering](#search-and-filtering)
- [Error Handling](#error-handling)
- [Rate Limiting](#rate-limiting)
- [Response Formats](#response-formats)
- [SDK Examples](#sdk-examples)

## Overview

The Property Listing API is a RESTful service that provides comprehensive property management capabilities. All endpoints return JSON responses and follow standard HTTP status codes.

### Base URL

- **Development**: `http://localhost:8000`
- **Staging**: `https://staging-api.yourdomain.com`
- **Production**: `https://api.yourdomain.com`

### API Version

Current API version: `v1`
All endpoints are prefixed with `/api/v1` (configurable via `API_V1_PREFIX`)

### Content Type

All requests should include:
```
Content-Type: application/json
```

## Authentication

The API uses JWT (JSON Web Token) based authentication. Tokens must be included in the Authorization header for protected endpoints.

### Login

Authenticate a user and receive an access token.

**Endpoint**: `POST /auth/login`

**Request Body**:
```json
{
  "email": "agent@example.com",
  "password": "password123"
}
```

**Response** (200 OK):
```json
{
  "access_token": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJ1c2VyX2lkIjoiMTIzZTQ1NjctZTg5Yi0xMmQzLWE0NTYtNDI2NjE0MTc0MDAwIiwiZW1haWwiOiJhZ2VudEBleGFtcGxlLmNvbSIsInJvbGUiOiJhZ2VudCIsImV4cCI6MTY0MDk5NTIwMH0.example-signature",
  "token_type": "bearer",
  "expires_in": 1800
}
```

**cURL Example**:
```bash
curl -X POST "http://localhost:8000/auth/login" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "agent@example.com",
    "password": "password123"
  }'
```

### Token Refresh

Refresh an existing access token.

**Endpoint**: `POST /auth/refresh`

**Headers**:
```
Authorization: Bearer <current_token>
```

**Response** (200 OK):
```json
{
  "access_token": "new_jwt_token_here",
  "token_type": "bearer",
  "expires_in": 1800
}
```

### Get Current User

Get information about the currently authenticated user.

**Endpoint**: `GET /auth/me`

**Headers**:
```
Authorization: Bearer <token>
```

**Response** (200 OK):
```json
{
  "id": "123e4567-e89b-12d3-a456-426614174000",
  "email": "agent@example.com",
  "full_name": "John Doe",
  "role": "agent",
  "is_active": true,
  "created_at": "2024-01-15T10:30:00Z"
}
```

## Property Management

### Create Property

Create a new property listing.

**Endpoint**: `POST /properties`

**Headers**:
```
Authorization: Bearer <token>
Content-Type: application/json
```

**Request Body**:
```json
{
  "title": "Beautiful 2BR Apartment in Downtown",
  "description": "Spacious apartment with modern amenities, great location near metro station and shopping centers.",
  "property_type": "rental",
  "price": 2500.00,
  "bedrooms": 2,
  "bathrooms": 2,
  "area_sqft": 1200,
  "location": "Downtown Dubai",
  "latitude": 25.2048,
  "longitude": 55.2708
}
```

**Response** (201 Created):
```json
{
  "id": "123e4567-e89b-12d3-a456-426614174000",
  "title": "Beautiful 2BR Apartment in Downtown",
  "description": "Spacious apartment with modern amenities...",
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
  "images": []
}
```

**cURL Example**:
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

### Get Property

Retrieve a specific property by ID.

**Endpoint**: `GET /properties/{property_id}`

**Response** (200 OK):
```json
{
  "id": "123e4567-e89b-12d3-a456-426614174000",
  "title": "Beautiful 2BR Apartment in Downtown",
  "description": "Spacious apartment with modern amenities...",
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

### Update Property

Update an existing property (only by owner or admin).

**Endpoint**: `PUT /properties/{property_id}`

**Headers**:
```
Authorization: Bearer <token>
Content-Type: application/json
```

**Request Body** (partial update supported):
```json
{
  "title": "Updated Property Title",
  "price": 2800.00,
  "description": "Updated description with new amenities"
}
```

**Response** (200 OK):
```json
{
  "id": "123e4567-e89b-12d3-a456-426614174000",
  "title": "Updated Property Title",
  "description": "Updated description with new amenities",
  "property_type": "rental",
  "price": 2800.00,
  "bedrooms": 2,
  "bathrooms": 2,
  "area_sqft": 1200,
  "location": "Downtown Dubai",
  "latitude": 25.2048,
  "longitude": 55.2708,
  "agent_id": "456e7890-e89b-12d3-a456-426614174001",
  "created_at": "2024-01-15T10:30:00Z",
  "updated_at": "2024-01-15T11:45:00Z",
  "images": []
}
```

### Delete Property

Delete a property (only by owner or admin).

**Endpoint**: `DELETE /properties/{property_id}`

**Headers**:
```
Authorization: Bearer <token>
```

**Response** (204 No Content)

**cURL Example**:
```bash
curl -X DELETE "http://localhost:8000/properties/123e4567-e89b-12d3-a456-426614174000" \
  -H "Authorization: Bearer <token>"
```

## Search and Filtering

### List Properties

Get a paginated list of properties with optional filtering.

**Endpoint**: `GET /properties`

**Query Parameters**:
- `page` (integer, default: 1): Page number
- `page_size` (integer, default: 20, max: 100): Items per page
- `location` (string): Filter by location
- `min_price` (decimal): Minimum price filter
- `max_price` (decimal): Maximum price filter
- `bedrooms` (integer): Minimum number of bedrooms
- `property_type` (string): "rental" or "sale"
- `sort_by` (string): "price", "created_at", "bedrooms"
- `sort_order` (string): "asc" or "desc"

**Example Request**:
```
GET /properties?location=Dubai&min_price=1000&max_price=5000&bedrooms=2&property_type=rental&page=1&page_size=10
```

**Response** (200 OK):
```json
{
  "items": [
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
      "images": []
    }
  ],
  "total": 150,
  "page": 1,
  "page_size": 10,
  "total_pages": 15,
  "has_next": true,
  "has_prev": false
}
```

**cURL Examples**:
```bash
# Basic listing
curl "http://localhost:8000/properties?page=1&page_size=10"

# Filtered search
curl "http://localhost:8000/properties?location=Dubai&min_price=1000&max_price=5000&bedrooms=2&property_type=rental"

# Sorted results
curl "http://localhost:8000/properties?sort_by=price&sort_order=asc"
```

### Advanced Search

Search properties with complex filters.

**Endpoint**: `POST /properties/search`

**Request Body**:
```json
{
  "filters": {
    "location": "Dubai",
    "price_range": {
      "min": 1000,
      "max": 5000
    },
    "bedrooms": {
      "min": 2,
      "max": 4
    },
    "property_type": "rental",
    "area_range": {
      "min": 800,
      "max": 2000
    }
  },
  "sort": {
    "field": "price",
    "order": "asc"
  },
  "pagination": {
    "page": 1,
    "page_size": 20
  }
}
```

## Image Management

### Upload Property Images

Upload one or more images for a property.

**Endpoint**: `POST /properties/{property_id}/images`

**Headers**:
```
Authorization: Bearer <token>
Content-Type: multipart/form-data
```

**Form Data**:
- `file`: Image file (JPEG, PNG, WebP, max 10MB)
- `is_primary` (optional): Boolean, set as primary image

**Response** (201 Created):
```json
{
  "id": "789e0123-e89b-12d3-a456-426614174002",
  "property_id": "123e4567-e89b-12d3-a456-426614174000",
  "filename": "living_room.jpg",
  "file_path": "/uploads/properties/123e4567-e89b-12d3-a456-426614174000/living_room.jpg",
  "file_size": 2048576,
  "mime_type": "image/jpeg",
  "upload_date": "2024-01-15T10:35:00Z",
  "is_primary": true,
  "url": "http://localhost:8000/uploads/properties/123e4567-e89b-12d3-a456-426614174000/living_room.jpg"
}
```

**cURL Example**:
```bash
curl -X POST "http://localhost:8000/properties/123e4567-e89b-12d3-a456-426614174000/images" \
  -H "Authorization: Bearer <token>" \
  -F "file=@/path/to/image.jpg" \
  -F "is_primary=true"
```

### Get Property Images

Get all images for a property.

**Endpoint**: `GET /properties/{property_id}/images`

**Response** (200 OK):
```json
[
  {
    "id": "789e0123-e89b-12d3-a456-426614174002",
    "property_id": "123e4567-e89b-12d3-a456-426614174000",
    "filename": "living_room.jpg",
    "file_path": "/uploads/properties/123e4567-e89b-12d3-a456-426614174000/living_room.jpg",
    "file_size": 2048576,
    "mime_type": "image/jpeg",
    "upload_date": "2024-01-15T10:35:00Z",
    "is_primary": true,
    "url": "http://localhost:8000/uploads/properties/123e4567-e89b-12d3-a456-426614174000/living_room.jpg"
  }
]
```

### Delete Image

Delete a specific image.

**Endpoint**: `DELETE /images/{image_id}`

**Headers**:
```
Authorization: Bearer <token>
```

**Response** (204 No Content)

## Error Handling

The API uses standard HTTP status codes and returns detailed error information.

### Error Response Format

```json
{
  "error": {
    "code": "ERROR_CODE",
    "message": "Human readable error message",
    "details": [
      {
        "field": "field_name",
        "message": "Field-specific error message"
      }
    ]
  }
}
```

### Common Error Codes

#### 400 Bad Request
```json
{
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "Validation failed",
    "details": [
      {
        "field": "price",
        "message": "Price must be greater than 0"
      },
      {
        "field": "email",
        "message": "Invalid email format"
      }
    ]
  }
}
```

#### 401 Unauthorized
```json
{
  "error": {
    "code": "UNAUTHORIZED",
    "message": "Authentication required"
  }
}
```

#### 403 Forbidden
```json
{
  "error": {
    "code": "FORBIDDEN",
    "message": "You don't have permission to access this resource"
  }
}
```

#### 404 Not Found
```json
{
  "error": {
    "code": "NOT_FOUND",
    "message": "Property not found"
  }
}
```

#### 422 Unprocessable Entity
```json
{
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "Invalid input data",
    "details": [
      {
        "field": "latitude",
        "message": "Latitude must be between -90 and 90"
      }
    ]
  }
}
```

#### 429 Too Many Requests
```json
{
  "error": {
    "code": "RATE_LIMIT_EXCEEDED",
    "message": "Too many requests. Please try again later.",
    "retry_after": 60
  }
}
```

#### 500 Internal Server Error
```json
{
  "error": {
    "code": "INTERNAL_ERROR",
    "message": "An unexpected error occurred"
  }
}
```

## Rate Limiting

The API implements rate limiting to prevent abuse:

- **General endpoints**: 100 requests per minute per IP
- **Authentication endpoints**: 10 requests per minute per IP
- **File upload endpoints**: 20 requests per minute per IP

Rate limit headers are included in responses:
```
X-RateLimit-Limit: 100
X-RateLimit-Remaining: 95
X-RateLimit-Reset: 1640995200
```

## Response Formats

### Pagination

All list endpoints support pagination:

```json
{
  "items": [...],
  "total": 150,
  "page": 1,
  "page_size": 20,
  "total_pages": 8,
  "has_next": true,
  "has_prev": false
}
```

### Timestamps

All timestamps are in ISO 8601 format (UTC):
```json
{
  "created_at": "2024-01-15T10:30:00Z",
  "updated_at": "2024-01-15T11:45:00Z"
}
```

### UUIDs

All resource IDs use UUID v4 format:
```json
{
  "id": "123e4567-e89b-12d3-a456-426614174000"
}
```

## SDK Examples

### JavaScript/Node.js

```javascript
class PropertyAPI {
  constructor(baseURL, token = null) {
    this.baseURL = baseURL;
    this.token = token;
  }

  async login(email, password) {
    const response = await fetch(`${this.baseURL}/auth/login`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ email, password })
    });
    
    if (response.ok) {
      const data = await response.json();
      this.token = data.access_token;
      return data;
    }
    throw new Error('Login failed');
  }

  async createProperty(propertyData) {
    const response = await fetch(`${this.baseURL}/properties`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${this.token}`
      },
      body: JSON.stringify(propertyData)
    });
    
    if (response.ok) {
      return await response.json();
    }
    throw new Error('Failed to create property');
  }

  async searchProperties(filters = {}) {
    const params = new URLSearchParams(filters);
    const response = await fetch(`${this.baseURL}/properties?${params}`);
    
    if (response.ok) {
      return await response.json();
    }
    throw new Error('Search failed');
  }
}

// Usage
const api = new PropertyAPI('http://localhost:8000');
await api.login('agent@example.com', 'password123');

const property = await api.createProperty({
  title: 'Beautiful Apartment',
  price: 2500,
  bedrooms: 2,
  location: 'Dubai'
});
```

### Python

```python
import requests
from typing import Optional, Dict, Any

class PropertyAPI:
    def __init__(self, base_url: str, token: Optional[str] = None):
        self.base_url = base_url
        self.token = token
        self.session = requests.Session()
    
    def login(self, email: str, password: str) -> Dict[str, Any]:
        response = self.session.post(
            f"{self.base_url}/auth/login",
            json={"email": email, "password": password}
        )
        response.raise_for_status()
        data = response.json()
        self.token = data["access_token"]
        self.session.headers.update({
            "Authorization": f"Bearer {self.token}"
        })
        return data
    
    def create_property(self, property_data: Dict[str, Any]) -> Dict[str, Any]:
        response = self.session.post(
            f"{self.base_url}/properties",
            json=property_data
        )
        response.raise_for_status()
        return response.json()
    
    def search_properties(self, **filters) -> Dict[str, Any]:
        response = self.session.get(
            f"{self.base_url}/properties",
            params=filters
        )
        response.raise_for_status()
        return response.json()

# Usage
api = PropertyAPI("http://localhost:8000")
api.login("agent@example.com", "password123")

property_data = {
    "title": "Beautiful Apartment",
    "price": 2500,
    "bedrooms": 2,
    "location": "Dubai"
}
property = api.create_property(property_data)
```

### cURL Scripts

```bash
#!/bin/bash

# Configuration
API_URL="http://localhost:8000"
EMAIL="agent@example.com"
PASSWORD="password123"

# Login and get token
TOKEN=$(curl -s -X POST "$API_URL/auth/login" \
  -H "Content-Type: application/json" \
  -d "{\"email\":\"$EMAIL\",\"password\":\"$PASSWORD\"}" \
  | jq -r '.access_token')

echo "Token: $TOKEN"

# Create property
PROPERTY_ID=$(curl -s -X POST "$API_URL/properties" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "title": "Beautiful Apartment",
    "description": "Great location",
    "property_type": "rental",
    "price": 2500,
    "bedrooms": 2,
    "bathrooms": 2,
    "area_sqft": 1200,
    "location": "Dubai",
    "latitude": 25.2048,
    "longitude": 55.2708
  }' | jq -r '.id')

echo "Created property: $PROPERTY_ID"

# Upload image
curl -X POST "$API_URL/properties/$PROPERTY_ID/images" \
  -H "Authorization: Bearer $TOKEN" \
  -F "file=@image.jpg" \
  -F "is_primary=true"

# Search properties
curl -s "$API_URL/properties?location=Dubai&min_price=1000&max_price=5000" \
  | jq '.items[] | {id, title, price, location}'
```

## Health and Monitoring

### Health Check

**Endpoint**: `GET /health`

**Response** (200 OK):
```json
{
  "status": "healthy",
  "timestamp": "2024-01-15T10:30:00Z",
  "version": "1.0.0",
  "environment": "production"
}
```

### Database Health

**Endpoint**: `GET /health/db`

**Response** (200 OK):
```json
{
  "status": "healthy",
  "database": "connected",
  "response_time_ms": 15
}
```

### API Documentation

Interactive API documentation is available at:
- **Swagger UI**: `/docs`
- **ReDoc**: `/redoc`
- **OpenAPI JSON**: `/openapi.json`