"""
pdf_processor_service imports OCR stacks at import time; stub them for fast tests.
"""

import sys
from unittest.mock import MagicMock

import mongomock
import pytest

import app.database.database as pdf_db

for _mod in ("pytesseract", "easyocr"):
    sys.modules.setdefault(_mod, MagicMock())


@pytest.fixture(autouse=True)
def mongo_pdf():
    pdf_db.sync_client = mongomock.MongoClient()
    yield
    pdf_db.sync_client = None
