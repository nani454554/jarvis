"""
Voice Service
Handles STT, TTS, Wake Word Detection, Voice Cloning
"""
import asyncio
import io
import wave
import numpy as np
from typing import Optional, AsyncGenerator
import logging
from pathlib import Path
import base64

# Whisper for STT
import whisper

# TTS imports
from TTS.api import TTS

# Audio processing
import sounddevice as sd
import scipy.io.wavfile as wavfile

from app.config import settings
from app.core.cache import cache

logger = logging.getLogger(__name__)

class VoiceService:
    """Advanced voice processing service"""
    
    def __init__(self):
        self.stt_model = None
        self.tts_model = None
        self.wake_word_detector = None
        self.is_initialized = False
        self._lock = asyncio.Lock()
        
        # Initialize in background
        asyncio.create_task(self._initialize())
    
    async def _initialize(self):
        """Initialize AI models"""
        async with self._lock:
            try:
                logger.info("🎤 Initializing Voice Service...")
                
                # Load Whisper STT model
                logger.info(f"Loading Whisper model: {settings.WHISPER_MODEL}")
                self.stt_model = whisper.load_model(settings.WHISPER_MODEL)
                
                # Load TTS model
                logger.info(f"Loading TTS model: {settings.TTS_MODEL}")
                self.tts_model = TTS(settings.TTS_MODEL)
                
                # Set default speaker for multi-speaker models
                if self.tts_model.speakers:
                    # Choose British-sounding speaker
                    british_speakers = [s for s in self.tts_model.speakers if 'p' in s.lower()]
                    if british_speakers:
                        self.default_speaker = british_speakers[0]
                    else:
                        self.default_speaker = self.tts_model.speakers[0]
                else:
                    self.default_speaker = None
                
                self.is_initialized = True
                logger.info("✅ Voice Service initialized successfully")
                
            except Exception as e:
                logger.error(f"❌ Failed to initialize Voice Service: {e}")
                self.is_initialized = False
    
    async def speech_to_text(
        self,
        audio_data: bytes,
        language: str = "en"
    ) -> dict:
        """
        Convert speech to text using Whisper
        
        Args:
            audio_data: Raw audio bytes (WAV format)
            language: Language code (default: en)
        
        Returns:
            dict with transcription and metadata
        """
        if not self.is_initialized:
            raise RuntimeError("Voice service not initialized")
        
        try:
            # Check cache first
            cache_key = f"stt:{hash(audio_data)}"
            cached = await cache.get(cache_key)
            if cached:
                logger.debug("STT cache hit")
                return cached
            
            # Convert bytes to numpy array
            audio_io = io.BytesIO(audio_data)
            sample_rate, audio_np = wavfile.read(audio_io)
            
            # Normalize to float32
            audio_np = audio_np.astype(np.float32) / 32768.0
            
            # Transcribe
            logger.info("Transcribing audio with Whisper...")
            result = await asyncio.get_event_loop().run_in_executor(
                None,
                lambda: self.stt_model.transcribe(
                    audio_np,
                    language=language,
                    fp16=False
                )
            )
            
            response = {
                "text": result["text"].strip(),
                "language": result.get("language", language),
                "segments": result.get("segments", []),
                "confidence": self._calculate_confidence(result)
            }
            
            # Cache result
            await cache.set(cache_key, response, expire=3600)
            
            logger.info(f"STT Result: {response['text']}")
            return response
            
        except Exception as e:
            logger.error(f"STT error: {e}")
            raise
    
    async def text_to_speech(
        self,
        text: str,
        speaker: Optional[str] = None,
        language: str = "en",
        emotion: str = "neutral"
    ) -> bytes:
        """
        Convert text to speech with JARVIS-like voice
        
        Args:
            text: Text to synthesize
            speaker: Speaker ID (optional)
            language: Language code
            emotion: Emotion/tone (neutral, urgent, calm)
        
        Returns:
            Audio bytes in WAV format
        """
        if not self.is_initialized:
            raise RuntimeError("Voice service not initialized")
        
        try:
            # Check cache
            cache_key = f"tts:{hash(text)}:{speaker}:{emotion}"
            cached = await cache.get(cache_key)
            if cached:
                logger.debug("TTS cache hit")
                return base64.b64decode(cached)
            
            logger.info(f"Synthesizing speech: {text[:50]}...")
            
            # Adjust text for emotion
            text = self._apply_emotion_modulation(text, emotion)
            
            # Generate speech
            speaker_id = speaker or self.default_speaker
            
            wav_data = await asyncio.get_event_loop().run_in_executor(
                None,
                lambda: self.tts_model.tts(
                    text=text,
                    speaker=speaker_id
                )
            )
            
            # Convert to bytes
            audio_bytes = self._numpy_to_wav_bytes(wav_data, self.tts_model.synthesizer.output_sample_rate)
            
            # Cache result
            await cache.set(cache_key, base64.b64encode(audio_bytes).decode(), expire=3600)
            
            return audio_bytes
            
        except Exception as e:
            logger.error(f"TTS error: {e}")
            raise
    
    async def detect_wake_word(
        self,
        audio_stream: AsyncGenerator[bytes, None]
    ) -> bool:
        """
        Detect wake word in audio stream
        
        Args:
            audio_stream: Async generator yielding audio chunks
        
        Returns:
            True if wake word detected
        """
        # Simplified wake word detection
        # In production, use Porcupine or similar
        
        try:
            async for chunk in audio_stream:
                # Process chunk
                transcription = await self.speech_to_text(chunk)
                if settings.WAKE_WORD.lower() in transcription["text"].lower():
                    logger.info(f"Wake word '{settings.WAKE_WORD}' detected!")
                    return True
            
            return False
            
        except Exception as e:
            logger.error(f"Wake word detection error: {e}")
            return False
    
    async def clone_voice(
        self,
        reference_audio: bytes,
        text: str
    ) -> bytes:
        """
        Clone voice from reference audio
        
        Args:
            reference_audio: Reference voice sample
            text: Text to synthesize in cloned voice
        
        Returns:
            Audio bytes in cloned voice
        """
        # Voice cloning using YourTTS or similar
        # This is a placeholder for advanced implementation
        
        logger.warning("Voice cloning not fully implemented, using default TTS")
        return await self.text_to_speech(text)
    
    def _calculate_confidence(self, whisper_result: dict) -> float:
        """Calculate average confidence from Whisper segments"""
        segments = whisper_result.get("segments", [])
        if not segments:
            return 0.0
        
        # Whisper doesn't provide confidence directly
        # We can estimate from various factors
        avg_logprob = np.mean([s.get("avg_logprob", -1.0) for s in segments])
        
        # Convert log probability to confidence (0-1)
        confidence = np.exp(avg_logprob)
        return min(max(confidence, 0.0), 1.0)
    
    def _apply_emotion_modulation(self, text: str, emotion: str) -> str:
        """Apply SSML-like modulation for emotion"""
        # Add prosody tags if supported by TTS
        modulations = {
            "urgent": {"rate": "+15%", "pitch": "+5%"},
            "calm": {"rate": "-10%", "pitch": "-3%"},
            "neutral": {"rate": "0%", "pitch": "0%"}
        }
        
        # For now, just return text
        # Advanced TTS models can accept SSML
        return text
    
    def _numpy_to_wav_bytes(self, audio_np: np.ndarray, sample_rate: int) -> bytes:
        """Convert numpy array to WAV bytes"""
        # Normalize
        audio_np = np.clip(audio_np, -1.0, 1.0)
        audio_int16 = (audio_np * 32767).astype(np.int16)
        
        # Create WAV file in memory
        buffer = io.BytesIO()
        with wave.open(buffer, 'wb') as wav_file:
            wav_file.setnchannels(1)  # Mono
            wav_file.setsampwidth(2)  # 16-bit
            wav_file.setframerate(sample_rate)
            wav_file.writeframes(audio_int16.tobytes())
        
        buffer.seek(0)
        return buffer.read()
    
    def is_ready(self) -> bool:
        """Check if service is ready"""
        return self.is_initialized
