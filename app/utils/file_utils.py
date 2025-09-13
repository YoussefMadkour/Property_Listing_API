"""
File upload utilities for handling image validation and storage.
Provides common file operations and validation functions.
"""

import os
import uuid
import mimetypes
import io
from pathlib import Path
from typing import List, Tuple, Optional
from PIL import Image
import aiofiles
from fastapi import UploadFile

from app.config import get_settings
from app.utils.exceptions import ValidationError

settings = get_settings()


class FileValidator:
    """Utility class for file validation operations."""
    
    # Supported image formats and their MIME types
    SUPPORTED_FORMATS = {
        'image/jpeg': ['.jpg', '.jpeg'],
        'image/png': ['.png'],
        'image/webp': ['.webp']
    }
    
    # Maximum file size (10MB by default)
    MAX_FILE_SIZE = 10 * 1024 * 1024
    
    # Image dimension constraints
    MIN_WIDTH = 100
    MIN_HEIGHT = 100
    MAX_WIDTH = 10000
    MAX_HEIGHT = 10000
    
    @classmethod
    def validate_file_extension(cls, filename: str) -> str:
        """
        Validate file extension.
        
        Args:
            filename: Name of the file
            
        Returns:
            Lowercase file extension
            
        Raises:
            ValidationError: If extension is not supported
        """
        if not filename:
            raise ValidationError("Filename is required")
        
        file_path = Path(filename)
        extension = file_path.suffix.lower()
        
        if not extension:
            raise ValidationError("File must have an extension")
        
        # Check if extension is supported
        supported_extensions = []
        for mime_type, extensions in cls.SUPPORTED_FORMATS.items():
            supported_extensions.extend(extensions)
        
        if extension not in supported_extensions:
            raise ValidationError(
                f"File extension '{extension}' not supported. "
                f"Supported extensions: {', '.join(supported_extensions)}"
            )
        
        return extension
    
    @classmethod
    def validate_mime_type(cls, mime_type: str) -> str:
        """
        Validate MIME type.
        
        Args:
            mime_type: MIME type to validate
            
        Returns:
            Validated MIME type
            
        Raises:
            ValidationError: If MIME type is not supported
        """
        if not mime_type:
            raise ValidationError("MIME type is required")
        
        if mime_type not in cls.SUPPORTED_FORMATS:
            supported_types = list(cls.SUPPORTED_FORMATS.keys())
            raise ValidationError(
                f"MIME type '{mime_type}' not supported. "
                f"Supported types: {', '.join(supported_types)}"
            )
        
        return mime_type
    
    @classmethod
    def validate_file_size(cls, file_size: int, max_size: Optional[int] = None) -> int:
        """
        Validate file size.
        
        Args:
            file_size: Size of the file in bytes
            max_size: Maximum allowed size in bytes (optional)
            
        Returns:
            Validated file size
            
        Raises:
            ValidationError: If file size exceeds limit
        """
        if file_size <= 0:
            raise ValidationError("File size must be greater than 0")
        
        max_allowed = max_size or cls.MAX_FILE_SIZE
        if file_size > max_allowed:
            max_mb = max_allowed / (1024 * 1024)
            actual_mb = file_size / (1024 * 1024)
            raise ValidationError(
                f"File size ({actual_mb:.1f}MB) exceeds maximum allowed size ({max_mb:.1f}MB)"
            )
        
        return file_size
    
    @classmethod
    def validate_image_dimensions(cls, width: int, height: int,
                                min_width: Optional[int] = None,
                                min_height: Optional[int] = None,
                                max_width: Optional[int] = None,
                                max_height: Optional[int] = None) -> Tuple[int, int]:
        """
        Validate image dimensions.
        
        Args:
            width: Image width in pixels
            height: Image height in pixels
            min_width: Minimum width (optional)
            min_height: Minimum height (optional)
            max_width: Maximum width (optional)
            max_height: Maximum height (optional)
            
        Returns:
            Tuple of validated (width, height)
            
        Raises:
            ValidationError: If dimensions are invalid
        """
        min_w = min_width or cls.MIN_WIDTH
        min_h = min_height or cls.MIN_HEIGHT
        max_w = max_width or cls.MAX_WIDTH
        max_h = max_height or cls.MAX_HEIGHT
        
        if width < min_w:
            raise ValidationError(f"Image width ({width}px) is below minimum ({min_w}px)")
        
        if height < min_h:
            raise ValidationError(f"Image height ({height}px) is below minimum ({min_h}px)")
        
        if width > max_w:
            raise ValidationError(f"Image width ({width}px) exceeds maximum ({max_w}px)")
        
        if height > max_h:
            raise ValidationError(f"Image height ({height}px) exceeds maximum ({max_h}px)")
        
        return width, height
    
    @classmethod
    async def validate_upload_file(cls, file: UploadFile) -> Tuple[int, int, str, int]:
        """
        Comprehensive validation of uploaded file.
        
        Args:
            file: FastAPI UploadFile object
            
        Returns:
            Tuple of (width, height, mime_type, file_size)
            
        Raises:
            ValidationError: If any validation fails
        """
        # Validate filename and extension
        if not file.filename:
            raise ValidationError("Filename is required")
        
        extension = cls.validate_file_extension(file.filename)
        
        # Validate MIME type
        mime_type = cls.validate_mime_type(file.content_type or "")
        
        # Check if extension matches MIME type
        expected_extensions = cls.SUPPORTED_FORMATS.get(mime_type, [])
        if extension not in expected_extensions:
            raise ValidationError(
                f"File extension '{extension}' doesn't match MIME type '{mime_type}'"
            )
        
        # Read file content for validation
        await file.seek(0)
        content = await file.read()
        await file.seek(0)  # Reset for later use
        
        # Validate file size
        file_size = cls.validate_file_size(len(content))
        
        # Validate image content using PIL
        try:
            with Image.open(io.BytesIO(content)) as img:
                width, height = img.size
                
                # Validate dimensions
                width, height = cls.validate_image_dimensions(width, height)
                
                # Verify image format matches expected format
                pil_format = img.format.lower() if img.format else ""
                expected_formats = {
                    'image/jpeg': ['jpeg'],
                    'image/png': ['png'],
                    'image/webp': ['webp']
                }
                
                if mime_type in expected_formats:
                    if pil_format not in expected_formats[mime_type]:
                        raise ValidationError(
                            f"Image format '{pil_format}' doesn't match MIME type '{mime_type}'"
                        )
                
                return width, height, mime_type, file_size
                
        except Exception as e:
            if isinstance(e, ValidationError):
                raise
            raise ValidationError(f"Invalid image file: {str(e)}")


