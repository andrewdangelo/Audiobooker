"""
Redis connection manager and utilities
Centralized Redis operations for the application
"""
import json
import redis.asyncio as redis
from typing import Optional, Any, List
from app.core.config_settings import settings

class RedisKeys:
    # Redis key prefixes
    QUEUE = "queue"
    QUEUED_REQUEST = "queued_request"
    SERVICE_ACTIVE = "service:active"
    ONE_HOUR_TTL = 3600
    REQUEST_TIMEOUT = 300

class RedisManager(RedisKeys):
    """Centralized Redis connection and operations manager"""
    
    def __init__(self):
        self.redis: Optional[redis.Redis] = None
        self._connection_pool: Optional[redis.ConnectionPool] = None
    
    async def connect(self):
        if self.redis:
            return

        redis_url = f"redis://"
        if settings.REDIS_PASSWORD:
            redis_url += f":{settings.REDIS_PASSWORD}@"
            
        redis_url += f"{settings.REDIS_HOST}:{settings.REDIS_PORT}/{settings.REDIS_DB}"

        self._connection_pool = redis.ConnectionPool.from_url(redis_url, decode_responses=True, max_connections=150)

        self.redis = redis.Redis(connection_pool=self._connection_pool)

        await self.redis.ping()
        print("Redis connected")
    
    async def _ensure_connection(self):
        """Ensure Redis connection is alive, reconnect if needed"""
        if self.redis is None:
            try:
                print("Redis not connected, connecting...")
                #TODO remove this way to start redis server and dedicate a vm for redis server or microservice. SUPER TEMPORARY FIX
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
        await self._ensure_connection()
        if self.redis:
            await self.redis.close()
            await self._connection_pool.disconnect()
            self.redis = None
            self._connection_pool = None
            print("*****Redis disconnected*****")
    
    async def health_check(self) -> bool:
        """Check if Redis is healthy"""
        await self._ensure_connection()
        try:
            await self.redis.ping()
            return True
        except Exception:
            return False
    
    # ==================== Key-Value Operations ====================
    
    async def set(self, key: str, value: Any, expire: Optional[int] = None) -> bool:
        await self._ensure_connection()
        if not isinstance(value, str):
            value = json.dumps(value)
        
        if expire:
            return await self.redis.setex(key, expire, value)
        else:
            return await self.redis.set(key, value)
    
    async def get(self, key: str, deserialize: bool = True) -> Optional[Any]:
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
    
    async def keys(self, pattern: str) -> List[str]:
        """Get keys matching pattern"""
        await self._ensure_connection()
        return await self.redis.keys(pattern)

    async def lrange(self, key: str, start: int, end: int) -> List[str]:
        """Get range of list elements"""
        await self._ensure_connection()
        return await self.redis.lrange(key, start, end)

    async def type(self, key: str) -> str:
        """Get type of key"""
        await self._ensure_connection()
        return await self.redis.type(key)
    
    async def rpush(self, key: str, *values:str) -> int:
        """Append values to end of list"""
        await self._ensure_connection()
        return await self.redis.rpush(key, *values)

    async def smembers(self, key: str) -> set:
        """Get all members of a set"""
        await self._ensure_connection()
        return await self.redis.smembers(key)

    async def zrange(self, key: str, start: int, end: int, withscores: bool = False):
        """Get range from sorted set"""
        await self._ensure_connection()
        return await self.redis.zrange(key, start, end, withscores=withscores)

    async def sadd(self, key: str, *members: str) -> int:
        """Add one or more members to a set"""
        await self._ensure_connection()
        return await self.redis.sadd(key, *members)

    async def srem(self, key: str, *members: str) -> int:
        """Remove one or more members from a set"""
        await self._ensure_connection()
        return await self.redis.srem(key, *members)

    async def llen(self, key: str) -> int:
        """Get length of a list"""
        await self._ensure_connection()
        return await self.redis.llen(key)

    async def scard(self, key: str) -> int:
        """Get number of members in a set"""
        await self._ensure_connection()
        return await self.redis.scard(key)

    async def ping(self) -> bool:
        """Ping Redis server"""
        await self._ensure_connection()
        return await self.redis.ping()
    
    def _try_deserialize(self, value):
        try:
            return json.loads(value)
        except:
            return value
    
    # ==================== Cache Operations ====================

    async def cache_set(self, key: str, value: dict, ttl: int = 3600):
        await self._ensure_connection()
        return await self.redis.setex(key, ttl, json.dumps(value))

    async def cache_get(self, key: str):
        await self._ensure_connection()
        value = await self.redis.get(key)
        if value:
            try:
                return json.loads(value)
            except:
                return value
        return None

    # ==================== Hash Operations ====================
    
    async def hset(self, key: str, field: str = None, value: any = None, mapping: dict = None):
        """Set a Redis hash field or multiple fields."""
        await self._ensure_connection()
        
        if mapping:
            mapping = {k: json.dumps(v) if not isinstance(v, str) else v for k, v in mapping.items()}
            return await self.redis.hset(key, mapping=mapping)
        
        if field is not None and value is not None:
            if not isinstance(value, str):
                value = json.dumps(value)
            return await self.redis.hset(key, field, value)
        
        raise ValueError("Provide either field & value, or mapping")
    
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

    async def lpush(self, key: str, value: str):
        await self._ensure_connection()
        return await self.redis.lpush(key, value)

    async def lrem(self, key: str, count: int, value: str):
        await self._ensure_connection()
        return await self.redis.lrem(key, count, value)

    async def blpop(self, keys, timeout: int = 0) -> Optional[tuple]:
        await self._ensure_connection()
        if isinstance(keys, str):
            keys = [keys]
        return await self.redis.blpop(keys, timeout)

    # ==================== Helper Methods ====================
    
    async def flush_db(self):
        """Becareful flushing the entire Redis database!!! Serious shit cuz"""
        await self._ensure_connection()
        await self.redis.flushdb()
    
    async def get_info(self) -> dict:
        """Get Redis server info"""
        await self._ensure_connection()
        return await self.redis.info()

# Global singleton instance
redis_manager = RedisManager()

# Convenience functions for direct access
async def get_redis() -> redis.Redis:
    """Get Redis client instance"""
    if redis_manager.redis is None:
        await redis_manager.connect()
    return redis_manager.redis
    