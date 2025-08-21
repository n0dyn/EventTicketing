"""
Recurring Events Service
Business logic for managing recurring events and event series
"""

from datetime import date, datetime, timedelta
from typing import List, Optional, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_, func, update, delete
from sqlalchemy.orm import selectinload

from app.models.recurring_event import EventSeries, RecurrencePattern, EventInstance
from app.models.event import Event
from app.schemas.recurring_event import (
    EventSeriesCreate, EventSeriesUpdate, RecurrencePatternCreate,
    EventInstanceCreate, EventInstanceUpdate, RecurrencePreview,
    BulkEventOperation, BulkEventResult
)
from app.core.caching import cached, CacheInvalidator


class RecurringEventService:
    """Service for managing recurring events and event series"""

    # Event Series Management
    
    @cached(ttl=300, key_prefix="event_series")
    async def get_event_series(
        self, 
        db: AsyncSession, 
        series_id: int, 
        user_id: str
    ) -> Optional[EventSeries]:
        """Get an event series by ID"""
        query = select(EventSeries).options(
            selectinload(EventSeries.recurrence_pattern),
            selectinload(EventSeries.events)
        ).where(
            and_(
                EventSeries.id == series_id,
                EventSeries.owner_id == user_id
            )
        )
        result = await db.execute(query)
        return result.scalar_one_or_none()

    async def create_event_series(
        self, 
        db: AsyncSession, 
        series_data: EventSeriesCreate, 
        user_id: str
    ) -> EventSeries:
        """Create a new event series with recurrence pattern"""
        
        # Create recurrence pattern first
        pattern = RecurrencePattern(**series_data.recurrence_pattern.model_dump())
        db.add(pattern)
        await db.flush()  # Get the pattern ID
        
        # Create event series
        series_dict = series_data.model_dump(exclude={'recurrence_pattern'})
        series_dict.update({
            'owner_id': user_id,
            'recurrence_pattern_id': pattern.id
        })
        
        series = EventSeries(**series_dict)
        db.add(series)
        await db.commit()
        await db.refresh(series)
        
        # Generate initial events
        await self.generate_events_for_series(db, series.id, user_id)
        
        # Invalidate caches
        await CacheInvalidator.invalidate_event_cache(0)  # Invalidate all events
        
        return series

    async def update_event_series(
        self, 
        db: AsyncSession, 
        series_id: int, 
        series_data: EventSeriesUpdate, 
        user_id: str
    ) -> Optional[EventSeries]:
        """Update an existing event series"""
        
        series = await self.get_event_series(db, series_id, user_id)
        if not series:
            return None
        
        # Update recurrence pattern if provided
        if series_data.recurrence_pattern:
            pattern_data = series_data.recurrence_pattern.model_dump(exclude_unset=True)
            await db.execute(
                update(RecurrencePattern)
                .where(RecurrencePattern.id == series.recurrence_pattern_id)
                .values(**pattern_data)
            )
        
        # Update series data
        update_data = series_data.model_dump(exclude_unset=True, exclude={'recurrence_pattern'})
        if update_data:
            await db.execute(
                update(EventSeries)
                .where(EventSeries.id == series_id)
                .values(**update_data)
            )
        
        await db.commit()
        
        # Regenerate events if pattern or dates changed
        if series_data.recurrence_pattern or 'series_end_date' in update_data:
            await self.regenerate_events_for_series(db, series_id, user_id)
        
        # Invalidate caches
        await CacheInvalidator.invalidate_event_cache(0)
        
        return await self.get_event_series(db, series_id, user_id)

    async def delete_event_series(
        self, 
        db: AsyncSession, 
        series_id: int, 
        user_id: str,
        delete_events: bool = True
    ) -> bool:
        """Delete an event series and optionally its events"""
        
        series = await self.get_event_series(db, series_id, user_id)
        if not series:
            return False
        
        if delete_events:
            # Delete all events in the series
            await db.execute(
                delete(Event).where(Event.event_series_id == series_id)
            )
        else:
            # Unlink events from series
            await db.execute(
                update(Event)
                .where(Event.event_series_id == series_id)
                .values(event_series_id=None, is_part_of_series=False)
            )
        
        # Delete the series (cascade will delete pattern)
        await db.execute(delete(EventSeries).where(EventSeries.id == series_id))
        await db.commit()
        
        # Invalidate caches
        await CacheInvalidator.invalidate_event_cache(0)
        
        return True

    # Event Generation
    
    async def generate_events_for_series(
        self, 
        db: AsyncSession, 
        series_id: int, 
        user_id: str,
        days_ahead: Optional[int] = None
    ) -> List[Event]:
        """Generate new events for a series"""
        
        series = await self.get_event_series(db, series_id, user_id)
        if not series or not series.is_active:
            return []
        
        new_events = series.generate_events(days_ahead)
        
        if new_events:
            for event in new_events:
                db.add(event)
            
            await db.commit()
            
            # Refresh events to get IDs
            for event in new_events:
                await db.refresh(event)
        
        return new_events

    async def regenerate_events_for_series(
        self, 
        db: AsyncSession, 
        series_id: int, 
        user_id: str
    ) -> List[Event]:
        """Regenerate all future events for a series"""
        
        # Delete future events that haven't started yet
        now = datetime.utcnow()
        await db.execute(
            delete(Event).where(
                and_(
                    Event.event_series_id == series_id,
                    Event.start_time > now
                )
            )
        )
        await db.commit()
        
        # Generate new events
        return await self.generate_events_for_series(db, series_id, user_id)

    async def preview_recurrence_dates(
        self, 
        pattern_data: RecurrencePatternCreate, 
        start_date: date,
        preview_count: int = 10
    ) -> RecurrencePreview:
        """Preview dates that would be generated by a recurrence pattern"""
        
        # Create temporary pattern (don't persist)
        pattern = RecurrencePattern(**pattern_data.model_dump())
        
        # Generate preview dates
        end_date = start_date + timedelta(days=365)  # Preview up to 1 year
        all_dates = pattern.generate_dates(start_date, end_date, limit=1000)
        
        preview_dates = all_dates[:preview_count]
        
        return RecurrencePreview(
            dates=preview_dates,
            total_count=len(all_dates),
            preview_count=len(preview_dates),
            has_more=len(all_dates) > preview_count
        )

    # Event Instance Management
    
    async def create_event_instance(
        self, 
        db: AsyncSession, 
        instance_data: EventInstanceCreate, 
        user_id: str
    ) -> Optional[EventInstance]:
        """Create a custom instance for a recurring event"""
        
        # Verify the event exists and belongs to user
        event_query = select(Event).where(
            and_(
                Event.id == instance_data.event_id,
                Event.owner_id == user_id,
                Event.is_part_of_series == True
            )
        )
        result = await db.execute(event_query)
        event = result.scalar_one_or_none()
        
        if not event:
            return None
        
        # Check if instance already exists
        existing_query = select(EventInstance).where(
            EventInstance.event_id == instance_data.event_id
        )
        result = await db.execute(existing_query)
        existing = result.scalar_one_or_none()
        
        if existing:
            return existing  # Already has customizations
        
        # Create new instance
        instance = EventInstance(**instance_data.model_dump())
        db.add(instance)
        await db.commit()
        await db.refresh(instance)
        
        # Invalidate event cache
        await CacheInvalidator.invalidate_event_cache(int(instance_data.event_id))
        
        return instance

    async def update_event_instance(
        self, 
        db: AsyncSession, 
        event_id: str, 
        instance_data: EventInstanceUpdate, 
        user_id: str
    ) -> Optional[EventInstance]:
        """Update customizations for a recurring event instance"""
        
        # Get existing instance
        query = select(EventInstance).join(Event).where(
            and_(
                EventInstance.event_id == event_id,
                Event.owner_id == user_id
            )
        )
        result = await db.execute(query)
        instance = result.scalar_one_or_none()
        
        if not instance:
            return None
        
        # Update instance
        update_data = instance_data.model_dump(exclude_unset=True)
        await db.execute(
            update(EventInstance)
            .where(EventInstance.id == instance.id)
            .values(**update_data)
        )
        
        await db.commit()
        
        # Invalidate event cache
        await CacheInvalidator.invalidate_event_cache(int(event_id))
        
        return await self.get_event_instance(db, event_id, user_id)

    async def get_event_instance(
        self, 
        db: AsyncSession, 
        event_id: str, 
        user_id: str
    ) -> Optional[EventInstance]:
        """Get event instance customizations"""
        
        query = select(EventInstance).join(Event).where(
            and_(
                EventInstance.event_id == event_id,
                Event.owner_id == user_id
            )
        )
        result = await db.execute(query)
        return result.scalar_one_or_none()

    # Bulk Operations
    
    async def bulk_operation_on_series_events(
        self, 
        db: AsyncSession, 
        series_id: int, 
        operation_data: BulkEventOperation, 
        user_id: str
    ) -> BulkEventResult:
        """Perform bulk operations on events in a series"""
        
        # Get events in the series
        query = select(Event).where(
            and_(
                Event.event_series_id == series_id,
                Event.owner_id == user_id,
                Event.id.in_(operation_data.event_ids)
            )
        )
        result = await db.execute(query)
        events = result.scalars().all()
        
        successful = 0
        failed = 0
        errors = []
        processed_ids = []
        
        for event in events:
            try:
                if operation_data.operation == "publish":
                    event.status = "published"
                elif operation_data.operation == "unpublish":
                    event.status = "draft"
                elif operation_data.operation == "cancel":
                    event.status = "cancelled"
                    # Create instance with cancellation reason if needed
                    if operation_data.reason:
                        instance = EventInstance(
                            event_id=event.id,
                            event_series_id=series_id,
                            is_cancelled=True,
                            cancellation_reason=operation_data.reason
                        )
                        db.add(instance)
                elif operation_data.operation == "delete":
                    await db.delete(event)
                
                processed_ids.append(event.id)
                successful += 1
                
            except Exception as e:
                failed += 1
                errors.append(f"Event {event.id}: {str(e)}")
        
        await db.commit()
        
        # Invalidate caches
        for event_id in processed_ids:
            await CacheInvalidator.invalidate_event_cache(int(event_id))
        
        return BulkEventResult(
            operation=operation_data.operation,
            total_requested=len(operation_data.event_ids),
            successful=successful,
            failed=failed,
            errors=errors,
            processed_event_ids=processed_ids
        )

    # Query Methods
    
    @cached(ttl=300, key_prefix="user_event_series")
    async def get_user_event_series(
        self, 
        db: AsyncSession, 
        user_id: str,
        skip: int = 0, 
        limit: int = 20,
        active_only: bool = True
    ) -> List[EventSeries]:
        """Get all event series for a user"""
        
        query = select(EventSeries).options(
            selectinload(EventSeries.recurrence_pattern)
        ).where(EventSeries.owner_id == user_id)
        
        if active_only:
            query = query.where(EventSeries.is_active == True)
        
        query = query.offset(skip).limit(limit).order_by(EventSeries.created_at.desc())
        
        result = await db.execute(query)
        return result.scalars().all()

    async def get_series_events(
        self, 
        db: AsyncSession, 
        series_id: int, 
        user_id: str,
        include_past: bool = False,
        skip: int = 0, 
        limit: int = 50
    ) -> List[Event]:
        """Get all events in a series"""
        
        query = select(Event).options(
            selectinload(Event.event_instance)
        ).where(
            and_(
                Event.event_series_id == series_id,
                Event.owner_id == user_id
            )
        )
        
        if not include_past:
            query = query.where(Event.start_time >= datetime.utcnow())
        
        query = query.offset(skip).limit(limit).order_by(Event.start_time)
        
        result = await db.execute(query)
        return result.scalars().all()


# Global service instance
recurring_event_service = RecurringEventService()