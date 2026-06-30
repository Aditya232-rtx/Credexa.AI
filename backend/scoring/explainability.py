from __future__ import annotations

from typing import Any, Dict, List, Sequence

from loguru import logger


def generate_explanation(
    flags: Sequence[Dict[str, Any]],
    risk_score: int,
    status: str,
    case_id: str = "",
    docs: Sequence[Dict[str, Any]] | None = None,
) -> str:
    from services.vlm import generate_explanation_vlm

    explanation = generate_explanation_vlm(flags, risk_score, status, case_id=case_id, docs=docs)
    if explanation:
        logger.info(f"VLM explainability generated for case {case_id}")
        return explanation

    return _template_explanation(flags, risk_score, status)


def _template_explanation(
    flags: List[Dict[str, Any]], risk_score: int, status: str
) -> str:
    """Deterministic fallback when VLM is unavailable."""
    if not flags:
        return "No material fraud indicators were detected across any submitted document."

    high_flags = [f for f in flags if f.get("severity") == "high"]
    medium_flags = [f for f in flags if f.get("severity") == "medium"]
    low_flags = [f for f in flags if f.get("severity") == "low"]

    parts = [f"Risk score {risk_score}/100 — {status.upper()}. Automated forensic analysis of {len(flags)} detection signal{'s' if len(flags) > 1 else ''} completed."]

    if high_flags:
        findings = "; ".join(f.get("finding", "Critical anomaly detected").strip() for f in high_flags[:3] if f.get("finding"))
        if findings:
            parts.append(f"High-severity findings: {findings}.")

    if medium_flags:
        findings = "; ".join(f.get("finding", "Suspicious pattern detected").strip() for f in medium_flags[:3] if f.get("finding"))
        if findings:
            parts.append(f"Medium-severity concerns: {findings}.")

    if low_flags and not high_flags and not medium_flags:
        findings = "; ".join(f.get("finding", "Minor issue detected").strip() for f in low_flags[:2] if f.get("finding"))
        if findings:
            parts.append(f"Low-severity observations: {findings}.")

    if len(parts) < 2:
        parts.append("Document verification completed. Review the detection layers for detailed findings.")

    return " ".join(parts)