class FileStorage:
    """Utility class for file storage operations."""
    
    def __init__(self, base_dir: Optional[Path] = None):
        self.base_dir = Path(base_dir or settings.upload_dir)
        self.base_dir.mkdir(parents=True, exist_ok=True)
    
    def generate_unique_filename(self, original_filename: str) -> str:
        """
        Generate a unique filename while preserving the extension.
        
        Args:
            original_filename: Original filename
            
        Returns:
            Unique filename with UUID
        """
        file_path = Path(original_filename)
        extension = file_path.suffix.lower()
        unique_name = f"{uuid.uuid4()}{extension}"
        return unique_name
    
    def get_property_directory(self, property_id: uuid.UUID) -> Path:
        """
        Get or create directory for property images.
        
        Args:
            property_id: UUID of the property
            
        Returns:
            Path to property directory
        """
        property_dir = self.base_dir / "properties" / str(property_id)
        property_dir.mkdir(parents=True, exist_ok=True)
        return property_dir
    
    def generate_file_path(self, property_id: uuid.UUID, filename: str) -> Path:
        """
        Generate full file path for storing an image.
        
        Args:
            property_id: UUID of the property
            filename: Original filename
            
        Returns:
            Full path where file should be stored
        """
        property_dir = self.get_property_directory(property_id)
        unique_filename = self.generate_unique_filename(filename)
        return property_dir / unique_filename
    
    def get_relative_path(self, full_path: Path) -> str:
        """
        Get relative path from base directory.
        
        Args:
            full_path: Full file path
            
        Returns:
            Relative path as string
        """
        try:
            return str(full_path.relative_to(self.base_dir))
        except ValueError:
            # If path is not relative to base_dir, return as-is
            return str(full_path)
    
    async def save_file(self, file: UploadFile, file_path: Path) -> int:
        """
        Save uploaded file to disk.
        
        Args:
            file: UploadFile object
            file_path: Path where to save the file
            
        Returns:
            Number of bytes written
            
        Raises:
            ValidationError: If file save fails
        """
        try:
            # Ensure directory exists
            file_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Save file
            await file.seek(0)
            content = await file.read()
            
            async with aiofiles.open(file_path, 'wb') as f:
                await f.write(content)
            
            return len(content)
            
        except Exception as e:
            # Clean up partial file if it exists
            if file_path.exists():
                try:
                    file_path.unlink()
                except Exception:
                    pass  # Ignore cleanup errors
            
            raise ValidationError(f"Failed to save file: {str(e)}")
    
    def delete_file(self, file_path: Path) -> bool:
        """
        Delete a file from disk.
        
        Args:
            file_path: Path to the file to delete
            
        Returns:
            True if file was deleted, False otherwise
        """
        try:
            if file_path.exists():
                file_path.unlink()
                return True
            return False
        except Exception:
            return False
    
    def cleanup_empty_directories(self, property_id: uuid.UUID) -> bool:
        """
        Clean up empty directories after file deletion.
        
        Args:
            property_id: UUID of the property
            
        Returns:
            True if cleanup was successful
        """
        try:
            property_dir = self.base_dir / "properties" / str(property_id)
            
            # Only remove if directory exists and is empty
            if property_dir.exists() and not any(property_dir.iterdir()):
                property_dir.rmdir()
                return True
            
            return False
        except Exception:
            return False
    
    def get_file_info(self, file_path: Path) -> dict:
        """
        Get information about a file.
        
        Args:
            file_path: Path to the file
            
        Returns:
            Dictionary with file information
        """
        if not file_path.exists():
            return {}
        
        stat = file_path.stat()
        
        return {
            'size': stat.st_size,
            'size_mb': round(stat.st_size / (1024 * 1024), 2),
            'created': stat.st_ctime,
            'modified': stat.st_mtime,
            'extension': file_path.suffix.lower(),
            'mime_type': mimetypes.guess_type(str(file_path))[0]
        }


