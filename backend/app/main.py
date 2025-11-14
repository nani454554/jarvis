"""
JARVIS Backend - Main Application Entry Point
FastAPI application with WebSocket support, security, and monitoring
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
import time
import uuid
from pathlib import Path

from app.config import settings
from app.core.logging import setup_logging, logger
from app.core.cache import cache
from app.core.database import engine, Base, SessionLocal
from app.api.v1 import auth, voice, vision, brain, skills, system
from app.api.v1.websocket import router as websocket_router
from app.services.voice_service import VoiceService
from app.services.vision_service import VisionService
from app.services.brain_service import BrainService

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
    """
    Application lifespan events
    Handles startup and shutdown procedures
    """
    # Startup
    logger.info(f"🚀 Starting {settings.APP_NAME} v{settings.APP_VERSION}")
    logger.info(f"Environment: {settings.ENVIRONMENT}")
    logger.info(f"Debug Mode: {settings.DEBUG}")
    
    # Create database tables
    try:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        logger.info("✅ Database tables created/verified")
    except Exception as e:
        logger.error(f"❌ Database initialization failed: {e}")
        raise
    
    # Initialize services
    try:
        app.state.voice_service = VoiceService()
        app.state.vision_service = VisionService()
        app.state.brain_service = BrainService()
        logger.info("✅ AI services initialized")
    except Exception as e:
        logger.error(f"❌ Service initialization failed: {e}")
        # Continue even if services fail (they may be in mock mode)
    
    # Initialize cache
    try:
        await cache.connect()
        logger.info("✅ Cache connected")
    except Exception as e:
        logger.warning(f"⚠️  Cache connection failed: {e}")
    
    logger.info("✅ All systems operational")
    
    yield
    
    # Shutdown
    logger.info("🔌 Shutting down JARVIS...")
    
    try:
        await cache.disconnect()
        logger.info("✅ Cache disconnected")
    except:
        pass
    
    try:
        await engine.dispose()
        logger.info("✅ Database connections closed")
    except:
        pass
    
    logger.info("✅ Shutdown complete")

# Create FastAPI app
app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="Just A Rather Very Intelligent System - AI Assistant Platform",
    docs_url="/docs" if settings.DEBUG else None,
    redoc_url="/redoc" if settings.DEBUG else None,
    openapi_url="/openapi.json" if settings.DEBUG else None,
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
    expose_headers=["X-Request-ID", "X-Process-Time"],
)

# 3. GZip compression
app.add_middleware(GZipMiddleware, minimum_size=1000)

# 4. Request timing middleware
@app.middleware("http")
async def add_process_time_header(request: Request, call_next):
    start_time = time.time()
    response = await call_next(request)
    process_time = time.time() - start_time
    response.headers["X-Process-Time"] = str(round(process_time, 3))
    return response

# 5. Request ID middleware
@app.middleware("http")
async def add_request_id(request: Request, call_next):
    request_id = str(uuid.uuid4())
    request.state.request_id = request_id
    response = await call_next(request)
    response.headers["X-Request-ID"] = request_id
    return response

# Exception handlers
@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(request: Request, exc: StarletteHTTPException):
    """Handle HTTP exceptions"""
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": {
                "type": "http_error",
                "message": exc.detail,
                "status_code": exc.status_code,
                "request_id": getattr(request.state, "request_id", None)
            }
        }
    )

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """Handle validation errors"""
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
    """Handle all other exceptions"""
    logger.exception("Unhandled exception occurred")
    
    # Don't expose internal errors in production
    error_message = str(exc) if settings.DEBUG else "An unexpected error occurred"
    
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "error": {
                "type": "internal_server_error",
                "message": error_message,
                "request_id": getattr(request.state, "request_id", None)
            }
        }
    )

# Root endpoint
@app.get("/", tags=["Root"])
async def root():
    """
    Root endpoint - System information
    """
    return {
        "system": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "status": "operational",
        "environment": settings.ENVIRONMENT,
        "docs": "/docs" if settings.DEBUG else "disabled",
        "timestamp": time.time()
    }

# Health check endpoint
@app.get("/health", tags=["Health"])
async def health_check():
    """
    Comprehensive health check
    Returns status of all services
    """
    health_status = {
        "status": "healthy",
        "timestamp": time.time(),
        "services": {}
    }
    
    # Check database
    try:
        db = SessionLocal()
        await db.execute("SELECT 1")
        await db.close()
        health_status["services"]["database"] = "healthy"
    except Exception as e:
        health_status["services"]["database"] = f"unhealthy: {str(e)}"
        health_status["status"] = "degraded"
    
    # Check cache
    try:
        if await cache.ping():
            health_status["services"]["cache"] = "healthy"
        else:
            health_status["services"]["cache"] = "unhealthy"
            health_status["status"] = "degraded"
    except Exception as e:
        health_status["services"]["cache"] = f"unhealthy: {str(e)}"
        health_status["status"] = "degraded"
    
    # Check AI services
    if hasattr(app.state, "voice_service"):
        health_status["services"]["voice"] = "healthy" if app.state.voice_service.is_ready() else "not_ready"
    else:
        health_status["services"]["voice"] = "not_initialized"
    
    if hasattr(app.state, "vision_service"):
        health_status["services"]["vision"] = "healthy" if app.state.vision_service.is_ready() else "not_ready"
    else:
        health_status["services"]["vision"] = "not_initialized"
    
    if hasattr(app.state, "brain_service"):
        health_status["services"]["brain"] = "healthy" if app.state.brain_service.is_ready() else "not_ready"
    else:
        health_status["services"]["brain"] = "not_initialized"
    
    return health_status

# Readiness probe (for Kubernetes)
@app.get("/ready", tags=["Health"])
async def readiness_check():
    """
    Readiness probe for Kubernetes
    """
    return {"ready": True, "timestamp": time.time()}

# Liveness probe (for Kubernetes)
@app.get("/alive", tags=["Health"])
async def liveness_check():
    """
    Liveness probe for Kubernetes
    """
    return {"alive": True, "timestamp": time.time()}

# Include API routers
app.include_router(
    auth.router,
    prefix=f"{settings.API_V1_PREFIX}/auth",
    tags=["Authentication"]
)

app.include_router(
    voice.router,
    prefix=f"{settings.API_V1_PREFIX}/voice",
    tags=["Voice"]
)

app.include_router(
    vision.router,
    prefix=f"{settings.API_V1_PREFIX}/vision",
    tags=["Vision"]
)

app.include_router(
    brain.router,
    prefix=f"{settings.API_V1_PREFIX}/brain",
    tags=["Brain"]
)

app.include_router(
    skills.router,
    prefix=f"{settings.API_V1_PREFIX}/skills",
    tags=["Skills"]
)

app.include_router(
    system.router,
    prefix=f"{settings.API_V1_PREFIX}/system",
    tags=["System"]
)

app.include_router(
    websocket_router,
    prefix="/ws",
    tags=["WebSocket"]
)

if __name__ == "__main__":
    import uvicorn
    
    print("""
    ╔═══════════════════════════════════════╗
    ║   J.A.R.V.I.S. Backend Server v2.0    ║
    ║   Just A Rather Very Intelligent      ║
    ║   System                              ║
    ╚═══════════════════════════════════════╝
    """)
    
    uvicorn.run(
        "app.main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.RELOAD,
        workers=settings.WORKERS if not settings.RELOAD else 1,
        log_level=settings.LOG_LEVEL.lower(),
        access_log=True,
    )
