"""
pdf_processor_service imports OCR stacks at import time; stub them for fast tests.
"""

import os
import sys

# Pydantic Settings requires R2 fields; set defaults before any `app.*` import pulls config.
for _k, _v in (
    ("R2_ACCOUNT_ID", "test"),
    ("R2_ACCESS_KEY_ID", "test"),
    ("R2_SECRET_ACCESS_KEY", "test"),
    ("R2_BUCKET_NAME", "test-bucket"),
):
    os.environ.setdefault(_k, _v)

# CI / minimal envs may lack ebooklib; provide a tiny stub so structure_detector imports.
try:
    import ebooklib  # noqa: F401
except ImportError:
    import types

    _elib = types.ModuleType("ebooklib")
    _elib.ITEM_DOCUMENT = 9
    _epub = types.ModuleType("ebooklib.epub")
    sys.modules["ebooklib"] = _elib
    sys.modules["ebooklib.epub"] = _epub
    _elib.epub = _epub

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
