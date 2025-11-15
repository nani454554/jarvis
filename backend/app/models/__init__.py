"""
Database models.
Import all models here for Alembic to detect them.
"""

from app.models.base import Base
from app.models.user import User
from app.models.conversation import Conversation, Message
from app.models.face import FaceEncoding
from app.models.memory import Document, DocumentChunk
from app.models.skill import Skill, SkillExecution

__all__ = [
    "Base",
    "User",
    "Conversation",
    "Message",
    "FaceEncoding",
    "Document",
    "DocumentChunk",
    "Skill",
    "SkillExecution",
]
