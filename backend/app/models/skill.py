"""
Skill Model
User skills and capabilities tracking
"""
from sqlalchemy import Column, String, DateTime, ForeignKey, JSON, Boolean, Integer, Index
from sqlalchemy.orm import relationship
from datetime import datetime
import uuid
from app.core.database import Base

class Skill(Base):
    """
    Skill model for tracking activated skills and their usage
    """
    __tablename__ = "skills"
    
    # Primary key
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    
    # Foreign keys
    user_id = Column(String, ForeignKey("users.id"), nullable=False, index=True)
    
    # Skill identification
    skill_name = Column(String(100), nullable=False, index=True)
    skill_version = Column(String(20), nullable=True)
    
    # Skill state
    is_active = Column(Boolean, default=False, nullable=False)
    is_installed = Column(Boolean, default=True, nullable=False)
    
    # Usage statistics
    usage_count = Column(Integer, default=0, nullable=False)
    last_used = Column(DateTime, nullable=True)
    
    # Configuration
    config = Column(JSON, default=dict, nullable=False)
    
    # Permissions
    permissions = Column(JSON, default=list, nullable=False)
    
    # Metadata
    metadata = Column(JSON, default=dict, nullable=False)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    activated_at = Column(DateTime, nullable=True)
    
    # Relationships
    user = relationship("User", back_populates="skills")
    
    # Indexes
    __table_args__ = (
        Index('idx_user_skill', 'user_id', 'skill_name', unique=True),
        Index('idx_user_active', 'user_id', 'is_active'),
    )
    
    def __repr__(self):
        return f"<Skill {self.skill_name} - User: {self.user_id}>"
    
    def to_dict(self):
        """Convert skill to dictionary"""
        return {
            "id": self.id,
            "skill_name": self.skill_name,
            "skill_version": self.skill_version,
            "is_active": self.is_active,
            "is_installed": self.is_installed,
            "usage_count": self.usage_count,
            "config": self.config,
            "permissions": self.permissions,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "last_used": self.last_used.isoformat() if self.last_used else None,
            "activated_at": self.activated_at.isoformat() if self.activated_at else None,
        }
    
    async def activate(self, session):
        """
        Activate skill
        
        Args:
            session: Database session
        """
        self.is_active = True
        self.activated_at = datetime.utcnow()
        await session.commit()
    
    async def deactivate(self, session):
        """
        Deactivate skill
        
        Args:
            session: Database session
        """
        self.is_active = False
        await session.commit()
    
    async def increment_usage(self, session):
        """
        Increment usage count
        
        Args:
            session: Database session
        """
        self.usage_count += 1
        self.last_used = datetime.utcnow()
        await session.commit()
