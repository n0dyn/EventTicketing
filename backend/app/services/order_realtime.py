"""
Enhanced order service with real-time WebSocket integration.
Extends the base order service with real-time notifications.
"""
from typing import List, Optional, Dict, Any
import logging
from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update
from sqlalchemy.orm import selectinload

from app.models.order import Order
from app.models.ticket import Ticket
from app.models.event import Event
from app.schemas.order import OrderCreate, OrderUpdate
from app.services.realtime_service import RealtimeService, notify_order_status, notify_ticket_sold

logger = logging.getLogger(__name__)


class OrderRealtimeService:
    """Order service with real-time WebSocket integration."""
    
    @staticmethod
    async def create_order_with_notification(
        db: AsyncSession,
        order_data: OrderCreate,
        user_id: int
    ) -> Order:
        """Create an order and broadcast real-time notification."""
        try:
            # Create the order
            order = Order(
                user_id=user_id,
                event_id=order_data.event_id,
                total_amount=order_data.total_amount,
                status="pending",
                payment_method=order_data.payment_method or "stripe",
                billing_address=order_data.billing_address,
                billing_city=order_data.billing_city,
                billing_country=order_data.billing_country,
                billing_postal_code=order_data.billing_postal_code,
            )
            
            db.add(order)
            await db.flush()  # Get the ID without committing
            
            # Add order items if provided
            total_tickets = 0
            if hasattr(order_data, 'items') and order_data.items:
                for item_data in order_data.items:
                    # Get ticket information
                    ticket_result = await db.execute(
                        select(Ticket).where(Ticket.id == item_data.ticket_id)
                    )
                    ticket = ticket_result.scalar_one_or_none()
                    
                    if not ticket:
                        raise ValueError(f"Ticket {item_data.ticket_id} not found")
                    
                    if ticket.available_quantity < item_data.quantity:
                        raise ValueError(f"Insufficient tickets available for {ticket.name}")
                    
                    # Update ticket availability
                    await db.execute(
                        update(Ticket)
                        .where(Ticket.id == item_data.ticket_id)
                        .values(available_quantity=ticket.available_quantity - item_data.quantity)
                    )
                    
                    total_tickets += item_data.quantity
                    
                    # Notify about ticket sale
                    await notify_ticket_sold(
                        db=db,
                        event_id=order_data.event_id,
                        ticket_type_id=item_data.ticket_id,
                        quantity=item_data.quantity,
                        remaining=ticket.available_quantity - item_data.quantity,
                        order_id=order.id
                    )
            
            await db.commit()
            await db.refresh(order)
            
            # Send real-time notification
            await notify_order_status(
                order_id=order.id,
                status="pending",
                user_id=user_id,
                event_id=order_data.event_id,
                total_amount=float(order_data.total_amount),
                total_tickets=total_tickets,
                created_at=order.created_at.isoformat()
            )
            
            logger.info(f"Created order {order.id} with real-time notification")
            return order
            
        except Exception as e:
            await db.rollback()
            logger.error(f"Failed to create order with notification: {e}")
            raise
    
    @staticmethod
    async def update_order_status_with_notification(
        db: AsyncSession,
        order_id: int,
        status: str,
        payment_intent_id: Optional[str] = None,
        additional_data: Optional[Dict[str, Any]] = None
    ) -> Optional[Order]:
        """Update order status and broadcast real-time notification."""
        try:
            # Get the order with event information
            order_result = await db.execute(
                select(Order)
                .options(selectinload(Order.event))
                .where(Order.id == order_id)
            )
            order = order_result.scalar_one_or_none()
            
            if not order:
                logger.warning(f"Order {order_id} not found")
                return None
            
            old_status = order.status
            
            # Update order status
            update_data = {"status": status}
            if payment_intent_id:
                update_data["payment_intent_id"] = payment_intent_id
            if status == "completed":
                update_data["completed_at"] = datetime.utcnow()
            
            await db.execute(
                update(Order)
                .where(Order.id == order_id)
                .values(**update_data)
            )
            
            await db.commit()
            await db.refresh(order)
            
            # Prepare notification data
            notification_data = {
                "event_id": order.event_id,
                "event_title": order.event.title if order.event else "Unknown Event",
                "total_amount": float(order.total_amount),
                "old_status": old_status,
                "payment_intent_id": payment_intent_id,
                "updated_at": datetime.utcnow().isoformat(),
                **(additional_data or {})
            }
            
            # Send real-time notification
            await notify_order_status(
                order_id=order_id,
                status=status,
                user_id=order.user_id,
                **notification_data
            )
            
            # Special handling for completed orders
            if status == "completed":
                await OrderRealtimeService._handle_order_completion(db, order)
            
            logger.info(f"Updated order {order_id} status to {status} with notification")
            return order
            
        except Exception as e:
            await db.rollback()
            logger.error(f"Failed to update order status with notification: {e}")
            raise
    
    @staticmethod
    async def _handle_order_completion(db: AsyncSession, order: Order):
        """Handle additional tasks when an order is completed."""
        try:
            # Create attendees for the completed order
            from app.services.attendee import create_attendees_from_order
            attendees = await create_attendees_from_order(db, order.id)
            
            # Send admin notification about the sale
            from app.services.realtime_service import notify_admin
            await notify_admin(
                notification_type="order_completed",
                title="New Order Completed",
                message=f"Order #{order.id} for {order.event.title if order.event else 'Unknown Event'} completed",
                priority="normal",
                order_id=order.id,
                amount=float(order.total_amount),
                attendee_count=len(attendees) if attendees else 0
            )
            
            # Update live analytics
            await RealtimeService.broadcast_event_analytics_update(
                event_id=order.event_id,
                analytics_data={
                    "recent_sale": {
                        "order_id": order.id,
                        "amount": float(order.total_amount),
                        "completed_at": datetime.utcnow().isoformat()
                    }
                }
            )
            
        except Exception as e:
            logger.error(f"Error handling order completion: {e}")
    
    @staticmethod
    async def cancel_order_with_notification(
        db: AsyncSession,
        order_id: int,
        cancellation_reason: Optional[str] = None
    ) -> Optional[Order]:
        """Cancel an order and restore ticket availability with real-time notification."""
        try:
            # Get the order with items
            order_result = await db.execute(
                select(Order)
                .options(selectinload(Order.items))
                .where(Order.id == order_id)
            )
            order = order_result.scalar_one_or_none()
            
            if not order:
                logger.warning(f"Order {order_id} not found")
                return None
            
            if order.status == "cancelled":
                logger.info(f"Order {order_id} already cancelled")
                return order
            
            # Restore ticket quantities for order items
            if hasattr(order, 'items') and order.items:
                for item in order.items:
                    await db.execute(
                        update(Ticket)
                        .where(Ticket.id == item.ticket_id)
                        .values(available_quantity=Ticket.available_quantity + item.quantity)
                    )
                    
                    # Get updated ticket info for notification
                    ticket_result = await db.execute(
                        select(Ticket).where(Ticket.id == item.ticket_id)
                    )
                    ticket = ticket_result.scalar_one_or_none()
                    
                    if ticket:
                        # Notify about ticket availability restoration
                        await notify_ticket_sold(
                            db=db,
                            event_id=order.event_id,
                            ticket_type_id=item.ticket_id,
                            quantity=-item.quantity,  # Negative quantity indicates restoration
                            remaining=ticket.available_quantity,
                            order_id=order_id
                        )
            
            # Update order status
            await db.execute(
                update(Order)
                .where(Order.id == order_id)
                .values(
                    status="cancelled",
                    cancelled_at=datetime.utcnow(),
                    cancellation_reason=cancellation_reason
                )
            )
            
            await db.commit()
            await db.refresh(order)
            
            # Send real-time notification
            await notify_order_status(
                order_id=order_id,
                status="cancelled",
                user_id=order.user_id,
                event_id=order.event_id,
                cancellation_reason=cancellation_reason,
                cancelled_at=datetime.utcnow().isoformat()
            )
            
            logger.info(f"Cancelled order {order_id} with notification")
            return order
            
        except Exception as e:
            await db.rollback()
            logger.error(f"Failed to cancel order with notification: {e}")
            raise
    
    @staticmethod
    async def get_live_order_stats(db: AsyncSession, event_id: int) -> Dict[str, Any]:
        """Get live order statistics for an event."""
        try:
            # Get order counts by status
            orders_result = await db.execute(
                select(Order).where(Order.event_id == event_id)
            )
            orders = orders_result.scalars().all()
            
            stats = {
                "total_orders": len(orders),
                "pending_orders": len([o for o in orders if o.status == "pending"]),
                "completed_orders": len([o for o in orders if o.status == "completed"]),
                "cancelled_orders": len([o for o in orders if o.status == "cancelled"]),
                "total_revenue": sum(float(o.total_amount) for o in orders if o.status == "completed"),
                "pending_revenue": sum(float(o.total_amount) for o in orders if o.status == "pending"),
                "updated_at": datetime.utcnow().isoformat()
            }
            
            return stats
            
        except Exception as e:
            logger.error(f"Failed to get live order stats: {e}")
            return {"error": "Failed to fetch order stats"}


# Integration functions for existing endpoints
async def integrate_order_realtime_notifications():
    """
    Integration helper to add real-time notifications to existing order endpoints.
    This can be called from existing order endpoints to add WebSocket support.
    """
    pass