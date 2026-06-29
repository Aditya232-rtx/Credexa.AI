import pytest
from backend.anomaly.main import (
    detect_anomalies,
    _build_feature_vector,
    _count_round_numbers,
    AnomalyResult,
)


class TestCountRoundNumbers:
    def test_no_amounts(self):
        count, pct = _count_round_numbers("No monetary values here")
        assert count == 0
        assert pct == 0.0

    def test_round_numbers(self):
        text = "Amounts: 1000, 50000, 100000, 250000"
        count, pct = _count_round_numbers(text)
        assert count == 4
        assert pct == 100.0  # All end in 000

    def test_mixed_round_numbers(self):
        text = "Amounts: 1000, 50050, 100000, 250001"
        count, pct = _count_round_numbers(text)
        assert count == 4
        assert pct == 50.0  # 2 out of 4 end in 000

    def test_out_of_range_amounts(self):
        text = "Amounts: 50, 200000000"
        count, pct = _count_round_numbers(text)
        assert count == 0  # Both out of range (100-100M)


class TestBuildFeatureVector:
    def test_empty_documents(self):
        vectors = _build_feature_vector([])
        assert vectors == []

    def test_single_document(self):
        docs = [{
            "text": "Transaction: ₹1,00,000 and ₹50,000",
            "flags": [{"score": 30}, {"score": 20}],
            "tables": [{}],
            "pages": [{"ocr_confidence": 0.95}],
            "metadata": {"author": "test"},
            "file_size": 1024,
        }]
        vectors = _build_feature_vector(docs)
        assert len(vectors) == 1
        assert len(vectors[0]) == 11  # 11 features
        # Check feature values make sense
        assert vectors[0][0] > 0  # text_length
        assert vectors[0][1] == 2  # flag_count
        assert vectors[0][2] == 1  # table_count
        assert vectors[0][3] == 1  # page_count
        assert vectors[0][6] > 0  # pct_round (has 100000 and 50000)

    def test_document_without_pages(self):
        docs = [{
            "text": "Simple text",
            "flags": [],
            "tables": [],
            "pages": [],
            "metadata": {},
            "file_size": 512,
        }]
        vectors = _build_feature_vector(docs)
        assert len(vectors) == 1
        assert vectors[0][8] == 0.0  # ocr_confidence_avg


class TestDetectAnomalies:
    def test_empty_documents(self):
        result = detect_anomalies([])
        assert isinstance(result, AnomalyResult)
        assert result.score == 0.0
        assert result.flags == []

    def test_insufficient_documents_heuristic(self):
        docs = [
            {"text": "Doc 1", "flags": [], "tables": [], "pages": [], "metadata": {}, "file_size": 100},
            {"text": "Doc 2", "flags": [{"score": 10}], "tables": [], "pages": [], "metadata": {}, "file_size": 200},
        ]
        result = detect_anomalies(docs)
        assert isinstance(result, AnomalyResult)
        # Uses heuristic since < 3 documents
        assert result.score >= 0

    def test_many_documents_isolation_forest(self):
        docs = []
        for i in range(5):
            docs.append({
                "text": f"Document {i} with amount {1000 * (i + 1)}",
                "flags": [{"score": 10 * i}],
                "tables": [],
                "pages": [{"ocr_confidence": 0.9}],
                "metadata": {"key": f"value{i}"},
                "file_size": 1000 * (i + 1),
            })
        result = detect_anomalies(docs)
        assert isinstance(result, AnomalyResult)
        assert 0 <= result.score <= 100
        assert isinstance(result.features, dict)

    def test_anomaly_flags_structure(self):
        docs = [{
            "document_id": "doc-1",
            "text": "Amount: 1000",
            "flags": [{"score": 50}],
            "tables": [],
            "pages": [{"ocr_confidence": 0.5}],
            "metadata": {},
            "file_size": 100,
        } for _ in range(3)]
        result = detect_anomalies(docs)
        for flag in result.flags:
            assert "layer" in flag
            assert "finding" in flag
            assert "severity" in flag
            assert "score" in flag
            assert flag["layer"] == "ML Anomaly"