# """
# Memory Model
# Long-term memory and knowledge base with RAG support
# """
# from sqlalchemy import Column, String, DateTime, ForeignKey, Text, JSON, Float, Integer, Index
# from sqlalchemy.orm import relationship
# from datetime import datetime
# import uuid
# from app.core.database import Base

# class Memory(Base):
#     """
#     Memory model for long-term knowledge storage
#     Supports RAG (Retrieval Augmented Generation) with vector embeddings
#     """
#     __tablename__ = "memories"
    
#     # Primary key
#     id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    
#     # Foreign keys
#     user_id = Column(String, ForeignKey("users.id"), nullable=False, index=True)
    
#     # Content
#     content = Column(Text, nullable=False)
#     summary = Column(Text, nullable=True)
#     title = Column(String(200), nullable=True)
    
#     # Vector embedding reference (actual vectors stored in vector DB)
#     vector_id = Column(String, nullable=True, index=True)
    
#     # Classification
#     memory_type = Column(
#         String(50),
#         nullable=False,
#         default="semantic",
#         index=True
#     )  # episodic, semantic, procedural
    
#     category = Column(String(100), nullable=True, index=True)
#     tags = Column(JSON, default=list, nullable=False)
    
#     # Importance and relevance
#     importance_score = Column(Float, default=0.5, nullable=False)  # 0.0 - 1.0
#     access_count = Column(Integer, default=0, nullable=False)
#     last_accessed = Column(DateTime, nullable=True)
    
#     # Source information
#     source = Column(String(100), nullable=True)  # conversation, document, manual, web
#     source_id = Column(String, nullable=True)  # Reference to source
    
#     # Metadata (arbitrary JSON data)
#     metadata = Column(JSON, default=dict, nullable=False)
    
#     # Timestamps
#     created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
#     updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
#     # Relationships
#     user = relationship("User", back_populates="memories")
    
#     # Indexes for performance
#     __table_args__ = (
#         Index('idx_user_type', 'user_id', 'memory_type'),
#         Index('idx_user_category', 'user_id', 'category'),
#         Index('idx_importance', 'importance_score'),
#         Index('idx_access_count', 'access_count'),
#     )
    
#     def __repr__(self):
#         return f"<Memory {self.id} - {self.memory_type}: {self.title or self.content[:50]}>"
    
#     def to_dict(self):
#         """Convert memory to dictionary"""
#         return {
#             "id": self.id,
#             "user_id": self.user_id,
#             "content": self.content,
#             "summary": self.summary,
#             "title": self.title,
#             "memory_type": self.memory_type,
#             "category": self.category,
#             "tags": self.tags,
#             "importance_score": self.importance_score,
#             "access_count": self.access_count,
#             "source": self.source,
#             "created_at": self.created_at.isoformat() if self.created_at else None,
#             "last_accessed": self.last_accessed.isoformat() if self.last_accessed else None,
#         }
    
#     async def increment_access(self, session):
#         """
#         Increment access count and update last accessed time
        
#         Args:
#             session: Database session
#         """
#         self.access_count += 1
#         self.last_accessed = datetime.utcnow()
#         await session.commit()
    
#     @classmethod
#     def create_from_conversation(
#         cls,
#         user_id: str,
#         conversation_id: str,
#         content: str,
#         **kwargs
#     ):
#         """
#         Factory method to create memory from conversation
        
#         Args:
#             user_id: User ID
#             conversation_id: Source conversation ID
#             content: Memory content
#             **kwargs: Additional fields
            
#         Returns:
#             Memory instance
#         """
#         return cls(
#             user_id=user_id,
#             content=content,
#             memory_type="episodic",
#             source="conversation",
#             source_id=conversation_id,
#             **kwargs
#         )

"""
RAG memory and document models.
"""

from sqlalchemy import Column, String, Integer, ForeignKey, Text, JSON, LargeBinary, Enum as SQLEnum
from sqlalchemy.orm import relationship
import enum

from app.models.base import BaseModel


class DocumentType(str, enum.Enum):
    """Document type enumeration."""
    PDF = "pdf"
    TEXT = "text"
    MARKDOWN = "markdown"
    CODE = "code"
    WEB = "web"
    OTHER = "other"


class Document(BaseModel):
    """Document model for RAG."""
    
    __tablename__ = "documents"
    
    # Metadata
    title = Column(String(500), nullable=False)
    doc_type = Column(SQLEnum(DocumentType), nullable=False)
    source = Column(String(1000))
    file_path = Column(String(1000))
    url = Column(String(2000))
    
    # Content
    content = Column(Text)
    content_hash = Column(String(64), index=True)
    
    # Metadata
    metadata = Column(JSON, default={})
    tags = Column(JSON, default=[])
    
    # Processing
    is_processed = Column(Boolean, default=False)
    chunk_count = Column(Integer, default=0)
    
    # Relationships
    chunks = relationship("DocumentChunk", back_populates="document", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<Document {self.id}: {self.title}>"


class DocumentChunk(BaseModel):
    """Document chunk model for vector storage."""
    
    __tablename__ = "document_chunks"
    
    document_id = Column(Integer, ForeignKey("documents.id", ondelete="CASCADE"), nullable=False)
    
    # Content
    content = Column(Text, nullable=False)
    chunk_index = Column(Integer, nullable=False)
    
    # Embedding
    embedding = Column(LargeBinary)
    embedding_model = Column(String(200))
    
    # Vector store reference
    vector_id = Column(String(100))
    
    # Metadata
    metadata = Column(JSON, default={})
    token_count = Column(Integer)
    
    # Relationships
    document = relationship("Document", back_populates="chunks")
    
    def __repr__(self):
        return f"<DocumentChunk {self.id}: Doc {self.document_id}, Chunk {self.chunk_index}>"
