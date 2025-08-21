"""
Background tasks for email processing
"""
import logging
from datetime import datetime, timedelta
from typing import List

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.db.session import async_session
from app.models.user import User
from app.models.event import Event
from app.models.order import Order
from app.services.email import EmailService

logger = logging.getLogger(__name__)


async def send_event_reminders():
    """
    Background task to send event reminders
    Send reminders 24 hours and 2 hours before event starts
    """
    async with async_session() as db:
        try:
            # Get events starting in 24 hours
            tomorrow = datetime.utcnow() + timedelta(hours=24)
            tomorrow_window = timedelta(hours=1)  # 1 hour window
            
            events_24h = await db.execute(
                select(Event).where(
                    Event.start_date.between(
                        tomorrow - tomorrow_window,
                        tomorrow + tomorrow_window
                    )
                )
            )
            events_24h = events_24h.scalars().all()
            
            # Get events starting in 2 hours
            two_hours = datetime.utcnow() + timedelta(hours=2)
            two_hours_window = timedelta(minutes=30)  # 30 minute window
            
            events_2h = await db.execute(
                select(Event).where(
                    Event.start_date.between(
                        two_hours - two_hours_window,
                        two_hours + two_hours_window
                    )
                )
            )
            events_2h = events_2h.scalars().all()
            
            # Send 24-hour reminders
            for event in events_24h:
                await send_event_reminder_for_event(db, event, 24)
            
            # Send 2-hour reminders
            for event in events_2h:
                await send_event_reminder_for_event(db, event, 2)
                
            logger.info(f"Sent reminders for {len(events_24h)} events (24h) and {len(events_2h)} events (2h)")
            
        except Exception as e:
            logger.error(f"Failed to send event reminders: {str(e)}")


async def send_event_reminder_for_event(db: AsyncSession, event: Event, hours_until: int):
    """Send reminders to all attendees of an event"""
    try:
        # Get all orders for this event
        orders = await db.execute(
            select(Order).where(
                Order.event_id == event.id,
                Order.status == "completed"
            ).options(
                # Eager load user relationship
                selectinload(Order.user)
            )
        )
        orders = orders.scalars().all()
        
        # Send reminder to each attendee
        for order in orders:
            if order.user and order.user.email:
                try:
                    await EmailService.send_event_reminder_email(
                        user=order.user,
                        event=event,
                        hours_until_event=hours_until
                    )
                except Exception as e:
                    logger.error(f"Failed to send reminder to {order.user.email}: {str(e)}")
                    
    except Exception as e:
        logger.error(f"Failed to send reminders for event {event.id}: {str(e)}")


async def send_daily_digest():
    """
    Send daily digest emails to users with upcoming events
    """
    async with async_session() as db:
        try:
            # Get all users who have orders for events in the next 7 days
            week_from_now = datetime.utcnow() + timedelta(days=7)
            
            # This is a simplified version - in production, you'd want more sophisticated logic
            users_with_upcoming_events = await db.execute(
                select(User).join(Order).join(Event).where(
                    Event.start_date <= week_from_now,
                    Event.start_date >= datetime.utcnow(),
                    Order.status == "completed"
                ).distinct()
            )
            
            users = users_with_upcoming_events.scalars().all()
            
            for user in users:
                # Get user's upcoming events
                user_events = await db.execute(
                    select(Event).join(Order).where(
                        Order.user_id == user.id,
                        Event.start_date <= week_from_now,
                        Event.start_date >= datetime.utcnow(),
                        Order.status == "completed"
                    )
                )
                events = user_events.scalars().all()
                
                if events:
                    await send_digest_email_to_user(user, events)
                    
            logger.info(f"Sent daily digest to {len(users)} users")
            
        except Exception as e:
            logger.error(f"Failed to send daily digest: {str(e)}")


async def send_digest_email_to_user(user: User, events: List[Event]):
    """Send digest email to a single user"""
    try:
        # Create a simple digest email
        subject = f"Your Upcoming Events - {len(events)} event{'s' if len(events) > 1 else ''}"
        
        # For now, use a simple template - in production you'd want a dedicated digest template
        context = {
            "user_name": user.full_name or user.email,
            "events": events,
            "project_name": "EventTicketing"
        }
        
        # You would create a digest.html template for this
        # For now, we'll use the event reminder template as a placeholder
        html_body = EmailService.render_template("event_reminder.html", {
            "user_name": user.full_name or user.email,
            "event_title": f"{len(events)} upcoming events",
            "event_date": events[0].start_date,
            "event_location": "Various locations",
            "hours_until": 168,  # 7 days
            "project_name": "EventTicketing"
        })
        
        await EmailService.send_email(
            email_to=user.email,
            subject=subject,
            html_body=html_body
        )
        
    except Exception as e:
        logger.error(f"Failed to send digest email to {user.email}: {str(e)}")


# These functions would typically be called by a task scheduler like Celery, APScheduler, or cron jobs
# For development, you might call them manually or set up a simple scheduler