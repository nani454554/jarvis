"""
Vision API Routes
Face detection, recognition, emotion analysis
"""
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, status
from typing import List

from app.core.security import get_current_user
from app.dependencies import get_vision_service
from app.services.vision_service import VisionService
from app.schemas.vision import (
    FaceDetectionResponse,
    FaceRecognitionResponse,
    EmotionResponse,
    VisionStatusResponse
)
import logging

logger = logging.getLogger(__name__)
router = APIRouter()

@router.post("/detect-faces", response_model=FaceDetectionResponse)
async def detect_faces(
    image: UploadFile = File(..., description="Image file (JPEG, PNG)"),
    current_user: dict = Depends(get_current_user),
    vision_service: VisionService = Depends(get_vision_service)
):
    """
    Detect all faces in image
    
    Upload image and get bounding boxes for all detected faces
    
    Args:
        image: Image file
        current_user: Current authenticated user
        vision_service: Vision service instance
        
    Returns:
        Detected faces with bounding boxes and metadata
    """
    try:
        # Read image data
        image_data = await image.read()
        
        # Validate file size (max 10MB)
        if len(image_data) > 10 * 1024 * 1024:
            raise HTTPException(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                detail="Image file too large (max 10MB)"
            )
        
        # Detect faces
        faces = await vision_service.detect_faces(image_data)
        
        logger.info(f"Detected {len(faces)} faces for user {current_user['username']}")
        
        return FaceDetectionResponse(
            faces=faces,
            count=len(faces)
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Face detection error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Face detection failed: {str(e)}"
        )

@router.post("/recognize-face", response_model=FaceRecognitionResponse)
async def recognize_face(
    image: UploadFile = File(..., description="Image file with face"),
    current_user: dict = Depends(get_current_user),
    vision_service: VisionService = Depends(get_vision_service)
):
    """
    Recognize face in image
    
    Returns identity if face is in database
    
    Args:
        image: Image file
        current_user: Current authenticated user
        vision_service: Vision service instance
        
    Returns:
        Identity and confidence score
    """
    try:
        # Read image data
        image_data = await image.read()
        
        # Recognize face
        result = await vision_service.recognize_face(image_data)
        
        logger.info(
            f"Face recognition result for user {current_user['username']}: "
            f"{result['identity']} ({result['confidence']:.2f})"
        )
        
        return FaceRecognitionResponse(**result)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Face recognition error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Face recognition failed: {str(e)}"
        )

@router.post("/detect-emotion", response_model=EmotionResponse)
async def detect_emotion(
    image: UploadFile = File(..., description="Image file with face"),
    current_user: dict = Depends(get_current_user),
    vision_service: VisionService = Depends(get_vision_service)
):
    """
    Detect emotion from facial expression
    
    Returns dominant emotion and all emotion scores
    
    Args:
        image: Image file
        current_user: Current authenticated user
        vision_service: Vision service instance
        
    Returns:
        Emotion classification results
    """
    try:
        # Read image data
        image_data = await image.read()
        
        # Detect emotion
        result = await vision_service.detect_emotion(image_data)
        
        logger.info(
            f"Emotion detected for user {current_user['username']}: "
            f"{result['emotion']} ({result['confidence']:.2f})"
        )
        
        return EmotionResponse(**result)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Emotion detection error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Emotion detection failed: {str(e)}"
        )

@router.post("/register-face")
async def register_face(
    image: UploadFile = File(..., description="Clear frontal face photo"),
    current_user: dict = Depends(get_current_user),
    vision_service: VisionService = Depends(get_vision_service)
):
    """
    Register current user's face for recognition
    
    Upload a clear frontal face photo to enable face recognition
    
    Args:
        image: Face image file
        current_user: Current authenticated user
        vision_service: Vision service instance
        
    Returns:
        Success message
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
            logger.info(f"✅ Face registered for user: {current_user['username']}")
            return {
                "message": "Face registered successfully",
                "user_id": current_user["user_id"]
            }
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No face detected in image or quality too low"
            )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Face registration error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Face registration failed: {str(e)}"
        )

@router.get("/status", response_model=VisionStatusResponse)
async def get_vision_status(
    current_user: dict = Depends(get_current_user),
    vision_service: VisionService = Depends(get_vision_service)
):
    """
    Get vision service status
    
    Returns information about vision service availability and capabilities
    
    Args:
        current_user: Current authenticated user
        vision_service: Vision service instance
        
    Returns:
        Vision service status
    """
    return VisionStatusResponse(
        is_ready=vision_service.is_ready(),
        face_detector_loaded=vision_service.face_detector is not None,
        face_recognizer_loaded=vision_service.face_recognizer is not None,
        emotion_detector_loaded=vision_service.emotion_detector is not None,
        registered_faces=len(vision_service.known_faces)
    )
