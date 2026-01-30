"""
Proxy router - All API endpoints
"""
import json
import logging
import httpx
from fastapi import APIRouter, Request, HTTPException, status
from fastapi.responses import JSONResponse

from app.core.config_settings import settings
from app.core.rate_limiter import limiter
from app.services.queue_service import QueueService
from app.services.request_service import RequestService
from app.core.redis_manager import redis_manager

logger = logging.getLogger(__name__)

router = APIRouter()


async def forward_or_queue(service_name: str, request: Request, path: str):
    """Forward request immediately or queue it if service is overloaded"""
    
    # Check if service can handle request
    can_handle = await QueueService.check_service_load(service_name)
    
    if can_handle:
        # Service has capacity - forward immediately
        slot_id = await QueueService.acquire_service_slot(service_name)
        try:
            return await RequestService.forward_request(service_name, request, path)
        finally:
            await QueueService.release_service_slot(service_name, slot_id)
    
    else:
        # Service overloaded - queue the request
        logger.info(f"{service_name} service overloaded - queueing request")
        
        request_data = {
            "method": request.method,
            "path": path,
            "query_params": str(request.query_params),
            "service": service_name
        }
        
        # Handle different content types
        if request.method == "POST":
            content_type = request.headers.get("content-type", "")
            request_data["content_type"] = content_type
            
            if "multipart/form-data" in content_type:
                # Store file uploads
                form = await request.form()
                files_data = {}
                for key, value in form.items():
                    if hasattr(value, "file"):
                        content = await value.read()
                        files_data[key] = {
                            "filename": value.filename,
                            "content": content.decode('latin1'),
                            "content_type": value.content_type
                        }
                request_data["files_data"] = json.dumps(files_data)
            else:
                body = await request.body()
                request_data["body"] = body.decode('utf-8', errors='ignore')
        
        # Get queue length BEFORE adding to get accurate position
        queue_length = await QueueService.get_queue_length(service_name)
        
        # Get quueue id
        queue_id = await QueueService.queue_request(service_name, request_data)
        
        return JSONResponse(
            status_code=status.HTTP_202_ACCEPTED,
            content={
                "status": "queued",
                "queue_id": queue_id,
                "message": f"Request queued - service at capacity",
                "queue_position": queue_length + 1,  # Position is current length + 1
                "check_status_url": f"/queue/{queue_id}"
            }
        )


# ======================================== PROXY PDF ROUTES ========================================
_pdf_service_name = "pdf"

# GET proxy for PDF
@router.get("/pdf_processor/{path:path}")
@limiter.limit(f"{settings.RATE_LIMIT_PER_HOUR}/hour")
async def proxy_pdf_processor_get(request: Request, path: str):
    """Forward /pdf_processor/* requests - queue if overloaded"""
    return await forward_or_queue(_pdf_service_name, request, path)

# POST proxy for PDF
@router.post("/pdf_processor/{path:path}")
@limiter.limit(f"{settings.RATE_LIMIT_PER_HOUR}/hour")
async def proxy_pdf_processor_post(request: Request, path: str):
    """Forward /pdf_processor/* requests - queue if overloaded"""
    return await forward_or_queue(_pdf_service_name, request, path)

# DELETE proxy for PDF
@router.delete("/pdf_processor/{path:path}")
@limiter.limit(f"{settings.RATE_LIMIT_PER_HOUR}/hour")
async def proxy_pdf_processor_delete(request: Request, path: str):
    """Forward /pdf_processor/* requests - queue if overloaded"""
    return await forward_or_queue(_pdf_service_name, request, path)


# ======================================== PROXY TTS ROUTES ========================================
_tts_service_name = "tts"

# GET proxy for TTS
@router.get("/tts_infra/{path:path}")
@limiter.limit(f"{settings.RATE_LIMIT_PER_HOUR}/hour")
async def proxy_tts_infra_get(request: Request, path: str):
    """Forward /tts_infra/* requests - queue if overloaded"""
    return await forward_or_queue(_tts_service_name, request, path)

