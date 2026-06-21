from __future__ import annotations

import os
import tempfile
from pathlib import Path
from typing import Any, Dict, List

import numpy as np
from PIL import Image, ImageChops


def run_ela(image_source: str | Path | Image.Image, quality: int = 90) -> List[Dict[str, Any]]:
    temp_path = None
    try:
        if isinstance(image_source, Image.Image):
            original = image_source.convert("RGB")
        else:
            original = Image.open(str(image_source)).convert("RGB")

        with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as temp_file:
            temp_path = temp_file.name
        original.save(temp_path, "JPEG", quality=quality)
        resaved = Image.open(temp_path)

        diff = ImageChops.difference(original, resaved)
        diff_array = np.array(diff)
        gray_diff = np.mean(diff_array, axis=2)
        threshold = 20
        high_diff_pixels = np.sum(gray_diff > threshold)
        total_pixels = gray_diff.shape[0] * gray_diff.shape[1]
        anomaly_percentage = (high_diff_pixels / total_pixels) * 100 if total_pixels else 0.0

        flags: List[Dict[str, Any]] = []
        if anomaly_percentage > 2.0:
            flags.append({"layer": "Visual Forensics", "finding": f"ELA anomaly detected: {anomaly_percentage:.2f}% of image shows significant compression artifact difference. Potential local edit or paste.", "severity": "high" if anomaly_percentage > 5.0 else "medium", "score": int(min(100, anomaly_percentage * 15))})
        return flags
    except Exception:
        return []
    finally:
        if temp_path and os.path.exists(temp_path):
            try:
                os.remove(temp_path)
            except Exception:
                pass
