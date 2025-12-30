"""
Service for forwarding requests to microservices
"""
import httpx
import logging
from fastapi import Request, HTTPException, status
from fastapi.responses import Response

from app.core.config_settings import settings

logger = logging.getLogger(__name__)


class RequestService:
    """Handles forwarding requests to microservices"""
    
    @staticmethod
    def get_service_url(service_name: str) -> str:
        """Get the base URL for a service"""
        service_map = {
            "pdf":settings.PDF_SERVICE_URL,
            "tts":settings.TTS_SERVICE_URL
        }
        return (service_map.get(service_name.lower()))
    
    @staticmethod
    async def forward_request(service_name: str, request: Request, path: str) -> Response:
        """Forward request directly to service"""
        
        service_url = RequestService.get_service_url(service_name)
        target_url = f"{service_url}/{path}"
        
        # Add query params
        query_params = str(request.query_params)
        if query_params:
            target_url += f"?{query_params}"
        
        logger.info(f"Forwarding {request.method} {path} -> {target_url}")
        
        try:
            async with httpx.AsyncClient(timeout=60.0) as client:
                
                if request.method == "GET":
                    response = await client.get(target_url)
                
                elif request.method == "POST":
                    content_type = request.headers.get("content-type", "")
                    
                    if "multipart/form-data" in content_type:
                        # Handle file uploads
                        form = await request.form()
                        files = {}
                        data = {}
                        
                        for key, value in form.items():
                            if hasattr(value, "file"):
                                files[key] = (value.filename, await value.read(), value.content_type)
                            else:
                                data[key] = value
                        
                        response = await client.post(target_url, files=files if files else None, data=data if data else None)
                    else:
                        # Handle JSON/other content
                        body = await request.body()
                        response = await client.post(target_url, content=body, headers={"content-type": content_type})
                
                elif request.method in ["PUT", "PATCH", "DELETE"]:
                    body = await request.body()
                    response = await client.request(request.method, target_url, content=body)
                
                else:
                    raise HTTPException(status_code=405, detail="Method not allowed")
                
                # Return the response
                return Response(content=response.content, status_code=response.status_code, headers=dict(response.headers))
        
        except httpx.TimeoutException:
            raise HTTPException(status_code=status.HTTP_504_GATEWAY_TIMEOUT, detail="Service timeout")
        except httpx.ConnectError:
            raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Service unavailable")
        except Exception as e:
            logger.error(f"Proxy error: {str(e)}", exc_info=True)
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Proxy error")