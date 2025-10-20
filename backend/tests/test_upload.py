"""
Tests for upload endpoints
"""

import pytest
from io import BytesIO


def test_upload_invalid_file_type(client):
    """Test uploading non-PDF file"""
    file_content = b"Not a PDF file"
    files = {"file": ("test.txt", BytesIO(file_content), "text/plain")}
    
    response = client.post("/api/v1/upload/", files=files)
    assert response.status_code == 400


# TODO: Add more tests
# - test_upload_pdf_success
# - test_upload_file_too_large
# - test_get_upload_status
