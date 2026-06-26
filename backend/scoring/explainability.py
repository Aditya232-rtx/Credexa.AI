"""
Explainability Engine — LLM-generated reasoning for risk scores.

Uses Ollama to produce a human-readable explanation of why a case was flagged,
suitable for bank underwriters who need to justify their decisions.
"""
from __future__ import annotations

import json
import os
import urllib.request
from typing import Any, Dict, List, Sequence

from loguru import logger


def generate_explanation(
    flags: Sequence[Dict[str, Any]],
    risk_score: int,
    status: str,
    case_id: str = "",
) -> str:
    """Call Ollama to produce a 2-3 sentence underwriter-facing explanation."""

    if not flags:
        return "No material fraud indicators were detected across any submitted document."

    # Build a concise JSON summary of the top flags (max 10)
    top_flags = []
    for f in sorted(flags, key=lambda x: -int(x.get("score", 0)))[:10]:
        top_flags.append({
            "layer": f.get("layer", "Unknown"),
            "finding": f.get("finding", ""),
            "severity": f.get("severity", "low"),
            "score": int(f.get("score", 0)),
        })

    prompt = f"""You are a financial fraud analyst at an Indian bank.

Given the following anomaly flags detected during automated document verification for loan application case {case_id}, write a 2-3 sentence explanation for a bank underwriter.

Risk Score: {risk_score}/100 (Status: {status})

Detected Anomalies:
{json.dumps(top_flags, indent=2)}

Requirements:
- Be specific. Cite the exact findings.
- Use professional language suitable for a bank credit report.
- If the risk is low, clearly state the documents appear genuine.
- Do NOT use markdown formatting. Plain text only.
- Keep it under 100 words."""

    ollama_model = os.environ.get("OLLAMA_MODEL", "qwen3.5:4b")
    ollama_url = os.environ.get("OLLAMA_URL", "http://localhost:11434")

    data = {
        "model": ollama_model,
        "prompt": prompt,
        "stream": False,
    }

    try:
        req = urllib.request.Request(
            f"{ollama_url}/api/generate",
            data=json.dumps(data).encode("utf-8"),
            headers={"Content-Type": "application/json"},
        )
        with urllib.request.urlopen(req, timeout=30) as response:
            result = json.loads(response.read())
            explanation = result.get("response", "").strip()
            if explanation:
                logger.info(f"LLM explainability generated for case {case_id}")
                return explanation
    except Exception as e:
        logger.warning(f"Ollama explainability call failed: {e}. Falling back to template.")

    # Fallback: build a template explanation
    return _template_explanation(top_flags, risk_score, status)


def _template_explanation(
    flags: List[Dict[str, Any]], risk_score: int, status: str
) -> str:
    """Deterministic fallback when LLM is unavailable."""
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
