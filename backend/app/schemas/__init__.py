"""
Pydantic Schemas
Request and response models for API validation
"""
from app.schemas.user import (
    UserCreate,
    UserUpdate,
    UserResponse,
    UserLogin,
    TokenResponse
)
from app.schemas.message import (
    Message,
    MessageCreate,
    ConversationResponse
)
from app.schemas.voice import (
    VoiceCommand,
    SpeechToTextRequest,
    SpeechToTextResponse,
    TextToSpeechRequest,
    VoiceStatusResponse
)
from app.schemas.vision import (
    FaceDetectionResponse,
    FaceRecognitionResponse,
    EmotionResponse,
    VisionStatusResponse
)

__all__ = [
    "UserCreate",
    "UserUpdate",
    "UserResponse",
    "UserLogin",
    "TokenResponse",
    "Message",
    "MessageCreate",
    "ConversationResponse",
    "VoiceCommand",
    "SpeechToTextRequest",
    "SpeechToTextResponse",
    "TextToSpeechRequest",
    "VoiceStatusResponse",
    "FaceDetectionResponse",
    "FaceRecognitionResponse",
    "EmotionResponse",
    "VisionStatusResponse",
]
