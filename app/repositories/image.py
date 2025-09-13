"""
Repository for PropertyImage model operations.
Handles database queries and operations for property images.
"""

import uuid
from typing import List, Optional, Dict, Any
from sqlalchemy import select, update, delete, func, and_, or_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.image import PropertyImage
from app.repositories.base import BaseRepository


class ImageRepository(BaseRepository[PropertyImage]):
    """Repository for PropertyImage database operations."""
    
    def __init__(self, db_session: AsyncSession):
        super().__init__(PropertyImage, db_session)
    
    async def get_by_property_id(self, property_id: uuid.UUID, 
                               include_inactive: bool = False) -> List[PropertyImage]:
        """
        Get all images for a specific property.
        
        Args:
            property_id: ID of the property
            include_inactive: Whether to include inactive images
            
        Returns:
            List of property images ordered by primary status and display order
        """
        query = select(PropertyImage).where(PropertyImage.property_id == property_id)
        
        # Order by primary status (primary first) then display order
        query = query.order_by(
            PropertyImage.is_primary.desc(),
            PropertyImage.display_order.asc(),
            PropertyImage.upload_date.asc()
        )
        
        result = await self.db_session.execute(query)
        return result.scalars().all()
    
    async def get_primary_image(self, property_id: uuid.UUID) -> Optional[PropertyImage]:
        """
        Get the primary image for a property.
        
        Args:
            property_id: ID of the property
            
        Returns:
            Primary image or None if not found
        """
        query = select(PropertyImage).where(
            and_(
                PropertyImage.property_id == property_id,
                PropertyImage.is_primary == True
            )
        )
        
        result = await self.db_session.execute(query)
        return result.scalar_one_or_none()
    
    async def count_by_property_id(self, property_id: uuid.UUID) -> int:
        """
        Count images for a specific property.
        
        Args:
            property_id: ID of the property
            
        Returns:
            Number of images for the property
        """
        query = select(func.count(PropertyImage.id)).where(
            PropertyImage.property_id == property_id
        )
        
        result = await self.db_session.execute(query)
        return result.scalar() or 0
    
    async def get_images_by_file_path(self, file_path: str) -> Optional[PropertyImage]:
        """
        Get image by file path (useful for cleanup operations).
        
        Args:
            file_path: Relative file path
            
        Returns:
            Property image or None if not found
        """
        query = select(PropertyImage).where(PropertyImage.file_path == file_path)
        
        result = await self.db_session.execute(query)
        return result.scalar_one_or_none()
    
    async def update_primary_status(self, property_id: uuid.UUID, 
                                  new_primary_id: uuid.UUID) -> bool:
        """
        Update primary image status for a property.
        Sets one image as primary and removes primary status from others.
        
        Args:
            property_id: ID of the property
            new_primary_id: ID of the image to set as primary
            
        Returns:
            True if update was successful
        """
        # First, remove primary status from all images of this property
        update_query = (
            update(PropertyImage)
            .where(PropertyImage.property_id == property_id)
            .values(is_primary=False)
        )
        await self.db_session.execute(update_query)
        
        # Then set the new primary image
        update_primary_query = (
            update(PropertyImage)
            .where(PropertyImage.id == new_primary_id)
            .values(is_primary=True)
        )
        result = await self.db_session.execute(update_primary_query)
        
        return result.rowcount > 0
    
    async def delete_by_property_id(self, property_id: uuid.UUID) -> int:
        """
        Delete all images for a property.
        
        Args:
            property_id: ID of the property
            
        Returns:
            Number of deleted images
        """
        delete_query = delete(PropertyImage).where(
            PropertyImage.property_id == property_id
        )
        
        result = await self.db_session.execute(delete_query)
        return result.rowcount or 0
    
    async def get_images_by_size_range(self, min_size: Optional[int] = None,
                                     max_size: Optional[int] = None) -> List[PropertyImage]:
        """
        Get images within a specific file size range.
        
        Args:
            min_size: Minimum file size in bytes
            max_size: Maximum file size in bytes
            
        Returns:
            List of images matching size criteria
        """
        query = select(PropertyImage)
        
        conditions = []
        if min_size is not None:
            conditions.append(PropertyImage.file_size >= min_size)
        if max_size is not None:
            conditions.append(PropertyImage.file_size <= max_size)
        
        if conditions:
            query = query.where(and_(*conditions))
        
        query = query.order_by(PropertyImage.upload_date.desc())
        
        result = await self.db_session.execute(query)
        return result.scalars().all()
    
    async def get_images_by_dimensions(self, min_width: Optional[int] = None,
                                     min_height: Optional[int] = None,
                                     max_width: Optional[int] = None,
                                     max_height: Optional[int] = None) -> List[PropertyImage]:
        """
        Get images within specific dimension ranges.
        
        Args:
            min_width: Minimum image width
            min_height: Minimum image height
            max_width: Maximum image width
            max_height: Maximum image height
            
        Returns:
            List of images matching dimension criteria
        """
        query = select(PropertyImage)
        
        conditions = []
        if min_width is not None:
            conditions.append(PropertyImage.width >= min_width)
        if min_height is not None:
            conditions.append(PropertyImage.height >= min_height)
        if max_width is not None:
            conditions.append(PropertyImage.width <= max_width)
        if max_height is not None:
            conditions.append(PropertyImage.height <= max_height)
        
        if conditions:
            query = query.where(and_(*conditions))
        
        query = query.order_by(PropertyImage.upload_date.desc())
        
        result = await self.db_session.execute(query)
        return result.scalars().all()
    
    async def get_images_by_mime_type(self, mime_types: List[str]) -> List[PropertyImage]:
        """
        Get images by MIME type.
        
        Args:
            mime_types: List of MIME types to filter by
            
        Returns:
            List of images with matching MIME types
        """
        query = select(PropertyImage).where(
            PropertyImage.mime_type.in_(mime_types)
        ).order_by(PropertyImage.upload_date.desc())
        
        result = await self.db_session.execute(query)
        return result.scalars().all()
    
    async def get_recent_uploads(self, limit: int = 50) -> List[PropertyImage]:
        """
        Get recently uploaded images.
        
        Args:
            limit: Maximum number of images to return
            
        Returns:
            List of recently uploaded images
        """
        query = (
            select(PropertyImage)
            .order_by(PropertyImage.upload_date.desc())
            .limit(limit)
        )
        
        result = await self.db_session.execute(query)
        return result.scalars().all()
    
    async def get_orphaned_images(self) -> List[PropertyImage]:
        """
        Get images that don't have associated properties (orphaned images).
        This requires a join with the properties table.
        
        Returns:
            List of orphaned images
        """
        from app.models.property import Property
        
        # Subquery to get all existing property IDs
        property_ids_subquery = select(Property.id)
        
        # Main query to find images with property_id not in existing properties
        query = select(PropertyImage).where(
            PropertyImage.property_id.notin_(property_ids_subquery)
        ).order_by(PropertyImage.upload_date.desc())
        
        result = await self.db_session.execute(query)
        return result.scalars().all()
    
    async def update_display_orders(self, property_id: uuid.UUID, 
                                  image_orders: Dict[uuid.UUID, int]) -> bool:
        """
        Update display orders for multiple images at once.
        
        Args:
            property_id: ID of the property
            image_orders: Dictionary mapping image IDs to display orders
            
        Returns:
            True if update was successful
        """
        try:
            for image_id, display_order in image_orders.items():
                update_query = (
                    update(PropertyImage)
                    .where(
                        and_(
                            PropertyImage.id == image_id,
                            PropertyImage.property_id == property_id
                        )
                    )
                    .values(display_order=display_order)
                )
                await self.db_session.execute(update_query)
            
            return True
        except Exception:
            return False
    
    async def get_storage_statistics(self) -> Dict[str, Any]:
        """
        Get storage statistics for images.
        
        Returns:
            Dictionary with storage statistics
        """
        # Total number of images
        total_count_query = select(func.count(PropertyImage.id))
        total_count_result = await self.db_session.execute(total_count_query)
        total_count = total_count_result.scalar() or 0
        
        # Total storage used
        total_size_query = select(func.sum(PropertyImage.file_size))
        total_size_result = await self.db_session.execute(total_size_query)
        total_size = total_size_result.scalar() or 0
        
        # Average file size
        avg_size_query = select(func.avg(PropertyImage.file_size))
        avg_size_result = await self.db_session.execute(avg_size_query)
        avg_size = avg_size_result.scalar() or 0
        
        # Count by MIME type
        mime_type_query = select(
            PropertyImage.mime_type,
            func.count(PropertyImage.id).label('count'),
            func.sum(PropertyImage.file_size).label('total_size')
        ).group_by(PropertyImage.mime_type)
        
        mime_type_result = await self.db_session.execute(mime_type_query)
        mime_type_stats = [
            {
                'mime_type': row.mime_type,
                'count': row.count,
                'total_size': row.total_size or 0
            }
            for row in mime_type_result
        ]
        
        return {
            'total_images': total_count,
            'total_size_bytes': total_size,
            'total_size_mb': round(total_size / (1024 * 1024), 2),
            'average_size_bytes': round(avg_size, 2),
            'average_size_mb': round(avg_size / (1024 * 1024), 2),
            'by_mime_type': mime_type_stats
        }