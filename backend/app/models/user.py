"""
User Model
Authentication and user management
"""
from sqlalchemy import Column, String, Boolean, DateTime, Integer, JSON, Text
from sqlalchemy.orm import relationship
from datetime import datetime
import uuid
from app.core.database import Base

class User(Base):
    """
    User model for authentication and profile management
    """
    __tablename__ = "users"
    
    # Primary key
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    
    # Authentication
    username = Column(String(50), unique=True, nullable=False, index=True)
    email = Column(String(255), unique=True, nullable=False, index=True)
    hashed_password = Column(String(255), nullable=False)
    
    # Profile
    full_name = Column(String(100), nullable=True)
    avatar_url = Column(String(500), nullable=True)
    bio = Column(Text, nullable=True)
    
    # Security
    is_active = Column(Boolean, default=True, nullable=False)
    is_superuser = Column(Boolean, default=False, nullable=False)
    is_verified = Column(Boolean, default=False, nullable=False)
    
    # Biometric data (stored as JSON)
    face_embeddings = Column(JSON, nullable=True)  # Face recognition embeddings
    voice_signature = Column(JSON, nullable=True)  # Voice biometric data
    
    # Preferences (stored as JSON)
    preferences = Column(JSON, default=dict, nullable=False)
    settings = Column(JSON, default=dict, nullable=False)
    
    # API keys
    api_key = Column(String(64), unique=True, nullable=True, index=True)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    last_login = Column(DateTime, nullable=True)
    
    # Relationships
    conversations = relationship(
        "Conversation",
        back_populates="user",
        cascade="all, delete-orphan"
    )
    
    memories = relationship(
        "Memory",
        back_populates="user",
        cascade="all, delete-orphan"
    )
    
    faces = relationship(
        "Face",
        back_populates="user",
        cascade="all, delete-orphan"
    )
    
    skills = relationship(
        "Skill",
        back_populates="user",
        cascade="all, delete-orphan"
    )
    
    def __repr__(self):
        return f"<User {self.username}>"
    
    def to_dict(self, include_sensitive=False):
        """
        Convert user to dictionary
        
        Args:
            include_sensitive: Whether to include sensitive data
            
        Returns:
            Dictionary representation of user
        """
        data = {
            "id": self.id,
            "username": self.username,
            "email": self.email,
            "full_name": self.full_name,
            "avatar_url": self.avatar_url,
            "is_active": self.is_active,
            "is_verified": self.is_verified,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "last_login": self.last_login.isoformat() if self.last_login else None,
        }
        
        if include_sensitive:
            data["is_superuser"] = self.is_superuser
            data["preferences"] = self.preferences
            data["settings"] = self.settings
        
        return data
    
    @property
    def has_face_recognition(self) -> bool:
        """Check if user has face recognition enabled"""
        return self.face_embeddings is not None and len(self.face_embeddings) > 0
    
    @property
    def has_voice_recognition(self) -> bool:
        """Check if user has voice recognition enabled"""
        return self.voice_signature is not None
