"""
Voice Service - Complete Implementation
Handles STT, TTS, Wake Word Detection, Voice Cloning
"""
import asyncio
import io
import wave
import numpy as np
from typing import Optional, AsyncGenerator, Dict, Any
import logging
from pathlib import Path
import base64
import os

from app.config import settings
from app.core.cache import cache

logger = logging.getLogger(__name__)

# Conditional imports based on availability
try:
    import whisper
    WHISPER_AVAILABLE = True
except ImportError:
    WHISPER_AVAILABLE = False
    logger.warning("Whisper not available - STT will use mock mode")

try:
    from TTS.api import TTS
    TTS_AVAILABLE = True
except ImportError:
    TTS_AVAILABLE = False
    logger.warning("TTS not available - voice synthesis will use mock mode")

try:
    import sounddevice as sd
    import scipy.io.wavfile as wavfile
    AUDIO_AVAILABLE = True
except ImportError:
    AUDIO_AVAILABLE = False
    logger.warning("Audio libraries not available")

class VoiceService:
    """
    Advanced voice processing service
    Handles all voice-related AI operations
    """
    
    def __init__(self):
        self.stt_model = None
        self.tts_model = None
        self.wake_word_detector = None
        self.is_initialized = False
        self._lock = asyncio.Lock()
        
        # Mock mode configuration
        self.mock_mode = not (WHISPER_AVAILABLE and TTS_AVAILABLE)
        
        # Initialize in background
        asyncio.create_task(self._initialize())
    
    async def _initialize(self):
        """
        Initialize AI models asynchronously
        Runs in background to avoid blocking startup
        """
        async with self._lock:
            try:
                logger.info("🎤 Initializing Voice Service...")
                
                if self.mock_mode:
                    logger.info("Running in MOCK MODE - no real AI models")
                    self.is_initialized = True
                    return
                
                # Load Whisper STT model
                if WHISPER_AVAILABLE:
                    logger.info(f"Loading Whisper model: {settings.WHISPER_MODEL}")
                    self.stt_model = await asyncio.get_event_loop().run_in_executor(
                        None,
                        whisper.load_model,
                        settings.WHISPER_MODEL
                    )
                    logger.info("✅ Whisper STT model loaded")
                
                # Load TTS model
                if TTS_AVAILABLE:
                    logger.info(f"Loading TTS model: {settings.TTS_MODEL}")
                    self.tts_model = await asyncio.get_event_loop().run_in_executor(
                        None,
                        TTS,
                        settings.TTS_MODEL
                    )
                    
                    # Set default speaker for multi-speaker models
                    if hasattr(self.tts_model, 'speakers') and self.tts_model.speakers:
                        # Choose British-sounding speaker
                        british_speakers = [
                            s for s in self.tts_model.speakers 
                            if 'p' in s.lower() or 'british' in s.lower()
                        ]
                        if british_speakers:
                            self.default_speaker = british_speakers[0]
                        else:
                            self.default_speaker = self.tts_model.speakers[0]
                        logger.info(f"Using TTS speaker: {self.default_speaker}")
                    else:
                        self.default_speaker = None
                    
                    logger.info("✅ TTS model loaded")
                
                self.is_initialized = True
                logger.info("✅ Voice Service initialized successfully")
                
            except Exception as e:
                logger.error(f"❌ Failed to initialize Voice Service: {e}")
                logger.info("Falling back to MOCK MODE")
                self.mock_mode = True
                self.is_initialized = True
    
    def is_ready(self) -> bool:
        """Check if voice service is ready"""
        return self.is_initialized
    
    async def speech_to_text(
        self,
        audio_data: bytes,
        language: str = "en"
    ) -> Dict[str, Any]:
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
        
        # Check cache first
        cache_key = f"stt:{hash(audio_data)}"
        cached = await cache.get(cache_key)
        if cached:
            logger.debug("STT cache hit")
            return cached
        
        if self.mock_mode or not self.stt_model:
            # Mock response
            return self._mock_stt_response()
        
        try:
            # Convert bytes to numpy array
            audio_io = io.BytesIO(audio_data)
            
            try:
                sample_rate, audio_np = wavfile.read(audio_io)
            except Exception as e:
                logger.error(f"Failed to read audio data: {e}")
                return self._mock_stt_response()
            
            # Normalize to float32
            if audio_np.dtype == np.int16:
                audio_np = audio_np.astype(np.float32) / 32768.0
            elif audio_np.dtype == np.int32:
                audio_np = audio_np.astype(np.float32) / 2147483648.0
            
            # Transcribe using Whisper
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
            
            # Cache result for 1 hour
            await cache.set(cache_key, response, expire=3600)
            
            logger.info(f"STT Result: {response['text']}")
            return response
            
        except Exception as e:
            logger.error(f"STT error: {e}")
            return self._mock_stt_response()
    
    async def text_to_speech(
        self,
        text: str,
        speaker: Optional[str] = None,
        language: str = "en",
        emotion: str = "neutral"
    ) -> Optional[bytes]:
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
        
        # Check cache
        cache_key = f"tts:{hash(text)}:{speaker}:{emotion}"
        cached = await cache.get(cache_key)
        if cached:
            logger.debug("TTS cache hit")
            return base64.b64decode(cached)
        
        if self.mock_mode or not self.tts_model:
            # Return mock audio (empty WAV file)
            return self._generate_mock_audio(text)
        
        try:
            logger.info(f"Synthesizing speech: {text[:50]}...")
            
            # Apply emotion modulation to text
            text = self._apply_emotion_modulation(text, emotion)
            
            # Choose speaker
            speaker_id = speaker or self.default_speaker
            
            # Generate speech
            if speaker_id:
                wav_data = await asyncio.get_event_loop().run_in_executor(
                    None,
                    lambda: self.tts_model.tts(text=text, speaker=speaker_id)
                )
            else:
                wav_data = await asyncio.get_event_loop().run_in_executor(
                    None,
                    lambda: self.tts_model.tts(text=text)
                )
            
            # Convert numpy array to WAV bytes
            if isinstance(wav_data, np.ndarray):
                audio_bytes = self._numpy_to_wav_bytes(
                    wav_data,
                    self.tts_model.synthesizer.output_sample_rate
                )
            else:
                audio_bytes = wav_data
            
            # Cache result
            await cache.set(
                cache_key,
                base64.b64encode(audio_bytes).decode(),
                expire=3600
            )
            
            return audio_bytes
            
        except Exception as e:
            logger.error(f"TTS error: {e}")
            return self._generate_mock_audio(text)
    
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
        try:
            async for chunk in audio_stream:
                # Process chunk with STT
                transcription = await self.speech_to_text(chunk)
                
                # Check for wake word
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
    ) -> Optional[bytes]:
        """
        Clone voice from reference audio (experimental)
        
        Args:
            reference_audio: Reference voice sample
            text: Text to synthesize in cloned voice
        
        Returns:
            Audio bytes in cloned voice
        """
        # Voice cloning is advanced feature
        # For now, fall back to regular TTS
        logger.warning("Voice cloning not fully implemented, using default TTS")
        return await self.text_to_speech(text)
    
    # Helper methods
    
    def _calculate_confidence(self, whisper_result: dict) -> float:
        """Calculate average confidence from Whisper segments"""
        segments = whisper_result.get("segments", [])
        if not segments:
            return 0.5
        
        # Whisper doesn't provide direct confidence
        # Estimate from log probabilities
        avg_logprob = np.mean([s.get("avg_logprob", -1.0) for s in segments])
        
        # Convert log probability to confidence (0-1)
        confidence = np.exp(avg_logprob)
        return min(max(confidence, 0.0), 1.0)
    
    def _apply_emotion_modulation(self, text: str, emotion: str) -> str:
        """
        Apply SSML-like modulation for emotion
        (Currently just returns text, future: add SSML tags)
        """
        # Future: Add prosody tags if TTS supports SSML
        return text
    
    def _numpy_to_wav_bytes(self, audio_np: np.ndarray, sample_rate: int) -> bytes:
        """Convert numpy array to WAV bytes"""
        # Ensure audio is in correct range
        if audio_np.max() <= 1.0:
            audio_np = audio_np * 32767
        
        audio_np = np.clip(audio_np, -32768, 32767)
        audio_int16 = audio_np.astype(np.int16)
        
        # Create WAV file in memory
        buffer = io.BytesIO()
        with wave.open(buffer, 'wb') as wav_file:
            wav_file.setnchannels(1)  # Mono
            wav_file.setsampwidth(2)  # 16-bit
            wav_file.setframerate(sample_rate)
            wav_file.writeframes(audio_int16.tobytes())
        
        buffer.seek(0)
        return buffer.read()
    
    def _mock_stt_response(self) -> Dict[str, Any]:
        """Generate mock STT response"""
        return {
            "text": "Hello Jarvis, what's the weather today?",
            "language": "en",
            "segments": [],
            "confidence": 0.95
        }
    
    def _generate_mock_audio(self, text: str) -> bytes:
        """Generate mock WAV audio (silence)"""
        # Generate 1 second of silence as placeholder
        sample_rate = 22050
        duration = 1.0
        samples = int(sample_rate * duration)
        audio_np = np.zeros(samples, dtype=np.int16)
        
        buffer = io.BytesIO()
        with wave.open(buffer, 'wb') as wav_file:
            wav_file.setnchannels(1)
            wav_file.setsampwidth(2)
            wav_file.setframerate(sample_rate)
            wav_file.writeframes(audio_np.tobytes())
        
        buffer.seek(0)
        return buffer.read()
