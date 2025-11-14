"""
API v1 Routes
All version 1 API endpoints
"""
from fastapi import APIRouter

# Import routers
from app.api.v1 import auth, voice, vision, brain, skills, system

# Create main v1 router
router = APIRouter()

# Include all sub-routers
router.include_router(auth.router, prefix="/auth", tags=["auth"])
router.include_router(voice.router, prefix="/voice", tags=["voice"])
router.include_router(vision.router, prefix="/vision", tags=["vision"])
router.include_router(brain.router, prefix="/brain", tags=["brain"])
router.include_router(skills.router, prefix="/skills", tags=["skills"])
router.include_router(system.router, prefix="/system", tags=["system"])

__all__ = ["router"]
