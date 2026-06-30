from __future__ import annotations

from typing import Any, Dict, List, Sequence

from loguru import logger

SEVERITY_WEIGHTS = {
    "low": 8,
    "medium": 22,
    "high": 40,
}

STATUS_THRESHOLDS = [
    (80, "flagged"),
    (45, "review"),
    (0, "cleared"),
]


def score_case(flags: Sequence[Dict[str, Any]], anomaly_score: float = 0.0, case_id: str = "", docs: Sequence[Dict[str, Any]] | None = None) -> Dict[str, Any]:
    weighted_flags = 0.0
    for flag in flags:
        weighted_flags += float(flag.get("score") or SEVERITY_WEIGHTS.get(str(flag.get("severity", "low")).lower(), 8))

    normalized_flag_component = min(65.0, weighted_flags)
    normalized_anomaly_component = min(35.0, max(0.0, anomaly_score * 0.35))
    risk_score = int(min(100.0, round(normalized_flag_component + normalized_anomaly_component)))

    status = "cleared"
    for threshold, candidate in STATUS_THRESHOLDS:
        if risk_score >= threshold:
            status = candidate
            break

    # Use LLM explainability engine when available, fall back to template
    try:
        from scoring.explainability import generate_explanation
        explanation = generate_explanation(flags, risk_score, status, case_id=case_id, docs=docs)
    except Exception as e:
        logger.warning(f"Explainability engine failed, using template: {e}")
        explanation = _build_summary(flags, anomaly_score, risk_score, status)

    return {
        "risk_score": risk_score,
        "status": status,
        "explanation": explanation,
    }


def _build_summary(flags: Sequence[Dict[str, Any]], anomaly_score: float, risk_score: int, status: str) -> str:
    if not flags and anomaly_score < 10:
        return "No material fraud indicators were detected."

    top_flags = list(flags)[:3]
    parts = [f"Risk score {risk_score}/100 — {status.upper()}."]
    for flag in top_flags:
        layer = flag.get("layer", "Analysis")
        finding = flag.get("finding", "").strip()
        if finding:
            parts.append(f"[{layer}] {finding}.")
    if len(parts) < 2:
        parts.append("Document verification completed with flags requiring review.")
    return " ".join(parts)
