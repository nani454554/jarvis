# """
# Event System
# Pub/Sub event handling for decoupled communication
# """
# from typing import Callable, Dict, List, Any
# import asyncio
# import logging
# from datetime import datetime

# logger = logging.getLogger(__name__)

# class EventSystem:
#     """
#     Simple event system for pub/sub pattern
#     Allows decoupled communication between components
#     """
    
#     def __init__(self):
#         # Event handlers: event_name -> List[callable]
#         self._handlers: Dict[str, List[Callable]] = {}
        
#         # Event history (for debugging)
#         self._event_history: List[dict] = []
#         self._max_history = 100
    
#     def subscribe(self, event_name: str, handler: Callable):
#         """
#         Subscribe to an event
        
#         Args:
#             event_name: Name of event to subscribe to
#             handler: Callback function to handle event
#         """
#         if event_name not in self._handlers:
#             self._handlers[event_name] = []
        
#         self._handlers[event_name].append(handler)
#         logger.debug(f"Subscribed to event: {event_name}")
    
#     def unsubscribe(self, event_name: str, handler: Callable):
#         """
#         Unsubscribe from an event
        
#         Args:
#             event_name: Name of event
#             handler: Handler to remove
#         """
#         if event_name in self._handlers:
#             try:
#                 self._handlers[event_name].remove(handler)
#                 logger.debug(f"Unsubscribed from event: {event_name}")
#             except ValueError:
#                 pass
    
#     async def publish(self, event_name: str, data: Any = None):
#         """
#         Publish an event
        
#         Args:
#             event_name: Name of event to publish
#             data: Event data
#         """
#         # Record event
#         event_record = {
#             "event": event_name,
#             "data": data,
#             "timestamp": datetime.utcnow().isoformat()
#         }
        
#         self._event_history.append(event_record)
        
#         # Keep history size manageable
#         if len(self._event_history) > self._max_history:
#             self._event_history.pop(0)
        
#         # Call all handlers
#         handlers = self._handlers.get(event_name, [])
        
#         for handler in handlers:
#             try:
#                 if asyncio.iscoroutinefunction(handler):
#                     await handler(data)
#                 else:
#                     handler(data)
#             except Exception as e:
#                 logger.error(f"Error in event handler for {event_name}: {e}")
    
#     def get_subscribers(self, event_name: str) -> int:
#         """
#         Get number of subscribers for an event
        
#         Args:
#             event_name: Event name
            
#         Returns:
#             Number of subscribers
#         """
#         return len(self._handlers.get(event_name, []))
    
#     def get_event_history(self, limit: int = 10) -> List[dict]:
#         """
#         Get recent event history
        
#         Args:
#             limit: Maximum number of events to return
            
#         Returns:
#             List of recent events
#         """
#         return self._event_history[-limit:]
    
#     def clear_history(self):
#         """Clear event history"""
#         self._event_history.clear()

# # Global event system
# events = EventSystem()

# # Common event names
# class Events:
#     """Event name constants"""
#     USER_REGISTERED = "user.registered"
#     USER_LOGIN = "user.login"
#     USER_LOGOUT = "user.logout"
    
#     VOICE_COMMAND_RECEIVED = "voice.command_received"
#     VOICE_RESPONSE_GENERATED = "voice.response_generated"
    
#     FACE_DETECTED = "vision.face_detected"
#     FACE_RECOGNIZED = "vision.face_recognized"
#     EMOTION_DETECTED = "vision.emotion_detected"
    
#     BRAIN_PROCESSING_START = "brain.processing_start"
#     BRAIN_PROCESSING_COMPLETE = "brain.processing_complete"
    
#     SKILL_ACTIVATED = "skill.activated"
#     SKILL_DEACTIVATED = "skill.deactivated"
    
#     SYSTEM_ERROR = "system.error"
#     SYSTEM_WARNING = "system.warning"


"""
Application startup and shutdown events.
Initialize and cleanup resources.
"""

from loguru import logger

from app.core.database import init_db, close_db, get_redis
from app.core.config import settings


async def startup_event():
    """
    Execute on application startup.
    Initialize database, cache, AI models, etc.
    """
    logger.info("=" * 60)
    logger.info("🚀 Starting JARVIS-IRON Backend")
    logger.info("=" * 60)
    
    # Initialize database
    try:
        await init_db()
        logger.info("✅ Database initialized")
    except Exception as e:
        logger.error(f"❌ Database initialization failed: {e}")
    
    # Check Redis connection
    try:
        redis = get_redis()
        redis.ping()
        logger.info("✅ Redis connected")
    except Exception as e:
        logger.error(f"❌ Redis connection failed: {e}")
    
    # Load AI models (async)
    try:
        from app.ai.llm.openai_client import OpenAIClient
        if settings.OPENAI_API_KEY:
            openai_client = OpenAIClient()
            logger.info("✅ OpenAI client initialized")
    except Exception as e:
        logger.warning(f"⚠️ OpenAI initialization skipped: {e}")
    
    # Load embedding model
    try:
        if settings.EMBEDDING_MODEL:
            from app.ai.rag.embeddings import EmbeddingService
            embedding_service = EmbeddingService()
            logger.info(f"✅ Embedding model loaded: {settings.EMBEDDING_MODEL}")
    except Exception as e:
        logger.warning(f"⚠️ Embedding model loading failed: {e}")
    
    # Load face recognition models
    try:
        if settings.FEATURE_VISION_ENABLED:
            import face_recognition
            logger.info("✅ Face recognition library loaded")
    except Exception as e:
        logger.warning(f"⚠️ Face recognition not available: {e}")
    
    # Load voice models
    try:
        if settings.FEATURE_VOICE_ENABLED and settings.STT_PROVIDER == "openai-whisper":
            import whisper
            logger.info("✅ Whisper STT available")
    except Exception as e:
        logger.warning(f"⚠️ Whisper STT not available: {e}")
    
    # Create necessary directories
    import os
    directories = [
        settings.UPLOAD_DIR,
        settings.FAISS_INDEX_PATH,
        "/data/face_encodings",
        "/var/log/jarvis",
    ]
    
    for directory in directories:
        os.makedirs(directory, exist_ok=True)
    
    logger.info("✅ Required directories created")
    
    logger.info("=" * 60)
    logger.info(f"🎯 Environment: {settings.APP_ENV}")
    logger.info(f"🔧 Debug Mode: {settings.DEBUG}")
    logger.info(f"🧠 LLM Provider: {settings.LLM_PROVIDER}")
    logger.info(f"💾 Vector Store: {settings.VECTOR_STORE}")
    logger.info("=" * 60)
    logger.info("✨ JARVIS-IRON is ready!")
    logger.info("=" * 60)


async def shutdown_event():
    """
    Execute on application shutdown.
    Cleanup resources, close connections, etc.
    """
    logger.info("=" * 60)
    logger.info("👋 Shutting down JARVIS-IRON Backend")
    logger.info("=" * 60)
    
    # Close database connections
    try:
        await close_db()
        logger.info("✅ Database connections closed")
    except Exception as e:
        logger.error(f"❌ Error closing database: {e}")
    
    # Close Redis connection
    try:
        redis = get_redis()
        redis.close()
        logger.info("✅ Redis connection closed")
    except Exception as e:
        logger.error(f"❌ Error closing Redis: {e}")
    
    logger.info("=" * 60)
    logger.info("✨ JARVIS-IRON stopped successfully")
    logger.info("=" * 60)
