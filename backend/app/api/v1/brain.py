"""
Brain API Routes
Natural language processing, conversation, memory management
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc
from typing import Optional, List

from app.core.database import get_db
from app.core.security import get_current_user
from app.dependencies import get_brain_service
from app.services.brain_service import BrainService
from app.models.conversation import Conversation
from app.schemas.message import MessageCreate, Message, ConversationResponse
from pydantic import BaseModel, Field
import logging

logger = logging.getLogger(__name__)
router = APIRouter()

class CommandRequest(BaseModel):
    """Command request schema"""
    text: str = Field(..., min_length=1, max_length=5000)
    session_id: Optional[str] = None
    context: Optional[dict] = None

class CommandResponse(BaseModel):
    """Command response schema"""
    text: str
    intent: str
    actions: List[dict] = []
    confidence: float
    timestamp: str

@router.post("/command", response_model=CommandResponse)
async def process_command(
    request: CommandRequest,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    brain_service: BrainService = Depends(get_brain_service)
):
    """
    Process natural language command
    
    Send text command and get AI response with actions
    
    Args:
        request: Command request
        current_user: Current authenticated user
        db: Database session
        brain_service: Brain service instance
        
    Returns:
        AI response with intent, actions, and metadata
    """
    try:
        # Process with brain service
        result = await brain_service.process_command(
            text=request.text,
            user_id=current_user["user_id"],
            context=request.context
        )
        
        # Save user message to conversation history
        user_msg = Conversation(
            user_id=current_user["user_id"],
            session_id=request.session_id,
            role="user",
            content=request.text,
            intent=result["intent"],
            metadata=request.context or {}
        )
        db.add(user_msg)
        
        # Save assistant response to conversation history
        assistant_msg = Conversation(
            user_id=current_user["user_id"],
            session_id=request.session_id,
            role="assistant",
            content=result["text"],
            intent=result["intent"],
            confidence=int(result["confidence"] * 100),
            metadata={"actions": result.get("actions", [])}
        )
        db.add(assistant_msg)
        
        await db.commit()
        
        logger.info(
            f"Command processed for {current_user['username']}: "
            f"{request.text[:50]} -> {result['intent']}"
        )
        
        return CommandResponse(
            text=result["text"],
            intent=result["intent"],
            actions=result.get("actions", []),
            confidence=result["confidence"],
            timestamp=result["timestamp"]
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Command processing error: {e}")
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Command processing failed: {str(e)}"
        )

@router.get("/conversation/{session_id}", response_model=ConversationResponse)
async def get_conversation_history(
    session_id: str,
    limit: int = 50,
    offset: int = 0,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Get conversation history for a session
    
    Args:
        session_id: Session identifier
        limit: Maximum number of messages to return
        offset: Number of messages to skip
        current_user: Current authenticated user
        db: Database session
        
    Returns:
        Conversation history with messages
    """
    try:
        # Query conversation messages
        stmt = select(Conversation).where(
            Conversation.user_id == current_user["user_id"],
            Conversation.session_id == session_id
        ).order_by(
            desc(Conversation.created_at)
        ).limit(limit).offset(offset)
        
        result = await db.execute(stmt)
        conversations = result.scalars().all()
        
        # Convert to response models
        messages = [
            Message(
                id=conv.id,
                user_id=conv.user_id,
                session_id=conv.session_id,
                role=conv.role,
                content=conv.content,
                intent=conv.intent,
                confidence=conv.confidence,
                metadata=conv.metadata,
                created_at=conv.created_at
            )
            for conv in reversed(conversations)
        ]
        
        return ConversationResponse(
            session_id=session_id,
            messages=messages,
            count=len(messages)
        )
        
    except Exception as e:
        logger.error(f"Get conversation error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get conversation: {str(e)}"
        )

