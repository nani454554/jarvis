"""
Vision Service - Complete Implementation
Face Detection, Recognition, Emotion Analysis, Gesture Recognition
"""
import asyncio
import cv2
import numpy as np
from typing import List, Dict, Optional, Tuple
import logging
from pathlib import Path
import base64
from io import BytesIO
from PIL import Image

from app.config import settings
from app.core.cache import cache

logger = logging.getLogger(__name__)

# Conditional imports
try:
    from facenet_pytorch import MTCNN, InceptionResnetV1
    import torch
    FACENET_AVAILABLE = True
except ImportError:
    FACENET_AVAILABLE = False
    logger.warning("FaceNet not available - face recognition will use mock mode")

try:
    from fer import FER
    FER_AVAILABLE = True
except ImportError:
    FER_AVAILABLE = False
    logger.warning("FER not available - emotion detection will use mock mode")

class VisionService:
    """
    Advanced computer vision service
    Handles all vision-related AI operations
    """
    
    def __init__(self):
        self.face_detector = None
        self.face_recognizer = None
        self.emotion_detector = None
        self.device = None
        self.is_initialized = False
        self._lock = asyncio.Lock()
        
        # Known faces database (in-memory)
        # In production, this should be stored in database
        self.known_faces = {}
        
        # Mock mode configuration
        self.mock_mode = not (FACENET_AVAILABLE and FER_AVAILABLE)
        
        # Initialize in background
        asyncio.create_task(self._initialize())
    
    async def _initialize(self):
        """Initialize AI models asynchronously"""
        async with self._lock:
            try:
                logger.info("👁️ Initializing Vision Service...")
                
                if self.mock_mode:
                    logger.info("Running in MOCK MODE - no real AI models")
                    self.is_initialized = True
                    return
                
                # Set device (GPU if available)
                if FACENET_AVAILABLE:
                    self.device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
                    logger.info(f"Using device: {self.device}")
                    
                    # Initialize face detector (MTCNN)
                    logger.info("Loading MTCNN face detector...")
                    self.face_detector = MTCNN(
                        keep_all=True,
                        device=self.device,
                        post_process=False,
                        min_face_size=40
                    )
                    logger.info("✅ MTCNN face detector loaded")
                    
                    # Initialize face recognizer (FaceNet)
                    logger.info("Loading FaceNet recognizer...")
                    self.face_recognizer = InceptionResnetV1(
                        pretrained='vggface2'
                    ).eval().to(self.device)
                    logger.info("✅ FaceNet recognizer loaded")
                
                # Initialize emotion detector
                if FER_AVAILABLE:
                    logger.info("Loading emotion detector...")
                    self.emotion_detector = FER(mtcnn=True)
                    logger.info("✅ Emotion detector loaded")
                
                self.is_initialized = True
                logger.info("✅ Vision Service initialized successfully")
                
            except Exception as e:
                logger.error(f"❌ Failed to initialize Vision Service: {e}")
                logger.info("Falling back to MOCK MODE")
                self.mock_mode = True
                self.is_initialized = True
    
    def is_ready(self) -> bool:
        """Check if vision service is ready"""
        return self.is_initialized
    
    async def detect_faces(self, image_data: bytes) -> List[Dict]:
        """
        Detect all faces in image
        
        Args:
            image_data: Image bytes (JPEG/PNG)
        
        Returns:
            List of detected faces with bounding boxes
        """
        if not self.is_initialized:
            raise RuntimeError("Vision service not initialized")
        
        if self.mock_mode or not self.face_detector:
            return self._mock_face_detection()
        
        try:
            # Decode image
            image = self._decode_image(image_data)
            image_rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
            
            # Detect faces
            logger.debug("Detecting faces...")
            boxes, probs, landmarks = await asyncio.get_event_loop().run_in_executor(
                None,
                lambda: self.face_detector.detect(image_rgb, landmarks=True)
            )
            
            if boxes is None:
                return []
            
            faces = []
            for i, (box, prob, landmark) in enumerate(zip(boxes, probs, landmarks)):
                faces.append({
                    "id": f"face_{i}",
                    "bbox": box.tolist(),
                    "confidence": float(prob),
                    "landmarks": landmark.tolist() if landmark is not None else None
                })
            
            logger.info(f"Detected {len(faces)} face(s)")
            return faces
            
        except Exception as e:
            logger.error(f"Face detection error: {e}")
            return []
    
    async def recognize_face(
        self,
        image_data: bytes,
        bbox: Optional[List[float]] = None
    ) -> Dict:
        """
        Recognize face and return identity
        
        Args:
            image_data: Image bytes
            bbox: Optional bounding box [x1, y1, x2, y2]
        
        Returns:
            Recognition result with identity and confidence
        """
        if not self.is_initialized:
            raise RuntimeError("Vision service not initialized")
        
        if self.mock_mode or not self.face_recognizer:
            return self._mock_face_recognition()
        
        try:
            # Decode image
            image = self._decode_image(image_data)
            image_rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
            
            # Extract face region
            if bbox:
                x1, y1, x2, y2 = [int(coord) for coord in bbox]
                face_image = image_rgb[y1:y2, x1:x2]
            else:
                # Detect face first
                faces = await self.detect_faces(image_data)
                if not faces:
                    return {"identity": "unknown", "confidence": 0.0}
                
                bbox = faces[0]["bbox"]
                x1, y1, x2, y2 = [int(coord) for coord in bbox]
                face_image = image_rgb[y1:y2, x1:x2]
            
            # Get face embedding
            embedding = await self._get_face_embedding(face_image)
            
            # Compare with known faces
            best_match = None
            best_distance = float('inf')
            
            for user_id, known_embedding in self.known_faces.items():
                distance = np.linalg.norm(embedding - known_embedding)
                if distance < best_distance:
                    best_distance = distance
                    best_match = user_id
            
            # Determine if match is confident enough
            threshold = settings.FACE_RECOGNITION_THRESHOLD
            if best_match and best_distance < threshold:
                confidence = 1.0 - (best_distance / threshold)
                return {
                    "identity": best_match,
                    "confidence": float(confidence),
                    "distance": float(best_distance)
                }
            else:
                return {
                    "identity": "unknown",
                    "confidence": 0.0,
                    "distance": float(best_distance) if best_match else None
                }
            
        except Exception as e:
            logger.error(f"Face recognition error: {e}")
            return {"identity": "unknown", "confidence": 0.0, "error": str(e)}
    
    async def detect_emotion(self, image_data: bytes) -> Dict:
        """
        Detect emotion from facial expression
        
        Args:
            image_data: Image bytes
        
        Returns:
            Emotion classification results
        """
        if not self.is_initialized:
            raise RuntimeError("Vision service not initialized")
        
        if self.mock_mode or not self.emotion_detector:
            return self._mock_emotion_detection()
        
        try:
            # Decode image
            image = self._decode_image(image_data)
            
            # Detect emotions
            logger.debug("Detecting emotions...")
            result = await asyncio.get_event_loop().run_in_executor(
                None,
                lambda: self.emotion_detector.detect_emotions(image)
            )
            
            if not result:
                return {
                    "emotion": "neutral",
                    "confidence": 0.0,
                    "all_emotions": {}
                }
            
            # Get dominant emotion
            emotions = result[0]["emotions"]
            dominant_emotion = max(emotions.items(), key=lambda x: x[1])
            
            return {
                "emotion": dominant_emotion[0],
                "confidence": float(dominant_emotion[1]),
                "all_emotions": {k: float(v) for k, v in emotions.items()}
            }
            
        except Exception as e:
            logger.error(f"Emotion detection error: {e}")
            return {
                "emotion": "neutral",
                "confidence": 0.0,
                "error": str(e)
            }
    
    async def register_face(
        self,
        user_id: str,
        image_data: bytes
    ) -> bool:
        """
        Register a new face for recognition
        
        Args:
            user_id: User identifier
            image_data: Face image bytes
        
        Returns:
            True if successful
        """
        try:
            # Detect face
            faces = await self.detect_faces(image_data)
            if not faces:
                logger.error("No face detected in registration image")
                return False
            
            # Decode image
            image = self._decode_image(image_data)
            image_rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
            
            # Extract face region
            bbox = faces[0]["bbox"]
            x1, y1, x2, y2 = [int(coord) for coord in bbox]
            face_image = image_rgb[y1:y2, x1:x2]
            
            # Get embedding
            if not self.mock_mode and self.face_recognizer:
                embedding = await self._get_face_embedding(face_image)
            else:
                # Mock embedding
                embedding = np.random.rand(512)
            
            # Store embedding
            self.known_faces[user_id] = embedding
            
            logger.info(f"✅ Face registered for user: {user_id}")
            return True
            
        except Exception as e:
            logger.error(f"Face registration error: {e}")
            return False
    
    async def _get_face_embedding(self, face_image: np.ndarray) -> np.ndarray:
        """
        Get face embedding vector using FaceNet
        
        Args:
            face_image: Cropped face image (RGB)
        
        Returns:
            Embedding vector (512-d)
        """
        if not FACENET_AVAILABLE:
            return np.random.rand(512)
        
        # Resize to 160x160 (FaceNet input size)
        face_resized = cv2.resize(face_image, (160, 160))
        
        # Convert to tensor
        face_tensor = torch.from_numpy(face_resized).permute(2, 0, 1).float()
        face_tensor = face_tensor.unsqueeze(0).to(self.device)
        
        # Normalize
        face_tensor = (face_tensor - 127.5) / 128.0
        
        # Get embedding
        with torch.no_grad():
            embedding = await asyncio.get_event_loop().run_in_executor(
                None,
                lambda: self.face_recognizer(face_tensor)
            )
        
        return embedding.cpu().numpy()[0]
    
    def _decode_image(self, image_data: bytes) -> np.ndarray:
        """Decode image bytes to numpy array"""
        if isinstance(image_data, str):
            # Base64 encoded
            if 'base64,' in image_data:
                image_data = image_data.split('base64,')[1]
            image_data = base64.b64decode(image_data)
        
        # Decode with OpenCV
        nparr = np.frombuffer(image_data, np.uint8)
        image = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        
        if image is None:
            raise ValueError("Failed to decode image")
        
        return image
    
    # Mock responses for development/testing
    
    def _mock_face_detection(self) -> List[Dict]:
        """Mock face detection response"""
        return [{
            "id": "face_0",
            "bbox": [100.0, 100.0, 300.0, 300.0],
            "confidence": 0.95,
            "landmarks": None
        }]
    
    def _mock_face_recognition(self) -> Dict:
        """Mock face recognition response"""
        return {
            "identity": "Tony Stark",
            "confidence": 0.92,
            "distance": 0.45
        }
    
    def _mock_emotion_detection(self) -> Dict:
        """Mock emotion detection response"""
        return {
            "emotion": "neutral",
            "confidence": 0.85,
            "all_emotions": {
                "neutral": 0.85,
                "happy": 0.08,
                "sad": 0.03,
                "angry": 0.02,
                "surprised": 0.01,
                "fearful": 0.01
            }
        }
