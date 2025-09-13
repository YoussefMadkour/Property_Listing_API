"""
Base repository class with common CRUD operations using async SQLAlchemy.
Provides generic database operations that can be extended by specific repositories.
"""

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, delete, func, and_, or_
from sqlalchemy.orm import selectinload
from app.database import Base
from typing import TypeVar, Generic, Optional, List, Dict, Any, Type, Union
import uuid
import logging

logger = logging.getLogger(__name__)

ModelType = TypeVar("ModelType", bound=Base)


class BaseRepository(Generic[ModelType]):
    """
    Base repository class providing common CRUD operations.
    Uses async SQLAlchemy for all database operations with proper error handling.
    """
    
    def __init__(self, model: Type[ModelType], db: AsyncSession):
        """
        Initialize repository with model class and database session.
        
        Args:
            model: SQLAlchemy model class
            db: Async database session
        """
        self.model = model
        self.db = db
    
    async def create(self, obj_in: Dict[str, Any]) -> ModelType:
        """
        Create a new record in the database.
        
        Args:
            obj_in: Dictionary of field values for the new record
            
        Returns:
            Created model instance
            
        Raises:
            Exception: If database operation fails
        """
        try:
            db_obj = self.model(**obj_in)
            self.db.add(db_obj)
            await self.db.commit()
            await self.db.refresh(db_obj)
            logger.debug(f"Created {self.model.__name__} with id: {db_obj.id}")
            return db_obj
        except Exception as e:
            await self.db.rollback()
            logger.error(f"Failed to create {self.model.__name__}: {e}")
            raise
    
    async def get_by_id(self, id: uuid.UUID, load_relationships: bool = False) -> Optional[ModelType]:
        """
        Get a record by its ID.
        
        Args:
            id: UUID of the record to retrieve
            load_relationships: Whether to eagerly load relationships
            
        Returns:
            Model instance if found, None otherwise
        """
        try:
            query = select(self.model).where(self.model.id == id)
            
            if load_relationships:
                # Load all relationships defined in the model
                for relationship in self.model.__mapper__.relationships:
                    query = query.options(selectinload(getattr(self.model, relationship.key)))
            
            result = await self.db.execute(query)
            obj = result.scalar_one_or_none()
            
            if obj:
                logger.debug(f"Retrieved {self.model.__name__} with id: {id}")
            else:
                logger.debug(f"{self.model.__name__} with id {id} not found")
            
            return obj
        except Exception as e:
            logger.error(f"Failed to get {self.model.__name__} by id {id}: {e}")
            raise
    
    async def get_multi(
        self,
        skip: int = 0,
        limit: int = 100,
        filters: Optional[Dict[str, Any]] = None,
        order_by: Optional[str] = None,
        load_relationships: bool = False
    ) -> List[ModelType]:
        """
        Get multiple records with optional filtering, pagination, and ordering.
        
        Args:
            skip: Number of records to skip (for pagination)
            limit: Maximum number of records to return
            filters: Dictionary of field filters
            order_by: Field name to order by (prefix with '-' for descending)
            load_relationships: Whether to eagerly load relationships
            
        Returns:
            List of model instances
        """
        try:
            query = select(self.model)
            
            # Apply filters
            if filters:
                for field, value in filters.items():
                    if hasattr(self.model, field):
                        if isinstance(value, list):
                            query = query.where(getattr(self.model, field).in_(value))
                        else:
                            query = query.where(getattr(self.model, field) == value)
            
            # Apply ordering
            if order_by:
                if order_by.startswith('-'):
                    field_name = order_by[1:]
                    if hasattr(self.model, field_name):
                        query = query.order_by(getattr(self.model, field_name).desc())
                else:
                    if hasattr(self.model, order_by):
                        query = query.order_by(getattr(self.model, order_by))
            else:
                # Default ordering by created_at descending
                query = query.order_by(self.model.created_at.desc())
            
            # Apply pagination
            query = query.offset(skip).limit(limit)
            
            # Load relationships if requested
            if load_relationships:
                for relationship in self.model.__mapper__.relationships:
                    query = query.options(selectinload(getattr(self.model, relationship.key)))
            
            result = await self.db.execute(query)
            objects = result.scalars().all()
            
            logger.debug(f"Retrieved {len(objects)} {self.model.__name__} records")
            return list(objects)
        except Exception as e:
            logger.error(f"Failed to get multiple {self.model.__name__} records: {e}")
            raise
    
    async def update(self, id: uuid.UUID, obj_in: Dict[str, Any]) -> Optional[ModelType]:
        """
        Update a record by its ID.
        
        Args:
            id: UUID of the record to update
            obj_in: Dictionary of field values to update
            
        Returns:
            Updated model instance if found, None otherwise
            
        Raises:
            Exception: If database operation fails
        """
        try:
            # Remove None values and empty strings from update data
            update_data = {k: v for k, v in obj_in.items() if v is not None and v != ""}
            
            if not update_data:
                logger.warning(f"No valid data provided for updating {self.model.__name__} {id}")
                return await self.get_by_id(id)
            
            # Update the record
            stmt = update(self.model).where(self.model.id == id).values(**update_data)
            result = await self.db.execute(stmt)
            
            if result.rowcount == 0:
                logger.debug(f"{self.model.__name__} with id {id} not found for update")
                return None
            
            await self.db.commit()
            
            # Return the updated object
            updated_obj = await self.get_by_id(id)
            logger.debug(f"Updated {self.model.__name__} with id: {id}")
            return updated_obj
        except Exception as e:
            await self.db.rollback()
            logger.error(f"Failed to update {self.model.__name__} {id}: {e}")
            raise
    
    async def delete(self, id: uuid.UUID) -> bool:
        """
        Delete a record by its ID.
        
        Args:
            id: UUID of the record to delete
            
        Returns:
            True if record was deleted, False if not found
            
        Raises:
            Exception: If database operation fails
        """
        try:
            stmt = delete(self.model).where(self.model.id == id)
            result = await self.db.execute(stmt)
            await self.db.commit()
            
            deleted = result.rowcount > 0
            if deleted:
                logger.debug(f"Deleted {self.model.__name__} with id: {id}")
            else:
                logger.debug(f"{self.model.__name__} with id {id} not found for deletion")
            
            return deleted
        except Exception as e:
            await self.db.rollback()
            logger.error(f"Failed to delete {self.model.__name__} {id}: {e}")
            raise
    
    async def count(self, filters: Optional[Dict[str, Any]] = None) -> int:
        """
        Count records with optional filtering.
        
        Args:
            filters: Dictionary of field filters
            
        Returns:
            Number of matching records
        """
        try:
            query = select(func.count(self.model.id))
            
            # Apply filters
            if filters:
                for field, value in filters.items():
                    if hasattr(self.model, field):
                        if isinstance(value, list):
                            query = query.where(getattr(self.model, field).in_(value))
                        else:
                            query = query.where(getattr(self.model, field) == value)
            
            result = await self.db.execute(query)
            count = result.scalar()
            
            logger.debug(f"Counted {count} {self.model.__name__} records")
            return count
        except Exception as e:
            logger.error(f"Failed to count {self.model.__name__} records: {e}")
            raise
    
    async def exists(self, id: uuid.UUID) -> bool:
        """
        Check if a record exists by its ID.
        
        Args:
            id: UUID of the record to check
            
        Returns:
            True if record exists, False otherwise
        """
        try:
            query = select(func.count(self.model.id)).where(self.model.id == id)
            result = await self.db.execute(query)
            count = result.scalar()
            
            exists = count > 0
            logger.debug(f"{self.model.__name__} with id {id} exists: {exists}")
            return exists
        except Exception as e:
            logger.error(f"Failed to check existence of {self.model.__name__} {id}: {e}")
            raise
    
    async def get_by_field(self, field: str, value: Any, load_relationships: bool = False) -> Optional[ModelType]:
        """
        Get a record by a specific field value.
        
        Args:
            field: Field name to search by
            value: Value to search for
            load_relationships: Whether to eagerly load relationships
            
        Returns:
            Model instance if found, None otherwise
        """
        try:
            if not hasattr(self.model, field):
                raise ValueError(f"Field '{field}' does not exist on {self.model.__name__}")
            
            query = select(self.model).where(getattr(self.model, field) == value)
            
            if load_relationships:
                for relationship in self.model.__mapper__.relationships:
                    query = query.options(selectinload(getattr(self.model, relationship.key)))
            
            result = await self.db.execute(query)
            obj = result.scalar_one_or_none()
            
            if obj:
                logger.debug(f"Retrieved {self.model.__name__} by {field}: {value}")
            else:
                logger.debug(f"{self.model.__name__} with {field}={value} not found")
            
            return obj
        except Exception as e:
            logger.error(f"Failed to get {self.model.__name__} by {field}={value}: {e}")
            raise
    
    async def bulk_create(self, objects_in: List[Dict[str, Any]]) -> List[ModelType]:
        """
        Create multiple records in a single transaction.
        
        Args:
            objects_in: List of dictionaries with field values
            
        Returns:
            List of created model instances
            
        Raises:
            Exception: If database operation fails
        """
        try:
            db_objects = [self.model(**obj_data) for obj_data in objects_in]
            self.db.add_all(db_objects)
            await self.db.commit()
            
            # Refresh all objects to get generated IDs and timestamps
            for obj in db_objects:
                await self.db.refresh(obj)
            
            logger.debug(f"Bulk created {len(db_objects)} {self.model.__name__} records")
            return db_objects
        except Exception as e:
            await self.db.rollback()
            logger.error(f"Failed to bulk create {self.model.__name__} records: {e}")
            raise
    
    async def bulk_update(self, updates: List[Dict[str, Any]]) -> int:
        """
        Update multiple records in a single transaction.
        Each update dict must contain an 'id' field.
        
        Args:
            updates: List of dictionaries with 'id' and field values to update
            
        Returns:
            Number of records updated
            
        Raises:
            Exception: If database operation fails
        """
        try:
            updated_count = 0
            
            for update_data in updates:
                if 'id' not in update_data:
                    raise ValueError("Each update must contain an 'id' field")
                
                record_id = update_data.pop('id')
                
                # Remove None values and empty strings
                clean_data = {k: v for k, v in update_data.items() if v is not None and v != ""}
                
                if clean_data:
                    stmt = update(self.model).where(self.model.id == record_id).values(**clean_data)
                    result = await self.db.execute(stmt)
                    updated_count += result.rowcount
            
            await self.db.commit()
            logger.debug(f"Bulk updated {updated_count} {self.model.__name__} records")
            return updated_count
        except Exception as e:
            await self.db.rollback()
            logger.error(f"Failed to bulk update {self.model.__name__} records: {e}")
            raise
    
    async def bulk_delete(self, ids: List[uuid.UUID]) -> int:
        """
        Delete multiple records by their IDs in a single transaction.
        
        Args:
            ids: List of UUIDs to delete
            
        Returns:
            Number of records deleted
            
        Raises:
            Exception: If database operation fails
        """
        try:
            stmt = delete(self.model).where(self.model.id.in_(ids))
            result = await self.db.execute(stmt)
            await self.db.commit()
            
            deleted_count = result.rowcount
            logger.debug(f"Bulk deleted {deleted_count} {self.model.__name__} records")
            return deleted_count
        except Exception as e:
            await self.db.rollback()
            logger.error(f"Failed to bulk delete {self.model.__name__} records: {e}")
            raise