@router.get("/conversations")
async def get_user_conversations(
    limit: int = 20,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Get all user's conversation sessions
    
    Args:
        limit: Maximum number of sessions to return
        current_user: Current authenticated user
        db: Database session
        
    Returns:
        List of conversation sessions with metadata
    """
    try:
        # Get unique session IDs with latest message
        stmt = select(
            Conversation.session_id,
            Conversation.created_at,
            Conversation.content
        ).where(
            Conversation.user_id == current_user["user_id"],
            Conversation.session_id.isnot(None)
        ).order_by(
            desc(Conversation.created_at)
        ).limit(limit)
        
        result = await db.execute(stmt)
        sessions = result.all()
        
        # Group by session and get metadata
        session_map = {}
        for session_id, created_at, content in sessions:
            if session_id not in session_map:
                session_map[session_id] = {
                    "session_id": session_id,
                    "last_message": content[:100],
                    "last_activity": created_at.isoformat()
                }
        
        return {
            "sessions": list(session_map.values()),
            "count": len(session_map)
        }
        
    except Exception as e:
        logger.error(f"Get conversations error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get conversations: {str(e)}"
        )

@router.post("/conversation/{session_id}/summary")
async def get_conversation_summary(
    session_id: str,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    brain_service: BrainService = Depends(get_brain_service)
):
    """
    Get AI-generated summary of conversation
    
    Args:
        session_id: Session identifier
        current_user: Current authenticated user
        db: Database session
        brain_service: Brain service instance
        
    Returns:
        Conversation summary
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
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Conversation not found"
            )
        
        # Format for summarization
        history = [
            {"role": conv.role, "content": conv.content}
            for conv in conversations
        ]
        
        # Generate summary
        summary = await brain_service.get_conversation_summary(history)
        
        logger.info(f"Summary generated for session {session_id}")
        
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
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
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
    
    Args:
        session_id: Session identifier
        current_user: Current authenticated user
        db: Database session
        
    Returns:
        Success message
    """
    try:
        # Get all messages in session
        stmt = select(Conversation).where(
            Conversation.user_id == current_user["user_id"],
            Conversation.session_id == session_id
        )
        
        result = await db.execute(stmt)
        conversations = result.scalars().all()
        
        # Delete all messages
        for conv in conversations:
            await db.delete(conv)
        
        await db.commit()
        
        logger.info(
            f"Deleted {len(conversations)} messages from session {session_id}"
        )
        
        return {
            "message": f"Deleted {len(conversations)} messages",
            "session_id": session_id
        }
        
    except Exception as e:
        logger.error(f"Delete conversation error: {e}")
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete conversation: {str(e)}"
        )

@router.post("/clear-history")
async def clear_all_history(
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Clear all conversation history for current user
    
    Args:
        current_user: Current authenticated user
        db: Database session
        
    Returns:
        Success message with count
    """
    try:
        # Get all user conversations
        stmt = select(Conversation).where(
            Conversation.user_id == current_user["user_id"]
        )
        
        result = await db.execute(stmt)
        conversations = result.scalars().all()
        
        # Delete all
        count = len(conversations)
        for conv in conversations:
            await db.delete(conv)
        
        await db.commit()
        
        logger.info(
            f"Cleared {count} messages for user {current_user['username']}"
        )
        
        return {
            "message": f"Cleared {count} messages",
            "user_id": current_user["user_id"]
        }
        
    except Exception as e:
        logger.error(f"Clear history error: {e}")
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to clear history: {str(e)}"
        )

@router.get("/status")
async def get_brain_status(
    current_user: dict = Depends(get_current_user),
    brain_service: BrainService = Depends(get_brain_service)
):
    """
    Get brain service status
    
    Args:
        current_user: Current authenticated user
        brain_service: Brain service instance
        
    Returns:
        Brain service status and capabilities
    """
    return {
        "is_ready": brain_service.is_ready(),
        "llm_provider": "openai" if brain_service.openai_client else "fallback",
        "model": "gpt-4" if brain_service.is_initialized else "mock",
        "conversation_history_length": len(brain_service.conversation_history)
    }
