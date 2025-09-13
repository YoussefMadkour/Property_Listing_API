"""
Image management API endpoints.
Handles image upload, retrieval, update, and deletion operations.
"""

import uuid
from typing import List, Optional
from pathlib import Path
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, Query, status
from fastapi.responses import FileResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.services.image import ImageService
from app.schemas.image import (
    PropertyImageResponse, 
    PropertyImageListResponse,
    ImageUploadResponse,
    MultipleImageUploadResponse,
    PropertyImageUpdate,
    ImageFilters
)
from app.schemas.user import UserResponse
from app.utils.dependencies import get_current_user
from app.utils.exceptions import ValidationError, NotFoundError, ForbiddenError

router = APIRouter(prefix="/images", tags=["images"])


@router.post("/property/{property_id}/upload", 
            response_model=ImageUploadResponse,
            status_code=status.HTTP_201_CREATED,
            summary="Upload single image for property",
            description="Upload a single image file for a property. Supports JPEG, PNG, and WebP formats up to 10MB.")
async def upload_property_image(
    property_id: str,
    file: UploadFile = File(..., description="Image file to upload"),
    is_primary: bool = Form(False, description="Set as primary image for the property"),
    display_order: int = Form(0, description="Display order for image gallery"),
    current_user: UserResponse = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Upload a single image for a property."""
    try:
        property_uuid = uuid.UUID(property_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid property ID format"
        )
    
    # TODO: Add property ownership validation
    # This would require checking if the current user owns the property
    
    image_service = ImageService(db)
    
    try:
        image = await image_service.upload_image(
            property_id=property_uuid,
            file=file,
            is_primary=is_primary,
            display_order=display_order
        )
        
        return ImageUploadResponse(
            success=True,
            message="Image uploaded successfully",
            image=image
        )
        
    except ValidationError as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to upload image: {str(e)}"
        )


@router.post("/property/{property_id}/upload-multiple",
            response_model=MultipleImageUploadResponse,
            status_code=status.HTTP_201_CREATED,
            summary="Upload multiple images for property",
            description="Upload multiple image files for a property at once.")
async def upload_multiple_property_images(
    property_id: str,
    files: List[UploadFile] = File(..., description="List of image files to upload"),
    current_user: UserResponse = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Upload multiple images for a property."""
    try:
        property_uuid = uuid.UUID(property_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid property ID format"
        )
    
    if not files:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No files provided"
        )
    
    if len(files) > 10:  # Limit to 10 files per upload
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Maximum 10 files allowed per upload"
        )
    
    image_service = ImageService(db)
    
    try:
        images = await image_service.upload_multiple_images(property_uuid, files)
        
        return MultipleImageUploadResponse(
            success=True,
            message=f"{len(images)} images uploaded successfully",
            images=images,
            uploaded_count=len(images),
            failed_count=len(files) - len(images),
            errors=[]
        )
        
    except ValidationError as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to upload images: {str(e)}"
        )


@router.get("/property/{property_id}",
           response_model=PropertyImageListResponse,
           summary="Get all images for property",
           description="Retrieve all images associated with a specific property.")
async def get_property_images(
    property_id: str,
    db: AsyncSession = Depends(get_db)
):
    """Get all images for a property."""
    try:
        property_uuid = uuid.UUID(property_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid property ID format"
        )
    
    image_service = ImageService(db)
    
    try:
        images = await image_service.get_property_images(property_uuid)
        
        # Find primary image
        primary_image = next((img for img in images if img.is_primary), None)
        
        return PropertyImageListResponse(
            images=images,
            total=len(images),
            primary_image=primary_image
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve images: {str(e)}"
        )


@router.get("/{image_id}",
           response_model=PropertyImageResponse,
           summary="Get image details",
           description="Retrieve details for a specific image.")
async def get_image_details(
    image_id: str,
    db: AsyncSession = Depends(get_db)
):
    """Get details for a specific image."""
    try:
        image_uuid = uuid.UUID(image_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid image ID format"
        )
    
    image_service = ImageService(db)
    
    try:
        image = await image_service.get_image_by_id(image_uuid)
        return image
        
    except NotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Image not found"
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve image: {str(e)}"
        )


