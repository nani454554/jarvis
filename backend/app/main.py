"""
JARVIS Backend - Production FastAPI Application
Enhanced with security, monitoring, and scalability
"""
import asyncio
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException
import sentry_sdk
from sentry_sdk.integrations.fastapi import FastApiIntegration
import logging
from prometheus_client import make_asgi_app
import time

from app.config import settings
from app.core.logging import setup_logging, logger
from app.core.cache import cache
from app.core.database import engine, Base, SessionLocal
from app.api.v1 import (
    auth, voice, vision, brain, skills, system, websocket_router
)
from app.services.voice_service import VoiceService
from app.services.vision_service import VisionService
from app.services.brain_service import BrainService
from app.tasks.celery_app import celery_app

# Setup logging
setup_logging()

# Sentry integration for production
if settings.SENTRY_DSN and settings.ENVIRONMENT == "production":
    sentry_sdk.init(
        dsn=settings.SENTRY_DSN,
        integrations=[FastApiIntegration()],
        traces_sample_rate=0.1,
        environment=settings.ENVIRONMENT,
    )

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan events"""
    # Startup
    logger.info(f"🚀 Starting {settings.APP_NAME} v{settings.APP_VERSION}")
    logger.info(f"Environment: {settings.ENVIRONMENT}")
    
    # Create database tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    # Initialize services
    app.state.voice_service = VoiceService()
    app.state.vision_service = VisionService()
    app.state.brain_service = BrainService()
    
    # Initialize cache
    await cache.connect()
    
    # Start background tasks
    logger.info("✅ All systems operational")
    
    yield
    
    # Shutdown
    logger.info("🔌 Shutting down JARVIS...")
    await cache.disconnect()
    await engine.dispose()
    logger.info("✅ Shutdown complete")

# Create FastAPI app
app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="Just A Rather Very Intelligent System - AI Assistant Platform",
    docs_url="/docs" if settings.DEBUG else None,
    redoc_url="/redoc" if settings.DEBUG else None,
    lifespan=lifespan,
)

# Middleware stack (order matters!)

# 1. Trusted Host (security)
if settings.ENVIRONMENT == "production":
    app.add_middleware(
        TrustedHostMiddleware,
        allowed_hosts=settings.ALLOWED_HOSTS
    )

# 2. CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["X-Request-ID"],
)

# 3. GZip compression
app.add_middleware(GZipMiddleware, minimum_size=1000)

# 4. Request timing middleware
@app.middleware("http")
async def add_process_time_header(request: Request, call_next):
    start_time = time.time()
    response = await call_next(request)
    process_time = time.time() - start_time
    response.headers["X-Process-Time"] = str(process_time)
    return response

# 5. Request ID middleware
@app.middleware("http")
async def add_request_id(request: Request, call_next):
    import uuid
    request_id = str(uuid.uuid4())
    request.state.request_id = request_id
    response = await call_next(request)
    response.headers["X-Request-ID"] = request_id
    return response

# Exception handlers
@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(request: Request, exc: StarletteHTTPException):
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": {
                "type": "http_error",
                "message": exc.detail,
                "request_id": getattr(request.state, "request_id", None)
            }
        }
    )

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "error": {
                "type": "validation_error",
                "message": "Invalid request data",
                "details": exc.errors(),
                "request_id": getattr(request.state, "request_id", None)
            }
        }
    )

@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    logger.exception("Unhandled exception occurred")
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "error": {
                "type": "internal_server_error",
                "message": "An unexpected error occurred",
                "request_id": getattr(request.state, "request_id", None)
            }
        }
    )

# Root endpoint
@app.get("/", tags=["Root"])
async def root():
    """Health check and system info"""
    return {
        "system": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "status": "operational",
        "environment": settings.ENVIRONMENT,
        "docs": "/docs" if settings.DEBUG else "disabled",
    }

# Health check endpoint
@app.get("/health", tags=["Health"])
async def health_check():
    """Comprehensive health check"""
    health_status = {
        "status": "healthy",
        "timestamp": time.time(),
        "services": {}
    }
    
    # Check database
    try:
        db = SessionLocal()
        db.execute("SELECT 1")
        db.close()
        health_status["services"]["database"] = "healthy"
    except Exception as e:
        health_status["services"]["database"] = f"unhealthy: {str(e)}"
        health_status["status"] = "degraded"
    
    # Check cache
    try:
        await cache.ping()
        health_status["services"]["cache"] = "healthy"
    except Exception as e:
        health_status["services"]["cache"] = f"unhealthy: {str(e)}"
        health_status["status"] = "degraded"
    
    # Check AI services
    health_status["services"]["voice"] = "healthy" if hasattr(app.state, "voice_service") else "not_initialized"
    health_status["services"]["vision"] = "healthy" if hasattr(app.state, "vision_service") else "not_initialized"
    health_status["services"]["brain"] = "healthy" if hasattr(app.state, "brain_service") else "not_initialized"
    
    return health_status

# Readiness probe (for Kubernetes)
@app.get("/ready", tags=["Health"])
async def readiness_check():
    """Readiness probe"""
    return {"ready": True}

# Liveness probe (for Kubernetes)
@app.get("/alive", tags=["Health"])
async def liveness_check():
    """Liveness probe"""
    return {"alive": True}

# Include API routers
app.include_router(auth.router, prefix=f"{settings.API_V1_PREFIX}/auth", tags=["Authentication"])
app.include_router(voice.router, prefix=f"{settings.API_V1_PREFIX}/voice", tags=["Voice"])
app.include_router(vision.router, prefix=f"{settings.API_V1_PREFIX}/vision", tags=["Vision"])
app.include_router(brain.router, prefix=f"{settings.API_V1_PREFIX}/brain", tags=["Brain"])
app.include_router(skills.router, prefix=f"{settings.API_V1_PREFIX}/skills", tags=["Skills"])
app.include_router(system.router, prefix=f"{settings.API_V1_PREFIX}/system", tags=["System"])
app.include_router(websocket_router, prefix="/ws", tags=["WebSocket"])

# Prometheus metrics endpoint
metrics_app = make_asgi_app()
app.mount("/metrics", metrics_app)

if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(
        "app.main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.RELOAD,
        workers=settings.WORKERS if not settings.RELOAD else 1,
        log_level=settings.LOG_LEVEL.lower(),
        access_log=True,
    )
