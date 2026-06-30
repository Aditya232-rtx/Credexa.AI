from __future__ import annotations

import os
import tempfile
from pathlib import Path
from typing import Any, Dict, List

import numpy as np
from PIL import Image, ImageChops

from loguru import logger


def analyze_forgery(image_source: str | Path | Image.Image) -> List[Dict[str, Any]]:
    temp_path = None
    try:
        if isinstance(image_source, Image.Image):
            original = image_source.convert("RGB")
        else:
            original = Image.open(str(image_source)).convert("RGB")

        with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as tf:
            temp_path = tf.name
            original.save(temp_path, "JPEG", quality=95)

        flags: List[Dict[str, Any]] = []

        try:
            from services.external_forensics import check_sightengine_ai
            se_flags = check_sightengine_ai(temp_path)
            flags.extend(se_flags)
        except Exception as e:
            logger.warning(f"Sightengine call failed unexpectedly: {e}")

        try:
            from services.external_forensics import check_veryfi_tampering
            vf_flags = check_veryfi_tampering(temp_path)
            flags.extend(vf_flags)
        except Exception as e:
            logger.warning(f"Veryfi call failed unexpectedly: {e}")

        return flags
    except Exception:
        return []
    finally:
        if temp_path and os.path.exists(temp_path):
            try:
                os.remove(temp_path)
            except Exception:
                pass


def run_dct_ghost(image_source: str | Path | Image.Image) -> List[Dict[str, Any]]:
    flags: List[Dict[str, Any]] = []
    temp_files: List[str] = []
    try:
        import cv2
        if isinstance(image_source, Image.Image):
            original = image_source.convert("RGB")
        else:
            original = Image.open(str(image_source)).convert("RGB")
        original_array = np.array(original)
        h, w = original_array.shape[:2]
        total_pixels = h * w
        if total_pixels < 100:
            return flags
        quality_levels = [60, 70, 80, 90]
        anomaly_detected = False
        pct_ghost = 0.0
        detected_quality = 0
        for quality in quality_levels:
            with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as tf:
                temp_files.append(tf.name)
                original.save(tf.name, "JPEG", quality=quality)
                resaved = np.array(Image.open(tf.name).convert("RGB"))
            diff = np.abs(original_array.astype(float) - resaved.astype(float))
            ghost_map = np.mean(diff, axis=2)
            block_size = 8
            block_means: List[float] = []
            for y in range(0, h - block_size, block_size):
                for x in range(0, w - block_size, block_size):
                    block = ghost_map[y:y + block_size, x:x + block_size]
                    block_means.append(float(np.mean(block)))
            if len(block_means) < 10:
                continue
            block_arr = np.array(block_means)
            mean_error = float(np.mean(block_arr))
            std_error = float(np.std(block_arr))
            if std_error > 0 and mean_error > 1.0:
                low_error_blocks = np.sum(block_arr < (mean_error - 2.0 * std_error))
                pct_ghost = (low_error_blocks / len(block_arr)) * 100.0
                if pct_ghost > 5.0:
                    anomaly_detected = True
                    detected_quality = quality
                    break
        if anomaly_detected:
            flags.append({
                "layer": "Visual Forensics",
                "finding": f"DCT Ghost analysis detected double-compression artifacts. {pct_ghost:.1f}% of image blocks show re-compression signatures at quality {detected_quality}, indicating the image was previously saved and re-edited.",
                "severity": "high",
                "score": 60,
            })
    except ImportError:
        pass
    except Exception:
        pass
    finally:
        for tf_path in temp_files:
            try:
                if os.path.exists(tf_path):
                    os.remove(tf_path)
            except Exception:
                pass
    return flags
