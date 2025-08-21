from typing import Any, Dict, List, Optional, Union

from sqlalchemy import select, and_, or_
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.event import Event
from app.schemas.event import EventCreate, EventUpdate
from app.core.caching import cached
from app.core.database_optimization import OptimizedQueries


class EventService:
    @cached(ttl=300, key_prefix="event_service_get")
    async def get(self, db: AsyncSession, id: str) -> Optional[Event]:
        """
        Get an event by ID
        """
        result = await db.execute(select(Event).where(Event.id == id))
        return result.scalars().first()

    async def get_multi(
        self, 
        db: AsyncSession, 
        *, 
        skip: int = 0, 
        limit: int = 100,
        search: Optional[str] = None,
        category_id: Optional[str] = None,
        user_id: Optional[str] = None
    ) -> List[Event]:
        """
        Get multiple events with filters
        """
        query = select(Event)
        filters = []
        
        # Apply search filter
        if search:
            filters.append(
                or_(
                    Event.title.ilike(f"%{search}%"),
                    Event.description.ilike(f"%{search}%")
                )
            )
        
        # Apply category filter
        if category_id:
            filters.append(Event.category_id == category_id)
            
        # Apply user filter (events owned by user)
        if user_id:
            filters.append(Event.owner_id == user_id)
        
        # Apply all filters
        if filters:
            query = query.where(and_(*filters))
            
        # Apply pagination
        query = query.offset(skip).limit(limit)
        
        result = await db.execute(query)
        return result.scalars().all()

    async def create(
        self, db: AsyncSession, *, obj_in: EventCreate, owner_id: str
    ) -> Event:
        """
        Create a new event
        """
        db_obj = Event(
            title=obj_in.title,
            description=obj_in.description,
            location=obj_in.location,
            start_date=obj_in.start_date,
            end_date=obj_in.end_date,
            category_id=obj_in.category_id,
            currency=obj_in.currency,
            featured_image=obj_in.featured_image,
            banner_image=obj_in.banner_image,
            is_published=False,  # Events are not published by default
            owner_id=owner_id,
        )
        db.add(db_obj)
        await db.commit()
        await db.refresh(db_obj)
        return db_obj

    async def update(
        self, db: AsyncSession, *, db_obj: Event, obj_in: Union[EventUpdate, Dict[str, Any]]
    ) -> Event:
        """
        Update an event
        """
        if isinstance(obj_in, dict):
            update_data = obj_in
        else:
            update_data = obj_in.model_dump(exclude_unset=True)
        
        for field, value in update_data.items():
            setattr(db_obj, field, value)
            
        db.add(db_obj)
        await db.commit()
        await db.refresh(db_obj)
        return db_obj

    async def remove(self, db: AsyncSession, *, id: str) -> Event:
        """
        Delete an event
        """
        obj = await self.get(db, id=id)
        await db.delete(obj)
        await db.commit()
        return obj

    async def publish(self, db: AsyncSession, *, db_obj: Event) -> Event:
        """
        Publish an event
        """
        db_obj.is_published = True
        db.add(db_obj)
        await db.commit()
        await db.refresh(db_obj)
        return db_obj

    async def unpublish(self, db: AsyncSession, *, db_obj: Event) -> Event:
        """
        Unpublish an event
        """
        db_obj.is_published = False
        db.add(db_obj)
        await db.commit()
        await db.refresh(db_obj)
        return db_obj

    @cached(ttl=300, key_prefix="public_events")
    async def get_public_events(
        self,
        db: AsyncSession,
        *,
        skip: int = 0,
        limit: int = 100,
        search: Optional[str] = None,
        category_id: Optional[str] = None,
        location: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        is_free: Optional[bool] = None,
    ) -> List[Event]:
        """
        Get all public published events
        """
        from app.models.event import EventStatus
        
        query = select(Event).where(
            and_(
                Event.is_public == True,
                Event.status == EventStatus.PUBLISHED
            )
        )
        
        filters = []
        
        # Apply search filter
        if search:
            filters.append(
                or_(
                    Event.title.ilike(f"%{search}%"),
                    Event.description.ilike(f"%{search}%")
                )
            )
        
        # Apply location filter
        if location:
            filters.append(Event.location.ilike(f"%{location}%"))
        
        # Apply date filters
        if start_date:
            from datetime import datetime
            start_dt = datetime.fromisoformat(start_date)
            filters.append(Event.start_time >= start_dt)
        
        if end_date:
            from datetime import datetime
            end_dt = datetime.fromisoformat(end_date)
            filters.append(Event.end_time <= end_dt)
        
        # Apply free events filter
        if is_free is not None:
            filters.append(Event.is_free == is_free)
        
        # Apply all filters
        if filters:
            query = query.where(and_(*filters))
        
        # Apply pagination
        query = query.offset(skip).limit(limit)
        
        result = await db.execute(query)
        return result.scalars().all()

    @cached(ttl=300, key_prefix="public_event_detail")
    async def get_public_event(self, db: AsyncSession, *, id: str) -> Optional[Event]:
        """
        Get a specific public event by ID
        """
        from app.models.event import EventStatus
        
        query = select(Event).where(
            and_(
                Event.id == id,
                Event.is_public == True,
                Event.status == EventStatus.PUBLISHED
            )
        )
        
        result = await db.execute(query)
        return result.scalars().first()

    async def get_events_with_stats(
        self, db: AsyncSession, *, skip: int = 0, limit: int = 20
    ) -> List[Dict[str, Any]]:
        """
        Get events with aggregated statistics using optimized queries
        """
        return await OptimizedQueries.get_events_with_stats(db, limit=limit)

    async def get_popular_events(
        self, db: AsyncSession, *, limit: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Get popular events using optimized queries
        """
        return await OptimizedQueries.get_popular_events(db, limit=limit)

    async def get_user_event_analytics(
        self, db: AsyncSession, *, user_id: int, limit: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Get user event analytics using optimized queries
        """
        return await OptimizedQueries.get_user_event_analytics(db, user_id=user_id, limit=limit)

    async def search_events_optimized(
        self, 
        db: AsyncSession, 
        *, 
        search_term: str, 
        limit: int = 20
    ) -> List[Dict[str, Any]]:
        """
        Search events using full-text search with optimized queries
        """
        return await OptimizedQueries.search_events_full_text(db, search_term=search_term, limit=limit)

    async def get_event_recommendations(
        self, 
        db: AsyncSession, 
        *, 
        user_id: int, 
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Get event recommendations for user using optimized queries
        """
        return await OptimizedQueries.get_event_recommendations(db, user_id=user_id, limit=limit)


event_service = EventService()