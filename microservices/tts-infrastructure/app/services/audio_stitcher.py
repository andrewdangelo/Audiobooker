import uuid
import asyncio
from pathlib import Path
from typing import Dict, List, Optional, AsyncGenerator
from datetime import datetime, timedelta

from app.models.audio_schemas import (
    StitchJob, ChunkInfo, JobStatus, AudioFormat
)
from app.utils.audio_processor import AudioProcessor
from app.core.redis_manager import redis_manager


class AudioStitcher:
    """Service for stitching audio chunks together with Redis persistence"""
    
    def __init__(self, audio_dir: str = "audio_output", output_dir: str = "stitched_audio"):
        self.audio_dir = Path(audio_dir)
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(exist_ok=True)
        self.processor = AudioProcessor()
        self._cleanup_task = None
    
    async def initialize(self):
        """Initialize service - call on startup"""
        # Ensure Redis is connected
        if redis_manager.redis is None:
            await redis_manager.connect()
        
        # Start cleanup task
        if self._cleanup_task is None:
            self._cleanup_task = asyncio.create_task(self._cleanup_old_jobs())
    
    async def close(self):
        """Close service - call on shutdown"""
        if self._cleanup_task:
            self._cleanup_task.cancel()
    
    # ==================== Job Storage ====================
    
    async def _save_job(self, job: StitchJob):
        """Save job to Redis with 7-day expiration"""
        key = f"{redis_manager.JOB_PREFIX}:{job.job_id}"
        await redis_manager.set(key, job.model_dump_json(), expire=60 * 60 * 24 * 7 )
    
    async def _get_job(self, job_id: str) -> Optional[StitchJob]:
        """Get job from Redis"""
        key = f"{redis_manager.JOB_PREFIX}:{job_id}"
        data = await redis_manager.get(key, deserialize=False)
        if data:
            return StitchJob.model_validate_json(data)
        return None
    
    # ==================== Job Creation & Queue ====================
    
    async def create_stitch_job(self, chunk_ids: List[str], crossfade_ms: int = 0, normalize: bool = True, output_format: AudioFormat = AudioFormat.MP3,
                                output_filename: Optional[str] = None, auto_queue: bool = True) -> StitchJob:
        """Create a new stitching job and optionally queue it"""
        job_id = str(uuid.uuid4())
        
        # Create chunk info list
        chunks = [ChunkInfo(chunk_id=chunk_id, audio_path=str(self.audio_dir / f"{chunk_id}.mp3")) for chunk_id in chunk_ids]
        
        # Generate output path
        if output_filename:
            output_path = str(self.output_dir / f"{output_filename}.{output_format.value}")
        else:
            output_path = str(self.output_dir / f"{job_id}.{output_format.value}")
        
        # Create job
        job = StitchJob(job_id=job_id, status=JobStatus.PENDING, chunks=chunks, total_chunks=len(chunks), output_path=output_path,
                        output_format=output_format, crossfade_ms=crossfade_ms, normalize=normalize)
        
        # Save to Redis
        await self._save_job(job)
        
        # Add to queue if requested
        if auto_queue:
            await self.queue_job(job_id)
        
        return job
    
    async def queue_job(self, job_id: str) -> bool:
        """Add job to processing queue"""
        await redis_manager.lpush(redis_manager.JOB_QUEUE, job_id)
        return True
    
    async def complete_job(self, job_id: str):
        """Mark job as complete and remove from processing set"""
        await redis_manager.lrem(self.redis_manager.JOB_PROCESSING, 0, job_id)
    
    # ==================== Validation ====================
    
    async def validate_chunks(self, job_id: str) -> tuple[bool, Optional[str]]:
        """Validate that all chunks exist and are readable"""
        job = await self._get_job(job_id)
        if not job:
            return False, f"Job not found: {job_id}"
        
        for chunk in job.chunks:
            # Check cache first
            cache_key = f"{self.METADATA_CACHE}:{chunk.chunk_id}"
            cached_metadata = await redis_manager.cache_get(cache_key)
            
            if cached_metadata:
                chunk.duration_seconds = cached_metadata["duration_seconds"]
                continue
            
            # Validate file
            is_valid, error = self.processor.validate_audio_file(chunk.audio_path)
            if not is_valid:
                chunk.status = "failed"
                chunk.error = error
                await self._save_job(job)
                return False, f"Chunk {chunk.chunk_id}: {error}"
            
            # Get and cache metadata
            try:
                metadata = self.processor.get_audio_metadata(chunk.audio_path)
                chunk.duration_seconds = metadata["duration_seconds"]
                
                # Cache for 1 hour
                await redis_manager.cache_set(cache_key, metadata, ttl=3600)
            except Exception as e:
                chunk.status = "failed"
                chunk.error = str(e)
                await self._save_job(job)
                return False, f"Failed to read chunk {chunk.chunk_id}: {str(e)}"
        
        # Calculate total duration
        total_duration = sum(c.duration_seconds or 0 for c in job.chunks)
        job.total_duration_seconds = total_duration
        
        await self._save_job(job)
        return True, None
    
    # ==================== Processing ====================
    
    async def stitch_audio(self, job_id: str) -> StitchJob:
        """Stitch audio chunks together and save to file"""
        job = await self._get_job(job_id)
        if not job:
            raise ValueError(f"Job not found: {job_id}")
        
        try:
            # Update job status
            job.status = JobStatus.PROCESSING
            job.started_at = datetime.utcnow()
            await self._save_job(job)
            
            # Validate chunks
            is_valid, error = await self.validate_chunks(job_id)
            if not is_valid:
                job.status = JobStatus.FAILED
                job.error_message = error
                await self._save_job(job)
                await self.complete_job(job_id)
                return job
            
            # Get file paths
            file_paths = [chunk.audio_path for chunk in job.chunks]
            
            # Concatenate audio
            combined_audio, sample_rate = self.processor.concatenate_audio_segments(file_paths=file_paths, crossfade_ms=job.crossfade_ms, normalize_levels=job.normalize)
            
            # Mark chunks as loaded
            for chunk in job.chunks:
                chunk.status = "loaded"
                job.processed_chunks += 1
            await self._save_job(job)
            
            # Export to file
            self.processor.export_audio(audio=combined_audio, output_path=job.output_path, sample_rate=sample_rate, format=job.output_format.value, bitrate="128k")
            
            # Update job
            job.status = JobStatus.COMPLETED
            job.completed_at = datetime.utcnow()
            job.total_duration_seconds = len(combined_audio) / sample_rate
            
            # Mark all chunks as processed
            for chunk in job.chunks:
                if chunk.status != "failed":
                    chunk.status = "processed"
            
            await self._save_job(job)
            await self.complete_job(job_id)
            
            return job
            
        except Exception as e:
            job.status = JobStatus.FAILED
            job.error_message = str(e)
            job.completed_at = datetime.utcnow()
            await self._save_job(job)
            await self.complete_job(job_id)
            return job
    
    async def stream_stitched_audio(self, job_id: str, buffer_size: int = 4096, bitrate: str = "128k") -> AsyncGenerator[bytes, None]:
        """Stream stitched audio in chunks"""
        job = await self._get_job(job_id)
        if not job:
            raise ValueError(f"Job not found: {job_id}")
        
        try:
            job.status = JobStatus.PROCESSING
            job.started_at = datetime.utcnow()
            await self._save_job(job)
            
            # Validate chunks
            is_valid, error = await self.validate_chunks(job_id)
            if not is_valid:
                job.status = JobStatus.FAILED
                job.error_message = error
                await self._save_job(job)
                raise Exception(error)
            
            file_paths = [chunk.audio_path for chunk in job.chunks]
            
            # Concatenate audio
            combined_audio, sample_rate = self.processor.concatenate_audio_segments(file_paths=file_paths, crossfade_ms=job.crossfade_ms, normalize_levels=job.normalize)
            
            # Mark chunks as loaded
            for chunk in job.chunks:
                chunk.status = "loaded"
                job.processed_chunks += 1
            
            await self._save_job(job)
            
            # Stream audio chunks
            for chunk_data in self.processor.get_audio_chunk_bytes(audio=combined_audio, sample_rate=sample_rate, chunk_size=buffer_size, format=job.output_format.value, bitrate=bitrate):
                yield chunk_data
                await asyncio.sleep(0)
            
            job.status = JobStatus.COMPLETED
            job.completed_at = datetime.utcnow()
            await self._save_job(job)
            
        except Exception as e:
            job.status = JobStatus.FAILED
            job.error_message = str(e)
            await self._save_job(job)
            raise
    
    # ==================== Query Redis Methods ====================
    
    async def get_job(self, job_id: str) -> Optional[StitchJob]:
        """Get job by ID"""
        return await self._get_job(job_id)
    
    async def get_all_jobs(self) -> List[StitchJob]:
        """Get all jobs (expensive - use sparingly!)"""
        keys = await redis_manager.keys(f"{redis_manager.JOB_PREFIX}:*")
        jobs = []
        for key in keys:
            data = await redis_manager.get(key, deserialize=False)
            if data:
                jobs.append(StitchJob.model_validate_json(data))
        return jobs
    
    # ==================== Job Management ====================
    
    async def cancel_job(self, job_id: str) -> bool:
        """Cancel a job"""
        job = await self._get_job(job_id)
        if job and job.status in [JobStatus.PENDING, JobStatus.PROCESSING]:
            job.status = JobStatus.CANCELLED
            await self._save_job(job)
            
            # Remove from queue/processing
            await redis_manager.lrem(redis_manager.JOB_QUEUE, 0, job_id)
            await redis_manager.lrem(self.redis_manager.JOB_PROCESSING, 0, job_id)
            return True
        return False
    
    async def delete_job(self, job_id: str) -> bool:
        """Delete a job and its output file"""
        job = await self._get_job(job_id)
        if not job:
            return False
        
        # Delete output file if exists
        if job.output_path and Path(job.output_path).exists():
            Path(job.output_path).unlink()
        
        # Remove from Redis
        key = f"{redis_manager.JOB_PREFIX}:{job_id}"
        await redis_manager.delete(key)
        
        # Remove from queue/processing
        await redis_manager.lrem(redis_manager.JOB_QUEUE, 0, job_id)
        await redis_manager.lrem(self.redis_manager.JOB_PROCESSING, 0, job_id)
        
        return True
    
    async def _cleanup_old_jobs(self):
        """Periodically cleanup old completed/failed jobs"""
        while True:
            try:
                # Run cleanup every hour in the background
                await asyncio.sleep(3600)  
                cutoff_time = datetime.utcnow() - timedelta(days=2)
  
                keys = await redis_manager.keys(f"{redis_manager.JOB_PREFIX}:*")
                for key in keys:
                    data = await redis_manager.get(key, deserialize=False)
                    if data:
                        job = StitchJob.model_validate_json(data)
                        if job.status in [JobStatus.COMPLETED, JobStatus.FAILED, JobStatus.CANCELLED]:
                            if job.completed_at and job.completed_at < cutoff_time:
                                try:
                                    await self.delete_job(job.job_id)
                                except Exception as e:
                                    print(f"Issue deleting Job {e}")
            except Exception as e:
                print(f"Error in cleanup task: {str(e)}")