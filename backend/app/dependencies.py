"""
FastAPI Dependencies
Reusable dependency injection functions
"""
from typing import AsyncGenerator
from fastapi import Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import SessionLocal
from app.core.security import get_current_user
from app.services.voice_service import VoiceService
from app.services.vision_service import VisionService
from app.services.brain_service import BrainService

# Database dependency
async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    Get database session
    Yields database session and handles cleanup
    """
    async with SessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()

# Service dependencies
def get_voice_service() -> VoiceService:
    """Get voice service instance"""
    from app.main import app
    if hasattr(app.state, "voice_service"):
        return app.state.voice_service
    raise HTTPException(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        detail="Voice service not available"
    )

def get_vision_service() -> VisionService:
    """Get vision service instance"""
    from app.main import app
    if hasattr(app.state, "vision_service"):
        return app.state.vision_service
    raise HTTPException(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        detail="Vision service not available"
    )

def get_brain_service() -> BrainService:
    """Get brain service instance"""
    from app.main import app
    if hasattr(app.state, "brain_service"):
        return app.state.brain_service
    raise HTTPException(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        detail="Brain service not available"
    )

# User dependency
async def get_current_active_user(
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Get current active user
    Validates user exists and is active
    """
    from app.models.user import User
    from sqlalchemy import select
    
    stmt = select(User).where(User.id == current_user["user_id"])
    result = await db.execute(stmt)
    user = result.scalar_one_or_none()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Inactive user"
        )
    
    return user

# Admin dependency
async def get_current_superuser(
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Get current superuser
    Validates user is superuser
    """
    user = await get_current_active_user(current_user, db)
    
    if not user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions"
        )
    
    return user
