from pydantic import BaseModel
from typing import Optional

class AudiobookDatabaseCreateRequest(BaseModel):
    __tablename__ = "processed_json_audiobooks"
    r2_key: str
    title: str
    pdf_path: Optional[str]
    status: str
    
class AudiobookDatabaseGetByIDRequest(BaseModel):
    audiobook_id: str

class AudiobookDatabaseDeleteRequest(BaseModel):
    audiobook_id: str


