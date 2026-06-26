"""
Pattern Detector — detects round-number clustering, fabricated sequences, and
monetary anomalies in extracted financial text.

Fraudsters commonly fabricate bank statements with suspiciously round amounts
(50,000 / 1,00,000 / 2,50,000). Real bank statements show irregular amounts
from actual transactions (47,832.50 / 1,03,417.00).
"""
from __future__ import annotations

import re
from typing import Any, Dict, List


def _extract_amounts(text: str) -> List[float]:
    """Extract all monetary amounts from text using Indian currency patterns."""
    patterns = [
        # ₹1,00,000.50 or Rs. 1,00,000.50 or INR 1,00,000.50
        r"(?:₹|rs\.?\s*|inr\s*)?(\d{1,2}(?:,\d{2})*(?:,\d{3})?(?:\.\d{1,2})?)",
        # Plain numbers with commas: 1,000,000.00 (Western format)
        r"(\d{1,3}(?:,\d{3})+(?:\.\d{1,2})?)",
        # Plain large numbers without commas: 50000, 100000
        r"(?<![.\d])(\d{4,10})(?:\.\d{1,2})?(?![.\d])",
    ]

    amounts: List[float] = []
    for pattern in patterns:
        for match in re.finditer(pattern, text, re.IGNORECASE):
            raw = match.group(1) if match.lastindex else match.group(0)
            cleaned = raw.replace(",", "")
            try:
                val = float(cleaned)
                if 100.0 <= val <= 100_000_000.0:  # Reasonable financial range
                    amounts.append(val)
            except ValueError:
                continue

    # Deduplicate while preserving order
    seen = set()
    unique: List[float] = []
    for a in amounts:
        if a not in seen:
            seen.add(a)
            unique.append(a)
    return unique


def detect_round_number_clustering(amounts: List[float]) -> Dict[str, Any]:
    """Check what percentage of amounts end in 000 or 00000 — a sign of fabrication."""
    if len(amounts) < 5:
        return {"pct_round": 0.0, "flagged": False}

    round_1000 = sum(1 for a in amounts if a % 1000 == 0)
    round_100000 = sum(1 for a in amounts if a % 100000 == 0)

    pct_round = (round_1000 / len(amounts)) * 100.0

    return {
        "total_amounts": len(amounts),
        "round_1000_count": round_1000,
        "round_100000_count": round_100000,
        "pct_round": round(pct_round, 1),
        "flagged": pct_round > 40.0,
    }


def detect_monotonic_sequences(amounts: List[float], min_run: int = 5) -> bool:
    """
    Detect suspiciously monotonic (always increasing or always decreasing) runs
    of amounts — a sign of fabricated sequential transactions.
    """
    if len(amounts) < min_run:
        return False

    increasing_run = 1
    decreasing_run = 1

    for i in range(1, len(amounts)):
        if amounts[i] > amounts[i - 1]:
            increasing_run += 1
            decreasing_run = 1
        elif amounts[i] < amounts[i - 1]:
            decreasing_run += 1
            increasing_run = 1
        else:
            increasing_run = 1
            decreasing_run = 1

        if increasing_run >= min_run or decreasing_run >= min_run:
            return True

    return False


def detect_duplicate_amounts(amounts: List[float]) -> Dict[str, Any]:
    """Flag if the same exact amount appears suspiciously often."""
    if len(amounts) < 5:
        return {"flagged": False}

    from collections import Counter
    counts = Counter(amounts)
    most_common_val, most_common_count = counts.most_common(1)[0]

    pct = (most_common_count / len(amounts)) * 100.0
    return {
        "most_repeated_amount": most_common_val,
        "repeat_count": most_common_count,
        "pct_repeated": round(pct, 1),
        "flagged": most_common_count >= 4 and pct > 15.0,
    }


def analyze_patterns(text: str) -> List[Dict[str, Any]]:
    """
    Run all pattern detection heuristics on extracted document text.
    Returns a list of fraud flags.
    """
    flags: List[Dict[str, Any]] = []
    amounts = _extract_amounts(text)

    if not amounts:
        return flags

    # 1. Round number clustering
    rnd = detect_round_number_clustering(amounts)
    if rnd["flagged"]:
        flags.append({
            "layer": "Pattern Detector",
            "finding": f"Suspicious round-number clustering: {rnd['pct_round']}% of {rnd['total_amounts']} monetary amounts end in 000. Genuine bank statements rarely exceed 20%.",
            "severity": "high",
            "score": 65,
        })

    # 2. Monotonic sequences
    if detect_monotonic_sequences(amounts):
        flags.append({
            "layer": "Pattern Detector",
            "finding": "Suspiciously monotonic transaction sequence detected — amounts are strictly increasing/decreasing for 5+ consecutive entries, typical of fabricated statements.",
            "severity": "high",
            "score": 70,
        })

    # 3. Duplicate amounts
    dup = detect_duplicate_amounts(amounts)
    if dup["flagged"]:
        flags.append({
            "layer": "Pattern Detector",
            "finding": f"Amount ₹{dup['most_repeated_amount']:,.2f} repeated {dup['repeat_count']} times ({dup['pct_repeated']}% of all transactions). Abnormal repetition pattern.",
            "severity": "medium",
            "score": 45,
        })

    return flags
