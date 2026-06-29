from __future__ import annotations

import os
import json
import urllib.request
import re
from typing import Any, Dict, List, Sequence

from loguru import logger


def clean_indian_currency(text: Any) -> float:
    if not isinstance(text, str):
        try:
            return float(text)
        except (ValueError, TypeError):
            return 0.0

    # Remove currency symbols and spaces, keep digits, dots, commas, leading minus
    cleaned = re.sub(r"[^\d.,-]", "", text)
    cleaned = cleaned.lstrip('.')
    # Handle trailing minus (e.g., "50,000-")
    if cleaned.endswith("-"):
        cleaned = "-" + cleaned.rstrip("-")
    cleaned = cleaned.replace(",", "")
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


def _extract_itr_income(text: str) -> float | None:
    """Extract total income from ITR document."""
    patterns = [
        r"Total\s+Income[:\s]*(?:₹|rs\.?|inr)?\s*([\d,]+(?:\.\d{1,2})?)",
        r"Gross\s+Total\s+Income[:\s]*(?:₹|rs\.?|inr)?\s*([\d,]+(?:\.\d{1,2})?)",
        r"Net\s+Income[:\s]*(?:₹|rs\.?|inr)?\s*([\d,]+(?:\.\d{1,2})?)",
    ]
    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            try:
                return clean_indian_currency(match.group(1))
            except (ValueError, TypeError):
                continue
    return None


def _extract_26as_credits(text: str) -> float | None:
    """Extract total credits from Form 26AS."""
    patterns = [
        r"Total\s+Credits?[:\s]*(?:₹|rs\.?|inr)?\s*([\d,]+(?:\.\d{1,2})?)",
        r"Tax\s+Deducted\s+at\s+Source[:\s]*(?:₹|rs\.?|inr)?\s*([\d,]+(?:\.\d{1,2})?)",
        r"TDS\s+Total[:\s]*(?:₹|rs\.?|inr)?\s*([\d,]+(?:\.\d{1,2})?)",
    ]
    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            try:
                return clean_indian_currency(match.group(1))
            except (ValueError, TypeError):
                continue
    return None


def validate_itr_vs_26as(itr_text: str, form26as_text: str) -> List[Dict[str, Any]]:
    """
    Cross-check ITR declared income vs Form 26AS credits.
    Significant discrepancy (>25%) indicates potential income concealment.
    """
    flags: List[Dict[str, Any]] = []
    
    itr_income = _extract_itr_income(itr_text)
    form26as_credits = _extract_26as_credits(form26as_text)
    
    if itr_income is not None and form26as_credits is not None and itr_income > 0:
        ratio = abs(form26as_credits - itr_income) / itr_income
        if ratio > 0.25:
            flags.append({
                "layer": "Math Validator",
                "finding": f"ITR vs 26AS Discrepancy: Declared income ₹{itr_income:,.0f} vs 26AS credits ₹{form26as_credits:,.0f} (difference {ratio*100:.0f}%). Potential income concealment.",
                "severity": "high",
                "score": 80,
            })
        elif ratio > 0.10:
            flags.append({
                "layer": "Math Validator",
                "finding": f"ITR vs 26AS Minor Discrepancy: Declared income ₹{itr_income:,.0f} vs 26AS credits ₹{form26as_credits:,.0f} (difference {ratio*100:.0f}%).",
                "severity": "medium",
                "score": 40,
            })
    
    return flags


def extract_financials_llm(text: str) -> dict:
    prompt = '''
    Extract the following financial data from the text if available. Return ONLY a valid JSON object.
    Keys: "opening_balance", "total_credits", "total_debits", "closing_balance", "revenue", "cogs", "gross_profit", "opex", "net_profit".
    If a value is not found, set it to null. Ensure values are floats or null.
    Text:
    ''' + text[:3000]

    data = {
        "model": os.environ.get("OLLAMA_MODEL", "qwen3.5:4b"),
        "prompt": prompt,
        "format": "json",
        "stream": False
    }
    try:
        ollama_url = os.environ.get("OLLAMA_URL", "http://localhost:11434")
        req = urllib.request.Request(
            f"{ollama_url}/api/generate", 
            data=json.dumps(data).encode('utf-8'), 
            headers={'Content-Type': 'application/json'}
        )
        with urllib.request.urlopen(req, timeout=15) as response:
            result = json.loads(response.read())
            return json.loads(result.get("response", "{}"))
    except Exception as e:
        logger.warning(f"Ollama LLM Error: {e}")
        return {}


