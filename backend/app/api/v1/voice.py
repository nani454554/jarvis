"""
Voice API Routes
Speech-to-text, text-to-speech, wake word detection
"""
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from fastapi.responses import Response
from typing import Optional
import logging

from app.services.voice_service import VoiceService
from app.core.security import get_current_user
from app.schemas.voice import (
    SpeechToTextRequest,
    SpeechToTextResponse,
    TextToSpeechRequest,
    VoiceStatusResponse
)

logger = logging.getLogger(__name__)
router = APIRouter()

@router.post("/stt", response_model=SpeechToTextResponse)
async def speech_to_text(
    audio: UploadFile = File(...),
    language: Optional[str] = "en",
    current_user: dict = Depends(get_current_user),
    voice_service: VoiceService = Depends(lambda: VoiceService())
):
    """
    Convert speech to text
    
    Upload audio file (WAV, MP3, etc.) and get transcription
    """
    try:
        # Read audio data
        audio_data = await audio.read()
        
        # Process with Whisper
        result = await voice_service.speech_to_text(audio_data, language)
        
        return SpeechToTextResponse(
            text=result["text"],
            language=result["language"],
            confidence=result["confidence"],
            segments=result.get("segments", [])
        )
        
    except Exception as e:
        logger.error(f"STT error: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Speech-to-text failed: {str(e)}"
        )

@router.post("/tts")
async def text_to_speech(
    request: TextToSpeechRequest,
    current_user: dict = Depends(get_current_user),
    voice_service: VoiceService = Depends(lambda: VoiceService())
):
    """
    Convert text to speech
    
    Returns audio file in WAV format
    """
    try:
        # Generate speech
        audio_bytes = await voice_service.text_to_speech(
            text=request.text,
            speaker=request.speaker,
            language=request.language,
            emotion=request.emotion
        )
        
        # Return audio response
        return Response(
            content=audio_bytes,
            media_type="audio/wav",
            headers={
                "Content-Disposition": "attachment; filename=speech.wav"
            }
        )
        
    except Exception as e:
        logger.error(f"TTS error: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Text-to-speech failed: {str(e)}"
        )

@router.get("/status", response_model=VoiceStatusResponse)
async def get_voice_status(
    current_user: dict = Depends(get_current_user),
    voice_service: VoiceService = Depends(lambda: VoiceService())
):
    """
    Get voice service status
    """
    return VoiceStatusResponse(
        is_ready=voice_service.is_ready(),
        stt_available=voice_service.stt_model is not None,
        tts_available=voice_service.tts_model is not None,
        wake_word_available=voice_service.wake_word_detector is not None
    )

@router.post("/clone-voice")
async def clone_voice(
    reference_audio: UploadFile = File(...),
    text: str = "Hello, this is a test.",
    current_user: dict = Depends(get_current_user),
    voice_service: VoiceService = Depends(lambda: VoiceService())
):
    """
    Clone voice from reference audio
    
    Experimental feature for voice cloning
    """
    try:
        # Read reference audio
        reference_data = await reference_audio.read()
        
        # Clone voice
        cloned_audio = await voice_service.clone_voice(reference_data, text)
        
        return Response(
            content=cloned_audio,
            media_type="audio/wav",
            headers={
                "Content-Disposition": "attachment; filename=cloned_voice.wav"
            }
        )
        
    except Exception as e:
        logger.error(f"Voice cloning error: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Voice cloning failed: {str(e)}"
        )
