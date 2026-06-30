from __future__ import annotations

import json
import os
import re
import tempfile
import zipfile
from pathlib import Path
from typing import Any, Dict, Sequence

from dotenv import load_dotenv
from loguru import logger

_LOADED_ENV = False


def _ensure_env_loaded() -> None:
    global _LOADED_ENV
    if not _LOADED_ENV:
        load_dotenv()
        _LOADED_ENV = True


_client = None


def _get_client():
    global _client
    if _client is not None:
        return _client
    _ensure_env_loaded()
    api_key = os.getenv("sarvam_ai_vision_api_key")
    if not api_key:
        logger.warning("sarvam_ai_vision_api_key not found in environment")
        return None
    try:
        from sarvamai import SarvamAI

        _client = SarvamAI(api_subscription_key=api_key)
        return _client
    except Exception as e:
        logger.warning(f"Failed to initialize SarvamAI client: {e}")
        return None


_ALLOWED_DOC_TYPES = frozenset({
    "bank_statement", "form_26as", "itr", "salary_slip",
    "balance_sheet", "profit_loss", "gst_return", "unknown",
})


def _sanitize_text(text: str, max_len: int = 2000) -> str:
    cleaned = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f]", "", str(text))
    return cleaned[:max_len]


def _sanitize_doc_type(doc_type: str) -> str:
    return doc_type if doc_type in _ALLOWED_DOC_TYPES else "unknown"


def _chat_completion(prompt: str, model: str = "sarvam-30b", max_tokens: int = 1024, temperature: float = 0.1) -> str:
    client = _get_client()
    if client is None:
        logger.warning("SarvamAI client not available for chat completion")
        return ""
    try:
        response = client.chat.completions(
            messages=[{"role": "user", "content": prompt}],
            model=model,
            max_tokens=max_tokens,
            temperature=temperature,
        )
        return response.choices[0].message.content or ""
    except Exception as e:
        logger.warning(f"SarvamAI chat completion error: {e}")
        return ""


def sarvam_extract_text(image_path: str) -> str:
    client = _get_client()
    if client is None:
        logger.warning("SarvamAI client not available for OCR")
        return ""
    try:
        job = client.document_intelligence.create_job(language="en-IN", output_format="md")
        job.upload_file(image_path)
        job.start()
        job.wait_until_complete(timeout=300)

        with tempfile.TemporaryDirectory() as tmpdir:
            zip_path = os.path.join(tmpdir, "output.zip")
            job.download_output(zip_path)

            extracted_parts = []
            with zipfile.ZipFile(zip_path, "r") as zf:
                for name in zf.namelist():
                    if name.endswith(".json"):
                        data = json.loads(zf.read(name))
                        text_content = data.get("text") or data.get("markdown") or data.get("content") or ""
                        if text_content:
                            extracted_parts.append(text_content)
                    elif name.endswith(".md"):
                        text_content = zf.read(name).decode("utf-8", errors="replace")
                        if text_content.strip():
                            extracted_parts.append(text_content)

            return "\n\n".join(extracted_parts)
    except Exception as e:
        logger.warning(f"SarvamAI OCR error for {image_path}: {e}")
        return ""


def sarvam_chat(prompt: str, model: str = "sarvam-30b", max_tokens: int = 1024, temperature: float = 0.1) -> str:
    return _chat_completion(prompt=prompt, model=model, max_tokens=max_tokens, temperature=temperature)


def sarvam_extract_kv(text: str, doc_type: str = "") -> dict:
    safe_doc_type = _sanitize_doc_type(doc_type)
    safe_text = _sanitize_text(text)

    schema_map = {
        "itr": '"total_income": float or null, "gross_total_income": float or null, "tax_paid": float or null, "assessment_year": str or null',
        "form_26as": '"total_tds_credited": float or null, "pan": str or null, "financial_year": str or null',
        "bank_statement": '"account_number": str or null, "ifsc_code": str or null, "opening_balance": float or null, "closing_balance": float or null, "total_credits": float or null, "total_debits": float or null, "statement_period": str or null',
        "salary_slip": '"employee_name": str or null, "pan": str or null, "gross_pay": float or null, "net_pay": float or null, "deductions": float or null, "month": str or null',
        "balance_sheet": '"total_assets": float or null, "total_liabilities": float or null, "shareholders_equity": float or null, "financial_year": str or null',
        "profit_loss": '"revenue": float or null, "cogs": float or null, "gross_profit": float or null, "operating_expenses": float or null, "net_profit": float or null, "financial_year": str or null',
        "gst_return": '"gstin": str or null, "total_taxable_value": float or null, "total_tax": float or null, "return_period": str or null',
    }
    schema = schema_map.get(safe_doc_type, '"key": value or null')

    prompt = f"""Extract key-value pairs from this {safe_doc_type} document.
Return ONLY valid JSON with these fields: {schema}

Document text:
---BEGIN TEXT---
{safe_text}
---END TEXT---

If a field is not visible in the document, set it to null.
Do NOT include any text outside the JSON object."""
    result = _chat_completion(prompt, max_tokens=512, temperature=0.1)
    try:
        start = result.index("{")
        end = result.rindex("}") + 1
        return json.loads(result[start:end])
    except (ValueError, json.JSONDecodeError):
        logger.warning(f"Failed to parse Sarvam KV extraction JSON: {result[:200]}")
        return {}


