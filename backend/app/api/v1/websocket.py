"""
WebSocket API Route
Real-time bidirectional communication handler
"""
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query
from typing import Optional
import json
import uuid
import logging
from datetime import datetime

from app.core.websocket import manager
from app.core.security import security_manager
from app.dependencies import get_voice_service, get_vision_service, get_brain_service

logger = logging.getLogger(__name__)
router = APIRouter()

@router.websocket("/connect")
async def websocket_endpoint(
    websocket: WebSocket,
    token: Optional[str] = Query(None)
):
    """
    Main WebSocket endpoint for real-time communication
    
    Features:
    - Voice commands
    - Camera feed processing
    - Real-time responses
    - System updates
    - Bidirectional streaming
    
    Args:
        websocket: WebSocket connection
        token: Optional JWT token for authentication
    """
    connection_id = str(uuid.uuid4())
    user_id = None
    username = "guest"
    
    try:
        # Validate token if provided
        if token:
            try:
                payload = security_manager.decode_token(token)
                user_id = payload.get("sub")
                username = payload.get("username", "user")
            except Exception as e:
                logger.warning(f"Invalid token in WebSocket: {e}")
        
        # Accept connection
        await manager.connect(
            websocket,
            connection_id,
            user_id,
            metadata={
                "username": username,
                "connected_at": datetime.utcnow().isoformat()
            }
        )
        
        # Send welcome message
        await manager.send_message(connection_id, {
            "type": "system",
            "event": "connected",
            "message": "Connection established. J.A.R.V.I.S. online.",
            "connection_id": connection_id,
            "username": username
        })
        
        # Join default room
        await manager.join_room(connection_id, "main")
        
        # Get services (lazy loading)
        voice_service = None
        vision_service = None
        brain_service = None
        
        try:
            from app.main import app
            if hasattr(app.state, "voice_service"):
                voice_service = app.state.voice_service
            if hasattr(app.state, "vision_service"):
                vision_service = app.state.vision_service
            if hasattr(app.state, "brain_service"):
                brain_service = app.state.brain_service
        except:
            pass
        
        # Message handling loop
        while True:
            # Receive message
            data = await websocket.receive_json()
            message_type = data.get("type")
            
            logger.debug(f"WebSocket [{connection_id}] received: {message_type}")
            
            # Handle different message types
            if message_type == "ping":
                await manager.send_message(connection_id, {
                    "type": "pong",
                    "timestamp": datetime.utcnow().isoformat()
                })
            
            elif message_type == "voice_command":
                await handle_voice_command(
                    connection_id,
                    data,
                    user_id,
                    brain_service,
                    voice_service
                )
            
            elif message_type == "camera_frame":
                await handle_camera_frame(
                    connection_id,
                    data,
                    vision_service
                )
            
            elif message_type == "audio_chunk":
                await handle_audio_chunk(
                    connection_id,
                    data,
                    voice_service,
                    brain_service,
                    user_id
                )
            
            elif message_type == "join_room":
                room = data.get("room", "main")
                await manager.join_room(connection_id, room)
                await manager.send_message(connection_id, {
                    "type": "room_joined",
                    "room": room
                })
            
            elif message_type == "leave_room":
                room = data.get("room")
                if room:
                    await manager.leave_room(connection_id, room)
                    await manager.send_message(connection_id, {
                        "type": "room_left",
                        "room": room
                    })
            
            elif message_type == "broadcast":
                # Broadcast to room
                room = data.get("room", "main")
                message = data.get("message", {})
                await manager.send_to_room(room, {
                    "type": "broadcast",
                    "from": username,
                    "message": message
                })
            
            else:
                logger.warning(f"Unknown message type: {message_type}")
                await manager.send_message(connection_id, {
                    "type": "error",
                    "message": f"Unknown message type: {message_type}"
                })
    
    except WebSocketDisconnect:
        logger.info(f"WebSocket disconnected: {connection_id}")
        manager.disconnect(connection_id)
    
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        try:
            await manager.send_message(connection_id, {
                "type": "error",
                "message": "An error occurred",
                "details": str(e) if logger.level == logging.DEBUG else None
            })
        except:
            pass
        manager.disconnect(connection_id)

