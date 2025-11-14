"""
Advanced WebSocket Connection Manager
With room support, broadcasting, and connection management
"""
from typing import Dict, List, Set
from fastapi import WebSocket, WebSocketDisconnect
from collections import defaultdict
import json
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

class ConnectionManager:
    """Advanced WebSocket connection manager"""
    
    def __init__(self):
        self.active_connections: Dict[str, WebSocket] = {}
        self.rooms: Dict[str, Set[str]] = defaultdict(set)
        self.user_connections: Dict[str, str] = {}  # user_id -> connection_id
    
    async def connect(
        self,
        websocket: WebSocket,
        connection_id: str,
        user_id: Optional[str] = None
    ):
        """Accept new WebSocket connection"""
        await websocket.accept()
        self.active_connections[connection_id] = websocket
        
        if user_id:
            self.user_connections[user_id] = connection_id
        
        logger.info(
            f"✅ WebSocket connected: {connection_id} "
            f"(user: {user_id}, total: {len(self.active_connections)})"
        )
    
    def disconnect(self, connection_id: str):
        """Remove WebSocket connection"""
        if connection_id in self.active_connections:
            del self.active_connections[connection_id]
        
        # Remove from all rooms
        for room_connections in self.rooms.values():
            room_connections.discard(connection_id)
        
        # Remove user mapping
        user_id = next(
            (uid for uid, cid in self.user_connections.items() if cid == connection_id),
            None
        )
        if user_id:
            del self.user_connections[user_id]
        
        logger.info(
            f"❌ WebSocket disconnected: {connection_id} "
            f"(remaining: {len(self.active_connections)})"
        )
    
    async def send_message(
        self,
        connection_id: str,
        message: dict
    ):
        """Send message to specific connection"""
        websocket = self.active_connections.get(connection_id)
        if websocket:
            try:
                await websocket.send_json({
                    **message,
                    "timestamp": datetime.utcnow().isoformat()
                })
            except Exception as e:
                logger.error(f"Error sending to {connection_id}: {e}")
                self.disconnect(connection_id)
    
    async def send_to_user(
        self,
        user_id: str,
        message: dict
    ):
        """Send message to user by user_id"""
        connection_id = self.user_connections.get(user_id)
        if connection_id:
            await self.send_message(connection_id, message)
    
    async def broadcast(
        self,
        message: dict,
        exclude: Optional[Set[str]] = None
    ):
        """Broadcast message to all connections"""
        exclude = exclude or set()
        disconnected = []
        
        for connection_id, websocket in self.active_connections.items():
            if connection_id not in exclude:
                try:
                    await websocket.send_json({
                        **message,
                        "timestamp": datetime.utcnow().isoformat()
                    })
                except Exception as e:
                    logger.error(f"Broadcast error to {connection_id}: {e}")
                    disconnected.append(connection_id)
        
        # Clean up failed connections
        for connection_id in disconnected:
            self.disconnect(connection_id)
    
    async def join_room(self, connection_id: str, room: str):
        """Add connection to a room"""
        if connection_id in self.active_connections:
            self.rooms[room].add(connection_id)
            logger.debug(f"Connection {connection_id} joined room {room}")
    
    async def leave_room(self, connection_id: str, room: str):
        """Remove connection from a room"""
        if room in self.rooms:
            self.rooms[room].discard(connection_id)
            logger.debug(f"Connection {connection_id} left room {room}")
    
    async def send_to_room(
        self,
        room: str,
        message: dict,
        exclude: Optional[Set[str]] = None
    ):
        """Send message to all connections in a room"""
        exclude = exclude or set()
        room_connections = self.rooms.get(room, set())
        
        for connection_id in room_connections:
            if connection_id not in exclude:
                await self.send_message(connection_id, message)
    
    def get_room_members(self, room: str) -> List[str]:
        """Get all connection IDs in a room"""
        return list(self.rooms.get(room, set()))
    
    def get_connection_count(self) -> int:
        """Get total active connections"""
        return len(self.active_connections)
    
    def get_room_count(self) -> int:
        """Get total number of rooms"""
        return len([r for r in self.rooms.values() if r])

# Global connection manager
manager = ConnectionManager()