def validate_financials(text: str, tables: Sequence[Sequence[Any]], file_type: str) -> List[Dict[str, Any]]:
    flags: List[Dict[str, Any]] = []
    
    # Try LLM Extraction first
    llm_data = extract_financials_llm(text)

    o_val = llm_data.get("opening_balance")
    c_val = llm_data.get("total_credits")
    d_val = llm_data.get("total_debits")
    cl_val = llm_data.get("closing_balance")

    if o_val is not None and c_val is not None and d_val is not None and cl_val is not None:
        if abs((o_val + c_val - d_val) - cl_val) > 1.0:
            flags.append({
                "layer": "Math Validator", 
                "finding": f"Bank Balance Mismatch (LLM): {o_val} + {c_val} - {d_val} != {cl_val}", 
                "severity": "high", 
                "score": 85
            })
    else:
        # Fallback Check Bank Statement Math
        opening = re.search(r"Opening Balance:(?:[^\d\n]+)?([\d,.]+)", text, re.IGNORECASE)
        credits = re.search(r"Total Credits:(?:[^\d\n]+)?([\d,.]+)", text, re.IGNORECASE)
        debits = re.search(r"Total Debits:(?:[^\d\n]+)?([\d,.]+)", text, re.IGNORECASE)
        closing = re.search(r"Closing Balance:(?:[^\d\n]+)?([\d,.]+)", text, re.IGNORECASE)
    
        if opening and credits and debits and closing:
            o_val_re = clean_indian_currency(opening.group(1))
            c_val_re = clean_indian_currency(credits.group(1))
            d_val_re = clean_indian_currency(debits.group(1))
            cl_val_re = clean_indian_currency(closing.group(1))
            
            if abs((o_val_re + c_val_re - d_val_re) - cl_val_re) > 1.0:
                flags.append({
                    "layer": "Math Validator", 
                    "finding": f"Bank Balance Mismatch: {o_val_re} + {c_val_re} - {d_val_re} != {cl_val_re}", 
                    "severity": "high", 
                    "score": 85
                })

    # Check P&L Math
    rev_val = llm_data.get("revenue")
    cogs_val = llm_data.get("cogs")
    gross_val = llm_data.get("gross_profit")
    opex_val = llm_data.get("opex")
    net_val = llm_data.get("net_profit")

    if rev_val is not None and cogs_val is not None and gross_val is not None:
        if abs((rev_val - cogs_val) - gross_val) > 1.0:
            flags.append({
                "layer": "Math Validator", 
                "finding": f"P&L Gross Profit Mismatch (LLM): {rev_val} - {cogs_val} != {gross_val}", 
                "severity": "high", 
                "score": 90
            })
    else:
        revenue = re.search(r"Revenue from Operations:(?:[^\d\n]+)?([\d,.]+)", text, re.IGNORECASE)
        cogs = re.search(r"Cost of Goods Sold:(?:[^\d\n]+)?([\d,.]+)", text, re.IGNORECASE)
        gross = re.search(r"Gross Profit:(?:[^\d\n]+)?([\d,.]+)", text, re.IGNORECASE)
        opex = re.search(r"Operating Expenses:(?:[^\d\n]+)?([\d,.]+)", text, re.IGNORECASE)
        net = re.search(r"Net Profit:(?:[^\d\n]+)?([\d,.]+)", text, re.IGNORECASE)

    if gross_val is not None and opex_val is not None and net_val is not None:
        if abs((gross_val - opex_val) - net_val) > 1.0:
            flags.append({
                "layer": "Math Validator", 
                "finding": f"P&L Net Profit Mismatch (LLM): {gross_val} - {opex_val} != {net_val}", 
                "severity": "high", 
                "score": 90
            })
    else:
        if revenue and cogs and gross:
            rev_val_re = clean_indian_currency(revenue.group(1))
            cogs_val_re = clean_indian_currency(cogs.group(1))
            gross_val_re = clean_indian_currency(gross.group(1))
            
            if abs((rev_val_re - cogs_val_re) - gross_val_re) > 1.0:
                flags.append({
                    "layer": "Math Validator", 
                    "finding": f"P&L Gross Profit Mismatch: {rev_val_re} - {cogs_val_re} != {gross_val_re}", 
                    "severity": "high", 
                    "score": 90
                })
    
        if gross and opex and net:
            gross_val_re = clean_indian_currency(gross.group(1))
            opex_val_re = clean_indian_currency(opex.group(1))
            net_val_re = clean_indian_currency(net.group(1))
            
            if abs((gross_val_re - opex_val_re) - net_val_re) > 1.0:
                flags.append({
                    "layer": "Math Validator", 
                    "finding": f"P&L Net Profit Mismatch: {gross_val_re} - {opex_val_re} != {net_val_re}", 
                    "severity": "high", 
                    "score": 90
                })

    lowered = (text or "").lower()
    if "reconciliation failure" in lowered or "suspicious balance" in lowered:
        flags.append({"layer": "Math Validator", "finding": "Balance reconciliation failed. Computed sum does not match stated closing balance.", "severity": "high", "score": 80})

    # ITR vs Form 26AS Cross-Check
    if file_type in ("itr", "form_26as", "tax_return"):
        # We need both documents - check if we can extract both
        itr_income = _extract_itr_income(text)
        form26as_credits = _extract_26as_credits(text)
        if itr_income is not None and form26as_credits is not None and itr_income > 0:
            ratio = abs(form26as_credits - itr_income) / itr_income
            if ratio > 0.25:
                flags.append({
                    "layer": "Math Validator",
                    "finding": f"ITR vs 26AS Discrepancy: Declared income ₹{itr_income:,.0f} vs 26AS credits ₹{form26as_credits:,.0f} (difference {ratio*100:.0f}%). Potential income concealment.",
                    "severity": "high",
                    "score": 80,
                })
            elif ratio > 0.10:
                flags.append({
                    "layer": "Math Validator",
                    "finding": f"ITR vs 26AS Minor Discrepancy: Declared income ₹{itr_income:,.0f} vs 26AS credits ₹{form26as_credits:,.0f} (difference {ratio*100:.0f}%).",
                    "severity": "medium",
                    "score": 40,
                })

    return flags
