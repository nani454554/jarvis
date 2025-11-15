# """
# Advanced WebSocket Connection Manager
# Supports rooms, broadcasting, and connection lifecycle management
# """
# from typing import Dict, List, Set, Optional
# from fastapi import WebSocket, WebSocketDisconnect
# from collections import defaultdict
# import json
# import logging
# from datetime import datetime
# import asyncio

# logger = logging.getLogger(__name__)

# class ConnectionManager:
#     """
#     Advanced WebSocket connection manager
#     Manages multiple connections, rooms, and broadcasting
#     """
    
#     def __init__(self):
#         # Active connections: connection_id -> WebSocket
#         self.active_connections: Dict[str, WebSocket] = {}
        
#         # Rooms: room_name -> Set[connection_id]
#         self.rooms: Dict[str, Set[str]] = defaultdict(set)
        
#         # User mappings: user_id -> connection_id
#         self.user_connections: Dict[str, str] = {}
        
#         # Connection metadata
#         self.connection_metadata: Dict[str, dict] = {}
    
#     async def connect(
#         self,
#         websocket: WebSocket,
#         connection_id: str,
#         user_id: Optional[str] = None,
#         metadata: Optional[dict] = None
#     ):
#         """
#         Accept new WebSocket connection
        
#         Args:
#             websocket: WebSocket instance
#             connection_id: Unique connection identifier
#             user_id: Optional user identifier
#             metadata: Optional connection metadata
#         """
#         await websocket.accept()
        
#         self.active_connections[connection_id] = websocket
        
#         if user_id:
#             self.user_connections[user_id] = connection_id
        
#         if metadata:
#             self.connection_metadata[connection_id] = metadata
        
#         logger.info(
#             f"✅ WebSocket connected: {connection_id} "
#             f"(user: {user_id}, total: {len(self.active_connections)})"
#         )
    
#     def disconnect(self, connection_id: str):
#         """
#         Remove WebSocket connection
        
#         Args:
#             connection_id: Connection identifier to remove
#         """
#         # Remove connection
#         if connection_id in self.active_connections:
#             del self.active_connections[connection_id]
        
#         # Remove from all rooms
#         for room_connections in self.rooms.values():
#             room_connections.discard(connection_id)
        
#         # Remove user mapping
#         user_id = next(
#             (uid for uid, cid in self.user_connections.items() if cid == connection_id),
#             None
#         )
#         if user_id:
#             del self.user_connections[user_id]
        
#         # Remove metadata
#         if connection_id in self.connection_metadata:
#             del self.connection_metadata[connection_id]
        
#         logger.info(
#             f"❌ WebSocket disconnected: {connection_id} "
#             f"(remaining: {len(self.active_connections)})"
#         )
    
#     async def send_message(
#         self,
#         connection_id: str,
#         message: dict
#     ):
#         """
#         Send message to specific connection
        
#         Args:
#             connection_id: Target connection ID
#             message: Message dictionary to send
#         """
#         websocket = self.active_connections.get(connection_id)
#         if websocket:
#             try:
#                 await websocket.send_json({
#                     **message,
#                     "timestamp": datetime.utcnow().isoformat()
#                 })
#             except Exception as e:
#                 logger.error(f"Error sending to {connection_id}: {e}")
#                 self.disconnect(connection_id)
    
#     async def send_to_user(
#         self,
#         user_id: str,
#         message: dict
#     ):
#         """
#         Send message to user by user_id
        
#         Args:
#             user_id: User identifier
#             message: Message to send
#         """
#         connection_id = self.user_connections.get(user_id)
#         if connection_id:
#             await self.send_message(connection_id, message)
    
#     async def broadcast(
#         self,
#         message: dict,
#         exclude: Optional[Set[str]] = None
#     ):
#         """
#         Broadcast message to all connections
        
#         Args:
#             message: Message to broadcast
#             exclude: Set of connection IDs to exclude
#         """
#         exclude = exclude or set()
#         disconnected = []
        
#         message_with_timestamp = {
#             **message,
#             "timestamp": datetime.utcnow().isoformat()
#         }
        
#         for connection_id, websocket in self.active_connections.items():
#             if connection_id not in exclude:
#                 try:
#                     await websocket.send_json(message_with_timestamp)
#                 except Exception as e:
#                     logger.error(f"Broadcast error to {connection_id}: {e}")
#                     disconnected.append(connection_id)
        
#         # Clean up failed connections
#         for connection_id in disconnected:
#             self.disconnect(connection_id)
    
#     async def join_room(self, connection_id: str, room: str):
#         """
#         Add connection to a room
        
#         Args:
#             connection_id: Connection identifier
#             room: Room name
#         """
#         if connection_id in self.active_connections:
#             self.rooms[room].add(connection_id)
#             logger.debug(f"Connection {connection_id} joined room {room}")
    
#     async def leave_room(self, connection_id: str, room: str):
#         """
#         Remove connection from a room
        
#         Args:
#             connection_id: Connection identifier
#             room: Room name
#         """
#         if room in self.rooms:
#             self.rooms[room].discard(connection_id)
#             logger.debug(f"Connection {connection_id} left room {room}")
    
#     async def send_to_room(
#         self,
#         room: str,
#         message: dict,
#         exclude: Optional[Set[str]] = None
#     ):
#         """
#         Send message to all connections in a room
        
#         Args:
#             room: Room name
#             message: Message to send
#             exclude: Set of connection IDs to exclude
#         """
#         exclude = exclude or set()
#         room_connections = self.rooms.get(room, set())
        
