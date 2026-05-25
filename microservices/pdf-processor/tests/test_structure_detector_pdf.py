"""StructureDetector smoke tests using in-memory PDFs."""

import fitz
import pytest

from app.services.structure_detector import StructureDetector


def _pdf_two_chapters_via_regex() -> bytes:
    """Minimal PDF where tier-3 regex can find two chapter headings."""
    doc = fitz.open()
    p1 = doc.new_page()
    p1.insert_text((72, 100), "Chapter 1\n\n" + ("word " * 80))
    p2 = doc.new_page()
    p2.insert_text((72, 100), "Chapter 2\n\n" + ("other " * 80))
    data = doc.tobytes()
    doc.close()
    return data


def test_detect_chapters_from_pdf_returns_list():
    pdf_bytes = _pdf_two_chapters_via_regex()
    det = StructureDetector()
    chapters = det.detect_chapters_from_pdf(pdf_bytes, [])
    assert isinstance(chapters, list)
    assert len(chapters) >= 1
    for ch in chapters:
        assert ch.text.strip()
        assert ch.chapter_number >= 1
        assert ch.detection_method


def test_single_page_pdf_fallback_one_chapter():
    doc = fitz.open()
    page = doc.new_page()
    page.insert_text((72, 72), "Just some prose without headings. " * 15)
    data = doc.tobytes()
    doc.close()
    det = StructureDetector()
    chapters = det.detect_chapters_from_pdf(data, [])
    assert len(chapters) == 1
    assert chapters[0].detection_method == "none" or chapters[0].chapter_number == 1
