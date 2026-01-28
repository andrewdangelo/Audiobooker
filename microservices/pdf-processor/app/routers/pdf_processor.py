"""
PDF Processor Router
"""
__author__ = "Mohammad Saifan"

from fastapi import (HTTPException, BackgroundTasks, status, APIRouter, UploadFile, File)

from app.models.schemas import (ProcessPDFRequest, ProcessPDFResponse, JobStatusResponse)
from app.models.audiobook import (Audiobook)
from app.database import (audio_book_db, database)
from app.services import (pdf_processor_service, r2_service)

from datetime import datetime
import logging

logger = logging.getLogger(__name__)
router = APIRouter()

# Initialize services
r2_svc = r2_service.R2Service()
pdf_processor = pdf_processor_service.PDFProcessorService()


@router.post("/upload_new_pdf")
async def upload_pdf(file: UploadFile = File(...)):
    """
    Upload a PDF file for conversion
    
    - **file**: PDF file to upload (max 50MB)
    
    Returns audiobook record with storage location
    """
    try:
        # Validate file extension
        if not file.filename or not file.filename.endswith('.pdf'):
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Only PDF files are allowed")
        
        # Validate filename is a string
        if not isinstance(file.filename, str):
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Invalid filename type: {type(file.filename).__name__}")
        
        # Read file content
        logger.info(f"Processing upload: {file.filename}")
        file_content = await file.read()
        file_size = len(file_content)
        
        # Validate file size (50MB) #TODO make configurable later
        if file_size > 52428800:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"File size exceeds maximum allowed size of 50MB")
        
        # Sanitize filename and generate R2 key and send up to R2
        r2_path, r2_key, r2_book_name, r2_file_type = r2_svc.generate_key(file_name=file.filename)
       
        # Upload to R2
        output_key = f"{r2_path}"
        send_up_to_r2 = r2_svc.upload_processed_data(key=output_key, data=file_content)        
               
        # Preparing data as dictionary
        audiobook_data = {
            "r2_key": r2_key,
            "title": r2_book_name,  
            "pdf_path": r2_path,
            "status": "COMPLETED"
        }
        
        logger.info(f"Creating database record")
        db_gen = database.get_db()
        db = next(db_gen)
        audiobook_service = audio_book_db.AudiobookDBService(db, Audiobook)
        audiobook = audiobook_service.create(audiobook_data)
        
        logger.info(f"Upload complete - ID: {audiobook.r2_key}")
        
        # Return audiobook details
        return {
            "id": str(audiobook.r2_key),
            "title": audiobook.title,
            "pdf_path": audiobook.pdf_path,
            "r2_key": send_up_to_r2["key"],
            "r2_bucket": send_up_to_r2["bucket"],
            "status": audiobook.status,
            "message": "File uploaded successfully to R2 and database"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Upload failed: {str(e)}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Failed to process upload: {str(e)}")


@router.post("/process_pdf", response_model=ProcessPDFResponse, status_code=status.HTTP_202_ACCEPTED)
async def process_pdf(request: ProcessPDFRequest, background_tasks: BackgroundTasks):
    """
    Process a PDF file from R2 storage
    
    Args:
        request: PDF processing request with R2 key and options
        background_tasks: FastAPI background tasks for async processing. Queue will be controlled from api proxy.
    
    Returns:
        Job information with job_id for status tracking
    """
    try:
        logger.info(f"Received PDF processing request for key: {request.r2_pdf_path}")
        
        # Verify file exists in R2
        if not r2_svc.file_exists(request.r2_pdf_path):
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"PDF not found in R2: {request.r2_pdf_path}")
        
        # Generate job ID
        job_id = f"job_{request.r2_pdf_path.replace('/', '_')}"
        
        # Initialize job in Redis
        await pdf_processor.create_job(job_id, {
            "job_id": job_id,
            "status": "pending",
            "r2_key": request.r2_pdf_path,
            "created_at": f"{datetime.now().strftime('%m-%d-%Y')} at {datetime.now().strftime('%I:%M %p')}",
            "progress": 0,
            "message": "Job queued for processing"
        })
        
        # Add processing task to background
        background_tasks.add_task(pdf_processor.process_pdf_task, job_id=job_id, r2_key=request.r2_pdf_path, chunk_size=request.chunk_size,
                            chunk_overlap=request.chunk_overlap, output_format=request.output_format)
        
        logger.info(f"Job {job_id} queued for processing")
        
        return ProcessPDFResponse(
            job_id=job_id,
            status="accepted",
            message="PDF processing job accepted",
            r2_key=request.r2_pdf_path
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error processing PDF request: {str(e)}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Failed to process PDF: {str(e)}")


@router.get("/job/{job_id}", response_model=JobStatusResponse)
async def get_job_status(job_id: str):
    """
    Get the status of a processing job
    
    Args:
        job_id: Unique job identifier from redis
    
    Returns:
        Current job status and details
    """
    job = await pdf_processor.get_job_by_id(job_id)
    
    if not job:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Job {job_id} not found")
    
    return JobStatusResponse(**job)

@router.get("/get_all_jobs")
async def get_jobs():
    """
    Get the status of a processing job from redis
    
    Args:
        job_id: Unique job identifier
    
    Returns:
        Current job status and details
    """
    job = await pdf_processor.get_all_jobs()
    
    if len(job) == 0:
        return {
            "JOBS": "NO JOBS FOUND"
        }
    else:
        return job