# POST proxy for TTS
@router.post("/tts_infra/{path:path}")
@limiter.limit(f"{settings.RATE_LIMIT_PER_HOUR}/hour")
async def proxy_tts_infra_post(request: Request, path: str):
    """Forward /tts_infra/* requests - queue if overloaded"""
    return await forward_or_queue(_tts_service_name, request, path)

# DELETE proxy for TTS
@router.delete("/tts_infra/{path:path}")
@limiter.limit(f"{settings.RATE_LIMIT_PER_HOUR}/hour")
async def proxy_tts_infra_delete(request: Request, path: str):
    """Forward /tts_infra/* requests - queue if overloaded"""
    return await forward_or_queue(_tts_service_name, request, path)


# ======================================== PROXY AUTH ROUTES ========================================
_auth_service_name = "auth"

# GET proxy for Auth (profile, settings, etc.)
@router.get("/auth/{path:path}")
@limiter.limit(f"{settings.RATE_LIMIT_PER_HOUR}/hour")
async def proxy_auth_get(request: Request, path: str):
    """Forward /auth/* requests - queue if overloaded"""
    return await forward_or_queue(_auth_service_name, request, path)

# POST proxy for Auth (signup, login, logout, refresh, etc.)
@router.post("/auth/{path:path}")
@limiter.limit(f"{settings.RATE_LIMIT_PER_HOUR}/hour")
async def proxy_auth_post(request: Request, path: str):
    """Forward /auth/* requests - queue if overloaded"""
    return await forward_or_queue(_auth_service_name, request, path)

# PUT proxy for Auth (update profile, settings)
@router.put("/auth/{path:path}")
@limiter.limit(f"{settings.RATE_LIMIT_PER_HOUR}/hour")
async def proxy_auth_put(request: Request, path: str):
    """Forward /auth/* requests - queue if overloaded"""
    return await forward_or_queue(_auth_service_name, request, path)

# DELETE proxy for Auth (delete account)
@router.delete("/auth/{path:path}")
@limiter.limit(f"{settings.RATE_LIMIT_PER_HOUR}/hour")
async def proxy_auth_delete(request: Request, path: str):
    """Forward /auth/* requests - queue if overloaded"""
    return await forward_or_queue(_auth_service_name, request, path)


# ======================================== PROXY PAYMENT ROUTES ========================================
_payment_service_name = "payment"

# GET proxy for Payment (config, status, user payments/orders)
@router.get("/payment/{path:path}")
@limiter.limit(f"{settings.RATE_LIMIT_PER_HOUR}/hour")
async def proxy_payment_get(request: Request, path: str):
    """Forward /payment/* requests - queue if overloaded"""
    return await forward_or_queue(_payment_service_name, request, path)

# POST proxy for Payment (create payment intent, checkout session, refunds, webhooks)
@router.post("/payment/{path:path}")
@limiter.limit(f"{settings.RATE_LIMIT_PER_HOUR}/hour")
async def proxy_payment_post(request: Request, path: str):
    """Forward /payment/* requests - queue if overloaded"""
    return await forward_or_queue(_payment_service_name, request, path)

# PUT proxy for Payment (update payment status if needed)
@router.put("/payment/{path:path}")
@limiter.limit(f"{settings.RATE_LIMIT_PER_HOUR}/hour")
async def proxy_payment_put(request: Request, path: str):
    """Forward /payment/* requests - queue if overloaded"""
    return await forward_or_queue(_payment_service_name, request, path)

# DELETE proxy for Payment (cancel payments if needed)
@router.delete("/payment/{path:path}")
@limiter.limit(f"{settings.RATE_LIMIT_PER_HOUR}/hour")
async def proxy_payment_delete(request: Request, path: str):
    """Forward /payment/* requests - queue if overloaded"""
    return await forward_or_queue(_payment_service_name, request, path)


