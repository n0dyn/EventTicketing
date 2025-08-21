"""
WebSocket endpoints for real-time features.
Handles different types of real-time connections and data streams.
"""
from typing import Optional
import asyncio
import logging

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.websocket import manager, authenticate_websocket, MessageType, create_message
from app.api import deps
from app.models.user import User

logger = logging.getLogger(__name__)
router = APIRouter()


@router.websocket("/events/{event_id}")
async def websocket_event_updates(
    websocket: WebSocket,
    event_id: int,
    token: Optional[str] = Query(None),
):
    """
    WebSocket endpoint for real-time event updates.
    
    Provides live updates for:
    - Ticket sales
    - Availability changes
    - Event modifications
    - Attendee check-ins
    """
    user = None
    if token:
        user = await authenticate_websocket(websocket, token)
        if user is None:
            return
    
    connection_id = None
    try:
        connection_id = await manager.connect(
            websocket=websocket,
            room_type="event",
            resource_id=str(event_id),
            user=user
        )
        
        # Send initial event data if user is authenticated
        if user:
            await websocket.send_text(create_message(
                MessageType.EVENT_UPDATED,
                {
                    "event_id": event_id,
                    "message": "Connected to event updates",
                    "user_role": user.role if user else "anonymous"
                }
            ))
        
        # Keep connection alive
        while True:
            try:
                # Wait for incoming messages (heartbeat, etc.)
                data = await websocket.receive_text()
                logger.debug(f"Received WebSocket message: {data}")
                
                # Handle client messages if needed
                # For now, we just acknowledge receipt
                await websocket.send_text(create_message(
                    MessageType.HEARTBEAT,
                    {"status": "acknowledged"}
                ))
                
            except asyncio.TimeoutError:
                # Send periodic heartbeat
                await websocket.send_text(create_message(
                    MessageType.HEARTBEAT,
                    {"status": "alive"}
                ))
                
    except WebSocketDisconnect:
        logger.info(f"WebSocket disconnected for event {event_id}")
    except Exception as e:
        logger.error(f"WebSocket error for event {event_id}: {e}")
    finally:
        if connection_id:
            await manager.disconnect(connection_id)


@router.websocket("/orders/{order_id}")
async def websocket_order_updates(
    websocket: WebSocket,
    order_id: int,
    token: str = Query(...),  # Order updates require authentication
):
    """
    WebSocket endpoint for real-time order updates.
    
    Provides live updates for:
    - Order status changes
    - Payment processing
    - Ticket delivery
    """
    user = await authenticate_websocket(websocket, token)
    if user is None:
        return
    
    connection_id = None
    try:
        connection_id = await manager.connect(
            websocket=websocket,
            room_type="order",
            resource_id=str(order_id),
            user=user
        )
        
        # Send initial connection confirmation
        await websocket.send_text(create_message(
            MessageType.ORDER_UPDATED,
            {
                "order_id": order_id,
                "message": "Connected to order updates",
                "user_id": user.id
            }
        ))
        
        # Keep connection alive
        while True:
            try:
                data = await websocket.receive_text()
                logger.debug(f"Received order WebSocket message: {data}")
                
            except asyncio.TimeoutError:
                await websocket.send_text(create_message(
                    MessageType.HEARTBEAT,
                    {"order_id": order_id, "status": "monitoring"}
                ))
                
    except WebSocketDisconnect:
        logger.info(f"WebSocket disconnected for order {order_id}")
    except Exception as e:
        logger.error(f"WebSocket error for order {order_id}: {e}")
    finally:
        if connection_id:
            await manager.disconnect(connection_id)


@router.websocket("/admin/dashboard")
async def websocket_admin_dashboard(
    websocket: WebSocket,
    token: str = Query(...),  # Admin dashboard requires authentication
):
    """
    WebSocket endpoint for real-time admin dashboard updates.
    
    Provides live updates for:
    - System notifications
    - User activity
    - Sales metrics
    - Security alerts
    """
    user = await authenticate_websocket(websocket, token)
    if user is None or user.role not in ["admin", "organizer"]:
        await websocket.close(code=4003, reason="Insufficient permissions")
        return
    
    connection_id = None
    try:
        connection_id = await manager.connect(
            websocket=websocket,
            room_type="admin",
            resource_id="dashboard",
            user=user
        )
        
        # Send initial dashboard data
        await websocket.send_text(create_message(
            MessageType.ADMIN_NOTIFICATION,
            {
                "message": "Connected to admin dashboard",
                "user_id": user.id,
                "role": user.role,
                "permissions": ["dashboard", "notifications"]
            }
        ))
        
        # Keep connection alive and handle admin-specific messages
        while True:
            try:
                data = await websocket.receive_text()
                logger.debug(f"Received admin WebSocket message: {data}")
                
                # Admin users can send commands or requests
                # Handle admin-specific WebSocket commands here
                
            except asyncio.TimeoutError:
                await websocket.send_text(create_message(
                    MessageType.HEARTBEAT,
                    {"dashboard": "active", "role": user.role}
                ))
                
    except WebSocketDisconnect:
        logger.info(f"Admin WebSocket disconnected: {user.email}")
    except Exception as e:
        logger.error(f"Admin WebSocket error: {e}")
    finally:
        if connection_id:
            await manager.disconnect(connection_id)


@router.websocket("/live-events/{event_id}")
async def websocket_live_event(
    websocket: WebSocket,
    event_id: int,
    token: Optional[str] = Query(None),
):
    """
    WebSocket endpoint for live event features.
    
    Provides real-time updates for:
    - Attendee check-ins
    - Live attendance count
    - Event announcements
    - Interactive features
    """
    user = None
    if token:
        user = await authenticate_websocket(websocket, token)
        if user is None:
            return
    
    connection_id = None
    try:
        connection_id = await manager.connect(
            websocket=websocket,
            room_type="live_event",
            resource_id=str(event_id),
            user=user
        )
        
        # Send current live stats
        await websocket.send_text(create_message(
            MessageType.LIVE_COUNT_UPDATE,
            {
                "event_id": event_id,
                "message": "Connected to live event updates",
                "live_attendees": 0,  # Would fetch from database
                "total_checked_in": 0,  # Would fetch from database
            }
        ))
        
        # Keep connection alive
        while True:
            try:
                data = await websocket.receive_text()
                logger.debug(f"Received live event message: {data}")
                
                # Handle live event interactions
                # Could include voting, Q&A, etc.
                
            except asyncio.TimeoutError:
                await websocket.send_text(create_message(
                    MessageType.HEARTBEAT,
                    {"event_id": event_id, "status": "live"}
                ))
                
    except WebSocketDisconnect:
        logger.info(f"Live event WebSocket disconnected for event {event_id}")
    except Exception as e:
        logger.error(f"Live event WebSocket error: {e}")
    finally:
        if connection_id:
            await manager.disconnect(connection_id)


@router.get("/stats")
async def get_websocket_stats(current_user: User = Depends(deps.get_current_admin)):
    """
    Get WebSocket connection statistics.
    Admin-only endpoint for monitoring real-time connections.
    """
    return manager.get_room_stats()


# Background task to send periodic heartbeats
async def heartbeat_task():
    """Background task to send periodic heartbeats to all connections."""
    while True:
        try:
            await manager.send_heartbeat()
            await asyncio.sleep(30)  # Send heartbeat every 30 seconds
        except Exception as e:
            logger.error(f"Heartbeat task error: {e}")
            await asyncio.sleep(5)  # Wait before retrying


# Start heartbeat task when the module is imported
# asyncio.create_task(heartbeat_task())