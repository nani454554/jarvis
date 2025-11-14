"""
Conversation Model
Chat history and context storage
"""
from sqlalchemy import Column, String, DateTime, ForeignKey, Text, JSON, Integer, Index
from sqlalchemy.orm import relationship
from datetime import datetime
import uuid
from app.core.database import Base

class Conversation(Base):
    """
    Conversation model for storing chat history
    Supports both user and assistant messages with metadata
    """
    __tablename__ = "conversations"
    
    # Primary key
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    
    # Foreign keys
    user_id = Column(String, ForeignKey("users.id"), nullable=False, index=True)
    
    # Session grouping
    session_id = Column(String, nullable=True, index=True)
    
    # Message data
    role = Column(String(20), nullable=False)  # user, assistant, system
    content = Column(Text, nullable=False)
    
    # Intent classification
    intent = Column(String(50), nullable=True, index=True)
    confidence = Column(Integer, nullable=True)  # 0-100
    
    # Metadata (arbitrary JSON data)
    metadata = Column(JSON, default=dict, nullable=False)
    
    # Embeddings for semantic search
    embedding = Column(JSON, nullable=True)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    
    # Relationships
    user = relationship("User", back_populates="conversations")
    
    # Indexes for performance
    __table_args__ = (
        Index('idx_user_session', 'user_id', 'session_id'),
        Index('idx_user_created', 'user_id', 'created_at'),
        Index('idx_intent', 'intent'),
    )
    
    def __repr__(self):
        return f"<Conversation {self.id} - {self.role}: {self.content[:50]}>"
    
    def to_dict(self):
        """Convert conversation to dictionary"""
        return {
            "id": self.id,
            "user_id": self.user_id,
            "session_id": self.session_id,
            "role": self.role,
            "content": self.content,
            "intent": self.intent,
            "confidence": self.confidence,
            "metadata": self.metadata,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
    
    @classmethod
    def create_message(cls, user_id: str, role: str, content: str, **kwargs):
        """
        Factory method to create a new conversation message
        
        Args:
            user_id: User ID
            role: Message role (user/assistant/system)
            content: Message content
            **kwargs: Additional fields
            
        Returns:
            Conversation instance
        """
        return cls(
            user_id=user_id,
            role=role,
            content=content,
            **kwargs
        )
