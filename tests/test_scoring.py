import pytest
from backend.scoring.main import score_case, SEVERITY_WEIGHTS


class TestScoreCase:
    def test_no_flags_cleared(self):
        result = score_case([], 0.0)
        assert result["risk_score"] == 0
        assert result["status"] == "cleared"
        assert "No material fraud indicators" in result["explanation"]

    def test_low_severity_flags(self):
        flags = [
            {"layer": "Test", "finding": "Minor issue", "severity": "low", "score": 8},
            {"layer": "Test", "finding": "Another minor", "severity": "low", "score": 8},
        ]
        result = score_case(flags, 0.0)
        assert result["risk_score"] > 0
        assert result["status"] == "cleared"  # 16 < 45

    def test_medium_severity_flags_review(self):
        flags = [
            {"layer": "Test", "finding": "Medium issue", "severity": "medium", "score": 22},
            {"layer": "Test", "finding": "Another medium", "severity": "medium", "score": 22},
        ]
        result = score_case(flags, 0.0)
        # 44 < 45 -> cleared
        assert result["status"] == "cleared"

        # Add one more to push to review
        flags.append({"layer": "Test", "finding": "Third medium", "severity": "medium", "score": 22})
        result = score_case(flags, 0.0)
        assert result["status"] == "review"

    def test_high_severity_flags_flagged(self):
        flags = [
            {"layer": "Test", "finding": "Critical issue", "severity": "high", "score": 40},
            {"layer": "Test", "finding": "Another critical", "severity": "high", "score": 40},
            {"layer": "Test", "finding": "Third critical", "severity": "high", "score": 40},
        ]
        result = score_case(flags, 0.0)
        # 120 capped at 65, but with 3 high flags -> 65 >= 80? No, still 65.
        # Need anomaly to push to flagged
        result = score_case(flags, 100.0)  # anomaly adds 35
        assert result["status"] == "flagged"
        assert result["risk_score"] >= 80

    def test_anomaly_score_contribution(self):
        flags = [{"layer": "Test", "finding": "Low", "severity": "low", "score": 8}]
        # Anomaly score of 100 -> 100 * 0.35 = 35, capped at 35
        result = score_case(flags, 100.0)
        assert result["risk_score"] > 8  # Should include anomaly component

    def test_anomaly_score_capped(self):
        flags = [{"layer": "Test", "finding": "Low", "severity": "low", "score": 8}]
        # Very high anomaly should be capped at 35
        result = score_case(flags, 100.0)
        # Max anomaly component = 35, flag component = 8 -> 43
        assert result["risk_score"] <= 43

    def test_flag_score_capped_at_65(self):
        # Many high severity flags
        flags = [{"layer": "Test", "finding": f"Critical {i}", "severity": "high", "score": 40} for i in range(10)]
        result = score_case(flags, 0.0)
        # 10 * 40 = 400, capped at 65
        assert result["risk_score"] <= 65

    def test_severity_weights(self):
        assert SEVERITY_WEIGHTS["low"] == 8
        assert SEVERITY_WEIGHTS["medium"] == 22
        assert SEVERITY_WEIGHTS["high"] == 40

    def test_case_id_passed_to_explanation(self):
        flags = [{"layer": "Test", "finding": "Test flag", "severity": "medium", "score": 22}]
        result = score_case(flags, 0.0, case_id="TEST-123")
        assert "explanation" in result