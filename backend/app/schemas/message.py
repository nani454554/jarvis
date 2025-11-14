"""
Message Schemas
Pydantic models for conversation messages
"""
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List
from datetime import datetime

class MessageBase(BaseModel):
    """Base message schema"""
    content: str = Field(..., min_length=1)
    role: str = Field(..., pattern="^(user|assistant|system)$")

class MessageCreate(MessageBase):
    """Schema for creating a message"""
    session_id: Optional[str] = None
    intent: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None

class Message(MessageBase):
    """Schema for message response"""
    id: str
    user_id: str
    session_id: Optional[str]
    intent: Optional[str]
    confidence: Optional[int]
    metadata: Dict[str, Any]
    created_at: datetime
    
    class Config:
        from_attributes = True

class ConversationResponse(BaseModel):
    """Schema for conversation history response"""
    session_id: Optional[str]
    messages: List[Message]
    count: int
