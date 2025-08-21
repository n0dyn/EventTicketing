"""
WebSocket connection manager for real-time features.
Handles connection lifecycle, room management, and message broadcasting.
"""
from typing import Dict, List, Set, Optional, Any
import json
import logging
from datetime import datetime
from enum import Enum

from fastapi import WebSocket, WebSocketDisconnect
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User
from app.core.security import decode_access_token

logger = logging.getLogger(__name__)


class MessageType(str, Enum):
    """WebSocket message types for different real-time features."""
    
    # Connection management
    CONNECT = "connect"
    DISCONNECT = "disconnect"
    HEARTBEAT = "heartbeat"
    
    # Event updates
    EVENT_CREATED = "event_created"
    EVENT_UPDATED = "event_updated"
    EVENT_DELETED = "event_deleted"
    
    # Ticket updates
    TICKET_SOLD = "ticket_sold"
    TICKET_AVAILABILITY_CHANGED = "ticket_availability_changed"
    
    # Order updates
    ORDER_CREATED = "order_created"
    ORDER_UPDATED = "order_updated"
    ORDER_COMPLETED = "order_completed"
    ORDER_CANCELLED = "order_cancelled"
    
    # Live event features
    ATTENDEE_CHECKED_IN = "attendee_checked_in"
    LIVE_COUNT_UPDATE = "live_count_update"
    
    # Admin notifications
    ADMIN_NOTIFICATION = "admin_notification"
    SYSTEM_ALERT = "system_alert"
    
    # Chat/Comments (future feature)
    MESSAGE = "message"
    
    # Error handling
    ERROR = "error"


class WebSocketRoom:
    """Manages WebSocket connections for a specific room/topic."""
    
    def __init__(self, room_id: str, room_type: str):
        self.room_id = room_id
        self.room_type = room_type
        self.connections: Dict[str, WebSocket] = {}
        self.user_data: Dict[str, Dict[str, Any]] = {}
        self.created_at = datetime.utcnow()
    
    async def add_connection(self, connection_id: str, websocket: WebSocket, user_data: Optional[Dict] = None):
        """Add a WebSocket connection to this room."""
        self.connections[connection_id] = websocket
        if user_data:
            self.user_data[connection_id] = user_data
        
        logger.info(f"Added connection {connection_id} to room {self.room_id}")
    
    async def remove_connection(self, connection_id: str):
        """Remove a WebSocket connection from this room."""
        if connection_id in self.connections:
            del self.connections[connection_id]
        if connection_id in self.user_data:
            del self.user_data[connection_id]
        
        logger.info(f"Removed connection {connection_id} from room {self.room_id}")
    
    async def broadcast(self, message: Dict[str, Any], exclude: Optional[Set[str]] = None):
        """Broadcast a message to all connections in this room."""
        exclude = exclude or set()
        disconnected = []
        
        message_str = json.dumps(message)
        
        for connection_id, websocket in self.connections.items():
            if connection_id in exclude:
                continue
                
            try:
                await websocket.send_text(message_str)
            except Exception as e:
                logger.warning(f"Failed to send message to {connection_id}: {e}")
                disconnected.append(connection_id)
        
        # Remove disconnected connections
        for connection_id in disconnected:
            await self.remove_connection(connection_id)
    
    def get_connection_count(self) -> int:
        """Get the number of active connections in this room."""
        return len(self.connections)
    
    def get_user_list(self) -> List[Dict[str, Any]]:
        """Get list of users in this room."""
        return list(self.user_data.values())


