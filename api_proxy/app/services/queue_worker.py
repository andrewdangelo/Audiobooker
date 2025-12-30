"""
Background queue workers
"""
import asyncio
import httpx
import json
import logging
from datetime import datetime
from typing import List

from app.core.redis_manager import redis_manager
from app.core.config_settings import settings
from app.services.queue_service import QueueService
from app.services.request_service import RequestService

logger = logging.getLogger(__name__)

# Global worker tasks
_worker_tasks: List[asyncio.Task] = []
_workers_running = False


async def process_queued_request(service_name: str, queue_id: str, slot_id: str):
    """Process a single queued request with pre-acquired slot"""
    
    # Get request data
    request_data = await redis_manager.hgetall(f"{redis_manager.QUEUED_REQUEST}:{queue_id}")
    if not request_data:
        logger.warning(f"Queue item {queue_id} not found")
        return
    
    logger.info(f"MOE *************************** ---> Processing {queue_id} with slot id: {slot_id}")
    
    try:
        # Update status
        await redis_manager.hset(f"{redis_manager.QUEUED_REQUEST}:{queue_id}", "status", "processing")
        await redis_manager.hset(f"{redis_manager.QUEUED_REQUEST}:{queue_id}", "processing_at", datetime.now().isoformat())
        
        # Build target URL
        service_url = RequestService.get_service_url(service_name)
        target_url = f"{service_url}/{request_data['path']}"
        
        if request_data.get('query_params'):
            target_url += f"?{request_data['query_params']}"
        
        # Forward request
        async with httpx.AsyncClient(timeout=60.0) as client:
            method = request_data['method']
            
            if method == "GET":
                response = await client.get(target_url)
            
            elif method == "POST":
                if request_data.get('files_data'):
                    # Reconstruct file uploads
                    files_data = json.loads(request_data['files_data'])
                    files = {
                        k: (
                            v['filename'], 
                            v['content'].encode('latin1'), 
                            v['content_type']
                        ) 
                        for k, v in files_data.items()
                    }
                    response = await client.post(target_url, files=files)
                else:
                    body = request_data.get('body', '').encode()
                    content_type = request_data.get('content_type', 'application/json')
                    response = await client.post(target_url, content=body, headers={"content-type": content_type})
            else:
                body = request_data.get('body', '').encode()
                response = await client.request(method, target_url, content=body)
        
        # Store response
        await redis_manager.hset(f"{redis_manager.QUEUED_REQUEST}:{queue_id}", "status", "completed")
        await redis_manager.hset(f"{redis_manager.QUEUED_REQUEST}:{queue_id}", "completed_at", datetime.now().isoformat())
        await redis_manager.hset(f"{redis_manager.QUEUED_REQUEST}:{queue_id}", "response_status", response.status_code)
        await redis_manager.hset(f"{redis_manager.QUEUED_REQUEST}:{queue_id}", "response_body", response.text)
        
        # Set expiration on completed request (1 hour for user to check status)
        await redis_manager.expire(f"{redis_manager.QUEUED_REQUEST}:{queue_id}", redis_manager.ONE_HOUR_TTL)
        
        logger.info(f"Completed queue item {queue_id} with status {response.status_code}")
        
    except Exception as e:
        logger.error(f"Error processing queue item {queue_id}: {str(e)}", exc_info=True)
        await redis_manager.hset(f"{redis_manager.QUEUED_REQUEST}:{queue_id}", "status", "failed")
        await redis_manager.hset(f"{redis_manager.QUEUED_REQUEST}:{queue_id}", "error", str(e))
        
        # Set expiration on failed request
        await redis_manager.expire(f"{redis_manager.QUEUED_REQUEST}:{queue_id}", redis_manager.ONE_HOUR_TTL)


async def queue_worker(service_name: str, worker_id: int):
    """Background worker that processes queued requests"""
    global _workers_running
    await redis_manager._ensure_connection()
    logger.info(f"Started queue worker {worker_id} for {service_name}")

    while _workers_running:
        # Pop an item 
        result = await redis_manager.blpop(f"{redis_manager.QUEUE}:{service_name}", timeout=1)
        
        if not result:
            continue  
        
        _, queue_id = result
        queue_id = queue_id.decode() if isinstance(queue_id, bytes) else queue_id
        
        logger.info(f"Worker {worker_id} picked up {queue_id}")
        
        # Acquire a slot 
        slot_id = await QueueService.acquire_service_slot(service_name)
        
        # Process the request
        try:
            await process_queued_request(service_name, queue_id, slot_id)
        except Exception as e:
            logger.error(f"Worker {worker_id} error processing {queue_id}: {e}", exc_info=True)
        finally:
            await QueueService.release_service_slot(service_name, slot_id)
    
    logger.info(f"Queue worker {worker_id} for {service_name} stopped")


async def start_queue_workers():
    """Start all queue workers"""
    global _worker_tasks, _workers_running
    
    _workers_running = True
    
    # Start workers for each service should be 10% of concurrency load measurement
    for i in range(int(settings.MAX_CONCURRENT_PDF * 0.10)):
        _worker_tasks.append(asyncio.create_task(queue_worker("pdf", i)))
    
    for i in range(int(settings.MAX_CONCURRENT_TTS * 0.10)):
        _worker_tasks.append(asyncio.create_task(queue_worker("tts", i)))
    
    logger.info(f"Started {len(_worker_tasks)} queue workers")


async def stop_queue_workers():
    """Stop all queue workers"""
    global _worker_tasks, _workers_running
    
    _workers_running = False
    
    # Cancel all worker tasks
    for task in _worker_tasks:
        task.cancel()
    
    # Wait for all to finish
    await asyncio.gather(*_worker_tasks, return_exceptions=True)
    
    _worker_tasks.clear()
    logger.info("All queue workers stopped")