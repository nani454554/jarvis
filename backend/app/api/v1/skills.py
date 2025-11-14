"""
Skills API Routes
Skill management and activation
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List
from pydantic import BaseModel

from app.core.database import get_db
from app.core.security import get_current_user
from app.models.skill import Skill
import logging

logger = logging.getLogger(__name__)
router = APIRouter()

class SkillResponse(BaseModel):
    """Skill response schema"""
    id: str
    skill_name: str
    skill_version: str
    is_active: bool
    is_installed: bool
    usage_count: int
    description: str
    
    class Config:
        from_attributes = True

class SkillActivateRequest(BaseModel):
    """Skill activation request"""
    skill_name: str

@router.get("/", response_model=List[SkillResponse])
async def list_skills(
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    List all available skills for current user
    
    Args:
        current_user: Current authenticated user
        db: Database session
        
    Returns:
        List of available skills
    """
    try:
        # Get user skills
        stmt = select(Skill).where(Skill.user_id == current_user["user_id"])
        result = await db.execute(stmt)
        skills = result.scalars().all()
        
        # If user has no skills, create default ones
        if not skills:
            default_skills = [
                {
                    "skill_name": "DevOpsMode",
                    "skill_version": "1.0.0",
                    "description": "Manage cloud infrastructure and CI/CD pipelines"
                },
                {
                    "skill_name": "CodingMode",
                    "skill_version": "1.0.0",
                    "description": "Code debugging, generation, and refactoring"
                },
                {
                    "skill_name": "CloudMode",
                    "skill_version": "1.0.0",
                    "description": "Cloud resource provisioning and management"
                },
                {
                    "skill_name": "CreatorMode",
                    "skill_version": "1.0.0",
                    "description": "Generate images, videos, and content"
                }
            ]
            
            for skill_data in default_skills:
                skill = Skill(
                    user_id=current_user["user_id"],
                    **skill_data,
                    metadata={"description": skill_data["description"]}
                )
                db.add(skill)
            
            await db.commit()
            
            # Re-fetch skills
            result = await db.execute(stmt)
            skills = result.scalars().all()
        
        # Convert to response
        return [
            SkillResponse(
                id=skill.id,
                skill_name=skill.skill_name,
                skill_version=skill.skill_version,
                is_active=skill.is_active,
                is_installed=skill.is_installed,
                usage_count=skill.usage_count,
                description=skill.metadata.get("description", "")
            )
            for skill in skills
        ]
        
    except Exception as e:
        logger.error(f"List skills error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list skills: {str(e)}"
        )

@router.post("/activate")
async def activate_skill(
    request: SkillActivateRequest,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Activate a skill
    
    Args:
        request: Skill activation request
        current_user: Current authenticated user
        db: Database session
        
    Returns:
        Success message
    """
    try:
        # Find skill
        stmt = select(Skill).where(
            Skill.user_id == current_user["user_id"],
            Skill.skill_name == request.skill_name
        )
        result = await db.execute(stmt)
        skill = result.scalar_one_or_none()
        
        if not skill:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Skill '{request.skill_name}' not found"
            )
        
        # Activate skill
        await skill.activate(db)
        
        logger.info(
            f"✅ Skill activated: {skill.skill_name} for user {current_user['username']}"
        )
        
        return {
            "message": f"Skill '{skill.skill_name}' activated",
            "skill_id": skill.id
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Activate skill error: {e}")
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to activate skill: {str(e)}"
        )

@router.post("/deactivate")
async def deactivate_skill(
    request: SkillActivateRequest,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Deactivate a skill
    
    Args:
        request: Skill deactivation request
        current_user: Current authenticated user
        db: Database session
        
    Returns:
        Success message
    """
    try:
        # Find skill
        stmt = select(Skill).where(
            Skill.user_id == current_user["user_id"],
            Skill.skill_name == request.skill_name
        )
        result = await db.execute(stmt)
        skill = result.scalar_one_or_none()
        
        if not skill:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Skill '{request.skill_name}' not found"
            )
        
        # Deactivate skill
        await skill.deactivate(db)
        
        logger.info(
            f"Skill deactivated: {skill.skill_name} for user {current_user['username']}"
        )
        
        return {
            "message": f"Skill '{skill.skill_name}' deactivated",
            "skill_id": skill.id
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Deactivate skill error: {e}")
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to deactivate skill: {str(e)}"
        )

@router.get("/active")
async def get_active_skills(
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Get all active skills for current user
    
    Args:
        current_user: Current authenticated user
        db: Database session
        
    Returns:
        List of active skills
    """
    try:
        stmt = select(Skill).where(
            Skill.user_id == current_user["user_id"],
            Skill.is_active == True
        )
        result = await db.execute(stmt)
        skills = result.scalars().all()
        
        return {
            "active_skills": [skill.skill_name for skill in skills],
            "count": len(skills)
        }
        
    except Exception as e:
        logger.error(f"Get active skills error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get active skills: {str(e)}"
        )
