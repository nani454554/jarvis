"""
Voice API Routes
Speech-to-text, text-to-speech, wake word detection
"""
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, status
from fastapi.responses import Response
from typing import Optional

from app.core.security import get_current_user
from app.dependencies import get_voice_service
from app.services.voice_service import VoiceService
from app.schemas.voice import (
    VoiceCommand,
    SpeechToTextResponse,
    TextToSpeechRequest,
    VoiceStatusResponse
)
import logging

logger = logging.getLogger(__name__)
router = APIRouter()

@router.post("/stt", response_model=SpeechToTextResponse)
async def speech_to_text(
    audio: UploadFile = File(..., description="Audio file (WAV, MP3, etc.)"),
    language: Optional[str] = "en",
    current_user: dict = Depends(get_current_user),
    voice_service: VoiceService = Depends(get_voice_service)
):
    """
    Convert speech to text
    
    Upload audio file and get transcription
    
    Args:
        audio: Audio file
        language: Language code (default: en)
        current_user: Current authenticated user
        voice_service: Voice service instance
        
    Returns:
        Transcribed text with confidence and metadata
    """
    try:
        # Read audio data
        audio_data = await audio.read()
        
        # Validate file size (max 25MB)
        if len(audio_data) > 25 * 1024 * 1024:
            raise HTTPException(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                detail="Audio file too large (max 25MB)"
            )
        
        # Process with STT
        result = await voice_service.speech_to_text(audio_data, language)
        
        logger.info(f"STT completed for user {current_user['username']}: {result['text'][:50]}")
        
        return SpeechToTextResponse(**result)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"STT error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Speech-to-text failed: {str(e)}"
        )

@router.post("/tts")
async def text_to_speech(
    request: TextToSpeechRequest,
    current_user: dict = Depends(get_current_user),
    voice_service: VoiceService = Depends(get_voice_service)
):
    """
    Convert text to speech
    
    Returns audio file in WAV format with JARVIS-like voice
    
    Args:
        request: TTS request with text and parameters
        current_user: Current authenticated user
        voice_service: Voice service instance
        
    Returns:
        Audio file (WAV format)
    """
    try:
        # Generate speech
        audio_bytes = await voice_service.text_to_speech(
            text=request.text,
            speaker=request.speaker,
            language=request.language,
            emotion=request.emotion
        )
        
        if not audio_bytes:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to generate speech"
            )
        
        logger.info(f"TTS completed for user {current_user['username']}")
        
        # Return audio response
        return Response(
            content=audio_bytes,
            media_type="audio/wav",
            headers={
                "Content-Disposition": "attachment; filename=speech.wav"
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"TTS error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Text-to-speech failed: {str(e)}"
        )

@router.get("/status", response_model=VoiceStatusResponse)
async def get_voice_status(
    current_user: dict = Depends(get_current_user),
    voice_service: VoiceService = Depends(get_voice_service)
):
    """
    Get voice service status
    
    Returns information about voice service availability and capabilities
    
    Args:
        current_user: Current authenticated user
        voice_service: Voice service instance
        
    Returns:
        Voice service status and capabilities
    """
    return VoiceStatusResponse(
        is_ready=voice_service.is_ready(),
        stt_available=voice_service.stt_model is not None,
        tts_available=voice_service.tts_model is not None,
        wake_word_available=voice_service.wake_word_detector is not None,
        supported_languages=["en", "es", "fr", "de", "it", "pt"]
    )

@router.post("/clone-voice")
async def clone_voice(
    reference_audio: UploadFile = File(..., description="Reference voice sample"),
    text: str = "Hello, this is a test of voice cloning.",
    current_user: dict = Depends(get_current_user),
    voice_service: VoiceService = Depends(get_voice_service)
):
    """
    Clone voice from reference audio (experimental)
    
    Args:
        reference_audio: Reference voice audio file
        text: Text to synthesize in cloned voice
        current_user: Current authenticated user
        voice_service: Voice service instance
        
    Returns:
        Audio file with cloned voice
    """
    try:
        # Read reference audio
        reference_data = await reference_audio.read()
        
        # Clone voice
        cloned_audio = await voice_service.clone_voice(reference_data, text)
        
        if not cloned_audio:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Voice cloning failed"
            )
        
        logger.info(f"Voice cloning completed for user {current_user['username']}")
        
        return Response(
            content=cloned_audio,
            media_type="audio/wav",
            headers={
                "Content-Disposition": "attachment; filename=cloned_voice.wav"
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Voice cloning error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Voice cloning failed: {str(e)}"
        )
