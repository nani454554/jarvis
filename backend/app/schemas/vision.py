"""
Vision Schemas
Pydantic models for vision-related requests and responses
"""
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any

class FaceDetection(BaseModel):
    """Schema for detected face"""
    id: str
    bbox: List[float]  # [x1, y1, x2, y2]
    confidence: float
    landmarks: Optional[List[List[float]]] = None

class FaceDetectionResponse(BaseModel):
    """Schema for face detection response"""
    faces: List[FaceDetection]
    count: int

class FaceRecognitionResponse(BaseModel):
    """Schema for face recognition response"""
    identity: str
    confidence: float
    distance: Optional[float] = None

class EmotionResponse(BaseModel):
    """Schema for emotion detection response"""
    emotion: str
    confidence: float
    all_emotions: Dict[str, float]

class VisionStatusResponse(BaseModel):
    """Schema for vision service status"""
    is_ready: bool
    face_detector_loaded: bool
    face_recognizer_loaded: bool
    emotion_detector_loaded: bool
    registered_faces: int