@router.get("/{image_id}/file",
           response_class=FileResponse,
           summary="Download image file",
           description="Download the actual image file.")
async def download_image_file(
    image_id: str,
    db: AsyncSession = Depends(get_db)
):
    """Download the actual image file."""
    try:
        image_uuid = uuid.UUID(image_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid image ID format"
        )
    
    image_service = ImageService(db)
    
    try:
        # Get image details
        image = await image_service.get_image_by_id(image_uuid)
        
        # Get file path
        file_path = await image_service.get_image_file_path(image_uuid)
        
        if not file_path.exists():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Image file not found on disk"
            )
        
        return FileResponse(
            path=str(file_path),
            filename=image.filename,
            media_type=image.mime_type
        )
        
    except NotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Image not found"
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to download image: {str(e)}"
        )


@router.put("/{image_id}",
           response_model=PropertyImageResponse,
           summary="Update image metadata",
           description="Update image metadata such as primary status and display order.")
async def update_image_metadata(
    image_id: str,
    image_update: PropertyImageUpdate,
    current_user: UserResponse = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Update image metadata."""
    try:
        image_uuid = uuid.UUID(image_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid image ID format"
        )
    
    # TODO: Add property ownership validation
    
    image_service = ImageService(db)
    
    try:
        updated_image = await image_service.update_image_metadata(
            image_id=image_uuid,
            is_primary=image_update.is_primary,
            display_order=image_update.display_order
        )
        
        return updated_image
        
    except NotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Image not found"
        )
    except ValidationError as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update image: {str(e)}"
        )


@router.delete("/{image_id}",
              status_code=status.HTTP_204_NO_CONTENT,
              summary="Delete image",
              description="Delete an image and its associated file.")
async def delete_image(
    image_id: str,
    current_user: UserResponse = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Delete an image and its file."""
    try:
        image_uuid = uuid.UUID(image_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid image ID format"
        )
    
    image_service = ImageService(db)
    
    try:
        await image_service.delete_image(image_uuid, current_user.id)
        
    except NotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Image not found"
        )
    except ForbiddenError:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have permission to delete this image"
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete image: {str(e)}"
        )


@router.post("/{image_id}/set-primary",
            response_model=PropertyImageResponse,
            summary="Set image as primary",
            description="Set an image as the primary image for its property.")
async def set_primary_image(
    image_id: str,
    current_user: UserResponse = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Set an image as primary for its property."""
    try:
        image_uuid = uuid.UUID(image_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid image ID format"
        )
    
    image_service = ImageService(db)
    
    try:
        updated_image = await image_service.update_image_metadata(
            image_id=image_uuid,
            is_primary=True
        )
        
        return updated_image
        
    except NotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Image not found"
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to set primary image: {str(e)}"
        )


# Admin endpoints for image management

@router.get("/",
           response_model=List[PropertyImageResponse],
           summary="List all images (Admin)",
           description="List all images in the system with filtering options. Admin only.")
async def list_all_images(
    filters: ImageFilters = Depends(),
    current_user: UserResponse = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """List all images with filtering (admin only)."""
    # TODO: Add admin role check
    # if current_user.role != "admin":
    #     raise HTTPException(
    #         status_code=status.HTTP_403_FORBIDDEN,
    #         detail="Admin access required"
    #     )
    
    # This is a placeholder implementation
    # In a real implementation, you would use the filters to query images
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="Admin image listing not yet implemented"
    )


@router.delete("/cleanup/orphaned",
              summary="Clean up orphaned images (Admin)",
              description="Remove images that don't have associated properties. Admin only.")
async def cleanup_orphaned_images(
    current_user: UserResponse = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Clean up orphaned images (admin only)."""
    # TODO: Add admin role check and implement cleanup logic
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="Orphaned image cleanup not yet implemented"
    )


@router.get("/stats/storage",
           summary="Get storage statistics (Admin)",
           description="Get storage usage statistics for images. Admin only.")
async def get_storage_statistics(
    current_user: UserResponse = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get storage statistics (admin only)."""
    # TODO: Add admin role check and implement statistics
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="Storage statistics not yet implemented"
    )