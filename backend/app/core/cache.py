"""
Redis Cache Manager
High-performance caching layer with async support
"""
import asyncio
import json
from typing import Any, Optional, List
import redis.asyncio as aioredis
from app.config import settings
import logging

logger = logging.getLogger(__name__)

class CacheManager:
    """
    Async Redis cache manager
    Handles connection, get/set operations, and cleanup
    """
    
    def __init__(self):
        self.redis: Optional[aioredis.Redis] = None
        self._connected = False
    
    async def connect(self):
        """
        Connect to Redis server
        """
        try:
            self.redis = await aioredis.from_url(
                settings.REDIS_URL,
                encoding="utf-8",
                decode_responses=True,
                max_connections=50,
                socket_connect_timeout=5,
                socket_timeout=5,
            )
            
            # Test connection
            await self.redis.ping()
            self._connected = True
            logger.info("✅ Connected to Redis")
            
        except Exception as e:
            logger.error(f"❌ Failed to connect to Redis: {e}")
            self._connected = False
    
    async def disconnect(self):
        """
        Disconnect from Redis
        """
        if self.redis:
            await self.redis.close()
            self._connected = False
            logger.info("🔌 Disconnected from Redis")
    
    async def get(self, key: str) -> Optional[Any]:
        """
        Get value from cache
        
        Args:
            key: Cache key
            
        Returns:
            Cached value or None if not found
        """
        if not self._connected:
            logger.warning("Cache not connected")
            return None
        
        try:
            value = await self.redis.get(key)
            if value:
                return json.loads(value)
            return None
        except json.JSONDecodeError:
            # Return raw value if not JSON
            return value
        except Exception as e:
            logger.error(f"Cache get error for key {key}: {e}")
            return None
    
    async def set(
        self,
        key: str,
        value: Any,
        expire: Optional[int] = None
    ) -> bool:
        """
        Set value in cache
        
        Args:
            key: Cache key
            value: Value to cache
            expire: Expiration time in seconds
            
        Returns:
            True if successful
        """
        if not self._connected:
            logger.warning("Cache not connected")
            return False
        
        try:
            # Serialize value to JSON
            serialized = json.dumps(value)
            
            if expire:
                await self.redis.setex(key, expire, serialized)
            else:
                await self.redis.set(key, serialized)
            
            return True
            
        except Exception as e:
            logger.error(f"Cache set error for key {key}: {e}")
            return False
    
    async def delete(self, key: str) -> bool:
        """
        Delete key from cache
        
        Args:
            key: Cache key to delete
            
        Returns:
            True if key was deleted
        """
        if not self._connected:
            return False
        
        try:
            result = await self.redis.delete(key)
            return result > 0
        except Exception as e:
            logger.error(f"Cache delete error for key {key}: {e}")
            return False
    
    async def exists(self, key: str) -> bool:
        """
        Check if key exists in cache
        
        Args:
            key: Cache key
            
        Returns:
            True if key exists
        """
        if not self._connected:
            return False
        
        try:
            return await self.redis.exists(key) > 0
        except Exception as e:
            logger.error(f"Cache exists error for key {key}: {e}")
            return False
    
    async def ping(self) -> bool:
        """
        Ping Redis server
        
        Returns:
            True if server responds
        """
        if not self._connected:
            return False
        
        try:
            await self.redis.ping()
            return True
        except Exception:
            return False
    
    async def clear(self, pattern: str = "*"):
        """
        Clear cache by pattern
        
        Args:
            pattern: Key pattern to match (default: all keys)
        """
        if not self._connected:
            return
        
        try:
            keys = await self.redis.keys(pattern)
            if keys:
                await self.redis.delete(*keys)
                logger.info(f"Cleared {len(keys)} cache keys")
        except Exception as e:
            logger.error(f"Cache clear error: {e}")
    
    async def get_many(self, keys: List[str]) -> dict:
        """
        Get multiple values from cache
        
        Args:
            keys: List of cache keys
            
        Returns:
            Dictionary of key-value pairs
        """
        if not self._connected or not keys:
            return {}
        
        try:
            values = await self.redis.mget(keys)
            result = {}
            for key, value in zip(keys, values):
                if value:
                    try:
                        result[key] = json.loads(value)
                    except json.JSONDecodeError:
                        result[key] = value
            return result
        except Exception as e:
            logger.error(f"Cache get_many error: {e}")
            return {}
    
    async def set_many(self, mapping: dict, expire: Optional[int] = None):
        """
        Set multiple values in cache
        
        Args:
            mapping: Dictionary of key-value pairs
            expire: Expiration time in seconds
        """
        if not self._connected or not mapping:
            return
        
        try:
            # Serialize all values
            serialized = {k: json.dumps(v) for k, v in mapping.items()}
            
            # Use pipeline for efficiency
            pipe = self.redis.pipeline()
            for key, value in serialized.items():
                if expire:
                    pipe.setex(key, expire, value)
                else:
                    pipe.set(key, value)
            
            await pipe.execute()
            
        except Exception as e:
            logger.error(f"Cache set_many error: {e}")
    
    async def increment(self, key: str, amount: int = 1) -> Optional[int]:
        """
        Increment numeric value in cache
        
        Args:
            key: Cache key
            amount: Amount to increment by
            
        Returns:
            New value after increment
        """
        if not self._connected:
            return None
        
        try:
            return await self.redis.incrby(key, amount)
        except Exception as e:
            logger.error(f"Cache increment error for key {key}: {e}")
            return None
    
    async def expire(self, key: str, seconds: int) -> bool:
        """
        Set expiration time for key
        
        Args:
            key: Cache key
            seconds: Expiration time in seconds
            
        Returns:
            True if expiration was set
        """
        if not self._connected:
            return False
        
        try:
            return await self.redis.expire(key, seconds)
        except Exception as e:
            logger.error(f"Cache expire error for key {key}: {e}")
            return False

# Global cache instance
cache = CacheManager()
