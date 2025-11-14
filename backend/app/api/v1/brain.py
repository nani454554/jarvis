"""
Brain API Routes
Natural language processing, conversation, memory
"""
from fastapi import APIRouter, Depends, HTTPException
from typing import List, Optional
import logging

from app.services.brain_service import BrainService
from app.core.security import get_current_user
from app.core.database import get_db
from app.models.conversation import Conversation
from app.schemas.brain import (
    CommandRequest,
    CommandResponse,
    ConversationHistoryResponse,
    BrainStatusResponse
)
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

logger = logging.getLogger(__name__)
router = APIRouter()

@router.post("/command", response_model=CommandResponse)
async def process_command(
    request: CommandRequest,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    brain_service: BrainService = Depends(lambda: BrainService())
):
    """
    Process natural language command
    
    Send text command and get AI response with actions
    """
    try:
        # Process with brain service
        result = await brain_service.process_command(
            text=request.text,
            user_id=current_user["user_id"],
            context=request.context
        )
        
        # Save to conversation history
        user_msg = Conversation(
            user_id=current_user["user_id"],
            session_id=request.session_id,
            role="user",
            content=request.text,
            intent=result["intent"]
        )
        db.add(user_msg)
        
        assistant_msg = Conversation(
            user_id=current_user["user_id"],
            session_id=request.session_id,
            role="assistant",
            content=result["text"],
            intent=result["intent"],
            confidence=int(result["confidence"] * 100)
        )
        db.add(assistant_msg)
        
        await db.commit()
        
        return CommandResponse(
            text=result["text"],
            intent=result["intent"],
            actions=result.get("actions", []),
            confidence=result["confidence"]
        )
        
    except Exception as e:
        logger.error(f"Command processing error: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Command processing failed: {str(e)}"
        )

@router.get("/conversation/{session_id}", response_model=ConversationHistoryResponse)
async def get_conversation_history(
    session_id: str,
    limit: int = 50,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Get conversation history for a session
    """
    try:
        stmt = select(Conversation).where(
            Conversation.user_id == current_user["user_id"],
            Conversation.session_id == session_id
        ).order_by(Conversation.created_at.desc()).limit(limit)
        
        result = await db.execute(stmt)
        conversations = result.scalars().all()
        
        return ConversationHistoryResponse(
            session_id=session_id,
            messages=[conv.to_dict() for conv in reversed(conversations)],
            count=len(conversations)
        )
        
    except Exception as e:
        logger.error(f"Get conversation error: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get conversation: {str(e)}"
        )

@router.post("/conversation/{session_id}/summary")
async def get_conversation_summary(
    session_id: str,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    brain_service: BrainService = Depends(lambda: BrainService())
):
    """
    Get AI-generated summary of conversation
    """
    try:
        # Get conversation history
        stmt = select(Conversation).where(
            Conversation.user_id == current_user["user_id"],
            Conversation.session_id == session_id
        ).order_by(Conversation.created_at)
        
        result = await db.execute(stmt)
        conversations = result.scalars().all()
        
        if not conversations:
            raise HTTPException(
                status_code=404,
                detail="Conversation not found"
            )
        
        # Format for summarization
        history = [
            {"role": conv.role, "content": conv.content}
            for conv in conversations
        ]
        
        # Generate summary
        summary = await brain_service.get_conversation_summary(history)
        
        return {
            "session_id": session_id,
            "summary": summary,
            "message_count": len(conversations)
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Summary generation error: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to generate summary: {str(e)}"
        )

@router.delete("/conversation/{session_id}")
async def delete_conversation(
    session_id: str,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Delete conversation history
    """
    try:
        stmt = select(Conversation).where(
            Conversation.user_id == current_user["user_id"],
            Conversation.session_id == session_id
        )
        
        result = await db.execute(stmt)
        conversations = result.scalars().all()
        
        for conv in conversations:
            await db.delete(conv)
        
        await db.commit()
        
        return {
            "message": f"Deleted {len(conversations)} messages",
            "session_id": session_id
        }
        
    except Exception as e:
        logger.error(f"Delete conversation error: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to delete conversation: {str(e)}"
        )

@router.get("/status", response_model=BrainStatusResponse)
async def get_brain_status(
    current_user: dict = Depends(get_current_user),
    brain_service: BrainService = Depends(lambda: BrainService())
):
    """
    Get brain service status
    """
    return BrainStatusResponse(
        is_ready=brain_service.is_ready(),
        llm_provider=brain_service.openai_client is not None and "openai" or "fallback",
        model=brain_service.is_initialized and "gpt-4" or "none"
    )
