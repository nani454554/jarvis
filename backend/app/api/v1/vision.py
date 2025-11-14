"""
Vision API Routes
Face detection, recognition, emotion analysis
"""
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from typing import List
import logging

from app.services.vision_service import VisionService
from app.core.security import get_current_user
from app.schemas.vision import (
    FaceDetectionResponse,
    FaceRecognitionResponse,
    EmotionResponse,
    VisionStatusResponse
)

logger = logging.getLogger(__name__)
router = APIRouter()

@router.post("/detect-faces", response_model=FaceDetectionResponse)
async def detect_faces(
    image: UploadFile = File(...),
    current_user: dict = Depends(get_current_user),
    vision_service: VisionService = Depends(lambda: VisionService())
):
    """
    Detect all faces in image
    
    Upload image and get bounding boxes for all detected faces
    """
    try:
        # Read image data
        image_data = await image.read()
        
        # Detect faces
        faces = await vision_service.detect_faces(image_data)
        
        return FaceDetectionResponse(
            faces=faces,
            count=len(faces)
        )
        
    except Exception as e:
        logger.error(f"Face detection error: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Face detection failed: {str(e)}"
        )

@router.post("/recognize-face", response_model=FaceRecognitionResponse)
async def recognize_face(
    image: UploadFile = File(...),
    current_user: dict = Depends(get_current_user),
    vision_service: VisionService = Depends(lambda: VisionService())
):
    """
    Recognize face in image
    
    Returns identity if face is in database
    """
    try:
        # Read image data
        image_data = await image.read()
        
        # Recognize face
        result = await vision_service.recognize_face(image_data)
        
        return FaceRecognitionResponse(
            identity=result["identity"],
            confidence=result["confidence"],
            distance=result.get("distance")
        )
        
    except Exception as e:
        logger.error(f"Face recognition error: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Face recognition failed: {str(e)}"
        )

@router.post("/detect-emotion", response_model=EmotionResponse)
async def detect_emotion(
    image: UploadFile = File(...),
    current_user: dict = Depends(get_current_user),
    vision_service: VisionService = Depends(lambda: VisionService())
):
    """
    Detect emotion from facial expression
    
    Returns dominant emotion and all emotion scores
    """
    try:
        # Read image data
        image_data = await image.read()
        
        # Detect emotion
        result = await vision_service.detect_emotion(image_data)
        
        return EmotionResponse(
            emotion=result["emotion"],
            confidence=result["confidence"],
            all_emotions=result.get("all_emotions", {})
        )
        
    except Exception as e:
        logger.error(f"Emotion detection error: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Emotion detection failed: {str(e)}"
        )

@router.post("/register-face")
async def register_face(
    image: UploadFile = File(...),
    current_user: dict = Depends(get_current_user),
    vision_service: VisionService = Depends(lambda: VisionService())
):
    """
    Register current user's face for recognition
    
    Upload a clear frontal face photo
    """
    try:
        # Read image data
        image_data = await image.read()
        
        # Register face
        success = await vision_service.register_face(
            user_id=current_user["user_id"],
            image_data=image_data
        )
        
        if success:
            return {
                "message": "Face registered successfully",
                "user_id": current_user["user_id"]
            }
        else:
            raise HTTPException(
                status_code=400,
                detail="No face detected in image"
            )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Face registration error: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Face registration failed: {str(e)}"
        )

@router.get("/status", response_model=VisionStatusResponse)
async def get_vision_status(
    current_user: dict = Depends(get_current_user),
    vision_service: VisionService = Depends(lambda: VisionService())
):
    """
    Get vision service status
    """
    return VisionStatusResponse(
        is_ready=vision_service.is_ready(),
        face_detector_loaded=vision_service.face_detector is not None,
        face_recognizer_loaded=vision_service.face_recognizer is not None,
        emotion_detector_loaded=vision_service.emotion_detector is not None,
        registered_faces=len(vision_service.known_faces)
    )
