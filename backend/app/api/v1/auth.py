"""
Authentication Routes
User registration, login, token management
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from datetime import datetime
from typing import Optional

from app.core.database import get_db
from app.core.security import security_manager, get_current_user
from app.models.user import User
from app.schemas.user import (
    UserCreate,
    UserUpdate,
    UserResponse,
    UserLogin,
    TokenResponse
)
from app.core.events import events, Events
import logging

logger = logging.getLogger(__name__)
router = APIRouter()

@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def register(
    user_data: UserCreate,
    db: AsyncSession = Depends(get_db)
):
    """
    Register new user
    
    Args:
        user_data: User registration data
        db: Database session
        
    Returns:
        Created user
        
    Raises:
        HTTPException: If username or email already exists
    """
    try:
        # Check if user exists
        stmt = select(User).where(
            (User.username == user_data.username) | (User.email == user_data.email)
        )
        result = await db.execute(stmt)
        existing_user = result.scalar_one_or_none()
        
        if existing_user:
            if existing_user.username == user_data.username:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Username already registered"
                )
            else:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Email already registered"
                )
        
        # Create new user
        hashed_password = security_manager.hash_password(user_data.password)
        
        new_user = User(
            username=user_data.username,
            email=user_data.email,
            full_name=user_data.full_name,
            hashed_password=hashed_password,
            preferences={
                "theme": "dark",
                "voice_enabled": True,
                "camera_enabled": True,
                "notifications": True
            },
            settings={
                "language": "en",
                "timezone": "UTC"
            }
        )
        
        db.add(new_user)
        await db.commit()
        await db.refresh(new_user)
        
        logger.info(f"✅ New user registered: {new_user.username}")
        
        # Publish event
        await events.publish(Events.USER_REGISTERED, {
            "user_id": new_user.id,
            "username": new_user.username
        })
        
        return UserResponse.model_validate(new_user)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Registration error: {e}")
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Registration failed"
        )

@router.post("/login", response_model=TokenResponse)
async def login(
    credentials: UserLogin,
    db: AsyncSession = Depends(get_db)
):
    """
    User login - returns access and refresh tokens
    
    Args:
        credentials: Login credentials
        db: Database session
        
    Returns:
        Access token, refresh token, and user info
        
    Raises:
        HTTPException: If credentials are invalid
    """
    try:
        # Find user by username or email
        stmt = select(User).where(
            (User.username == credentials.username) | 
            (User.email == credentials.username)
        )
        result = await db.execute(stmt)
        user = result.scalar_one_or_none()
        
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Incorrect username or password"
            )
        
        # Verify password
        if not security_manager.verify_password(
            credentials.password,
            user.hashed_password
        ):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Incorrect username or password"
            )
        
        # Check if user is active
        if not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Account is inactive"
            )
        
        # Create tokens
        access_token = security_manager.create_access_token(
            data={
                "sub": user.id,
                "username": user.username,
                "email": user.email
            }
        )
        
        refresh_token = security_manager.create_refresh_token(
            data={"sub": user.id}
        )
        
        # Update last login
        user.last_login = datetime.utcnow()
        await db.commit()
        
        logger.info(f"✅ User logged in: {user.username}")
        
        # Publish event
        await events.publish(Events.USER_LOGIN, {
            "user_id": user.id,
            "username": user.username
        })
        
        return TokenResponse(
            access_token=access_token,
            refresh_token=refresh_token,
            user=UserResponse.model_validate(user)
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Login error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Login failed"
        )

@router.post("/refresh", response_model=TokenResponse)
async def refresh_token(
    refresh_token: str,
    db: AsyncSession = Depends(get_db)
):
    """
    Refresh access token using refresh token
    
    Args:
        refresh_token: Refresh token
        db: Database session
        
    Returns:
        New access and refresh tokens
    """
    try:
        # Decode refresh token
        payload = security_manager.decode_token(refresh_token)
        
        if payload.get("type") != "refresh":
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token type"
            )
        
        user_id = payload.get("sub")
        
        # Get user
        stmt = select(User).where(User.id == user_id)
        result = await db.execute(stmt)
        user = result.scalar_one_or_none()
        
        if not user or not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid user"
            )
        
        # Create new tokens
        new_access_token = security_manager.create_access_token(
            data={
                "sub": user.id,
                "username": user.username,
                "email": user.email
            }
        )
        
        new_refresh_token = security_manager.create_refresh_token(
            data={"sub": user.id}
        )
        
        return TokenResponse(
            access_token=new_access_token,
            refresh_token=new_refresh_token,
            user=UserResponse.model_validate(user)
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Token refresh error: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token"
        )

@router.get("/me", response_model=UserResponse)
async def get_current_user_info(
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Get current user information
    
    Args:
        current_user: Current authenticated user
        db: Database session
        
    Returns:
        User information
    """
    try:
        stmt = select(User).where(User.id == current_user["user_id"])
        result = await db.execute(stmt)
        user = result.scalar_one_or_none()
        
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        
        return UserResponse.model_validate(user)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Get user error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get user"
        )

@router.put("/me", response_model=UserResponse)
async def update_current_user(
    user_update: UserUpdate,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Update current user profile
    
    Args:
        user_update: User update data
        current_user: Current authenticated user
        db: Database session
        
    Returns:
        Updated user information
    """
    try:
        stmt = select(User).where(User.id == current_user["user_id"])
        result = await db.execute(stmt)
        user = result.scalar_one_or_none()
        
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        
        # Update fields
        update_data = user_update.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(user, field, value)
        
        await db.commit()
        await db.refresh(user)
        
        logger.info(f"✅ User updated: {user.username}")
        
        return UserResponse.model_validate(user)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Update user error: {e}")
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update user"
        )

@router.post("/logout")
async def logout(
    current_user: dict = Depends(get_current_user)
):
    """
    Logout user (client should delete tokens)
    
    Args:
        current_user: Current authenticated user
        
    Returns:
        Success message
    """
    logger.info(f"User logged out: {current_user['username']}")
    
    # Publish event
    await events.publish(Events.USER_LOGOUT, {
        "user_id": current_user["user_id"],
        "username": current_user["username"]
    })
    
    return {"message": "Successfully logged out"}

@router.post("/change-password")
async def change_password(
    old_password: str,
    new_password: str,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Change user password
    
    Args:
        old_password: Current password
        new_password: New password
        current_user: Current authenticated user
        db: Database session
        
    Returns:
        Success message
    """
    try:
        stmt = select(User).where(User.id == current_user["user_id"])
        result = await db.execute(stmt)
        user = result.scalar_one_or_none()
        
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        
        # Verify old password
        if not security_manager.verify_password(old_password, user.hashed_password):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Incorrect password"
            )
        
        # Update password
        user.hashed_password = security_manager.hash_password(new_password)
        await db.commit()
        
        logger.info(f"✅ Password changed for user: {user.username}")
        
        return {"message": "Password changed successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Change password error: {e}")
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to change password"
        )
