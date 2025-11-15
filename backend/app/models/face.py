# """
# Face Model
# Face recognition data and embeddings
# """
# from sqlalchemy import Column, String, DateTime, ForeignKey, JSON, Float, Boolean, Index
# from sqlalchemy.orm import relationship
# from datetime import datetime
# import uuid
# from app.core.database import Base

# class Face(Base):
#     """
#     Face model for storing face recognition data
#     Stores embeddings and metadata for facial recognition
#     """
#     __tablename__ = "faces"
    
#     # Primary key
#     id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    
#     # Foreign keys
#     user_id = Column(String, ForeignKey("users.id"), nullable=False, index=True)
    
#     # Face data
#     embedding = Column(JSON, nullable=False)  # Face embedding vector (512-d or 128-d)
    
#     # Face metadata
#     face_image_url = Column(String(500), nullable=True)  # URL to face image
#     detection_confidence = Column(Float, nullable=True)  # Confidence of detection
    
#     # Quality metrics
#     image_quality = Column(Float, nullable=True)  # 0.0 - 1.0
#     pose_quality = Column(Float, nullable=True)  # Face angle quality
#     lighting_quality = Column(Float, nullable=True)  # Lighting conditions
    
#     # Face characteristics (for filtering/searching)
#     has_glasses = Column(Boolean, default=False)
#     has_mask = Column(Boolean, default=False)
#     age_estimate = Column(Integer, nullable=True)
#     gender_estimate = Column(String(20), nullable=True)
    
#     # Registration info
#     registration_source = Column(String(50), nullable=True)  # camera, upload, admin
#     is_primary = Column(Boolean, default=False)  # Primary face for user
#     is_active = Column(Boolean, default=True)  # Active for recognition
    
#     # Metadata
#     metadata = Column(JSON, default=dict, nullable=False)
    
#     # Timestamps
#     created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
#     last_used = Column(DateTime, nullable=True)
    
#     # Relationships
#     user = relationship("User", back_populates="faces")
    
#     # Indexes
#     __table_args__ = (
#         Index('idx_user_active', 'user_id', 'is_active'),
#         Index('idx_user_primary', 'user_id', 'is_primary'),
#     )
    
#     def __repr__(self):
#         return f"<Face {self.id} - User: {self.user_id}>"
    
#     def to_dict(self, include_embedding=False):
#         """
#         Convert face to dictionary
        
#         Args:
#             include_embedding: Whether to include embedding vector
            
#         Returns:
#             Dictionary representation
#         """
#         data = {
#             "id": self.id,
#             "user_id": self.user_id,
#             "detection_confidence": self.detection_confidence,
#             "image_quality": self.image_quality,
#             "is_primary": self.is_primary,
#             "is_active": self.is_active,
#             "created_at": self.created_at.isoformat() if self.created_at else None,
#             "last_used": self.last_used.isoformat() if self.last_used else None,
#         }
        
#         if include_embedding:
#             data["embedding"] = self.embedding
        
#         return data
    
#     async def mark_as_used(self, session):
#         """
#         Update last used timestamp
        
#         Args:
#             session: Database session
#         """
#         self.last_used = datetime.utcnow()
#         await session.commit()

"""
Face recognition model.
"""

from sqlalchemy import Column, String, Integer, ForeignKey, LargeBinary, JSON, Float
from sqlalchemy.orm import relationship

from app.models.base import BaseModel


class FaceEncoding(BaseModel):
    """Face encoding model for recognition."""
    
    __tablename__ = "face_encodings"
    
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    
    # Identity
    name = Column(String(255), nullable=False)
    label = Column(String(100))
    
    # Encoding (encrypted)
    encoding = Column(LargeBinary, nullable=False)
    encoding_version = Column(String(50), default="v1")
    
    # Image metadata
    image_url = Column(String(500))
    image_hash = Column(String(64))
    
    # Quality metrics
    face_quality_score = Column(Float)
    detection_confidence = Column(Float)
    
    # Metadata
    metadata = Column(JSON, default={})
    
    # Status
    is_active = Column(Boolean, default=True)
    
    # Relationships
    user = relationship("User", back_populates="face_encodings")
    
    def __repr__(self):
        return f"<FaceEncoding {self.id}: {self.name}>"
