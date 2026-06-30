from __future__ import annotations

from typing import Any, Dict, List, Sequence

from loguru import logger


def generate_explanation(
    flags: Sequence[Dict[str, Any]],
    risk_score: int,
    status: str,
    case_id: str = "",
) -> str:
    from services.vlm import generate_explanation_vlm

    explanation = generate_explanation_vlm(flags, risk_score, status, case_id=case_id)
    if explanation:
        logger.info(f"VLM explainability generated for case {case_id}")
        return explanation

    return _template_explanation(flags, risk_score, status)


def _template_explanation(
    flags: List[Dict[str, Any]], risk_score: int, status: str
) -> str:
    """Deterministic fallback when VLM is unavailable."""
    if not flags:
        return "No material fraud indicators were detected."

    high_flags = [f for f in flags if f.get("severity") == "high"]
    medium_flags = [f for f in flags if f.get("severity") == "medium"]

    parts = [f"Risk score {risk_score}/100 ({status})."]

    if high_flags:
        findings = "; ".join(f["finding"] for f in high_flags[:3])
        parts.append(f"Critical findings: {findings}.")

    if medium_flags:
        findings = "; ".join(f["finding"] for f in medium_flags[:2])
        parts.append(f"Additional concerns: {findings}.")

    return " ".join(parts)