def sarvam_extract_financials(text: str) -> dict:
    safe_text = _sanitize_text(text, max_len=3000)
    prompt = f"""Extract financial data from the text below. Return ONLY valid JSON.
Keys: "opening_balance", "total_credits", "total_debits", "closing_balance", "revenue", "cogs", "gross_profit", "opex", "net_profit"
If a value is not found, set it to null. Ensure values are floats or null.

Text:
---BEGIN TEXT---
{safe_text}
---END TEXT---"""
    result = _chat_completion(prompt, max_tokens=256, temperature=0.0)
    try:
        start = result.index("{")
        end = result.rindex("}") + 1
        return json.loads(result[start:end])
    except (ValueError, json.JSONDecodeError):
        logger.warning(f"Failed to parse Sarvam financials JSON: {result[:200]}")
        return {}


def sarvam_classify_doc(text: str) -> str:
    safe_text = _sanitize_text(text)
    prompt = f"""Classify this Indian financial document into exactly one category:
- bank_statement
- form_26as
- itr (income tax return)
- salary_slip
- balance_sheet
- profit_loss
- gst_return
- unknown

Document text preview:
---BEGIN TEXT---
{safe_text}
---END TEXT---

Respond with ONLY the category name, nothing else."""
    result = _chat_completion(prompt, max_tokens=32, temperature=0.0)
    for dt in _ALLOWED_DOC_TYPES:
        if dt in result.lower():
            return dt
    return "unknown"


def sarvam_explain(flags, risk_score, status, case_id="", docs=None) -> str:
    safe_case_id = re.sub(r"[^A-Z0-9-]", "", case_id)[:20] if case_id else ""
    if not flags:
        return "No material fraud indicators were detected across any submitted document."

    top_flags = sorted(flags, key=lambda x: -int(x.get("score", 0)))[:10]
    flags_json = json.dumps(top_flags, indent=2, default=str)
    safe_flags_json = _sanitize_text(flags_json, max_len=3000)

    doc_context = ""
    if docs:
        categories = [d.get("doc_category", "") for d in docs if d.get("doc_category")]
        if categories:
            doc_context = f"Document{'' if len(categories) == 1 else 's'} submitted: {', '.join(categories)}.\n"

    prompt = f"""You are a financial fraud analyst at an Indian bank.

Given the anomaly flags detected during automated document verification for loan application case {safe_case_id}, write a detailed 3-5 sentence explanation for a bank underwriter.

Risk Score: {risk_score}/100 (Status: {status})

{doc_context}Detected Anomalies:
{safe_flags_json}

Requirements:
- Start by stating the overall finding and document types analyzed.
- Be specific. Cite the exact findings and which document or layer triggered them.
- Use professional language suitable for a bank credit report.
- If the risk is low, clearly state the documents appear genuine.
- Do NOT use markdown formatting. Plain text only.
- Write at least 3 complete sentences and at most 5."""
    result = _chat_completion(prompt, max_tokens=350, temperature=0.3)
    return result or ""


def sarvam_vision_analyze(image_path: str, prompt: str) -> str:
    extracted_text = sarvam_extract_text(image_path)
    if not extracted_text:
        logger.warning(f"Sarvam OCR returned no text for {image_path}; sending prompt without document context")
        return _chat_completion(prompt, max_tokens=512, temperature=0.1)

    combined_prompt = f"""Document text extracted from image:
---BEGIN DOCUMENT TEXT---
{_sanitize_text(extracted_text, max_len=4000)}
---END DOCUMENT TEXT---

User query: {prompt}

Answer the user query based on the document text above. If the document does not contain relevant information, say so."""
    return _chat_completion(combined_prompt, max_tokens=512, temperature=0.1)
