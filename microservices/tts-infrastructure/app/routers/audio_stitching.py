from fastapi import (APIRouter, WebSocket, WebSocketDisconnect, HTTPException)
from fastapi.responses import FileResponse
from typing import Optional
import json
import base64
import asyncio

from app.models.audio_schemas import (StitchRequest, StitchResponse, StitchAndSaveRequest, StitchAndSaveResponse, JobStatus, StreamConfig)
from app.services.audio_stitcher import AudioStitcher

router = APIRouter()

# Initialize audio stitcher service
audio_stitcher = AudioStitcher(audio_dir="audio_output", output_dir="audio_output/stitched_audio")

@router.post("/prepare", response_model=StitchResponse)
async def prepare_stitch_job(request: StitchRequest):
    """
        - Prepares a stitching job ONLY.
        - Validates chunk IDs and creates a job record that can be used to download or stream.
        - Returns job metadata (total chunks, estimated duration).
        - The job can then be streamed via the /stream WebSocket in the front end.
        - Does NOT stitch audio with this endpoint.
    """
    try:
        # Create job
        job = await audio_stitcher.create_stitch_job(chunk_ids=request.chunk_ids, crossfade_ms=request.crossfade_ms, normalize=request.normalize,
                                    output_format=request.output_format, output_filename=request.output_filename, auto_queue=False)
        
        # Validate chunks
        is_valid, error = await audio_stitcher.validate_chunks(job.job_id)
        
        if not is_valid:
            job.status = JobStatus.FAILED
            job.error_message = error
            raise HTTPException(status_code=400, detail=error)
        
        return StitchResponse(
            job_id=job.job_id, 
            status=job.status, 
            message="Job prepared successfully. Connect to WebSocket to stream.", 
            total_chunks=job.total_chunks, 
            estimated_duration_seconds=job.total_duration_seconds
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/stitch-and-save", response_model=StitchAndSaveResponse)
async def stitch_and_save(request: StitchAndSaveRequest):
    """
        - Fully stitches all audio chunks immediately (non-streaming).
        - Saves the stitched audio file to disk "audio_dir".
        - Returns job status, final file path, and file size.
        - We will only use this when we need the complete file immediately, not streamed.
    """
    try:
        # Create job (auto-queue by default)
        job = await audio_stitcher.create_stitch_job(chunk_ids=request.chunk_ids, crossfade_ms=request.crossfade_ms, normalize=request.normalize,
                                    output_format=request.output_format, output_filename=request.output_filename, auto_queue=False)
        
        # Stitch audio
        job = await audio_stitcher.stitch_audio(job.job_id)
        
        if job.status == JobStatus.FAILED:
            raise HTTPException(status_code=500, detail=job.error_message)
        
        # Get file size
        from pathlib import Path
        file_size_mb = Path(job.output_path).stat().st_size / (1024 * 1024)
        
        return StitchAndSaveResponse(
            job_id=job.job_id, 
            status=job.status, 
            output_path=job.output_path, 
            total_duration_seconds=job.total_duration_seconds, 
            file_size_mb=round(file_size_mb, 2)
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/status/{job_id}", response_model=StitchResponse)
async def get_job_status(job_id: str):
    """
        - Retrieves the current status of a stitching job.
        - Shows whether the job is PENDING, PROCESSING, COMPLETED, or FAILED.
        - Returns output file path only if stitching is completed.
    """
    job = await audio_stitcher.get_job(job_id)  
    
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    
    return StitchResponse(
        job_id=job.job_id, 
        status=job.status, 
        message=job.error_message or "Job is processing", 
        total_chunks=job.total_chunks, 
        estimated_duration_seconds=job.total_duration_seconds, 
        output_path=job.output_path if job.status == JobStatus.COMPLETED else None
    )

@router.delete("/delete_job/{job_id}")
async def delete_job(job_id: str):
    """
        - Deletes the job record and its output file (if exists).
        - Should be used for cleanup after job completion or failures.
    """
    success = await audio_stitcher.delete_job(job_id)
    
    if not success:
        raise HTTPException(status_code=404, detail="Job not found")
    
    return {"message": "Job deleted successfully", "job_id": job_id}

@router.get("/download/{job_id}")
async def download_stitched_audio(job_id: str):
    """
        - Serves the stitched audio file for download.
        - Only available if the job is COMPLETED.
        - Returns a proper audio file response.
    """
    job = await audio_stitcher.get_job(job_id)  
    
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    
    if job.status != JobStatus.COMPLETED:
        raise HTTPException(status_code=400, detail="Job is not completed yet")
    
    if not job.output_path:
        raise HTTPException(status_code=404, detail="Output file not found")
    
    return FileResponse(
        job.output_path,
        media_type=f"audio/{job.output_format.value}",
        filename=f"stitched_{job.job_id}.{job.output_format.value}"
    )

@router.get("/jobs")
async def list_all_jobs():
    """
    List all stitching jobs
    """
    try:
        jobs = await audio_stitcher.get_all_jobs()  
        return {
            "total_jobs": len(jobs),
            "jobs": [job.model_dump() for job in jobs]
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.websocket("/stream")
async def websocket_stream_audio(websocket: WebSocket):
    """
    WebSocket endpoint for streaming stitched audio
    
    Client sends:
    {
        "action": "start",
        "job_id": "51599687-d3e0-4389-9c04-05e611e51b38",
        "config": {
            "buffer_size": 4096,
            "bitrate": "128k"
        }
    }
    
    Server sends:
    - Metadata message with total duration and format
    - Audio chunks
    - Progress updates
    - Completion/error messages
    """
    await websocket.accept()
    
    try:
        # Receive initial message
        data = await websocket.receive_text()
        message = json.loads(data)
        action = message.get("action")
        job_id = message.get("job_id")
        config = message.get("config", {})
        
        if not job_id:
            await websocket.send_json({
                "type": "error",
                "message": "job_id is required"
            })
            await websocket.close()
            return
        
        # Get job
        job = await audio_stitcher.get_job(job_id)  
        if not job:
            await websocket.send_json({
                "type": "error",
                "message": f"Job not found: {job_id}"
            })
            await websocket.close()
            return
        
        if action == "start":
            # Send metadata
            await websocket.send_json({
                "type": "metadata",
                "data": {
                    "job_id": job.job_id,
                    "total_duration": job.total_duration_seconds,
                    "format": job.output_format.value,
                    "chunks_count": job.total_chunks,
                    "crossfade_ms": job.crossfade_ms
                }
            })
            
            # Stream audio
            buffer_size = config.get("buffer_size", 4096)
            bitrate = config.get("bitrate", "128k")
            
            chunk_index = 0
            total_bytes = 0
            
            try:
                async for audio_chunk in audio_stitcher.stream_stitched_audio(
                    job_id=job_id, 
                    buffer_size=buffer_size, 
                    bitrate=bitrate
                ):
                    # Encode to base64 for JSON transport
                    encoded_chunk = base64.b64encode(audio_chunk).decode('utf-8')
                    
                    # Send audio chunk
                    await websocket.send_json({
                        "type": "audio_chunk",
                        "data": encoded_chunk,
                        "chunk_index": chunk_index,
                        "size_bytes": len(audio_chunk)
                    })
                    
                    chunk_index += 1
                    total_bytes += len(audio_chunk)
                    
                    # Send progress update every 50 chunks
                    if chunk_index % 50 == 0:
                        await websocket.send_json({
                            "type": "progress",
                            "data": {
                                "chunks_sent": chunk_index,
                                "bytes_sent": total_bytes
                            }
                        })
                
                # Send completion message
                await websocket.send_json({
                    "type": "status",
                    "message": "Streaming completed",
                    "data": {
                        "status": "completed",
                        "total_chunks_sent": chunk_index,
                        "total_bytes_sent": total_bytes
                    }
                })
                
            except Exception as e:
                await websocket.send_json({
                    "type": "error",
                    "message": f"Streaming error: {str(e)}"
                })
        
        elif action == "stop":
            await websocket.send_json({
                "type": "status",
                "message": "Streaming stopped"
            })
        
        else:
            await websocket.send_json({
                "type": "error",
                "message": f"Unknown action: {action}"
            })
    
    except WebSocketDisconnect:
        print(f"WebSocket disconnected")
    except json.JSONDecodeError:
        await websocket.send_json({
            "type": "error",
            "message": "Invalid JSON message"
        })
    except Exception as e:
        try:
            await websocket.send_json({
                "type": "error",
                "message": str(e)
            })
        except:
            pass
    finally:
        try:
            await websocket.close()
        except:
            pass