async def handle_voice_command(
    connection_id: str,
    data: dict,
    user_id: Optional[str],
    brain_service,
    voice_service
):
    """Handle voice command from WebSocket"""
    try:
        text = data.get("text", "")
        
        if not text:
            await manager.send_message(connection_id, {
                "type": "error",
                "message": "Empty command"
            })
            return
        
        # Process with brain
        if brain_service:
            result = await brain_service.process_command(
                text=text,
                user_id=user_id or "anonymous",
                context=data.get("context")
            )
            
            # Generate speech if voice service available
            audio_data = None
            if voice_service:
                try:
                    audio_bytes = await voice_service.text_to_speech(result["text"])
                    if audio_bytes:
                        import base64
                        audio_data = base64.b64encode(audio_bytes).decode()
                except Exception as e:
                    logger.error(f"TTS error: {e}")
            
            # Send response
            await manager.send_message(connection_id, {
                "type": "voice_response",
                "text": result["text"],
                "intent": result["intent"],
                "audio": audio_data,
                "actions": result.get("actions", []),
                "confidence": result["confidence"]
            })
        else:
            await manager.send_message(connection_id, {
                "type": "voice_response",
                "text": "Brain service not available. Running in limited mode.",
                "intent": "system_message"
            })
        
    except Exception as e:
        logger.error(f"Voice command error: {e}")
        await manager.send_message(connection_id, {
            "type": "error",
            "message": "Failed to process voice command",
            "details": str(e)
        })

async def handle_camera_frame(
    connection_id: str,
    data: dict,
    vision_service
):
    """Handle camera frame from WebSocket"""
    try:
        frame_data = data.get("frame")
        
        if not frame_data or not vision_service:
            return
        
        # Decode base64 image
        import base64
        if isinstance(frame_data, str) and 'base64,' in frame_data:
            frame_data = frame_data.split('base64,')[1]
        
        image_bytes = base64.b64decode(frame_data)
        
        # Detect faces
        faces = await vision_service.detect_faces(image_bytes)
        
        # Recognize faces if detected
        recognition_results = []
        if faces:
            for face in faces[:3]:  # Limit to 3 faces for performance
                recognition = await vision_service.recognize_face(
                    image_bytes,
                    bbox=face["bbox"]
                )
                recognition_results.append(recognition)
        
        # Detect emotion
        emotion = None
        if faces:
            emotion = await vision_service.detect_emotion(image_bytes)
        
        # Send results
        await manager.send_message(connection_id, {
            "type": "vision_update",
            "faces": faces,
            "recognition": recognition_results,
            "emotion": emotion,
            "timestamp": datetime.utcnow().isoformat()
        })
        
    except Exception as e:
        logger.error(f"Camera frame error: {e}")

async def handle_audio_chunk(
    connection_id: str,
    data: dict,
    voice_service,
    brain_service,
    user_id: Optional[str]
):
    """Handle audio chunk for real-time STT"""
    try:
        audio_data = data.get("audio")
        is_final = data.get("is_final", False)
        
        if not audio_data or not voice_service:
            return
        
        # Decode base64 audio
        import base64
        audio_bytes = base64.b64decode(audio_data)
        
        # Transcribe
        result = await voice_service.speech_to_text(audio_bytes)
        
        # Send transcription
        await manager.send_message(connection_id, {
            "type": "transcription",
            "text": result["text"],
            "is_final": is_final,
            "confidence": result["confidence"]
        })
        
        # If final, process as command
        if is_final and result["text"].strip():
            await handle_voice_command(
                connection_id,
                {"text": result["text"]},
                user_id,
                brain_service,
                voice_service
            )
        
    except Exception as e:
        logger.error(f"Audio chunk error: {e}")
