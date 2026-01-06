"""
Queue management service
"""
import uuid
import json
from datetime import datetime
from typing import Optional
import logging

from app.core.redis_manager import redis_manager
from app.core.config_settings import settings
from app.services.request_service import RequestService

logger = logging.getLogger(__name__)


class QueueService:
    """Manages request queueing in Redis"""
    
    @staticmethod
    async def check_service_load(service_name: str) -> bool:
        """Check if service can handle more requests"""
        key = f"{redis_manager.SERVICE_ACTIVE}:{service_name}"
        active_count = await redis_manager.scard(key)
        max_concurrent = (settings.MAX_CONCURRENT_PDF if service_name == "pdf" else settings.MAX_CONCURRENT_TTS)
        return active_count < max_concurrent
    
    @staticmethod
    async def acquire_service_slot(service_name: str) -> str:
        """Acquire a slot to send request to service"""
        slot_id = f"{service_name}:{uuid.uuid4().hex[:8]}"
        key = f"{redis_manager.SERVICE_ACTIVE}:{service_name}"
        
        await redis_manager.sadd(key, slot_id)
        
        logger.info(f"Acquired {service_name} slot: {slot_id}")
        return slot_id
    
    @staticmethod
    async def release_service_slot(service_name: str, slot_id: str):
        """Release service slot"""
        key = f"{redis_manager.SERVICE_ACTIVE}:{service_name}"
        await redis_manager.srem(key, slot_id)
        logger.info(f"Released {service_name} slot: {slot_id}")
    
    @staticmethod
    async def queue_request(service_name: str, request_data: dict) -> str:
        """Queue a request for later processing"""
        queue_id = f"queue_{service_name}_{uuid.uuid4().hex}"
        
        request_data["queue_id"] = queue_id
        request_data["queued_at"] = datetime.now().isoformat()
        request_data["status"] = "queued"
        
        # StorinG REQUEST DATA (no expiration until completed/failed)
        await redis_manager.hset(f"{redis_manager.QUEUED_REQUEST}:{queue_id}", mapping=request_data)
        
        # Add to processing queue
        await redis_manager.rpush(f"{redis_manager.QUEUE}:{service_name}", queue_id)
        
        logger.info(f"Queued request {queue_id} for {service_name}")
        return queue_id
    
    @staticmethod
    async def get_queue_status(queue_id: str) -> Optional[dict]:
        """Get status of queued request"""
        data = await redis_manager.hgetall(f"{redis_manager.QUEUED_REQUEST}:{queue_id}")
        return data if data else None
    
    @staticmethod
    async def get_queue_length(service_name: str) -> int:
        """Get number of queued requests"""
        return await redis_manager.llen(f"{redis_manager.QUEUE}:{service_name}")
    
    @staticmethod
    async def get_active_count(service_name: str) -> int:
        """Get number of active requests"""
        return await redis_manager.scard(f"{redis_manager.SERVICE_ACTIVE}:{service_name}")
    
    @staticmethod
    async def cleanup_completed_request(queue_id: str):
        """Clean up a completed/failed request from Redis"""
        # Delete the hash containing request data
        await redis_manager.delete(f"{redis_manager.QUEUED_REQUEST}:{queue_id}")
        logger.info(f"Cleaned up request data for {queue_id}")