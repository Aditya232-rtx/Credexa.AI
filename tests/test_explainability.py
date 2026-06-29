import pytest
from backend.scoring.explainability import generate_explanation, _template_explanation


class TestGenerateExplanation:
    def test_no_flags_returns_default_message(self):
        result = generate_explanation([], 0, "cleared", "TEST-123")
        assert "No material fraud indicators" in result

    def test_high_flags_in_explanation(self):
        flags = [
            {"layer": "Test", "finding": "Critical issue found", "severity": "high", "score": 40},
            {"layer": "Test", "finding": "Another critical", "severity": "high", "score": 35},
        ]
        result = generate_explanation(flags, 85, "flagged", "TEST-123")
        assert "Critical issue found" in result
        assert "85" in result or "flagged" in result.lower()

    def test_medium_flags_in_explanation(self):
        flags = [
            {"layer": "Test", "finding": "Medium concern", "severity": "medium", "score": 22},
        ]
        result = generate_explanation(flags, 45, "review", "TEST-123")
        assert "Medium concern" in result

    def test_case_id_in_prompt(self):
        flags = [{"layer": "Test", "finding": "Test flag", "severity": "medium", "score": 22}]
        # Just verify it doesn't crash with case_id
        result = generate_explanation(flags, 50, "review", "CASE-456")
        assert isinstance(result, str)
        assert len(result) > 0


class TestTemplateExplanation:
    def test_no_flags(self):
        result = _template_explanation([], 0, "cleared")
        assert "No material fraud indicators" in result

    def test_high_flags_only(self):
        flags = [
            {"layer": "Layer1", "finding": "High finding 1", "severity": "high", "score": 40},
            {"layer": "Layer2", "finding": "High finding 2", "severity": "high", "score": 35},
            {"layer": "Layer3", "finding": "High finding 3", "severity": "high", "score": 30},
            {"layer": "Layer4", "finding": "High finding 4", "severity": "high", "score": 25},
        ]
        result = _template_explanation(flags, 85, "flagged")
        assert "Critical findings:" in result
        assert "High finding 1" in result
        assert "High finding 2" in result
        assert "High finding 3" in result

    def test_medium_flags_only(self):
        flags = [
            {"layer": "Layer1", "finding": "Medium finding", "severity": "medium", "score": 22},
        ]
        result = _template_explanation(flags, 45, "review")
        assert "Additional concerns:" in result
        assert "Medium finding" in result

    def test_mixed_severity(self):
        flags = [
            {"layer": "Layer1", "finding": "High finding", "severity": "high", "score": 40},
            {"layer": "Layer2", "finding": "Medium finding", "severity": "medium", "score": 22},
            {"layer": "Layer3", "finding": "Low finding", "severity": "low", "score": 8},
        ]
        result = _template_explanation(flags, 70, "flagged")
        assert "Critical findings:" in result
        assert "Additional concerns:" in result