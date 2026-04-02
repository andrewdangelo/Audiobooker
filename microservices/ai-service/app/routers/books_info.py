from fastapi import APIRouter, HTTPException, UploadFile, File, Depends
from fastapi.responses import FileResponse
from typing import Optional
import json
import uuid
from datetime import datetime
from app.services.ai_text_service import AITextService
from app.services.ai_emb_service import AIEmbeddingService

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Tuple, Dict, Any, Optional

from app.services.ai_model_factory import ModelProvider

router = APIRouter()

# CRUD for Book Info manager -> character names and summary for verification when processing PDF

# Based on data generation and seeding and storage -> then reference later

# shortlist default of well-known books