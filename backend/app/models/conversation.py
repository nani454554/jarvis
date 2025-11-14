"""
Conversation Model
Stores chat history and context
"""
from sqlalchemy import Column, String, DateTime, ForeignKey, Text, JSON, Integer
from sqlalchemy.orm import relationship
from datetime import datetime
import uuid
from app.core.database import Base

class Conversation(Base):
    """Conversation model"""
    __tablename__ = "conversations"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String, ForeignKey("users.id"), nullable=False, index=True)
    session_id = Column(String, nullable=True, index=True)
    
    # Message data
    role = Column(String(20), nullable=False)  # user, assistant, system
    content = Column(Text, nullable=False)
    
    # Metadata
    metadata = Column(JSON, default=dict)
    intent = Column(String(50), nullable=True)
    confidence = Column(Integer, nullable=True)  # 0-100
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    
    # Relationships
    user = relationship("User", back_populates="conversations")
    
    def __repr__(self):
        return f"<Conversation {self.id} - {self.role}>"
    
    def to_dict(self):
        return {
            "id": self.id,
            "role": self.role,
            "content": self.content,
            "intent": self.intent,
            "confidence": self.confidence,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "metadata": self.metadata,
        }