# ==================== QUEUE STATUS and Redis QUEUE ====================

@router.get("/queue/{queue_id}")
async def check_queue_status(queue_id: str):
    """Check status of queued request"""
    status_data = await QueueService.get_queue_status(queue_id)
    
    if not status_data:
        raise HTTPException(status_code=404, detail="Queue ID not found or expired")
    
    response = {
        "queue_id": queue_id,
        "status": status_data.get("status"),
        "queued_at": status_data.get("queued_at"),
        "processing_at": status_data.get("processing_at"),
        "completed_at": status_data.get("completed_at")
    }
    
    if status_data.get("status") == "completed":
        response["response"] = {
            "status_code": int(status_data.get("response_status", 200)),
            "body": status_data.get("response_body")
        }
    elif status_data.get("status") in ["failed", "timeout"]:
        response["error"] = status_data.get("error")
    
    return response

@router.get("/redis/active_requests")
async def redis_service_active_requests_keys():
    """Return all Redis keys that start with 'service:active:' with their values."""

    keys = await redis_manager.keys(f"{redis_manager.SERVICE_ACTIVE}:*")
    results = []

    for key in keys:
        value = await redis_manager.smembers(key)
        results.append({
            "key": key,
            "type": "set",
            "value": list(value)  
        })

    return {
        "total_keys": len(results),
        "keys": results
    }

@router.get("/redis/all")
async def redis_inspect_all():
    """Return ALL Redis keys with their types and values."""

    keys = await redis_manager.keys("*")
    results = []

    for key in keys:
        key_type = await redis_manager.type(key)

        if key_type == "string":
            value = await redis_manager.get(key)
        elif key_type == "list":
            value = await redis_manager.lrange(key, 0, -1)
        elif key_type == "set":
            value = await redis_manager.smembers(key)
        elif key_type == "hash":
            value = await redis_manager.hgetall(key)
        elif key_type == "zset":
            value = await redis_manager.zrange(key, 0, -1, withscores=True)
        else:
            value = "(unknown type)"

        results.append({
            "key": key,
            "type": key_type,
            "value": value
        })

    return {
        "total_keys": len(results),
        "keys": results
    }

@router.post("/redis/clear")
async def redis_clear():
    """Delete all keys from Redis"""
    keys = await redis_manager.keys("*")
    deleted_count = 0

    for key in keys:
        try:
            await redis_manager.delete(key)
            deleted_count += 1
        except Exception:
            pass  

    return {"cleared": deleted_count, "message": "All Redis keys deleted"}

# ==================== HEALTH & METRICS ====================

