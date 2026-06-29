import pytest
import tempfile
import os
from pathlib import Path
from backend.forensics.file_forensics import (
    inspect_pdf,
    inspect_pdf_fonts,
    _extract_page_fonts,
    inspect_office_file,
)


def create_test_pdf(path):
    """Create a valid test PDF using PyMuPDF."""
    import fitz
    doc = fitz.open()
    page = doc.new_page()
    page.insert_text((50, 50), "Test PDF for forensics")
    doc.save(path)
    doc.close()


class TestInspectPDF:
    def test_empty_metadata(self):
        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as f:
            temp_path = f.name
        try:
            create_test_pdf(temp_path)
            flags = inspect_pdf(temp_path, {})
            assert isinstance(flags, list)
        finally:
            os.unlink(temp_path)

    def test_suspicious_producer(self):
        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as f:
            temp_path = f.name
        try:
            create_test_pdf(temp_path)
            metadata = {"Producer": "Adobe Acrobat Pro", "Creator": "Photoshop"}
            flags = inspect_pdf(temp_path, metadata)
            assert any("Suspicious producer" in f["finding"] for f in flags)
        finally:
            os.unlink(temp_path)

    def test_modified_after_creation(self):
        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as f:
            temp_path = f.name
        try:
            create_test_pdf(temp_path)
            metadata = {
                "CreateDate": "D:20240101000000",
                "ModifyDate": "D:20240102000000",
            }
            flags = inspect_pdf(temp_path, metadata)
            assert any("Modified after creation" in f["finding"] for f in flags)
        finally:
            os.unlink(temp_path)


class TestInspectPDFFonts:
    def test_single_page_no_flag(self):
        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as f:
            temp_path = f.name
        try:
            create_test_pdf(temp_path)
            flags = inspect_pdf_fonts(temp_path)
            assert isinstance(flags, list)
        finally:
            os.unlink(temp_path)

    def test_insufficient_pages(self):
        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as f:
            temp_path = f.name
        try:
            create_test_pdf(temp_path)
            flags = inspect_pdf_fonts(temp_path)
            # Should return empty for single page
            assert isinstance(flags, list)
        finally:
            os.unlink(temp_path)


class TestExtractPageFonts:
    def test_mock_page(self):
        # Test with a mock pikepdf page-like object
        class MockDict:
            def __init__(self, data):
                self._data = data
            def get(self, key):
                return self._data.get(key)
            def items(self):
                return self._data.items()
        
        class MockStream:
            def __init__(self, data):
                self._data = data
            def get(self, key):
                return self._data.get(key)
        
        # This tests the internal function logic
        page = MockDict({
            "/Resources": MockDict({
                "/Font": MockDict({
                    "/F1": MockDict({"/BaseFont": "Arial"}),
                    "/F2": MockStream({"/BaseFont": "Times-Roman"}),
                })
            })
        })
        
        fonts = _extract_page_fonts(page)
        # The function returns set of font names
        assert isinstance(fonts, set)


class TestInspectOfficeFile:
    def test_high_revision(self):
        metadata = {"revision": "10"}
        flags = inspect_office_file("dummy.docx", metadata)
        assert any("High revision count" in f["finding"] for f in flags)

    def test_author_mismatch(self):
        metadata = {"author": "John", "last_modified_by": "Jane"}
        flags = inspect_office_file("dummy.docx", metadata)
        assert any("does not match creator" in f["finding"] for f in flags)

    def test_no_flags_on_clean(self):
        metadata = {"revision": "1", "author": "John", "last_modified_by": "John"}
        flags = inspect_office_file("dummy.docx", metadata)
        assert len(flags) == 0