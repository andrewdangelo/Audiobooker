"""
Redis connection manager and utilities
"""

__author__ = "Mohammad Saifan"

import json
import redis.asyncio as redis
from typing import Optional, Any, List

from app.core.config_settings import settings

class RedisKeys:
    # Redis key prefixes
    JOB_PREFIX = "job:processing"
    JOB_TTL = 86400  # 24 hours #TODO for now expiring in 24 hours

class RedisManager(RedisKeys):
    """Centralized Redis connection and operations manager"""
    
    def __init__(self):
        self.redis: Optional[redis.Redis] = None
        self._connection_pool: Optional[redis.ConnectionPool] = None
    
    async def connect(self):
        """Initialize or re-initialize Redis connection pool"""
        if self.redis is not None:
            try:
                await self.redis.close()
                await self._connection_pool.disconnect()
            except Exception:
                pass  
            finally:
                self.redis = None
                self._connection_pool = None

        redis_url = "redis://"
        if settings.REDIS_PASSWORD:
            redis_url += f":{settings.REDIS_PASSWORD}@"
        redis_url += f"{settings.REDIS_HOST}:{settings.REDIS_PORT}/{settings.REDIS_DB}"

        self._connection_pool = redis.ConnectionPool.from_url(
            redis_url, 
            decode_responses=True,
            max_connections=300, 
            socket_keepalive=True,
            socket_keepalive_options={1: 1, 2: 1, 3: 3},
            health_check_interval=30, 
            retry_on_timeout=True,
            socket_connect_timeout=5,
            socket_timeout=5
        )
        
        self.redis = redis.Redis(connection_pool=self._connection_pool)

        # Test connection
        await self.redis.ping()
        print(f"****Redis connected: {settings.REDIS_HOST}:{settings.REDIS_PORT}****")
    
    async def _ensure_connection(self):
        """Ensure Redis connection is alive, reconnect if needed"""
        if self.redis is None:
            try:
                print("Redis not connected, connecting...")
                # import subprocess as sp
                # sp.run('wsl -d Ubuntu bash -c "sudo service redis-server start"', shell=True, capture_output=True)
                await self.connect()
            except Exception as e:
                print(f"Failed to connect to Redis: {str(e)}")
                
            return

        try:
            await self.redis.ping()
        except Exception:
            print("Redis connection lost, reconnecting...")
            #TODO remove this way to start redis server and dedicate a vm for redis server or microservice. SUPER TEMPORARY FIX
            # import subprocess as sp
            # sp.run('wsl -d Ubuntu bash -c "sudo service redis-server start"', shell=True, capture_output=True)
            await self.connect()
    
    async def disconnect(self):
        """Close Redis connection"""
        if self.redis:
            await self.redis.close()
            await self._connection_pool.disconnect()
            self.redis = None
            self._connection_pool = None
            print("*****Redis disconnected*****")
    
    async def health_check(self) -> bool:
        """Check if Redis is healthy by pinging to it"""
        try:
            await self._ensure_connection()
            await self.redis.ping()
            return True
        except Exception:
            return False
    
    # ==================== Normal Key-Value Dict Operations #TODO add more if applicable ====================
    
    async def set(self, key: str, value: Any, expire: Optional[int] = None) -> bool:
        """
        Set a key-value pair
        
        Args:
            key: Redis key
            value: Value to store (will be JSON serialized if not string)
            expire: Expiration in seconds
        """
        await self._ensure_connection()
        if not isinstance(value, str):
            value = json.dumps(value)
        
        if expire:
            return await self.redis.setex(key, expire, value)
        else:
            return await self.redis.set(key, value)
    
    async def get(self, key: str, deserialize: bool = True) -> Optional[Any]:
        """
        Get a value by key
        
        Args:
            key: Redis key
            deserialize: Auto-deserialize JSON if True
        """
        await self._ensure_connection()
        value = await self.redis.get(key)
        if value and deserialize:
            try:
                return json.loads(value)
            except json.JSONDecodeError:
                return value
        return value
    
    async def delete(self, key: str) -> bool:
        """Delete a key"""
        await self._ensure_connection()
        return await self.redis.delete(key) > 0
    
    async def exists(self, key: str) -> bool:
        """Check if key exists"""
        await self._ensure_connection()
        return await self.redis.exists(key) > 0
    
    async def expire(self, key: str, seconds: int) -> bool:
        """Set expiration on a key"""
        await self._ensure_connection()
        return await self.redis.expire(key, seconds)
    
    # ==================== Hash Operations ====================
    
    async def hset(self, key: str, field: str, value: Any) -> bool:
        """Set hash field"""
        await self._ensure_connection()
        if not isinstance(value, str):
            value = json.dumps(value)
        return await self.redis.hset(key, field, value)
    
    async def hget(self, key: str, field: str, deserialize: bool = True) -> Optional[Any]:
        """Get hash field"""
        await self._ensure_connection()
        value = await self.redis.hget(key, field)
        if value and deserialize:
            try:
                return json.loads(value)
            except json.JSONDecodeError:
                return value
        return value
    
    async def hgetall(self, key: str, deserialize: bool = True) -> dict:
        """Get all hash fields"""
        await self._ensure_connection()
        data = await self.redis.hgetall(key)
        if deserialize:
            return {k: self._try_deserialize(v) for k, v in data.items()}
        return data

    async def hdel(self, key: str, *fields: str) -> int:
        """Delete hash fields"""
        await self._ensure_connection()
        return await self.redis.hdel(key, *fields)
    
    def _try_deserialize(self, value: Any) -> Any:
        """Attempt to JSON-deserialize a Redis value, fallback to raw"""
        if not isinstance(value, str):
            return value

        try:
            return json.loads(value)
        except (json.JSONDecodeError, TypeError):
            return value

        
    # ==================== Helper Methods ====================
    
    async def flush_db(self):
        """Becareful flushing the entire Redis database!!! Serious shit cuz"""
        await self._ensure_connection()
        await self.redis.flushdb()
    
    async def get_info(self) -> dict:
        """Get Redis server info"""
        await self._ensure_connection()
        return await self.redis.info()

    async def scan_keys(self, pattern: str, count: int = 1000) -> List[str]:
        """
        Scan all redis and grab results
        """
        await self._ensure_connection()

        keys: List[str] = []
        cursor = 0

        while True:
            cursor, batch = await self.redis.scan(cursor=cursor, match=pattern, count=count)
            keys.extend(batch)

            if cursor == 0:
                break
        return keys

# Global singleton instance
redis_manager = RedisManager()

# Convenience functions for direct access
async def get_redis() -> redis.Redis:
    """Get Redis client instance"""
    if redis_manager.redis is None:
        await redis_manager.connect()
    return redis_manager.redis