@router.get("/health")
async def health_check():
    """Health check with service status"""
        
    # Check Redis
    try:
        await redis_manager._ensure_connection()
        await redis_manager.ping()
        redis_ok = True
    except Exception as e:
        logger.error(f"Redis health check failed: {e}")
        redis_ok = False
    
    # Check services
    pdf_ok = tts_ok = auth_ok = payment_ok = False
    
    try:
        async with httpx.AsyncClient(timeout=5) as client:
            pdf_response = await client.get(f"{settings.PDF_SERVICE_URL}/health/check_health")
            pdf_ok = pdf_response.status_code == 200
    except Exception as e:
        logger.error(f"PDF service health check failed: {e}")
    
    try:
        async with httpx.AsyncClient(timeout=5) as client:
            tts_response = await client.get(f"{settings.TTS_SERVICE_URL}/health/check_health")
            tts_ok = tts_response.status_code == 200
    except Exception as e:
        logger.error(f"TTS service health check failed: {e}")
    
    try:
        async with httpx.AsyncClient(timeout=5) as client:
            auth_response = await client.get(f"{settings.AUTH_SERVICE_URL}/health/")
            auth_ok = auth_response.status_code == 200
    except Exception as e:
        logger.error(f"Auth service health check failed: {e}")
    
    try:
        async with httpx.AsyncClient(timeout=5) as client:
            payment_response = await client.get(f"{settings.PAYMENT_SERVICE_URL}/health/")
            payment_ok = payment_response.status_code == 200
    except Exception as e:
        logger.error(f"Payment service health check failed: {e}")
    
    # Get queue metrics
    pdf_queue = await QueueService.get_queue_length("pdf")
    tts_queue = await QueueService.get_queue_length("tts")
    auth_queue = await QueueService.get_queue_length("auth")
    payment_queue = await QueueService.get_queue_length("payment")
    pdf_active = await QueueService.get_active_count("pdf")
    tts_active = await QueueService.get_active_count("tts")
    auth_active = await QueueService.get_active_count("auth")
    payment_active = await QueueService.get_active_count("payment")
    
    healthy = redis_ok and pdf_ok and tts_ok and auth_ok and payment_ok
    unhealthy = []
    if not redis_ok:
        unhealthy.append("[REDIS Service]")
    if not pdf_ok:
        unhealthy.append("[PDF Microservice]")
    if not tts_ok:
        unhealthy.append("[TTS Microservice]")
    if not auth_ok:
        unhealthy.append("[AUTH Microservice]")
    if not payment_ok:
        unhealthy.append("[PAYMENT Microservice]")
    
    return {
        "status": "healthy" if healthy else f"[CRITICAL]: Check on {', '.join(unhealthy)} failed",
        "services": {
            "redis": "ok" if redis_ok else "error",
            "pdf": "ok" if pdf_ok else "error",
            "tts": "ok" if tts_ok else "error",
            "auth": "ok" if auth_ok else "error",
            "payment": "ok" if payment_ok else "error"
        },
        "queues": {
            "pdf": {
                "queued": pdf_queue,
                "active": pdf_active,
                "max": settings.MAX_CONCURRENT_PDF
            },
            "tts": {
                "queued": tts_queue,
                "active": tts_active,
                "max": settings.MAX_CONCURRENT_TTS
            },
            "auth": {
                "queued": auth_queue,
                "active": auth_active,
                "max": settings.MAX_CONCURRENT_AUTH
            },
            "payment": {
                "queued": payment_queue,
                "active": payment_active,
                "max": settings.MAX_CONCURRENT_PAYMENT
            }
        }
    }


@router.get("/metrics")
async def get_metrics():
    """Get detailed metrics"""
    pdf_queue = await QueueService.get_queue_length("pdf")
    tts_queue = await QueueService.get_queue_length("tts")
    auth_queue = await QueueService.get_queue_length("auth")
    payment_queue = await QueueService.get_queue_length("payment")
    pdf_active = await QueueService.get_active_count("pdf")
    tts_active = await QueueService.get_active_count("tts")
    auth_active = await QueueService.get_active_count("auth")
    payment_active = await QueueService.get_active_count("payment")
    
    return {
        "pdf_service": {
            "queued_requests": pdf_queue,
            "active_requests": pdf_active,
            "max_concurrent": settings.MAX_CONCURRENT_PDF,
            "available_slots": settings.MAX_CONCURRENT_PDF - pdf_active
        },
        "tts_service": {
            "queued_requests": tts_queue,
            "active_requests": tts_active,
            "max_concurrent": settings.MAX_CONCURRENT_TTS,
            "available_slots": settings.MAX_CONCURRENT_TTS - tts_active
        },
        "auth_service": {
            "queued_requests": auth_queue,
            "active_requests": auth_active,
            "max_concurrent": settings.MAX_CONCURRENT_AUTH,
            "available_slots": settings.MAX_CONCURRENT_AUTH - auth_active
        },
        "payment_service": {
            "queued_requests": payment_queue,
            "active_requests": payment_active,
            "max_concurrent": settings.MAX_CONCURRENT_PAYMENT,
            "available_slots": settings.MAX_CONCURRENT_PAYMENT - payment_active
        }
    }