#         message_with_timestamp = {
#             **message,
#             "timestamp": datetime.utcnow().isoformat()
#         }
        
#         for connection_id in room_connections:
#             if connection_id not in exclude:
#                 await self.send_message(connection_id, message_with_timestamp)
    
#     def get_room_members(self, room: str) -> List[str]:
#         """
#         Get all connection IDs in a room
        
#         Args:
#             room: Room name
            
#         Returns:
#             List of connection IDs
#         """
#         return list(self.rooms.get(room, set()))
    
#     def get_connection_count(self) -> int:
#         """
#         Get total active connections
        
#         Returns:
#             Number of active connections
#         """
#         return len(self.active_connections)
    
#     def get_room_count(self) -> int:
#         """
#         Get total number of active rooms
        
#         Returns:
#             Number of rooms with at least one member
#         """
#         return len([r for r in self.rooms.values() if r])
    
#     def get_connection_info(self, connection_id: str) -> Optional[dict]:
#         """
#         Get connection metadata
        
#         Args:
#             connection_id: Connection identifier
            
#         Returns:
#             Connection metadata or None
#         """
#         return self.connection_metadata.get(connection_id)
    
#     async def close_all(self):
#         """
#         Close all active connections
#         """
#         for connection_id in list(self.active_connections.keys()):
#             try:
#                 await self.active_connections[connection_id].close()
#             except:
#                 pass
#             self.disconnect(connection_id)
        
#         logger.info("All WebSocket connections closed")

# # Global connection manager
# manager = ConnectionManager()

"""
WebSocket connection manager for real-time communication.
"""

from typing import Dict, List, Optional
from fastapi import WebSocket, WebSocketDisconnect
from loguru import logger
import json
import asyncio
from datetime import datetime


class ConnectionManager:
    """Manage WebSocket connections."""
    
    def __init__(self):
        self.active_connections: Dict[str, WebSocket] = {}
        self.user_connections: Dict[str, List[str]] = {}
    
    async def connect(self, websocket: WebSocket, client_id: str, user_id: Optional[str] = None):
        """Accept new WebSocket connection."""
        await websocket.accept()
        self.active_connections[client_id] = websocket
        
        if user_id:
            if user_id not in self.user_connections:
                self.user_connections[user_id] = []
            self.user_connections[user_id].append(client_id)
        
        logger.info(f"WebSocket connected: {client_id} (user: {user_id})")
        
        # Send welcome message
        await self.send_personal_message(
            {
                "type": "connection",
                "status": "connected",
                "client_id": client_id,
                "timestamp": datetime.utcnow().isoformat()
            },
            client_id
        )
    
    def disconnect(self, client_id: str, user_id: Optional[str] = None):
        """Remove WebSocket connection."""
        if client_id in self.active_connections:
            del self.active_connections[client_id]
        
        if user_id and user_id in self.user_connections:
            self.user_connections[user_id] = [
                cid for cid in self.user_connections[user_id] if cid != client_id
            ]
            if not self.user_connections[user_id]:
                del self.user_connections[user_id]
        
        logger.info(f"WebSocket disconnected: {client_id}")
    
    async def send_personal_message(self, message: dict, client_id: str):
        """Send message to specific client."""
        if client_id in self.active_connections:
            try:
                await self.active_connections[client_id].send_json(message)
            except Exception as e:
                logger.error(f"Error sending message to {client_id}: {e}")
                self.disconnect(client_id)
    
    async def send_to_user(self, message: dict, user_id: str):
        """Send message to all connections of a user."""
        if user_id in self.user_connections:
            for client_id in self.user_connections[user_id]:
                await self.send_personal_message(message, client_id)
    
    async def broadcast(self, message: dict, exclude: Optional[List[str]] = None):
        """Broadcast message to all connected clients."""
        exclude = exclude or []
        disconnected = []
        
        for client_id, websocket in self.active_connections.items():
            if client_id not in exclude:
                try:
                    await websocket.send_json(message)
                except Exception as e:
                    logger.error(f"Error broadcasting to {client_id}: {e}")
                    disconnected.append(client_id)
        
        # Clean up disconnected clients
        for client_id in disconnected:
            self.disconnect(client_id)
    
    async def send_voice_stream(self, audio_data: bytes, client_id: str):
        """Send audio stream data."""
        if client_id in self.active_connections:
            try:
                await self.active_connections[client_id].send_bytes(audio_data)
            except Exception as e:
                logger.error(f"Error sending audio to {client_id}: {e}")
    
    async def send_status_update(self, status: str, message: str, client_id: str):
        """Send status update to client."""
        await self.send_personal_message(
            {
                "type": "status",
                "status": status,
                "message": message,
                "timestamp": datetime.utcnow().isoformat()
            },
            client_id
        )
    
    async def send_thinking_indicator(self, client_id: str, thinking: bool = True):
        """Send thinking indicator."""
        await self.send_personal_message(
            {
                "type": "thinking",
                "thinking": thinking,
                "timestamp": datetime.utcnow().isoformat()
            },
            client_id
        )
    
    async def send_error(self, error: str, client_id: str):
        """Send error message."""
        await self.send_personal_message(
            {
                "type": "error",
                "error": error,
                "timestamp": datetime.utcnow().isoformat()
            },
            client_id
        )
    
    def get_active_connections_count(self) -> int:
        """Get count of active connections."""
        return len(self.active_connections)
    
    def get_user_connections_count(self, user_id: str) -> int:
        """Get count of connections for a user."""
        return len(self.user_connections.get(user_id, []))


# Global connection manager instance
manager = ConnectionManager()
