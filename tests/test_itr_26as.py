import pytest
from backend.forensics.math_validator import (
    _extract_itr_income,
    _extract_26as_credits,
    validate_itr_vs_26as,
    validate_financials,
)


class TestExtractITRIncome:
    def test_total_income_pattern(self):
        text = "Total Income: ₹10,00,000"
        result = _extract_itr_income(text)
        assert result == 1000000.0

    def test_gross_total_income_pattern(self):
        text = "Gross Total Income: 500000"
        result = _extract_itr_income(text)
        assert result == 500000.0

    def test_net_income_pattern(self):
        text = "Net Income: ₹2,50,000.50"
        result = _extract_itr_income(text)
        assert result == 250000.50

    def test_no_income_found(self):
        text = "Some other text without income"
        result = _extract_itr_income(text)
        assert result is None


class TestExtract26ASCredits:
    def test_total_credits_pattern(self):
        text = "Total Credits: ₹5,00,000"
        result = _extract_26as_credits(text)
        assert result == 500000.0

    def test_tds_total_pattern(self):
        text = "TDS Total: 300000"
        result = _extract_26as_credits(text)
        assert result == 300000.0

    def test_tax_deducted_pattern(self):
        text = "Tax Deducted at Source: ₹1,50,000"
        result = _extract_26as_credits(text)
        assert result == 150000.0

    def test_no_credits_found(self):
        text = "Some other text"
        result = _extract_26as_credits(text)
        assert result is None


class TestValidateITRvs26AS:
    def test_large_discrepancy_flagged(self):
        itr_text = "Total Income: ₹10,00,000"
        form26as_text = "Total Credits: ₹5,00,000"
        flags = validate_itr_vs_26as(itr_text, form26as_text)
        assert any("ITR vs 26AS Discrepancy" in f["finding"] for f in flags)
        flag = next(f for f in flags if "ITR vs 26AS Discrepancy" in f["finding"])
        assert flag["severity"] == "high"
        assert flag["score"] == 80

    def test_minor_discrepancy_flagged(self):
        itr_text = "Total Income: ₹10,00,000"
        form26as_text = "Total Credits: ₹8,50,000"  # 15% difference
        flags = validate_itr_vs_26as(itr_text, form26as_text)
        assert any("ITR vs 26AS Minor Discrepancy" in f["finding"] for f in flags)
        flag = next(f for f in flags if "ITR vs 26AS Minor" in f["finding"])
        assert flag["severity"] == "medium"
        assert flag["score"] == 40

    def test_no_discrepancy_no_flag(self):
        itr_text = "Total Income: ₹10,00,000"
        form26as_text = "Total Credits: ₹9,80,000"  # 2% difference
        flags = validate_itr_vs_26as(itr_text, form26as_text)
        assert not any("ITR vs 26AS" in f["finding"] for f in flags)

    def test_missing_values_no_flag(self):
        itr_text = "Total Income: ₹10,00,000"
        form26as_text = "No credits here"
        flags = validate_itr_vs_26as(itr_text, form26as_text)
        assert len(flags) == 0

    def test_zero_income_no_flag(self):
        itr_text = "Total Income: 0"
        form26as_text = "Total Credits: ₹5,00,000"
        flags = validate_itr_vs_26as(itr_text, form26as_text)
        assert len(flags) == 0


class TestValidateFinancialsITR26AS:
    def test_itr_vs_26as_in_financials(self):
        text = "Total Income: ₹10,00,000\nTotal Credits: ₹5,00,000"
        flags = validate_financials(text, [], "itr")
        assert any("ITR vs 26AS" in f["finding"] for f in flags)

    def test_form26as_type_triggers_check(self):
        text = "Total Income: ₹10,00,000\nTotal Credits: ₹5,00,000"
        flags = validate_financials(text, [], "form_26as")
        assert any("ITR vs 26AS" in f["finding"] for f in flags)

    def test_other_types_no_check(self):
        text = "Total Income: ₹10,00,000\nTotal Credits: ₹5,00,000"
        flags = validate_financials(text, [], "bank_statement")
        # Should not trigger ITR vs 26AS check for bank statements
        assert not any("ITR vs 26AS" in f["finding"] for f in flags)