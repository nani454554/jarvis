"""
Advanced Configuration Management
Supports multiple environments with validation
"""
from typing import Optional, List
from pydantic_settings import BaseSettings
from pydantic import Field, validator, PostgresDsn, RedisDsn
from functools import lru_cache
import secrets

class Settings(BaseSettings):
    """Application settings with environment-based configuration"""
    
    # Application
    APP_NAME: str = "JARVIS"
    APP_VERSION: str = "2.0.0"
    ENVIRONMENT: str = Field(default="development", env="ENVIRONMENT")
    DEBUG: bool = Field(default=False, env="DEBUG")
    API_V1_PREFIX: str = "/api/v1"
    
    # Server
    HOST: str = Field(default="0.0.0.0", env="HOST")
    PORT: int = Field(default=8000, env="PORT")
    WORKERS: int = Field(default=4, env="WORKERS")
    RELOAD: bool = Field(default=True, env="RELOAD")
    
    # Security
    SECRET_KEY: str = Field(default_factory=lambda: secrets.token_urlsafe(32))
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 7  # 7 days
    REFRESH_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 30  # 30 days
    ALGORITHM: str = "HS256"
    ALLOWED_HOSTS: List[str] = ["*"]
    
    # Database
    DATABASE_URL: PostgresDsn = Field(
        default="postgresql://jarvis:jarvis123@localhost:5432/jarvis_db",
        env="DATABASE_URL"
    )
    DB_POOL_SIZE: int = 20
    DB_MAX_OVERFLOW: int = 10
    DB_ECHO: bool = False
    
    # Redis
    REDIS_URL: RedisDsn = Field(
        default="redis://localhost:6379/0",
        env="REDIS_URL"
    )
    REDIS_CACHE_TTL: int = 3600  # 1 hour
    
    # Celery
    CELERY_BROKER_URL: str = Field(
        default="redis://localhost:6379/1",
        env="CELERY_BROKER_URL"
    )
    CELERY_RESULT_BACKEND: str = Field(
        default="redis://localhost:6379/2",
        env="CELERY_RESULT_BACKEND"
    )
    
    # AI Services
    OPENAI_API_KEY: Optional[str] = Field(default=None, env="OPENAI_API_KEY")
    ANTHROPIC_API_KEY: Optional[str] = Field(default=None, env="ANTHROPIC_API_KEY")
    GOOGLE_API_KEY: Optional[str] = Field(default=None, env="GOOGLE_API_KEY")
    
    # Voice
    WHISPER_MODEL: str = "base.en"
    TTS_MODEL: str = "tts_models/en/vctk/vits"
    PORCUPINE_API_KEY: Optional[str] = Field(default=None, env="PORCUPINE_API_KEY")
    WAKE_WORD: str = "jarvis"
    
    # Vision
    FACE_DETECTION_MODEL: str = "retinaface"
    FACE_RECOGNITION_THRESHOLD: float = 0.7
    EMOTION_MODEL: str = "fer"
    
    # LLM
    LLM_PROVIDER: str = "openai"  # openai, anthropic, local
    LLM_MODEL: str = "gpt-4-turbo-preview"
    LLM_TEMPERATURE: float = 0.7
    LLM_MAX_TOKENS: int = 2000
    EMBEDDING_MODEL: str = "text-embedding-3-small"
    
    # RAG
    VECTOR_DB: str = "qdrant"  # qdrant, pinecone, chroma
    VECTOR_DB_URL: str = Field(default="http://localhost:6333", env="VECTOR_DB_URL")
    VECTOR_DIMENSION: int = 1536
    
    # AWS
    AWS_REGION: str = Field(default="us-east-1", env="AWS_REGION")
    AWS_ACCESS_KEY_ID: Optional[str] = Field(default=None, env="AWS_ACCESS_KEY_ID")
    AWS_SECRET_ACCESS_KEY: Optional[str] = Field(default=None, env="AWS_SECRET_ACCESS_KEY")
    S3_BUCKET_MODELS: str = "jarvis-models"
    S3_BUCKET_DATA: str = "jarvis-data"
    S3_BUCKET_LOGS: str = "jarvis-logs"
    
    # Monitoring
    SENTRY_DSN: Optional[str] = Field(default=None, env="SENTRY_DSN")
    LOG_LEVEL: str = Field(default="INFO", env="LOG_LEVEL")
    
    # CORS
    CORS_ORIGINS: List[str] = [
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "https://jarvis.yourdomain.com"
    ]
    
    # Rate Limiting
    RATE_LIMIT_REQUESTS: int = 100
    RATE_LIMIT_PERIOD: int = 60  # seconds
    
    @validator("ENVIRONMENT")
    def validate_environment(cls, v):
        allowed = ["development", "staging", "production"]
        if v not in allowed:
            raise ValueError(f"ENVIRONMENT must be one of {allowed}")
        return v
    
    @validator("LOG_LEVEL")
    def validate_log_level(cls, v):
        allowed = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        if v.upper() not in allowed:
            raise ValueError(f"LOG_LEVEL must be one of {allowed}")
        return v.upper()
    
    class Config:
        env_file = ".env"
        case_sensitive = True
        extra = "allow"

@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance"""
    return Settings()

# Convenience access
settings = get_settings()
