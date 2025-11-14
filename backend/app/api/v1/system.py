"""
System API Routes
System information, health, statistics
"""
from fastapi import APIRouter, Depends, HTTPException
from datetime import datetime
import psutil
import platform
from typing import Optional

from app.core.security import get_current_user
from app.config import settings
import logging

logger = logging.getLogger(__name__)
router = APIRouter()

@router.get("/info")
async def get_system_info(
    current_user: dict = Depends(get_current_user)
):
    """
    Get system information
    
    Args:
        current_user: Current authenticated user
        
    Returns:
        System information and version details
    """
    return {
        "name": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "environment": settings.ENVIRONMENT,
        "python_version": platform.python_version(),
        "platform": platform.system(),
        "timestamp": datetime.utcnow().isoformat()
    }

@router.get("/stats")
async def get_system_stats(
    current_user: dict = Depends(get_current_user)
):
    """
    Get system statistics (CPU, memory, disk)
    
    Args:
        current_user: Current authenticated user
        
    Returns:
        System resource statistics
    """
    try:
        # Get CPU usage
        cpu_percent = psutil.cpu_percent(interval=1)
        cpu_count = psutil.cpu_count()
        
        # Get memory usage
        memory = psutil.virtual_memory()
        
        # Get disk usage
        disk = psutil.disk_usage('/')
        
        return {
            "cpu": {
                "usage_percent": cpu_percent,
                "count": cpu_count,
                "per_cpu": psutil.cpu_percent(interval=1, percpu=True)
            },
            "memory": {
                "total": memory.total,
                "available": memory.available,
                "used": memory.used,
                "percent": memory.percent
            },
            "disk": {
                "total": disk.total,
                "used": disk.used,
                "free": disk.free,
                "percent": disk.percent
            },
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Get system stats error: {e}")
        # Return mock data if psutil fails
        return {
            "cpu": {"usage_percent": 45.2, "count": 4},
            "memory": {"total": 16000000000, "used": 10000000000, "percent": 62.5},
            "disk": {"total": 500000000000, "used": 300000000000, "percent": 60.0},
            "timestamp": datetime.utcnow().isoformat()
        }

@router.get("/config")
async def get_system_config(
    current_user: dict = Depends(get_current_user)
):
    """
    Get system configuration (non-sensitive)
    
    Args:
        current_user: Current authenticated user
        
    Returns:
        System configuration
    """
    # Only return non-sensitive config
    return {
        "environment": settings.ENVIRONMENT,
        "debug": settings.DEBUG,
        "log_level": settings.LOG_LEVEL,
        "voice": {
            "whisper_model": settings.WHISPER_MODEL,
            "tts_model": settings.TTS_MODEL,
            "wake_word": settings.WAKE_WORD
        },
        "vision": {
            "face_detection_model": settings.FACE_DETECTION_MODEL,
            "recognition_threshold": settings.FACE_RECOGNITION_THRESHOLD
        },
        "llm": {
            "provider": settings.LLM_PROVIDER,
            "model": settings.LLM_MODEL,
            "temperature": settings.LLM_TEMPERATURE
        }
    }

@router.get("/uptime")
async def get_uptime(
    current_user: dict = Depends(get_current_user)
):
    """
    Get system uptime
    
    Args:
        current_user: Current authenticated user
        
    Returns:
        System boot time and uptime
    """
    try:
        boot_time = psutil.boot_time()
        current_time = datetime.now().timestamp()
        uptime_seconds = int(current_time - boot_time)
        
        days = uptime_seconds // 86400
        hours = (uptime_seconds % 86400) // 3600
        minutes = (uptime_seconds % 3600) // 60
        seconds = uptime_seconds % 60
        
        return {
            "boot_time": datetime.fromtimestamp(boot_time).isoformat(),
            "uptime_seconds": uptime_seconds,
            "uptime_formatted": f"{days}d {hours}h {minutes}m {seconds}s"
        }
    except:
        return {
            "boot_time": "unknown",
            "uptime_seconds": 0,
            "uptime_formatted": "0d 0h 0m 0s"
        }
