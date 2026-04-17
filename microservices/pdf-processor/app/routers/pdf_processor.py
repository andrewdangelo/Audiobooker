"""
PDF Processor Router
"""
__author__ = "Mohammad Saifan"

from fastapi import HTTPException, BackgroundTasks, status, APIRouter, UploadFile, File, Query, Depends
from app.models.schemas import ProcessPDFRequest, ProcessPDFResponse, JobStatusResponse
import json
from typing import Any, Dict
from app.database import database, db_engine
from app.models.db_models import Collections
from app.services import pdf_processor_service, r2_service
from app.utils.validators import is_allowed_book_magic
from datetime import datetime
import logging

logger = logging.getLogger(__name__)
router = APIRouter()

# Initialize services
r2_svc = r2_service.R2Service()
pdf_processor = pdf_processor_service.PDFProcessorService()


@router.post("/upload_new_pdf")
async def upload_pdf(user_id: str = Query(..., description="User ID"), file: UploadFile = File(...)):
    """Upload a PDF or EPUB file for conversion."""
    try:
        if not file.filename or not isinstance(file.filename, str):
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Invalid filename type: {type(file.filename).__name__}")
        lower = file.filename.lower()
        if not (lower.endswith(".pdf") or lower.endswith(".epub")):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Only PDF and EPUB files are allowed",
            )

        logger.info(f"Processing upload: {file.filename} for user {user_id}")
        file_content = await file.read()
        file_size = len(file_content)

        if not is_allowed_book_magic(file_content, file.filename):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="File content does not match a valid PDF or EPUB",
            )
        
        if file_size > 52428800:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"File size exceeds maximum allowed size of 50MB")
        
        r2_path, r2_key, r2_book_name, r2_file_type = r2_svc.generate_key(file_name=file.filename)
        output_key = f"{r2_path}"
        send_up_to_r2 = r2_svc.upload_processed_data(key=output_key, data=file_content)
        
        audiobook_data = {"r2_key": r2_key, "user_id": user_id, "title": r2_book_name, "pdf_path": r2_path, "status": "COMPLETED"}
        
        logger.info(f"Creating database record")
        db_func = database.get_db()
        db = db_func()
        audiobook_service = db_engine.MongoDBService(db, Collections.AUDIOBOOKS)
        audiobook = audiobook_service.create(audiobook_data)
        
        logger.info(f"Upload complete - ID: {audiobook.get('r2_key')}")
        
        return {"id": str(audiobook.get("r2_key")), "title": audiobook.get("title"), "pdf_path": audiobook.get("pdf_path"), "r2_key": send_up_to_r2["key"], "r2_bucket": send_up_to_r2["bucket"], "status": audiobook.get("status"), "message": "File uploaded successfully to R2 and database"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Upload failed: {str(e)}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Failed to process upload: {str(e)}")


@router.post("/process_pdf", response_model=ProcessPDFResponse, status_code=status.HTTP_202_ACCEPTED)
async def process_pdf(user_id: str = Query(..., description="User ID"), request: ProcessPDFRequest = None, background_tasks: BackgroundTasks = None):
    """Process a PDF file from R2 storage"""
    try:
        logger.info(f"Received PDF processing request for key: {request.r2_pdf_path} from user {user_id}")
        
        if not r2_svc.file_exists(request.r2_pdf_path):
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"PDF not found in R2: {request.r2_pdf_path}")
        
        job_id = f"job_{request.r2_pdf_path.replace('/', '_')}"
        
        meta = request.metadata or {}
        credit_type = meta.get("credit_type") if isinstance(meta.get("credit_type"), str) else "basic"
        if credit_type not in ("basic", "premium"):
            credit_type = "basic"

        await pdf_processor.create_job(
            job_id,
            {
                "job_id": job_id,
                "user_id": user_id,
                "status": "pending",
                "r2_key": request.r2_pdf_path,
                "pipeline_stage": "pdf_processing",
                "created_at": f"{datetime.now().strftime('%m-%d-%Y')} at {datetime.now().strftime('%I:%M %p')}",
                "progress": 0,
                "message": "Job queued for processing",
            },
        )

        background_tasks.add_task(
            pdf_processor.process_pdf_task,
            job_id=job_id,
            user_id=user_id,
            r2_key=request.r2_pdf_path,
            chunk_size=request.chunk_size,
            chunk_overlap=request.chunk_overlap,
            output_format=request.output_format,
            credit_type=credit_type,
        )
        
        logger.info(f"Job {job_id} queued for processing")
        
        return ProcessPDFResponse(job_id=job_id, status="accepted", message="PDF processing job accepted", r2_key=request.r2_pdf_path)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error processing PDF request: {str(e)}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Failed to process PDF: {str(e)}")


@router.get("/job/{job_id}", response_model=JobStatusResponse)
async def get_job_status(job_id: str, user_id: str = Query(..., description="User ID")):
    """Get the status of a processing job"""
    job = await pdf_processor.get_job_by_id(job_id)

    if not job:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Job {job_id} not found")

    j: Dict[str, Any] = dict(job)
    progress_raw = j.get("progress", 0)
    try:
        progress = int(progress_raw)
    except (TypeError, ValueError):
        progress = 0
    progress = max(0, min(100, progress))

    raw_result = j.get("result")
    parsed_result = None
    if isinstance(raw_result, dict):
        parsed_result = raw_result
    elif isinstance(raw_result, str):
        try:
            parsed_result = json.loads(raw_result)
        except json.JSONDecodeError:
            parsed_result = None

    return JobStatusResponse(
        job_id=str(j.get("job_id") or job_id),
        status=str(j.get("status") or "pending"),
        progress=progress,
        message=str(j.get("message") or ""),
        created_at=str(j.get("created_at") or ""),
        completed_at=j.get("completed_at"),
        result=parsed_result,
        error=j.get("error"),
        pipeline_stage=j.get("pipeline_stage") if j.get("pipeline_stage") is not None else None,
        audiobook_id=j.get("audiobook_id") if j.get("audiobook_id") is not None else None,
    )


@router.get("/get_all_jobs")
async def get_jobs(user_id: str = Query(..., description="User ID")):
    """Get all processing jobs"""
    job = await pdf_processor.get_all_jobs()
    
    if len(job) == 0:
        return {"JOBS": "NO JOBS FOUND"}
    else:
        return job
