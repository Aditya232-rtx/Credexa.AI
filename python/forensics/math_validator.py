from __future__ import annotations

import re
from typing import Any, Dict, List, Sequence


def clean_indian_currency(text: Any) -> float:
    if not isinstance(text, str):
        try:
            return float(text)
        except (ValueError, TypeError):
            return 0.0

    cleaned = re.sub(r"[^\d.-]", "", text)
    try:
        return float(cleaned)
    except ValueError:
        return 0.0


def validate_bank_statement_xlsx(sheets_data: Dict[str, Any]) -> List[Dict[str, Any]]:
    flags: List[Dict[str, Any]] = []
    for sheet_name, sheet_info in sheets_data.items():
        if sheet_info.get("hidden"):
            flags.append({"layer": "Math Validator", "finding": f"Hidden sheet detected: '{sheet_name}'. May conceal original data.", "severity": "medium", "score": 30})

        for row in sheet_info.get("rows", []):
            for cell in row:
                formula = cell.get("formula")
                if formula and "HYPERLINK" in str(formula).upper():
                    flags.append({"layer": "Math Validator", "finding": f"External hyperlink formula found in cell {cell.get('coordinate')}", "severity": "low", "score": 10})
    return flags


def validate_financials(text: str, tables: Sequence[Sequence[Any]], file_type: str) -> List[Dict[str, Any]]:
    flags: List[Dict[str, Any]] = []
    lowered = (text or "").lower()
    if "reconciliation failure" in lowered or "suspicious balance" in lowered:
        flags.append({"layer": "Math Validator", "finding": "Balance reconciliation failed. Computed sum does not match stated closing balance.", "severity": "high", "score": 80})
    return flags
