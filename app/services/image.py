"""
Image service for handling property image uploads, storage, and management.
Provides file validation, storage operations, and cleanup functionality.
"""

import os
import uuid
import shutil
import io
from pathlib import Path
from typing import List, Optional, Tuple
from PIL import Image
import aiofiles
from fastapi import UploadFile, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.models.image import PropertyImage
from app.schemas.image import PropertyImageCreate, PropertyImageResponse
from app.repositories.base import BaseRepository
from app.utils.exceptions import ValidationError, NotFoundError

settings = get_settings()


class ImageService:
    """Service for managing property image uploads and storage."""
    
    def __init__(self, db_session: AsyncSession):
        self.db_session = db_session
        self.repository = BaseRepository(PropertyImage, db_session)
        self.upload_dir = Path(settings.upload_dir)
        self.max_file_size = settings.max_file_size
        self.allowed_types = settings.allowed_file_types
        
        # Ensure upload directory exists
        self.upload_dir.mkdir(parents=True, exist_ok=True)
    
    async def validate_image_file(self, file: UploadFile) -> Tuple[int, int, str]:
        """
        Validate uploaded image file.
        
        Args:
            file: Uploaded file object
            
        Returns:
            Tuple of (width, height, mime_type)
            
        Raises:
            ValidationError: If file validation fails
        """
        # Check file size
        if file.size and file.size > self.max_file_size:
            max_mb = self.max_file_size / (1024 * 1024)
            raise ValidationError(f"File size exceeds maximum allowed size of {max_mb:.1f}MB")
        
        # Check content type
        if file.content_type not in self.allowed_types:
            raise ValidationError(f"File type '{file.content_type}' not allowed. Allowed types: {', '.join(self.allowed_types)}")
        
        # Validate file extension
        if not file.filename:
            raise ValidationError("Filename is required")
        
        file_ext = Path(file.filename).suffix.lower()
        allowed_extensions = {'.jpg', '.jpeg', '.png', '.webp'}
        if file_ext not in allowed_extensions:
            raise ValidationError(f"File extension '{file_ext}' not allowed. Allowed extensions: {', '.join(allowed_extensions)}")
        
        # Read file content to validate it's a real image
        try:
            # Reset file position
            await file.seek(0)
            content = await file.read()
            await file.seek(0)  # Reset for later use
            
            # Validate image using PIL
            with Image.open(io.BytesIO(content)) as img:
                width, height = img.size
                # Verify image format matches content type
                pil_format = img.format.lower()
                expected_formats = {
                    'image/jpeg': ['jpeg', 'jpg'],
                    'image/png': ['png'],
                    'image/webp': ['webp']
                }
                
                if file.content_type in expected_formats:
                    if pil_format not in expected_formats[file.content_type]:
                        raise ValidationError(f"File content doesn't match declared type {file.content_type}")
                
                return width, height, file.content_type
                
        except Exception as e:
            if isinstance(e, ValidationError):
                raise
            raise ValidationError(f"Invalid image file: {str(e)}")
    
    def _generate_file_path(self, property_id: uuid.UUID, filename: str) -> Path:
        """
        Generate unique file path for uploaded image.
        
        Args:
            property_id: ID of the property
            filename: Original filename
            
        Returns:
            Path object for the file
        """
        # Create property-specific directory
        property_dir = self.upload_dir / "properties" / str(property_id)
        property_dir.mkdir(parents=True, exist_ok=True)
        
        # Generate unique filename
        file_ext = Path(filename).suffix.lower()
        unique_filename = f"{uuid.uuid4()}{file_ext}"
        
        return property_dir / unique_filename
    
    async def save_image_file(self, file: UploadFile, file_path: Path) -> int:
        """
        Save uploaded file to disk.
        
        Args:
            file: Uploaded file object
            file_path: Path where to save the file
            
        Returns:
            File size in bytes
            
        Raises:
            ValidationError: If file save fails
        """
        try:
            # Ensure directory exists
            file_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Save file
            async with aiofiles.open(file_path, 'wb') as f:
                await file.seek(0)
                content = await file.read()
                await f.write(content)
            
            return len(content)
            
        except Exception as e:
            # Clean up partial file if it exists
            if file_path.exists():
                file_path.unlink()
            raise ValidationError(f"Failed to save image file: {str(e)}")
    
    async def upload_image(self, property_id: uuid.UUID, file: UploadFile, 
                          is_primary: bool = False, display_order: int = 0) -> PropertyImageResponse:
        """
        Upload and store a property image.
        
        Args:
            property_id: ID of the property
            file: Uploaded image file
            is_primary: Whether this is the primary image
            display_order: Display order for the image
            
        Returns:
            Created property image response
            
        Raises:
            ValidationError: If validation fails
            NotFoundError: If property doesn't exist
        """
        # Validate the image file
        width, height, mime_type = await self.validate_image_file(file)
        
        # Generate file path
        file_path = self._generate_file_path(property_id, file.filename)
        
        # Save file to disk
        file_size = await self.save_image_file(file, file_path)
        
        # Create relative path for database storage
        relative_path = str(file_path.relative_to(self.upload_dir))
        
        try:
            # Create image record
            image_data = PropertyImageCreate(
                filename=file.filename,
                file_path=relative_path,
                file_size=file_size,
                mime_type=mime_type,
                width=width,
                height=height,
                is_primary=is_primary,
                display_order=display_order
            )
            
            # Create database record
            image_dict = image_data.model_dump()
            image_dict['property_id'] = property_id
            
            db_image = await self.repository.create(image_dict)
            
            # If this is set as primary, update other images for this property
            if is_primary:
                await self._update_primary_image(property_id, db_image.id)
            
            return PropertyImageResponse.model_validate(db_image)
            
        except Exception as e:
            # Clean up file if database operation fails
            if file_path.exists():
                file_path.unlink()
            raise ValidationError(f"Failed to create image record: {str(e)}")
    
    async def upload_multiple_images(self, property_id: uuid.UUID, 
                                   files: List[UploadFile]) -> List[PropertyImageResponse]:
        """
        Upload multiple images for a property.
        
        Args:
            property_id: ID of the property
            files: List of uploaded image files
            
        Returns:
            List of created property image responses
        """
        uploaded_images = []
        errors = []
        
        for i, file in enumerate(files):
            try:
                # Set display order based on upload order
                display_order = i + 1
                is_primary = i == 0 and not await self._has_primary_image(property_id)
                
                image = await self.upload_image(property_id, file, is_primary, display_order)
                uploaded_images.append(image)
                
            except Exception as e:
                errors.append(f"Failed to upload {file.filename}: {str(e)}")
        
        if errors and not uploaded_images:
            raise ValidationError(f"All uploads failed: {'; '.join(errors)}")
        
        return uploaded_images
    
    async def get_property_images(self, property_id: uuid.UUID, 
                                include_inactive: bool = False) -> List[PropertyImageResponse]:
        """
        Get all images for a property.
        
        Args:
            property_id: ID of the property
            include_inactive: Whether to include inactive images
            
        Returns:
            List of property images
        """
        filters = {"property_id": property_id}
        order_by = [PropertyImage.is_primary.desc(), PropertyImage.display_order.asc()]
        
        images = await self.repository.get_multi(filters=filters, order_by=order_by)
        return [PropertyImageResponse.model_validate(img) for img in images]
    
    async def get_image_by_id(self, image_id: uuid.UUID) -> PropertyImageResponse:
        """
        Get image by ID.
        
        Args:
            image_id: ID of the image
            
        Returns:
            Property image response
            
        Raises:
            NotFoundError: If image not found
        """
        image = await self.repository.get(image_id)
        if not image:
            raise NotFoundError("Image not found")
        
        return PropertyImageResponse.model_validate(image)
    
    async def delete_image(self, image_id: uuid.UUID, user_id: uuid.UUID) -> bool:
        """
        Delete an image and its file.
        
        Args:
            image_id: ID of the image to delete
            user_id: ID of the user requesting deletion
            
        Returns:
            True if deleted successfully
            
        Raises:
            NotFoundError: If image not found
            ValidationError: If user doesn't have permission
        """
        # Get image record
        image = await self.repository.get(image_id)
        if not image:
            raise NotFoundError("Image not found")
        
        # TODO: Add permission check - user should own the property
        # This would require property repository access
        
        # Delete file from disk
        file_path = self.upload_dir / image.file_path
        if file_path.exists():
            try:
                file_path.unlink()
            except Exception as e:
                # Log error but don't fail the operation
                print(f"Warning: Failed to delete image file {file_path}: {e}")
        
        # Delete database record
        await self.repository.delete(image_id)
        
        # If this was the primary image, set another image as primary
        if image.is_primary:
            await self._set_new_primary_image(image.property_id)
        
        return True
    
    async def update_image_metadata(self, image_id: uuid.UUID, 
                                  is_primary: Optional[bool] = None,
                                  display_order: Optional[int] = None) -> PropertyImageResponse:
        """
        Update image metadata.
        
        Args:
            image_id: ID of the image
            is_primary: Whether this should be the primary image
            display_order: New display order
            
        Returns:
            Updated property image response
            
        Raises:
            NotFoundError: If image not found
        """
        image = await self.repository.get(image_id)
        if not image:
            raise NotFoundError("Image not found")
        
        update_data = {}
        if is_primary is not None:
            update_data['is_primary'] = is_primary
        if display_order is not None:
            update_data['display_order'] = display_order
        
        if update_data:
            updated_image = await self.repository.update(image_id, update_data)
            
            # Handle primary image logic
            if is_primary:
                await self._update_primary_image(image.property_id, image_id)
            
            return PropertyImageResponse.model_validate(updated_image)
        
        return PropertyImageResponse.model_validate(image)
    
    async def delete_property_images(self, property_id: uuid.UUID) -> int:
        """
        Delete all images for a property (used when property is deleted).
        
        Args:
            property_id: ID of the property
            
        Returns:
            Number of images deleted
        """
        # Get all images for the property
        images = await self.repository.get_multi(filters={"property_id": property_id})
        
        deleted_count = 0
        for image in images:
            try:
                # Delete file from disk
                file_path = self.upload_dir / image.file_path
                if file_path.exists():
                    file_path.unlink()
                
                # Delete database record
                await self.repository.delete(image.id)
                deleted_count += 1
                
            except Exception as e:
                # Log error but continue with other images
                print(f"Warning: Failed to delete image {image.id}: {e}")
        
        # Clean up empty property directory
        property_dir = self.upload_dir / "properties" / str(property_id)
        if property_dir.exists() and not any(property_dir.iterdir()):
            try:
                property_dir.rmdir()
            except Exception:
                pass  # Directory not empty or other error
        
        return deleted_count
    
    async def get_image_file_path(self, image_id: uuid.UUID) -> Path:
        """
        Get the file system path for an image.
        
        Args:
            image_id: ID of the image
            
        Returns:
            Path to the image file
            
        Raises:
            NotFoundError: If image not found
        """
        image = await self.repository.get(image_id)
        if not image:
            raise NotFoundError("Image not found")
        
        return self.upload_dir / image.file_path
    
    async def _has_primary_image(self, property_id: uuid.UUID) -> bool:
        """Check if property already has a primary image."""
        filters = {"property_id": property_id, "is_primary": True}
        images = await self.repository.get_multi(filters=filters, limit=1)
        return len(images) > 0
    
    async def _update_primary_image(self, property_id: uuid.UUID, new_primary_id: uuid.UUID):
        """Update primary image for a property."""
        # First, remove primary status from all other images
        filters = {"property_id": property_id, "is_primary": True}
        current_primary_images = await self.repository.get_multi(filters=filters)
        
        for image in current_primary_images:
            if image.id != new_primary_id:
                await self.repository.update(image.id, {"is_primary": False})
    
    async def _set_new_primary_image(self, property_id: uuid.UUID):
        """Set a new primary image when the current primary is deleted."""
        # Find the next image to set as primary (lowest display_order)
        filters = {"property_id": property_id}
        order_by = [PropertyImage.display_order.asc()]
        images = await self.repository.get_multi(filters=filters, order_by=order_by, limit=1)
        
        if images:
            await self.repository.update(images[0].id, {"is_primary": True})


