"""
Custom Exception Classes
"""

from fastapi import HTTPException, status


class AudiobookNotFoundException(HTTPException):
    """Raised when an audiobook is not found"""
    
    def __init__(self, audiobook_id: str):
        super().__init__(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Audiobook with id '{audiobook_id}' not found"
        )


class FileUploadException(HTTPException):
    """Raised when file upload fails"""
    
    def __init__(self, message: str = "File upload failed"):
        super().__init__(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=message
        )


class ConversionException(HTTPException):
    """Raised when conversion fails"""
    
    def __init__(self, message: str = "Conversion failed"):
        super().__init__(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=message
        )


class InvalidFileException(HTTPException):
    """Raised when uploaded file is invalid"""
    
    def __init__(self, message: str = "Invalid file"):
        super().__init__(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=message
        )
