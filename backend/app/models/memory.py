"""
Memory Model
Long-term memory storage with vector embeddings
"""
from sqlalchemy import Column, String, DateTime, ForeignKey, Text, JSON, Float
from sqlalchemy.orm import relationship
from datetime import datetime
import uuid
from app.core.database import Base

class Memory(Base):
    """Memory/Knowledge base model"""
    __tablename__ = "memories"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String, ForeignKey("users.id"), nullable=False, index=True)
    
    # Content
    content = Column(Text, nullable=False)
    summary = Column(Text, nullable=True)
    
    # Vector embedding (stored in separate vector DB, this is just metadata)
    vector_id = Column(String, nullable=True, index=True)
    
    # Classification
    memory_type = Column(String(50), nullable=False)  # episodic, semantic, procedural
    category = Column(String(100), nullable=True, index=True)
    tags = Column(JSON, default=list)
    
    # Importance and access
    importance_score = Column(Float, default=0.5)  # 0.0 - 1.0
    access_count = Column(Integer, default=0)
    last_accessed = Column(DateTime, nullable=True)
    
    # Metadata
    metadata = Column(JSON, default=dict)
    source = Column(String(100), nullable=True)  # conversation, document, manual
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    user = relationship("User", back_populates="memories")
    
    def __repr__(self):
        return f"<Memory {self.id} - {self.memory_type}>"
    
    def to_dict(self):
        return {
            "id": self.id,
            "content": self.content,
            "summary": self.summary,
            "memory_type": self.memory_type,
            "category": self.category,
            "tags": self.tags,
            "importance_score": self.importance_score,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
