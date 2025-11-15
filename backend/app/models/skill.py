# """
# Skill Model
# User skills and capabilities tracking
# """
# from sqlalchemy import Column, String, DateTime, ForeignKey, JSON, Boolean, Integer, Index
# from sqlalchemy.orm import relationship
# from datetime import datetime
# import uuid
# from app.core.database import Base

# class Skill(Base):
#     """
#     Skill model for tracking activated skills and their usage
#     """
#     __tablename__ = "skills"
    
#     # Primary key
#     id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    
#     # Foreign keys
#     user_id = Column(String, ForeignKey("users.id"), nullable=False, index=True)
    
#     # Skill identification
#     skill_name = Column(String(100), nullable=False, index=True)
#     skill_version = Column(String(20), nullable=True)
    
#     # Skill state
#     is_active = Column(Boolean, default=False, nullable=False)
#     is_installed = Column(Boolean, default=True, nullable=False)
    
#     # Usage statistics
#     usage_count = Column(Integer, default=0, nullable=False)
#     last_used = Column(DateTime, nullable=True)
    
#     # Configuration
#     config = Column(JSON, default=dict, nullable=False)
    
#     # Permissions
#     permissions = Column(JSON, default=list, nullable=False)
    
#     # Metadata
#     metadata = Column(JSON, default=dict, nullable=False)
    
#     # Timestamps
#     created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
#     updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
#     activated_at = Column(DateTime, nullable=True)
    
#     # Relationships
#     user = relationship("User", back_populates="skills")
    
#     # Indexes
#     __table_args__ = (
#         Index('idx_user_skill', 'user_id', 'skill_name', unique=True),
#         Index('idx_user_active', 'user_id', 'is_active'),
#     )
    
#     def __repr__(self):
#         return f"<Skill {self.skill_name} - User: {self.user_id}>"
    
#     def to_dict(self):
#         """Convert skill to dictionary"""
#         return {
#             "id": self.id,
#             "skill_name": self.skill_name,
#             "skill_version": self.skill_version,
#             "is_active": self.is_active,
#             "is_installed": self.is_installed,
#             "usage_count": self.usage_count,
#             "config": self.config,
#             "permissions": self.permissions,
#             "created_at": self.created_at.isoformat() if self.created_at else None,
#             "last_used": self.last_used.isoformat() if self.last_used else None,
#             "activated_at": self.activated_at.isoformat() if self.activated_at else None,
#         }
    
#     async def activate(self, session):
#         """
#         Activate skill
        
#         Args:
#             session: Database session
#         """
#         self.is_active = True
#         self.activated_at = datetime.utcnow()
#         await session.commit()
    
#     async def deactivate(self, session):
#         """
#         Deactivate skill
        
#         Args:
#             session: Database session
#         """
#         self.is_active = False
#         await session.commit()
    
#     async def increment_usage(self, session):
#         """
#         Increment usage count
        
#         Args:
#             session: Database session
#         """
#         self.usage_count += 1
#         self.last_used = datetime.utcnow()
#         await session.commit()

"""
Skill and execution tracking models.
"""

from sqlalchemy import Column, String, Integer, Text, JSON, Float, Enum as SQLEnum
from sqlalchemy.orm import relationship
import enum

from app.models.base import BaseModel


class SkillCategory(str, enum.Enum):
    """Skill category enumeration."""
    DEVOPS = "devops"
    CODING = "coding"
    CLOUD = "cloud"
    CREATOR = "creator"
    SYSTEM = "system"
    CUSTOM = "custom"


class SkillStatus(str, enum.Enum):
    """Skill execution status."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class Skill(BaseModel):
    """Skill definition model."""
    
    __tablename__ = "skills"
    
    # Identity
    name = Column(String(200), unique=True, nullable=False)
    display_name = Column(String(200), nullable=False)
    description = Column(Text)
    
    # Classification
    category = Column(SQLEnum(SkillCategory), nullable=False)
    tags = Column(JSON, default=[])
    
    # Configuration
    config = Column(JSON, default={})
    parameters_schema = Column(JSON, default={})
    
    # Code
    handler_path = Column(String(500))
    
    # Metadata
    version = Column(String(50), default="1.0.0")
    is_enabled = Column(Boolean, default=True)
    is_public = Column(Boolean, default=True)
    
    # Usage stats
    execution_count = Column(Integer, default=0)
    success_count = Column(Integer, default=0)
    avg_execution_time = Column(Float)
    
    # Relationships
    executions = relationship("SkillExecution", back_populates="skill")
    
    def __repr__(self):
        return f"<Skill {self.name}>"


class SkillExecution(BaseModel):
    """Skill execution tracking model."""
    
    __tablename__ = "skill_executions"
    
    skill_id = Column(Integer, ForeignKey("skills.id", ondelete="CASCADE"), nullable=False)
    
    # Input/Output
    input_data = Column(JSON)
    output_data = Column(JSON)
    
    # Execution
    status = Column(SQLEnum(SkillStatus), default=SkillStatus.PENDING)
    error_message = Column(Text)
    
    # Metrics
    execution_time_ms = Column(Float)
    tokens_used = Column(Integer)
    
    # Metadata
    metadata = Column(JSON, default={})
    
    # Relationships
    skill = relationship("Skill", back_populates="executions")
    
    def __repr__(self):
        return f"<SkillExecution {self.id}: {self.status.value}>"