class ImageProcessor:
    """Utility class for image processing operations."""
    
    @staticmethod
    def get_image_info(image_path: Path) -> dict:
        """
        Get detailed information about an image file.
        
        Args:
            image_path: Path to the image file
            
        Returns:
            Dictionary with image information
        """
        try:
            with Image.open(image_path) as img:
                return {
                    'width': img.width,
                    'height': img.height,
                    'format': img.format,
                    'mode': img.mode,
                    'aspect_ratio': round(img.width / img.height, 2),
                    'has_transparency': img.mode in ('RGBA', 'LA') or 'transparency' in img.info
                }
        except Exception:
            return {}
    
    @staticmethod
    def create_thumbnail(image_path: Path, thumbnail_path: Path, 
                        size: Tuple[int, int] = (300, 300)) -> bool:
        """
        Create a thumbnail for an image.
        
        Args:
            image_path: Path to the original image
            thumbnail_path: Path where thumbnail should be saved
            size: Thumbnail size as (width, height)
            
        Returns:
            True if thumbnail was created successfully
        """
        try:
            with Image.open(image_path) as img:
                # Create thumbnail maintaining aspect ratio
                img.thumbnail(size, Image.Resampling.LANCZOS)
                
                # Ensure thumbnail directory exists
                thumbnail_path.parent.mkdir(parents=True, exist_ok=True)
                
                # Save thumbnail
                img.save(thumbnail_path, optimize=True, quality=85)
                
                return True
        except Exception:
            return False


