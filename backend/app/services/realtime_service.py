"""
Real-time service for broadcasting events and managing live updates.
Integrates with the WebSocket manager to send notifications.
"""
from typing import Dict, Any, Optional, List
import logging
from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.websocket import manager, MessageType, create_message
from app.models.event import Event
from app.models.order import Order
from app.models.ticket import Ticket
from app.models.attendee import Attendee
from app.models.user import User

logger = logging.getLogger(__name__)


class RealtimeService:
    """Service for managing real-time updates and notifications."""
    
    @staticmethod
    async def broadcast_event_update(
        event_id: int,
        update_type: MessageType,
        data: Dict[str, Any],
        exclude_user_id: Optional[int] = None
    ):
        """Broadcast event-related updates to all connected clients."""
        try:
            message = create_message(update_type, {
                "event_id": event_id,
                **data
            })
            
            exclude_connections = set()
            if exclude_user_id:
                # Find connections for the user to exclude
                for conn_id, conn_info in manager.connections.items():
                    if conn_info.get("user_id") == exclude_user_id:
                        exclude_connections.add(conn_id)
            
            await manager.broadcast_to_room(
                room_type="event",
                resource_id=str(event_id),
                message=message,
                exclude_connections=exclude_connections
            )
            
            logger.info(f"Broadcast {update_type} for event {event_id}")
            
        except Exception as e:
            logger.error(f"Failed to broadcast event update: {e}")
    
    @staticmethod
    async def broadcast_ticket_sold(
        db: AsyncSession,
        event_id: int,
        ticket_type_id: int,
        quantity_sold: int,
        remaining_quantity: int,
        order_id: Optional[int] = None
    ):
        """Broadcast ticket sale updates."""
        try:
            # Get ticket type information
            ticket_result = await db.execute(
                select(Ticket).where(Ticket.id == ticket_type_id)
            )
            ticket = ticket_result.scalar_one_or_none()
            
            if not ticket:
                logger.warning(f"Ticket type {ticket_type_id} not found")
                return
            
            data = {
                "ticket_type_id": ticket_type_id,
                "ticket_name": ticket.name,
                "quantity_sold": quantity_sold,
                "remaining_quantity": remaining_quantity,
                "is_sold_out": remaining_quantity <= 0,
                "order_id": order_id,
                "timestamp": datetime.utcnow().isoformat()
            }
            
            await RealtimeService.broadcast_event_update(
                event_id=event_id,
                update_type=MessageType.TICKET_SOLD,
                data=data
            )
            
        except Exception as e:
            logger.error(f"Failed to broadcast ticket sold: {e}")
    
    @staticmethod
    async def broadcast_order_update(
        order_id: int,
        status: str,
        data: Dict[str, Any],
        user_id: Optional[int] = None
    ):
        """Broadcast order status updates."""
        try:
            message_type = {
                "pending": MessageType.ORDER_CREATED,
                "completed": MessageType.ORDER_COMPLETED,
                "cancelled": MessageType.ORDER_CANCELLED,
            }.get(status, MessageType.ORDER_UPDATED)
            
            message = create_message(message_type, {
                "order_id": order_id,
                "status": status,
                **data
            })
            
            await manager.broadcast_to_room(
                room_type="order",
                resource_id=str(order_id),
                message=message
            )
            
            # Also notify the user directly if specified
            if user_id:
                await manager.broadcast_to_user_rooms(user_id, message)
            
            logger.info(f"Broadcast order update: {order_id} - {status}")
            
        except Exception as e:
            logger.error(f"Failed to broadcast order update: {e}")
    
    @staticmethod
    async def broadcast_attendee_checkin(
        db: AsyncSession,
        event_id: int,
        attendee_id: int,
        checked_in_by: int
    ):
        """Broadcast attendee check-in updates."""
        try:
            # Get attendee information
            attendee_result = await db.execute(
                select(Attendee).where(Attendee.id == attendee_id)
            )
            attendee = attendee_result.scalar_one_or_none()
            
            if not attendee:
                logger.warning(f"Attendee {attendee_id} not found")
                return
            
            # Get total check-in count for the event
            checked_in_count_result = await db.execute(
                select(Attendee).where(
                    Attendee.event_id == event_id,
                    Attendee.checked_in == True
                )
            )
            total_checked_in = len(checked_in_count_result.scalars().all())
            
            data = {
                "attendee_id": attendee_id,
                "attendee_name": attendee.full_name,
                "attendee_email": attendee.email,
                "checked_in_at": datetime.utcnow().isoformat(),
                "checked_in_by": checked_in_by,
                "total_checked_in": total_checked_in
            }
            
            # Broadcast to event room
            await RealtimeService.broadcast_event_update(
                event_id=event_id,
                update_type=MessageType.ATTENDEE_CHECKED_IN,
                data=data
            )
            
            # Broadcast to live event room
            await manager.broadcast_to_room(
                room_type="live_event",
                resource_id=str(event_id),
                message=create_message(MessageType.LIVE_COUNT_UPDATE, {
                    "event_id": event_id,
                    "total_checked_in": total_checked_in,
                    "latest_checkin": data
                })
            )
            
            logger.info(f"Broadcast check-in for attendee {attendee_id} at event {event_id}")
            
        except Exception as e:
            logger.error(f"Failed to broadcast attendee check-in: {e}")
    
    @staticmethod
    async def broadcast_admin_notification(
        notification_type: str,
        title: str,
        message: str,
        priority: str = "normal",
        data: Optional[Dict[str, Any]] = None
    ):
        """Broadcast notifications to admin users."""
        try:
            notification_data = {
                "type": notification_type,
                "title": title,
                "message": message,
                "priority": priority,
                "timestamp": datetime.utcnow().isoformat(),
                **(data or {})
            }
            
            await manager.broadcast_to_admin_users(
                create_message(MessageType.ADMIN_NOTIFICATION, notification_data)
            )
            
            logger.info(f"Broadcast admin notification: {title}")
            
        except Exception as e:
            logger.error(f"Failed to broadcast admin notification: {e}")
    
    @staticmethod
    async def broadcast_system_alert(
        alert_type: str,
        message: str,
        severity: str = "info",
        affected_services: Optional[List[str]] = None
    ):
        """Broadcast system-wide alerts."""
        try:
            alert_data = {
                "alert_type": alert_type,
                "message": message,
                "severity": severity,
                "affected_services": affected_services or [],
                "timestamp": datetime.utcnow().isoformat()
            }
            
            # Broadcast to admin dashboard
            await manager.broadcast_to_room(
                room_type="admin",
                resource_id="dashboard",
                message=create_message(MessageType.SYSTEM_ALERT, alert_data)
            )
            
            logger.info(f"Broadcast system alert: {alert_type} - {severity}")
            
        except Exception as e:
            logger.error(f"Failed to broadcast system alert: {e}")
    
    @staticmethod
    async def broadcast_event_analytics_update(
        event_id: int,
        analytics_data: Dict[str, Any]
    ):
        """Broadcast real-time analytics updates for an event."""
        try:
            data = {
                "event_id": event_id,
                "analytics": analytics_data,
                "updated_at": datetime.utcnow().isoformat()
            }
            
            # Broadcast to event organizers and admins
            await manager.broadcast_to_room(
                room_type="event",
                resource_id=str(event_id),
                message=create_message(MessageType.EVENT_UPDATED, data)
            )
            
            # Also broadcast to admin dashboard
            await manager.broadcast_to_room(
                room_type="admin",
                resource_id="dashboard",
                message=create_message(MessageType.ADMIN_NOTIFICATION, {
                    "type": "analytics_update",
                    "event_id": event_id,
                    "data": analytics_data
                })
            )
            
            logger.info(f"Broadcast analytics update for event {event_id}")
            
        except Exception as e:
            logger.error(f"Failed to broadcast analytics update: {e}")
    
    @staticmethod
    async def get_live_event_stats(db: AsyncSession, event_id: int) -> Dict[str, Any]:
        """Get current live statistics for an event."""
        try:
            # Get total ticket sales
            tickets_result = await db.execute(
                select(Ticket).where(Ticket.event_id == event_id)
            )
            tickets = tickets_result.scalars().all()
            
            total_capacity = sum(ticket.quantity for ticket in tickets)
            total_sold = sum(ticket.quantity - ticket.available_quantity for ticket in tickets)
            
            # Get check-in stats
            checked_in_result = await db.execute(
                select(Attendee).where(
                    Attendee.event_id == event_id,
                    Attendee.checked_in == True
                )
            )
            total_checked_in = len(checked_in_result.scalars().all())
            
            # Get active WebSocket connections for this event
            room_id = f"event:{event_id}"
            active_viewers = 0
            if room_id in manager.rooms:
                active_viewers = manager.rooms[room_id].get_connection_count()
            
            live_room_id = f"live_event:{event_id}"
            live_viewers = 0
            if live_room_id in manager.rooms:
                live_viewers = manager.rooms[live_room_id].get_connection_count()
            
            return {
                "event_id": event_id,
                "total_capacity": total_capacity,
                "total_sold": total_sold,
                "total_checked_in": total_checked_in,
                "active_viewers": active_viewers,
                "live_viewers": live_viewers,
                "attendance_rate": (total_checked_in / total_sold * 100) if total_sold > 0 else 0,
                "sales_rate": (total_sold / total_capacity * 100) if total_capacity > 0 else 0,
                "updated_at": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Failed to get live event stats: {e}")
            return {
                "event_id": event_id,
                "error": "Failed to fetch live stats"
            }


# Convenience functions for common real-time operations
async def notify_ticket_sold(
    db: AsyncSession,
    event_id: int,
    ticket_type_id: int,
    quantity: int,
    remaining: int,
    order_id: Optional[int] = None
):
    """Convenience function to notify about ticket sales."""
    await RealtimeService.broadcast_ticket_sold(
        db=db,
        event_id=event_id,
        ticket_type_id=ticket_type_id,
        quantity_sold=quantity,
        remaining_quantity=remaining,
        order_id=order_id
    )


async def notify_order_status(
    order_id: int,
    status: str,
    user_id: Optional[int] = None,
    **kwargs
):
    """Convenience function to notify about order status changes."""
    await RealtimeService.broadcast_order_update(
        order_id=order_id,
        status=status,
        data=kwargs,
        user_id=user_id
    )


async def notify_admin(
    notification_type: str,
    title: str,
    message: str,
    priority: str = "normal",
    **kwargs
):
    """Convenience function to send admin notifications."""
    await RealtimeService.broadcast_admin_notification(
        notification_type=notification_type,
        title=title,
        message=message,
        priority=priority,
        data=kwargs
    )