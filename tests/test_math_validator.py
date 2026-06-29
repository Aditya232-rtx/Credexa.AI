import pytest
from backend.forensics.math_validator import (
    clean_indian_currency,
    validate_bank_statement_xlsx,
    validate_financials,
    extract_financials_llm,
)


class TestCleanIndianCurrency:
    def test_plain_number(self):
        assert clean_indian_currency("1000") == 1000.0
        assert clean_indian_currency("1000.50") == 1000.50

    def test_indian_format_with_commas(self):
        assert clean_indian_currency("1,00,000") == 100000.0
        assert clean_indian_currency("10,00,000.50") == 1000000.50

    def test_with_currency_symbol(self):
        assert clean_indian_currency("₹1,00,000") == 100000.0
        assert clean_indian_currency("Rs. 50,000") == 50000.0

    def test_invalid_input(self):
        assert clean_indian_currency("abc") == 0.0
        assert clean_indian_currency(None) == 0.0
        assert clean_indian_currency("") == 0.0

    def test_numeric_input(self):
        assert clean_indian_currency(1000) == 1000.0
        assert clean_indian_currency(1000.50) == 1000.50


class TestValidateBankStatementXlsx:
    def test_hidden_sheet_flagged(self):
        sheets = {
            "HiddenSheet": {"hidden": True, "rows": []},
            "VisibleSheet": {"hidden": False, "rows": []},
        }
        flags = validate_bank_statement_xlsx(sheets)
        assert any("Hidden sheet detected" in f["finding"] for f in flags)

    def test_hyperlink_formula_flagged(self):
        sheets = {
            "Sheet1": {
                "hidden": False,
                "rows": [[{"coordinate": "A1", "formula": "=HYPERLINK(\"http://evil.com\")"}]],
            }
        }
        flags = validate_bank_statement_xlsx(sheets)
        assert any("External hyperlink formula found" in f["finding"] for f in flags)

    def test_no_flags_on_clean_sheet(self):
        sheets = {
            "Sheet1": {"hidden": False, "rows": [[{"coordinate": "A1", "formula": None}]]}
        }
        flags = validate_bank_statement_xlsx(sheets)
        assert len(flags) == 0


class TestValidateFinancials:
    def test_bank_balance_mismatch_regex_fallback(self):
        text = (
            "Opening Balance: 1,00,000\n"
            "Total Credits: 50,000\n"
            "Total Debits: 30,000\n"
            "Closing Balance: 1,10,000\n"  # Should be 1,20,000
        )
        flags = validate_financials(text, [], "bank_statement")
        assert any("Bank Balance Mismatch" in f["finding"] for f in flags)

    def test_bank_balance_match_no_flag(self):
        text = (
            "Opening Balance: 1,00,000\n"
            "Total Credits: 50,000\n"
            "Total Debits: 30,000\n"
            "Closing Balance: 1,20,000\n"
        )
        flags = validate_financials(text, [], "bank_statement")
        assert not any("Bank Balance Mismatch" in f["finding"] for f in flags)

    def test_pl_mismatch_regex_fallback(self):
        text = (
            "Revenue from Operations: 10,00,000\n"
            "Cost of Goods Sold: 4,00,000\n"
            "Gross Profit: 5,00,000\n"  # Should be 6,00,000
            "Operating Expenses: 2,00,000\n"
            "Net Profit: 3,00,000\n"
        )
        flags = validate_financials(text, [], "pl_statement")
        assert any("P&L Gross Profit Mismatch" in f["finding"] for f in flags)

    def test_pl_net_profit_mismatch(self):
        text = (
            "Revenue from Operations: 10,00,000\n"
            "Cost of Goods Sold: 4,00,000\n"
            "Gross Profit: 6,00,000\n"
            "Operating Expenses: 2,00,000\n"
            "Net Profit: 3,00,000\n"  # Should be 4,00,000
        )
        flags = validate_financials(text, [], "pl_statement")
        assert any("P&L Net Profit Mismatch" in f["finding"] for f in flags)

    def test_reconciliation_failure_keyword(self):
        text = "Reconciliation failure detected"
        flags = validate_financials(text, [], "bank_statement")
        assert any("reconciliation" in f["finding"].lower() for f in flags)


class TestExtractFinancialsLLM:
    def test_returns_dict_on_error(self):
        # Without Ollama running, should return empty dict
        result = extract_financials_llm("some text")
        assert isinstance(result, dict)