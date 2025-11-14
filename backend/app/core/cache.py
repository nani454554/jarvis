"""
Redis Cache Manager
High-performance caching layer
"""
import asyncio
import json
from typing import Any, Optional
import redis.asyncio as aioredis
from app.config import settings
import logging

logger = logging.getLogger(__name__)

class CacheManager:
    """Async Redis cache manager"""
    
    def __init__(self):
        self.redis: Optional[aioredis.Redis] = None
        self._connected = False
    
    async def connect(self):
        """Connect to Redis"""
        try:
            self.redis = await aioredis.from_url(
                str(settings.REDIS_URL),
                encoding="utf-8",
                decode_responses=True,
                max_connections=50,
            )
            # Test connection
            await self.redis.ping()
            self._connected = True
            logger.info("✅ Connected to Redis")
        except Exception as e:
            logger.error(f"❌ Failed to connect to Redis: {e}")
            self._connected = False
    
    async def disconnect(self):
        """Disconnect from Redis"""
        if self.redis:
            await self.redis.close()
            self._connected = False
            logger.info("🔌 Disconnected from Redis")
    
    async def get(self, key: str) -> Optional[Any]:
        """Get value from cache"""
        if not self._connected:
            return None
        
        try:
            value = await self.redis.get(key)
            if value:
                return json.loads(value)
        except Exception as e:
            logger.error(f"Cache get error for key {key}: {e}")
        return None
    
    async def set(
        self,
        key: str,
        value: Any,
        expire: Optional[int] = None
    ):
        """Set value in cache"""
        if not self._connected:
            return
        
        try:
            serialized = json.dumps(value)
            if expire:
                await self.redis.setex(key, expire, serialized)
            else:
                await self.redis.set(key, serialized)
        except Exception as e:
            logger.error(f"Cache set error for key {key}: {e}")
    
    async def delete(self, key: str):
        """Delete key from cache"""
        if not self._connected:
            return
        
        try:
            await self.redis.delete(key)
        except Exception as e:
            logger.error(f"Cache delete error for key {key}: {e}")
    
    async def exists(self, key: str) -> bool:
        """Check if key exists"""
        if not self._connected:
            return False
        
        try:
            return await self.redis.exists(key) > 0
        except Exception as e:
            logger.error(f"Cache exists error for key {key}: {e}")
            return False
    
    async def ping(self) -> bool:
        """Ping Redis server"""
        if not self._connected:
            return False
        
        try:
            await self.redis.ping()
            return True
        except Exception:
            return False
    
    async def clear(self, pattern: str = "*"):
        """Clear cache by pattern"""
        if not self._connected:
            return
        
        try:
            keys = await self.redis.keys(pattern)
            if keys:
                await self.redis.delete(*keys)
        except Exception as e:
            logger.error(f"Cache clear error: {e}")

# Global cache instance
cache = CacheManager()s
