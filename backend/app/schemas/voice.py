"""
Voice Schemas
Pydantic models for voice-related requests and responses
"""
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any

class VoiceCommand(BaseModel):
    """Schema for voice command"""
    text: str = Field(..., min_length=1)
    language: str = "en"
    context: Optional[Dict[str, Any]] = None

class SpeechToTextRequest(BaseModel):
    """Schema for speech-to-text request"""
    language: str = "en"
    enable_automatic_punctuation: bool = True

class SpeechToTextResponse(BaseModel):
    """Schema for speech-to-text response"""
    text: str
    language: str
    confidence: float
    segments: Optional[List[Dict[str, Any]]] = None

class TextToSpeechRequest(BaseModel):
    """Schema for text-to-speech request"""
    text: str = Field(..., min_length=1, max_length=5000)
    language: str = "en"
    speaker: Optional[str] = None
    emotion: str = "neutral"
    speed: float = 1.0
    pitch: float = 1.0

class VoiceStatusResponse(BaseModel):
    """Schema for voice service status"""
    is_ready: bool
    stt_available: bool
    tts_available: bool
    wake_word_available: bool
    supported_languages: List[str] = ["en", "es", "fr", "de"]
