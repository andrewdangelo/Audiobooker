from fastapi import (FastAPI, HTTPException, BackgroundTasks, status, APIRouter)
from app.models.schemas import (ProcessPDFRequest, ProcessPDFResponse, JobStatusResponse, HealthResponse)
from app.database import (audio_book_db, database)
from app.services import (pdf_processor_service, r2_service)

from typing import Dict, Any
from datetime import datetime
import logging

logger = logging.getLogger(__name__)
router = APIRouter()

# Initialize services
r2_service = r2_service.R2Service()
pdf_processor = pdf_processor_service.PDFProcessorService()

# In-memory job tracking (use Redis in production)
job_store: Dict[str, Dict[str, Any]] = {}

@router.post("/process_pdf", response_model=ProcessPDFResponse, status_code=status.HTTP_202_ACCEPTED)
async def process_pdf(request: ProcessPDFRequest, background_tasks: BackgroundTasks):
    """
    Process a PDF file from R2 storage
    
    Args:
        request: PDF processing request with R2 key and options
        background_tasks: FastAPI background tasks for async processing
    
    Returns:
        Job information with job_id for status tracking
    """
    try:
        logger.info(f"Received PDF processing request for key: {request.r2_key}")
        # Verify file exists in R2
        if not r2_service.file_exists(request.r2_key):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"PDF not found in R2: {request.r2_key}"
            )
        
        # Generate job ID
        job_id = f"job_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}_{request.r2_key.replace('/', '_')}"
        
        # Initialize job tracking
        job_store[job_id] = {
            "job_id": job_id,
            "status": "pending",
            "r2_key": request.r2_key,
            "created_at": datetime.utcnow().isoformat(),
            "progress": 0,
            "message": "Job queued for processing"
        }
        
        # Add processing task to background
        background_tasks.add_task(process_pdf_task, job_id=job_id, r2_key=request.r2_key, chunk_size=request.chunk_size, chunk_overlap=request.chunk_overlap, output_format=request.output_format)
        
        logger.info(f"Job {job_id} queued for processing")
        
        return ProcessPDFResponse(
            job_id=job_id,
            status="accepted",
            message="PDF processing job accepted",
            r2_key=request.r2_key
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error processing PDF request: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to process PDF: {str(e)}"
        )

async def process_pdf_task(job_id: str, r2_key: str, chunk_size: int, chunk_overlap: int, output_format: str):
    """
    Background task for processing PDF
    
    Args:
        job_id: Unique job identifier
        r2_key: R2 storage key for the PDF
        chunk_size: Size of text chunks
        chunk_overlap: Overlap between chunks
        output_format: Output format (json, text, markdown)
    """
    try:
        logger.info(f"Starting PDF processing for job {job_id}")
        
        # Update job status
        job_store[job_id]["status"] = "processing"
        job_store[job_id]["message"] = "Downloading PDF from R2"
        job_store[job_id]["progress"] = 10
        
        # Download PDF from R2
        pdf_data = r2_service.download_file(r2_key)
        
        job_store[job_id]["message"] = "Extracting text from PDF"
        job_store[job_id]["progress"] = 30
        
        # Process PDF
        result = await pdf_processor.process_pdf(pdf_data=pdf_data, chunk_size=chunk_size, chunk_overlap=chunk_overlap, output_format=output_format)
        
        job_store[job_id]["progress"] = 80
        job_store[job_id]["message"] = "Uploading processed data to R2"
        
        # Upload results back to R2 after getting final json output
        output_key = f"processed/{r2_key.replace('.pdf', '')}_processed.json"
        r2_service.upload_processed_data(output_key, result)
        
        # Create audiobook record in database
        logger.info(f"Creating database record")
        db_gen = database.get_db()
        db = next(db_gen)
        audiobook_service = audio_book_db.AudiobookDBService(db)
        
        # Preparing data as dictionary
        audiobook_data = {
            "id": job_id,
            "title": r2_key.split("/")[-1],  # Remove .pdf extension so you can attain the name of the book
            "pdf_path": r2_key,  # r2://bucket/key format
            "status": "COMPLETED"
        }
        
        audiobook = audiobook_service.create(audiobook_data)
        
        logger.info(f"Upload complete - ID: {audiobook.id}")
        
        # Update job with results
        job_store[job_id]["status"] = "completed"
        job_store[job_id]["progress"] = 100
        job_store[job_id]["message"] = "Processing completed successfully"
        job_store[job_id]["completed_at"] = datetime.utcnow().isoformat()
        job_store[job_id]["result"] = {
            "output_key": output_key,
            "total_chunks": result.get("total_chunks", 0),
            "total_pages": result.get("total_pages", 0),
            "total_characters": result.get("total_characters", 0)
        }
        
        logger.info(f"Job {job_id} completed successfully")
        
    except Exception as e:
        logger.error(f"Job {job_id} failed: {str(e)}", exc_info=True)
        
        job_store[job_id]["status"] = "failed"
        job_store[job_id]["progress"] = 0
        job_store[job_id]["message"] = "Processing failed"
        job_store[job_id]["completed_at"] = datetime.utcnow().isoformat()
        job_store[job_id]["error"] = str(e)