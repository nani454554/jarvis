"""
Vision Service
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

# Face detection and recognition
from facenet_pytorch import MTCNN, InceptionResnetV1
import torch

# Emotion detection
from fer import FER

from app.config import settings
from app.core.cache import cache

logger = logging.getLogger(__name__)

class VisionService:
    """Advanced computer vision service"""
    
    def __init__(self):
        self.face_detector = None
        self.face_recognizer = None
        self.emotion_detector = None
        self.device = None
        self.is_initialized = False
        self._lock = asyncio.Lock()
        
        # Known faces database (in-memory, should use DB in production)
        self.known_faces = {}
        
        # Initialize in background
        asyncio.create_task(self._initialize())
    
    async def _initialize(self):
        """Initialize AI models"""
        async with self._lock:
            try:
                logger.info("👁️ Initializing Vision Service...")
                
                # Set device
                self.device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
                logger.info(f"Using device: {self.device}")
                
                # Initialize face detector (MTCNN)
                logger.info("Loading MTCNN face detector...")
                self.face_detector = MTCNN(
                    keep_all=True,
                    device=self.device,
                    post_process=False
                )
                
                # Initialize face recognizer (FaceNet)
                logger.info("Loading FaceNet recognizer...")
                self.face_recognizer = InceptionResnetV1(
                    pretrained='vggface2'
                ).eval().to(self.device)
                
                # Initialize emotion detector
                logger.info("Loading emotion detector...")
                self.emotion_detector = FER(mtcnn=True)
                
                self.is_initialized = True
                logger.info("✅ Vision Service initialized successfully")
                
            except Exception as e:
                logger.error(f"❌ Failed to initialize Vision Service: {e}")
                self.is_initialized = False
    
    async def detect_faces(
        self,
        image_data: bytes
    ) -> List[Dict]:
        """
        Detect all faces in image
        
        Args:
            image_data: Image bytes (JPEG/PNG)
        
        Returns:
            List of detected faces with bounding boxes
        """
        if not self.is_initialized:
            raise RuntimeError("Vision service not initialized")
        
        try:
            # Decode image
            image = self._decode_image(image_data)
            
            # Convert to RGB
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
        
        try:
            # Decode image
            image = self._decode_image(image_data)
            image_rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
            
            # Extract face
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
    
    async def detect_emotion(
        self,
        image_data: bytes
    ) -> Dict:
        """
        Detect emotion from facial expression
        
        Args:
            image_data: Image bytes
        
        Returns:
            Emotion classification results
        """
        if not self.is_initialized:
            raise RuntimeError("Vision service not initialized")
        
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
                return {"emotion": "neutral", "confidence": 0.0, "all_emotions": {}}
            
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
            return {"emotion": "neutral", "confidence": 0.0, "error": str(e)}
    
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
            
            # Get embedding
            image = self._decode_image(image_data)
            image_rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
            
            bbox = faces[0]["bbox"]
            x1, y1, x2, y2 = [int(coord) for coord in bbox]
            face_image = image_rgb[y1:y2, x1:x2]
            
            embedding = await self._get_face_embedding(face_image)
            
            # Store embedding
            self.known_faces[user_id] = embedding
            
            logger.info(f"✅ Face registered for user: {user_id}")
            return True
            
        except Exception as e:
            logger.error(f"Face registration error: {e}")
            return False
    
    async def _get_face_embedding(
        self,
        face_image: np.ndarray
    ) -> np.ndarray:
        """
        Get face embedding vector
        
        Args:
            face_image: Cropped face image (RGB)
        
        Returns:
            Embedding vector (512-d)
        """
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
        
        return image
    
    def is_ready(self) -> bool:
        """Check if service is ready"""
        return self.is_initialized
