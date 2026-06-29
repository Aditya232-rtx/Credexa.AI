import json
import tempfile
from pathlib import Path
from typing import Any, Dict

import pytest

from backend.anomaly.main import detect_anomalies
from backend.consistency.cross_doc import cross_check_documents, extract_entities
from backend.forensics.file_forensics import inspect_pdf, inspect_office_file
from backend.forensics.math_validator import validate_financials
from backend.forensics.visual_forensics import run_ela
from backend.scoring.main import score_case
from backend.router.classifier import DocumentRouter


class TestFullPipelineIntegration:
    """End-to-end pipeline test using synthetic text docs."""

    def test_empty_case_returns_zero(self):
        flags = []
        anomaly = detect_anomalies([])
        result = score_case(flags, anomaly.score)
        assert result["risk_score"] == 0
        assert result["status"] == "cleared"

    def test_single_doc_with_flags_flows_through_scoring(self):
        doc = {
            "text": "PAN: ABCDE1234F\nAmount: ₹10,00,000\nURN: FAKE-DOC-001",
            "flags": [],
            "tables": [],
            "pages": [{"ocr_confidence": 0.92}],
            "metadata": {"author": "test"},
            "file_size": 2048,
        }
        anomaly = detect_anomalies([doc])
        flags = anomaly.flags
        result = score_case(flags + [], anomaly.score)
        assert "risk_score" in result
        assert "status" in result
        assert "explanation" in result
        assert 0 <= result["risk_score"] <= 100

    def test_cross_doc_flag_generation(self):
        docs = [
            {
                "text": "My name is Rajesh Kumar. My PAN is ABCDE1234F. I earn ₹5,00,000 per annum.",
                "flags": [],
                "tables": [],
                "pages": [],
                "metadata": {},
                "file_size": 100,
            },
            {
                "text": "Name: Rajesh Mehta. PAN: ABCDE1234F. Reported income: ₹8,00,000.",
                "flags": [],
                "tables": [],
                "pages": [],
                "metadata": {},
                "file_size": 100,
            },
        ]
        entities_list = [extract_entities(d["text"]) for d in docs]
        results = cross_check_documents(entities_list)
        assert isinstance(results, list)

    def test_anomaly_plus_flags_aggregates_correctly(self):
        docs = [
            {
                "text": f"Document {i} with amount {1000 * (i + 1)}",
                "flags": [{"score": 10 * i}],
                "tables": [],
                "pages": [{"ocr_confidence": 0.9}],
                "metadata": {"key": f"value{i}"},
                "file_size": 1000 * (i + 1),
            }
            for i in range(5)
        ]
        anomaly = detect_anomalies(docs)
        all_flags = anomaly.flags
        result = score_case(all_flags, anomaly.score)
        assert 0 <= result["risk_score"] <= 100
        assert result["status"] in ("cleared", "review", "flagged")

    def test_full_pipeline_no_crash(self):
        docs = [
            {
                "text": "Statement from HDFC Bank for account 123456789. Total credit: ₹1,00,000. Total debit: ₹50,000.",
                "flags": [],
                "tables": [{"rows": 5}],
                "pages": [{"ocr_confidence": 0.88}],
                "metadata": {"bank": "HDFC"},
                "file_size": 5000,
            },
            {
                "text": "ITR for AY 2024-25. Gross total income: ₹1,00,000. Tax payable: ₹5,000.",
                "flags": [],
                "tables": [],
                "pages": [{"ocr_confidence": 0.95}],
                "metadata": {"type": "ITR"},
                "file_size": 3000,
            },
        ]
        try:
            entities = [extract_entities(d["text"]) for d in docs]
            cross_flags = cross_check_documents(entities)
            anomaly = detect_anomalies(docs)
            all_flags = []
            all_flags.extend(cross_flags)
            all_flags.extend(anomaly.flags)
            result = score_case(all_flags, anomaly.score)
            assert isinstance(result["risk_score"], (int, float))
            assert isinstance(result["status"], str)
        except Exception as e:
            pytest.fail(f"Pipeline crashed: {e}")

    def test_router_classifier_does_not_crash(self):
        router = DocumentRouter()
        result = router.classify_document({"filename": "statement.pdf", "text": "bank statement", "page_count": 1})
        assert isinstance(result, str)


class TestVisualForensicsMock:
    def test_ela_on_synthetic_image(self):
        from PIL import Image
        import io
        img = Image.new("RGB", (100, 100), color="white")
        flags = run_ela(img)
        assert isinstance(flags, list)

    def test_ela_returns_list(self):
        from PIL import Image
        img = Image.new("RGB", (200, 200), color="gray")
        flags = run_ela(img)
        assert isinstance(flags, list)


class TestFileForensicsMock:
    def test_inspect_on_empty_pdf(self):
        import io
        from reportlab.pdfgen import canvas
        buf = io.BytesIO()
        c = canvas.Canvas(buf)
        c.drawString(100, 750, "Test PDF")
        c.save()
        pdf_bytes = buf.getvalue()

        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as f:
            f.write(pdf_bytes)
            pdf_path = f.name

        try:
            result = inspect_pdf(pdf_path, {})
            assert isinstance(result, list)
        finally:
            Path(pdf_path).unlink(missing_ok=True)

    def test_inspect_office_file_no_crash(self):
        import io
        try:
            from openpyxl import Workbook
            wb = Workbook()
            ws = wb.active
            ws.title = "Sheet1"
            ws["A1"] = "Test"
            with tempfile.NamedTemporaryFile(suffix=".xlsx", delete=False) as f:
                wb.save(f.name)
                xlsx_path = f.name
            try:
                result = inspect_office_file(xlsx_path, {})
                assert isinstance(result, list)
            finally:
                Path(xlsx_path).unlink(missing_ok=True)
        except ImportError:
            pytest.skip("openpyxl not available")


class TestMathValidatorSimple:
    def test_financial_validation_no_crash(self):
        text = "Income: ₹5,00,000. Expenses: ₹3,00,000."
        tables = [["Income", "5,00,000"], ["Expenses", "3,00,000"]]
        result = validate_financials(text, tables, "pdf")
        assert isinstance(result, list)
