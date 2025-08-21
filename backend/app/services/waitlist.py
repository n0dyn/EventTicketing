"""
Waitlist Management Service
Business logic for managing event waitlists, notifications, and priority queuing
"""

from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any, Tuple
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_, func, update, delete, desc, asc
from sqlalchemy.orm import selectinload, joinedload
import asyncio
import logging

from app.models.waitlist import (
    EventWaitlist, WaitlistEntry, WaitlistNotification, 
    WaitlistRelease, WaitlistPreference,
    WaitlistStatus, WaitlistPriority
)
from app.models.event import Event
from app.models.user import User
from app.schemas.waitlist import (
    EventWaitlistCreate, EventWaitlistUpdate,
    WaitlistEntryCreate, WaitlistEntryUpdate,
    WaitlistReleaseCreate, WaitlistPreferencesUpdate,
    BulkWaitlistOperation, BulkWaitlistResult,
    WaitlistPosition, WaitlistStats
)
from app.core.caching import cached, CacheInvalidator
from app.services.email import email_service
from app.services.notification import notification_service

logger = logging.getLogger(__name__)


class WaitlistService:
    """Service for managing event waitlists and notifications"""

    # Event Waitlist Management
    
    async def create_event_waitlist(
        self, 
        db: AsyncSession, 
        waitlist_data: EventWaitlistCreate, 
        user_id: str
    ) -> EventWaitlist:
        """Create a waitlist for an event"""
        
        # Verify event exists and user owns it
        event_query = select(Event).where(
            and_(Event.id == waitlist_data.event_id, Event.owner_id == user_id)
        )
        result = await db.execute(event_query)
        event = result.scalar_one_or_none()
        
        if not event:
            raise ValueError("Event not found or access denied")
        
        # Check if waitlist already exists
        existing_query = select(EventWaitlist).where(
            EventWaitlist.event_id == waitlist_data.event_id
        )
        result = await db.execute(existing_query)
        existing = result.scalar_one_or_none()
        
        if existing:
            raise ValueError("Waitlist already exists for this event")
        
        # Create waitlist
        waitlist = EventWaitlist(**waitlist_data.model_dump())
        db.add(waitlist)
        await db.commit()
        await db.refresh(waitlist)
        
        return waitlist

    @cached(ttl=300, key_prefix="event_waitlist")
    async def get_event_waitlist(
        self, 
        db: AsyncSession, 
        event_id: str
    ) -> Optional[EventWaitlist]:
        """Get waitlist for an event"""
        
        query = select(EventWaitlist).where(EventWaitlist.event_id == event_id)
        result = await db.execute(query)
        return result.scalar_one_or_none()

    async def update_event_waitlist(
        self, 
        db: AsyncSession, 
        event_id: str, 
        waitlist_data: EventWaitlistUpdate, 
        user_id: str
    ) -> Optional[EventWaitlist]:
        """Update event waitlist settings"""
        
        # Verify ownership
        event_query = select(Event).where(
            and_(Event.id == event_id, Event.owner_id == user_id)
        )
        result = await db.execute(event_query)
        event = result.scalar_one_or_none()
        
        if not event:
            return None
        
        # Update waitlist
        update_data = waitlist_data.model_dump(exclude_unset=True)
        await db.execute(
            update(EventWaitlist)
            .where(EventWaitlist.event_id == event_id)
            .values(**update_data)
        )
        await db.commit()
        
        # Invalidate cache
        await CacheInvalidator.invalidate_event_cache(int(event_id))
        
        return await self.get_event_waitlist(db, event_id)

    # Waitlist Entry Management
    
    async def join_waitlist(
        self, 
        db: AsyncSession, 
        entry_data: WaitlistEntryCreate, 
        user_id: str
    ) -> WaitlistEntry:
        """Add user to event waitlist"""
        
        # Get or create event waitlist
        waitlist = await self.get_event_waitlist(db, entry_data.event_id)
        if not waitlist:
            raise ValueError("Waitlist not enabled for this event")
        
        if not waitlist.is_enabled:
            raise ValueError("Waitlist is currently disabled")
        
        if waitlist.is_full:
            raise ValueError("Waitlist is full")
        
        # Check if user already on waitlist
        existing_query = select(WaitlistEntry).where(
            and_(
                WaitlistEntry.event_id == entry_data.event_id,
                WaitlistEntry.user_id == user_id,
                WaitlistEntry.status == WaitlistStatus.ACTIVE.value
            )
        )
        result = await db.execute(existing_query)
        existing = result.scalar_one_or_none()
        
        if existing:
            raise ValueError("User already on waitlist for this event")
        
        # Get user preferences for defaults
        preferences = await self.get_user_preferences(db, user_id)
        
        # Determine priority
        priority = WaitlistPriority.NORMAL
        priority_score = 0.0
        
        if preferences and preferences.priority_eligible:
            if preferences.priority_level == WaitlistPriority.VIP.value:
                priority = WaitlistPriority.VIP
                priority_score = 10.0
            elif preferences.priority_level == WaitlistPriority.HIGH.value:
                priority = WaitlistPriority.HIGH
                priority_score = 5.0
        
        # Create entry
        entry_dict = entry_data.model_dump()
        entry_dict.update({
            'waitlist_id': waitlist.id,
            'user_id': user_id,
            'position': waitlist.get_next_position(),
            'priority': priority.value,
            'priority_score': priority_score
        })
        
        # Apply user preferences if not explicitly set
        if preferences:
            entry_dict.setdefault('email_notifications', preferences.default_email_notifications)
            entry_dict.setdefault('sms_notifications', preferences.default_sms_notifications)
            entry_dict.setdefault('push_notifications', preferences.default_push_notifications)
        
        entry = WaitlistEntry(**entry_dict)
        db.add(entry)
        
        # Update waitlist statistics
        waitlist.total_entries += 1
        waitlist.active_entries += 1
        
        await db.commit()
        await db.refresh(entry)
        
        # Update user preferences statistics
        if preferences:
            preferences.total_waitlist_joins += 1
            await db.commit()
        
        # Send confirmation email
        await self._send_waitlist_confirmation(db, entry)
        
        return entry

    async def update_waitlist_entry(
        self, 
        db: AsyncSession, 
        entry_id: int, 
        entry_data: WaitlistEntryUpdate, 
        user_id: str
    ) -> Optional[WaitlistEntry]:
        """Update user's waitlist entry"""
        
        # Get entry
        query = select(WaitlistEntry).where(
            and_(
                WaitlistEntry.id == entry_id,
                WaitlistEntry.user_id == user_id,
                WaitlistEntry.status == WaitlistStatus.ACTIVE.value
            )
        )
        result = await db.execute(query)
        entry = result.scalar_one_or_none()
        
        if not entry:
            return None
        
        # Update entry
        update_data = entry_data.model_dump(exclude_unset=True)
        await db.execute(
            update(WaitlistEntry)
            .where(WaitlistEntry.id == entry_id)
            .values(**update_data)
        )
        await db.commit()
        
        return await self.get_waitlist_entry(db, entry_id, user_id)

    async def leave_waitlist(
        self, 
        db: AsyncSession, 
        entry_id: int, 
        user_id: str
    ) -> bool:
        """Remove user from waitlist"""
        
        # Get entry
        entry = await self.get_waitlist_entry(db, entry_id, user_id)
        if not entry or entry.status != WaitlistStatus.ACTIVE.value:
            return False
        
        # Update entry status
        await db.execute(
            update(WaitlistEntry)
            .where(WaitlistEntry.id == entry_id)
            .values(status=WaitlistStatus.CANCELLED.value)
        )
        
        # Update waitlist statistics
        await db.execute(
            update(EventWaitlist)
            .where(EventWaitlist.id == entry.waitlist_id)
            .values(active_entries=EventWaitlist.active_entries - 1)
        )
        
        await db.commit()
        
        # Reorder positions for remaining entries
        await self._reorder_waitlist_positions(db, entry.waitlist_id)
        
        return True

    async def get_waitlist_entry(
        self, 
        db: AsyncSession, 
        entry_id: int, 
        user_id: str
    ) -> Optional[WaitlistEntry]:
        """Get specific waitlist entry"""
        
        query = select(WaitlistEntry).where(
            and_(
                WaitlistEntry.id == entry_id,
                WaitlistEntry.user_id == user_id
            )
        )
        result = await db.execute(query)
        return result.scalar_one_or_none()

    async def get_user_waitlist_position(
        self, 
        db: AsyncSession, 
        event_id: str, 
        user_id: str
    ) -> Optional[WaitlistPosition]:
        """Get user's position in waitlist"""
        
        # Get user's entry
        entry_query = select(WaitlistEntry).where(
            and_(
                WaitlistEntry.event_id == event_id,
                WaitlistEntry.user_id == user_id,
                WaitlistEntry.status == WaitlistStatus.ACTIVE.value
            )
        )
        result = await db.execute(entry_query)
        entry = result.scalar_one_or_none()
        
        if not entry:
            return None
        
        # Get total waitlist count
        total_query = select(func.count(WaitlistEntry.id)).where(
            and_(
                WaitlistEntry.event_id == event_id,
                WaitlistEntry.status == WaitlistStatus.ACTIVE.value
            )
        )
        result = await db.execute(total_query)
        total_count = result.scalar() or 0
        
        # Calculate effective position considering priority
        effective_position = entry.calculate_effective_position()
        
        # Count entries ahead (considering priority)
        ahead_query = select(func.count(WaitlistEntry.id)).where(
            and_(
                WaitlistEntry.event_id == event_id,
                WaitlistEntry.status == WaitlistStatus.ACTIVE.value,
                or_(
                    WaitlistEntry.position < entry.position,
                    and_(
                        WaitlistEntry.position == entry.position,
                        WaitlistEntry.priority_score > entry.priority_score
                    )
                )
            )
        )
        result = await db.execute(ahead_query)
        ahead_count = result.scalar() or 0
        
        # Estimate wait time (rough calculation)
        estimated_hours = await self._estimate_wait_time(db, event_id, effective_position)
        
        return WaitlistPosition(
            entry_id=entry.id,
            position=entry.position,
            effective_position=int(effective_position),
            estimated_wait_time_hours=estimated_hours,
            ahead_of_user=ahead_count,
            total_in_waitlist=total_count,
            priority=WaitlistPriority(entry.priority),
            status=WaitlistStatus(entry.status),
            joined_at=entry.joined_at
        )

    # Ticket Release and Notification
    
    async def process_ticket_release(
        self, 
        db: AsyncSession, 
        release_data: WaitlistReleaseCreate, 
        user_id: str
    ) -> WaitlistRelease:
        """Process ticket release to waitlist"""
        
        # Verify event ownership
        event_query = select(Event).where(
            and_(Event.id == release_data.event_id, Event.owner_id == user_id)
        )
        result = await db.execute(event_query)
        event = result.scalar_one_or_none()
        
        if not event:
            raise ValueError("Event not found or access denied")
        
        # Get waitlist
        waitlist = await self.get_event_waitlist(db, release_data.event_id)
        if not waitlist or not waitlist.is_enabled:
            raise ValueError("Waitlist not available for this event")
        
        # Create release record
        release = WaitlistRelease(
            **release_data.model_dump(),
            waitlist_id=waitlist.id,
            created_by=user_id
        )
        db.add(release)
        await db.flush()  # Get release ID
        
        # Get eligible entries based on processing method
        entries = await self._get_eligible_entries(
            db, waitlist.id, release_data.tickets_released, release_data.processing_method
        )
        
        # Distribute tickets considering priority
        vip_count, regular_count = await self._distribute_notifications(
            db, entries, waitlist, release
        )
        
        # Update release statistics
        release.notifications_sent = len(entries)
        release.vip_notifications = vip_count
        release.regular_notifications = regular_count
        
        await db.commit()
        
        return release

    async def _get_eligible_entries(
        self, 
        db: AsyncSession, 
        waitlist_id: int, 
        ticket_count: int, 
        method: str
    ) -> List[WaitlistEntry]:
        """Get eligible waitlist entries for notification"""
        
        query = select(WaitlistEntry).where(
            and_(
                WaitlistEntry.waitlist_id == waitlist_id,
                WaitlistEntry.status == WaitlistStatus.ACTIVE.value
            )
        )
        
        if method == "priority":
            # Order by priority score then position
            query = query.order_by(
                desc(WaitlistEntry.priority_score),
                asc(WaitlistEntry.position)
            )
        elif method == "random":
            # Random selection
            query = query.order_by(func.random())
        else:  # fifo (first in, first out)
            query = query.order_by(asc(WaitlistEntry.position))
        
        query = query.limit(ticket_count)
        
        result = await db.execute(query)
        return result.scalars().all()

    async def _distribute_notifications(
        self, 
        db: AsyncSession, 
        entries: List[WaitlistEntry], 
        waitlist: EventWaitlist, 
        release: WaitlistRelease
    ) -> Tuple[int, int]:
        """Distribute notifications to waitlist entries"""
        
        vip_count = 0
        regular_count = 0
        
        for entry in entries:
            # Create notification
            expires_at = datetime.utcnow() + timedelta(hours=waitlist.notification_window_hours)
            
            notification = WaitlistNotification(
                waitlist_id=waitlist.id,
                entry_id=entry.id,
                user_id=entry.user_id,
                notification_type="email",  # Default to email
                subject=f"Tickets Available: {entry.event.title}",
                message=waitlist.custom_message or self._get_default_notification_message(entry),
                available_tickets=1,  # For now, assume 1 ticket per notification
                expires_at=expires_at
            )
            db.add(notification)
            
            # Update entry status
            entry.status = WaitlistStatus.NOTIFIED.value
            entry.notified_at = datetime.utcnow()
            entry.expires_at = expires_at
            
            # Count by priority
            if entry.priority in [WaitlistPriority.VIP.value, WaitlistPriority.STAFF.value]:
                vip_count += 1
            else:
                regular_count += 1
            
            # Send notification (async)
            asyncio.create_task(self._send_notification(db, notification, entry))
        
        return vip_count, regular_count

    async def _send_notification(
        self, 
        db: AsyncSession, 
        notification: WaitlistNotification, 
        entry: WaitlistEntry
    ):
        """Send notification to user"""
        
        try:
            # Get user
            user_query = select(User).where(User.id == entry.user_id)
            result = await db.execute(user_query)
            user = result.scalar_one_or_none()
            
            if not user:
                logger.error(f"User not found for notification {notification.id}")
                return
            
            # Send email notification
            if entry.email_notifications and user.email:
                await email_service.send_waitlist_notification(
                    to_email=user.email,
                    user_name=user.full_name or user.email,
                    event_title=entry.event.title,
                    available_tickets=notification.available_tickets,
                    expires_at=notification.expires_at,
                    purchase_link=f"/events/{entry.event_id}/tickets?waitlist_token={notification.uuid}"
                )
            
            # Send push notification
            if entry.push_notifications:
                await notification_service.send_push_notification(
                    user_id=user.id,
                    title="Tickets Available!",
                    message=f"Tickets are now available for {entry.event.title}",
                    data={
                        "type": "waitlist_notification",
                        "event_id": entry.event_id,
                        "notification_id": str(notification.uuid)
                    }
                )
            
            # Update delivery status
            notification.delivery_status = "delivered"
            await db.commit()
            
        except Exception as e:
            logger.error(f"Failed to send notification {notification.id}: {e}")
            notification.delivery_status = "failed"
            notification.error_message = str(e)
            await db.commit()

    async def _send_waitlist_confirmation(
        self, 
        db: AsyncSession, 
        entry: WaitlistEntry
    ):
        """Send confirmation email when user joins waitlist"""
        
        try:
            # Get user
            user_query = select(User).where(User.id == entry.user_id)
            result = await db.execute(user_query)
            user = result.scalar_one_or_none()
            
            if user and user.email:
                position = await self.get_user_waitlist_position(db, entry.event_id, entry.user_id)
                
                await email_service.send_waitlist_confirmation(
                    to_email=user.email,
                    user_name=user.full_name or user.email,
                    event_title=entry.event.title,
                    position=position.position if position else entry.position,
                    estimated_wait=position.estimated_wait_time_hours if position else 0
                )
                
        except Exception as e:
            logger.error(f"Failed to send waitlist confirmation for entry {entry.id}: {e}")

    # User Preferences
    
    async def get_user_preferences(
        self, 
        db: AsyncSession, 
        user_id: str
    ) -> Optional[WaitlistPreference]:
        """Get user's waitlist preferences"""
        
        query = select(WaitlistPreference).where(WaitlistPreference.user_id == user_id)
        result = await db.execute(query)
        return result.scalar_one_or_none()

    async def update_user_preferences(
        self, 
        db: AsyncSession, 
        user_id: str, 
        preferences_data: WaitlistPreferencesUpdate
    ) -> WaitlistPreference:
        """Update user's waitlist preferences"""
        
        # Get or create preferences
        preferences = await self.get_user_preferences(db, user_id)
        
        if preferences:
            # Update existing
            update_data = preferences_data.model_dump(exclude_unset=True)
            await db.execute(
                update(WaitlistPreference)
                .where(WaitlistPreference.user_id == user_id)
                .values(**update_data)
            )
        else:
            # Create new
            preferences_dict = preferences_data.model_dump()
            preferences_dict['user_id'] = user_id
            preferences = WaitlistPreference(**preferences_dict)
            db.add(preferences)
        
        await db.commit()
        return await self.get_user_preferences(db, user_id)

    # Utility Methods
    
    async def _reorder_waitlist_positions(self, db: AsyncSession, waitlist_id: int):
        """Reorder positions after entry removal"""
        
        # Get all active entries ordered by current position
        query = select(WaitlistEntry).where(
            and_(
                WaitlistEntry.waitlist_id == waitlist_id,
                WaitlistEntry.status == WaitlistStatus.ACTIVE.value
            )
        ).order_by(WaitlistEntry.position)
        
        result = await db.execute(query)
        entries = result.scalars().all()
        
        # Update positions
        for i, entry in enumerate(entries, 1):
            entry.position = i
        
        await db.commit()

    async def _estimate_wait_time(
        self, 
        db: AsyncSession, 
        event_id: str, 
        position: int
    ) -> float:
        """Estimate wait time based on historical data"""
        
        # This is a simplified calculation
        # In practice, you'd use more sophisticated algorithms
        
        # Get average conversion rate and time from historical data
        avg_conversion_rate = 0.3  # 30% typical conversion rate
        avg_response_time_hours = 12  # Average time to respond to notifications
        
        # Estimate based on position and conversion patterns
        estimated_notifications_ahead = position / avg_conversion_rate
        estimated_hours = estimated_notifications_ahead * avg_response_time_hours
        
        return max(1.0, estimated_hours)  # Minimum 1 hour

    def _get_default_notification_message(self, entry: WaitlistEntry) -> str:
        """Get default notification message"""
        return f"""
Great news! Tickets are now available for {entry.event.title}.

You have {entry.waitlist.notification_window_hours} hours to complete your purchase 
before we offer these tickets to the next person on the waitlist.

Click the link below to secure your tickets now:
[Purchase Link]

Thank you for your patience!
        """.strip()


# Global service instance
waitlist_service = WaitlistService()