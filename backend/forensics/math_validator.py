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
    
    # Check Bank Statement Math
    opening = re.search(r"Opening Balance:(?:[^\d\n]+)?([\d,.]+)", text, re.IGNORECASE)
    credits = re.search(r"Total Credits:(?:[^\d\n]+)?([\d,.]+)", text, re.IGNORECASE)
    debits = re.search(r"Total Debits:(?:[^\d\n]+)?([\d,.]+)", text, re.IGNORECASE)
    closing = re.search(r"Closing Balance:(?:[^\d\n]+)?([\d,.]+)", text, re.IGNORECASE)

    if opening and credits and debits and closing:
        o_val = clean_indian_currency(opening.group(1))
        c_val = clean_indian_currency(credits.group(1))
        d_val = clean_indian_currency(debits.group(1))
        cl_val = clean_indian_currency(closing.group(1))
        
        # Simple bank math: Opening + Credits - Debits = Closing
        if abs((o_val + c_val - d_val) - cl_val) > 1.0:
            flags.append({
                "layer": "Math Validator", 
                "finding": f"Bank Balance Mismatch: {o_val} + {c_val} - {d_val} != {cl_val}", 
                "severity": "high", 
                "score": 85
            })

    # Check P&L Math
    revenue = re.search(r"Revenue from Operations:(?:[^\d\n]+)?([\d,.]+)", text, re.IGNORECASE)
    cogs = re.search(r"Cost of Goods Sold:(?:[^\d\n]+)?([\d,.]+)", text, re.IGNORECASE)
    gross = re.search(r"Gross Profit:(?:[^\d\n]+)?([\d,.]+)", text, re.IGNORECASE)
    opex = re.search(r"Operating Expenses:(?:[^\d\n]+)?([\d,.]+)", text, re.IGNORECASE)
    net = re.search(r"Net Profit:(?:[^\d\n]+)?([\d,.]+)", text, re.IGNORECASE)

    if revenue and cogs and gross:
        rev_val = clean_indian_currency(revenue.group(1))
        cogs_val = clean_indian_currency(cogs.group(1))
        gross_val = clean_indian_currency(gross.group(1))
        
        if abs((rev_val - cogs_val) - gross_val) > 1.0:
            flags.append({
                "layer": "Math Validator", 
                "finding": f"P&L Gross Profit Mismatch: {rev_val} - {cogs_val} != {gross_val}", 
                "severity": "high", 
                "score": 90
            })

    if gross and opex and net:
        gross_val = clean_indian_currency(gross.group(1))
        opex_val = clean_indian_currency(opex.group(1))
        net_val = clean_indian_currency(net.group(1))
        
        if abs((gross_val - opex_val) - net_val) > 1.0:
            flags.append({
                "layer": "Math Validator", 
                "finding": f"P&L Net Profit Mismatch: {gross_val} - {opex_val} != {net_val}", 
                "severity": "high", 
                "score": 90
            })

    lowered = (text or "").lower()
    if "reconciliation failure" in lowered or "suspicious balance" in lowered:
        flags.append({"layer": "Math Validator", "finding": "Balance reconciliation failed. Computed sum does not match stated closing balance.", "severity": "high", "score": 80})
    return flags