class ConnectionManager:
    """Manages WebSocket connections, rooms, and message broadcasting."""
    
    def __init__(self):
        self.rooms: Dict[str, WebSocketRoom] = {}
        self.connections: Dict[str, Dict[str, Any]] = {}  # connection_id -> connection_info
    
    def _generate_connection_id(self, websocket: WebSocket) -> str:
        """Generate a unique connection ID."""
        return f"conn_{id(websocket)}_{datetime.utcnow().timestamp()}"
    
    def _get_room_id(self, room_type: str, resource_id: str) -> str:
        """Generate a room ID for a specific resource."""
        return f"{room_type}:{resource_id}"
    
    async def connect(
        self, 
        websocket: WebSocket, 
        room_type: str, 
        resource_id: str,
        user: Optional[User] = None
    ) -> str:
        """Accept WebSocket connection and add to appropriate room."""
        await websocket.accept()
        
        connection_id = self._generate_connection_id(websocket)
        room_id = self._get_room_id(room_type, resource_id)
        
        # Store connection info
        self.connections[connection_id] = {
            "websocket": websocket,
            "room_id": room_id,
            "user_id": user.id if user else None,
            "connected_at": datetime.utcnow(),
        }
        
        # Create room if it doesn't exist
        if room_id not in self.rooms:
            self.rooms[room_id] = WebSocketRoom(room_id, room_type)
        
        # Add connection to room
        user_data = None
        if user:
            user_data = {
                "user_id": user.id,
                "email": user.email,
                "full_name": user.full_name,
                "role": user.role,
            }
        
        await self.rooms[room_id].add_connection(connection_id, websocket, user_data)
        
        # Send connection confirmation
        await self._send_to_connection(connection_id, {
            "type": MessageType.CONNECT,
            "data": {
                "connection_id": connection_id,
                "room_id": room_id,
                "connected_at": datetime.utcnow().isoformat(),
                "user_count": self.rooms[room_id].get_connection_count(),
            }
        })
        
        logger.info(f"WebSocket connection established: {connection_id} in room {room_id}")
        return connection_id
    
    async def disconnect(self, connection_id: str):
        """Remove WebSocket connection."""
        if connection_id not in self.connections:
            return
        
        connection_info = self.connections[connection_id]
        room_id = connection_info["room_id"]
        
        # Remove from room
        if room_id in self.rooms:
            await self.rooms[room_id].remove_connection(connection_id)
            
            # Clean up empty rooms
            if self.rooms[room_id].get_connection_count() == 0:
                del self.rooms[room_id]
                logger.info(f"Removed empty room {room_id}")
        
        # Remove connection
        del self.connections[connection_id]
        
        logger.info(f"WebSocket connection disconnected: {connection_id}")
    
    async def _send_to_connection(self, connection_id: str, message: Dict[str, Any]):
        """Send message to a specific connection."""
        if connection_id not in self.connections:
            return False
        
        websocket = self.connections[connection_id]["websocket"]
        try:
            await websocket.send_text(json.dumps(message))
            return True
        except Exception as e:
            logger.warning(f"Failed to send message to {connection_id}: {e}")
            await self.disconnect(connection_id)
            return False
    
    async def broadcast_to_room(
        self, 
        room_type: str, 
        resource_id: str, 
        message: Dict[str, Any],
        exclude_connections: Optional[Set[str]] = None
    ):
        """Broadcast message to all connections in a specific room."""
        room_id = self._get_room_id(room_type, resource_id)
        
        if room_id not in self.rooms:
            logger.debug(f"No active room found: {room_id}")
            return
        
        await self.rooms[room_id].broadcast(message, exclude_connections)
    
    async def broadcast_to_user_rooms(self, user_id: int, message: Dict[str, Any]):
        """Broadcast message to all rooms where a specific user is connected."""
        user_connections = [
            conn_id for conn_id, conn_info in self.connections.items()
            if conn_info["user_id"] == user_id
        ]
        
        for connection_id in user_connections:
            await self._send_to_connection(connection_id, message)
    
    async def broadcast_to_admin_users(self, message: Dict[str, Any]):
        """Broadcast message to all admin/organizer users."""
        admin_connections = []
        
        for room in self.rooms.values():
            for connection_id, user_data in room.user_data.items():
                if user_data.get("role") in ["admin", "organizer"]:
                    admin_connections.append(connection_id)
        
        for connection_id in admin_connections:
            await self._send_to_connection(connection_id, message)
    
    def get_room_stats(self) -> Dict[str, Any]:
        """Get statistics about active rooms and connections."""
        stats = {
            "total_rooms": len(self.rooms),
            "total_connections": len(self.connections),
            "rooms": {}
        }
        
        for room_id, room in self.rooms.items():
            stats["rooms"][room_id] = {
                "connection_count": room.get_connection_count(),
                "room_type": room.room_type,
                "created_at": room.created_at.isoformat(),
            }
        
        return stats
    
    async def send_heartbeat(self):
        """Send heartbeat to all connections to keep them alive."""
        message = {
            "type": MessageType.HEARTBEAT,
            "data": {"timestamp": datetime.utcnow().isoformat()}
        }
        
        disconnected = []
        for connection_id in self.connections.keys():
            success = await self._send_to_connection(connection_id, message)
            if not success:
                disconnected.append(connection_id)
        
        # Clean up disconnected connections
        for connection_id in disconnected:
            await self.disconnect(connection_id)


# Global connection manager instance
manager = ConnectionManager()


async def authenticate_websocket(websocket: WebSocket, token: str) -> Optional[User]:
    """Authenticate WebSocket connection using JWT token."""
    try:
        payload = decode_access_token(token)
        if payload is None:
            await websocket.close(code=4001, reason="Invalid token")
            return None
        
        # In a real implementation, you would fetch the user from the database
        # For now, we'll create a mock user from the token payload
        user = User(
            id=payload.get("sub"),
            email=payload.get("email", ""),
            full_name=payload.get("full_name", ""),
            role=payload.get("role", "user"),
        )
        
        return user
    except Exception as e:
        logger.warning(f"WebSocket authentication failed: {e}")
        await websocket.close(code=4001, reason="Authentication failed")
        return None


def create_message(message_type: MessageType, data: Dict[str, Any]) -> Dict[str, Any]:
    """Create a standardized WebSocket message."""
    return {
        "type": message_type,
        "data": data,
        "timestamp": datetime.utcnow().isoformat(),
    }