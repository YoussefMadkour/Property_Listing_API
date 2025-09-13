# Image Upload and Management System

This document describes the image upload and management system implemented for the Property Listing API.

## Overview

The image upload system provides comprehensive functionality for managing property images, including:

- File upload with validation (JPEG, PNG, WebP formats)
- Image storage with Docker volume support
- Image metadata management
- Automatic cleanup when properties are deleted
- RESTful API endpoints for all operations

## Features Implemented

### 1. File Upload Utilities (`app/utils/file_utils.py`)

- **FileValidator**: Validates image files for format, size, and dimensions
- **FileStorage**: Handles file storage operations with unique naming
- **ImageProcessor**: Provides image processing utilities (future extension)

**Supported formats**: JPEG, PNG, WebP
**Maximum file size**: 10MB
**Minimum dimensions**: 100x100 pixels
**Maximum dimensions**: 10000x10000 pixels

### 2. Image Service (`app/services/image.py`)

Core business logic for image management:

- `upload_image()`: Upload single image with validation
- `upload_multiple_images()`: Upload multiple images at once
- `get_property_images()`: Retrieve all images for a property
- `delete_image()`: Delete image and file
- `delete_property_images()`: Clean up all images when property is deleted
- `update_image_metadata()`: Update image properties (primary status, display order)

### 3. Image Repository (`app/repositories/image.py`)

Database operations for image management:

- CRUD operations for PropertyImage model
- Query methods for filtering and searching
- Batch operations for efficiency
- Statistics and reporting functions

### 4. API Endpoints (`app/routers/images.py`)

RESTful endpoints for image operations:

#### Upload Operations
- `POST /api/v1/images/property/{property_id}/upload` - Upload single image
- `POST /api/v1/images/property/{property_id}/upload-multiple` - Upload multiple images

#### Retrieval Operations
- `GET /api/v1/images/property/{property_id}` - Get all images for property
- `GET /api/v1/images/{image_id}` - Get image details
- `GET /api/v1/images/{image_id}/file` - Download image file

#### Management Operations
- `PUT /api/v1/images/{image_id}` - Update image metadata
- `DELETE /api/v1/images/{image_id}` - Delete image
- `POST /api/v1/images/{image_id}/set-primary` - Set as primary image

### 5. Database Model (`app/models/image.py`)

PropertyImage model with comprehensive metadata:

- File information (name, path, size, MIME type)
- Image dimensions (width, height, aspect ratio)
- Display properties (primary status, display order)
- Timestamps and relationships

### 6. Docker Volume Support

Images are stored in Docker volumes for persistence:

- **Development**: `uploads_data` volume mounted to `/app/uploads`
- **File structure**: `uploads/properties/{property_id}/{unique_filename}`
- **Automatic cleanup**: Empty directories removed when properties deleted

## Usage Examples

### Upload Single Image

```bash
curl -X POST "http://localhost:8000/api/v1/images/property/123e4567-e89b-12d3-a456-426614174000/upload" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -F "file=@apartment.jpg" \
  -F "is_primary=true" \
  -F "display_order=1"
```

### Get Property Images

```bash
curl -X GET "http://localhost:8000/api/v1/images/property/123e4567-e89b-12d3-a456-426614174000"
```

### Download Image File

```bash
curl -X GET "http://localhost:8000/api/v1/images/123e4567-e89b-12d3-a456-426614174001/file" \
  -o downloaded_image.jpg
```

## File Validation Rules

1. **File Extensions**: `.jpg`, `.jpeg`, `.png`, `.webp`
2. **MIME Types**: `image/jpeg`, `image/png`, `image/webp`
3. **File Size**: Maximum 10MB
4. **Dimensions**: 
   - Minimum: 100x100 pixels
   - Maximum: 10000x10000 pixels
5. **Content Validation**: Files are validated using PIL to ensure they are valid images

## Error Handling

The system provides comprehensive error handling:

- **ValidationError**: File format, size, or dimension issues
- **NotFoundError**: Image or property not found
- **ForbiddenError**: Permission issues
- **Structured responses**: All errors return consistent JSON format

## Security Features

1. **Authentication Required**: All upload/modify operations require JWT token
2. **File Type Validation**: Only image files accepted
3. **Size Limits**: Prevents large file uploads
4. **Path Sanitization**: Secure file path generation
5. **Permission Checks**: Users can only manage their own property images

## Integration with Property Management

- **Cascade Delete**: Images automatically deleted when property is deleted
- **Primary Image**: Each property can have one primary image
- **Display Order**: Images can be ordered for gallery display
- **Relationship**: Proper foreign key relationships with properties

## Testing

Basic tests are included in `tests/test_image_upload.py`:

- File validation tests
- Storage path generation tests
- API endpoint tests
- Application startup tests

Run tests with:
```bash
python -m pytest tests/test_image_upload.py -v
```

## Configuration

Image upload settings in `app/config.py`:

```python
upload_dir: str = "./uploads"
max_file_size: int = 10 * 1024 * 1024  # 10MB
allowed_file_types: List[str] = ["image/jpeg", "image/png", "image/webp"]
```

## Future Enhancements

Potential improvements for the image system:

1. **Thumbnail Generation**: Automatic thumbnail creation
2. **Image Optimization**: Compress images for web delivery
3. **Cloud Storage**: Support for AWS S3, Google Cloud Storage
4. **Image Resizing**: Multiple size variants
5. **Watermarking**: Add property branding to images
6. **Bulk Operations**: Advanced batch upload/management
7. **Image Analytics**: Track image views and performance

## Requirements Satisfied

This implementation satisfies all requirements from the specification:

- ✅ **3.1**: Image storage and property association
- ✅ **3.2**: Image URLs in property details
- ✅ **3.3**: File format validation (JPEG, PNG, WebP)
- ✅ **3.4**: File size validation (10MB limit)
- ✅ **3.5**: Image cleanup on property deletion
- ✅ **3.6**: Error handling for upload failures

The system is production-ready and provides a solid foundation for property image management.