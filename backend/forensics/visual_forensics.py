from __future__ import annotations

import os
import tempfile
from pathlib import Path
from typing import Any, Dict, List

import numpy as np
from PIL import Image, ImageChops

try:
    import torch
    import torchvision.models as models
    import torchvision.transforms as T
    
    mobilenet = models.mobilenet_v3_small(weights=models.MobileNet_V3_Small_Weights.DEFAULT)
    mobilenet.eval()
except Exception:
    mobilenet = None


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
        
        # Deep Learning Forensics with MobileNetV3
        deep_score = 0.0
        if mobilenet is not None and anomaly_percentage > 0.5:
            transform = T.Compose([
                T.Resize((224, 224)),
                T.ToTensor(),
                T.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225])
            ])
            input_tensor = transform(diff).unsqueeze(0)
            with torch.no_grad():
                features = mobilenet.features(input_tensor)
                # Use feature variance as an AI anomaly heuristic
                deep_score = torch.var(features).item() * 500

        final_score = max(anomaly_percentage, deep_score)

        if final_score > 2.0:
            flags.append({
                "layer": "Visual Forensics", 
                "finding": f"ELA + MobileNetV3 anomaly detected: High variance in compression artifacts. Potential local edit or paste.", 
                "severity": "high" if final_score > 5.0 else "medium", 
                "score": int(min(100, final_score * 15))
            })
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
    """
    DCT (Discrete Cosine Transform) Ghost Analysis.
    
    Detects double-compression artifacts in JPEG images. When an image is edited
    and re-saved, previously compressed regions show anomalously low error at the
    original quality level, creating 'ghosts' that reveal tampered areas.
    """
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

        # Re-save at multiple quality levels and compute ghost maps
        quality_levels = [60, 70, 80, 90]
        anomaly_detected = False

        for quality in quality_levels:
            with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as tf:
                temp_files.append(tf.name)
                original.save(tf.name, "JPEG", quality=quality)
                resaved = np.array(Image.open(tf.name).convert("RGB"))

            # Compute absolute difference (ghost map)
            diff = np.abs(original_array.astype(float) - resaved.astype(float))
            ghost_map = np.mean(diff, axis=2)  # average across channels

            # Divide into 8x8 blocks (DCT block size) and check variance
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

            # Regions with anomalously LOW error at this quality were already
            # compressed at this quality before editing — they are ghosts
            if std_error > 0 and mean_error > 1.0:
                low_error_blocks = np.sum(block_arr < (mean_error - 2.0 * std_error))
                pct_ghost = (low_error_blocks / len(block_arr)) * 100.0

                if pct_ghost > 5.0:
                    anomaly_detected = True
                    break

        if anomaly_detected:
            flags.append({
                "layer": "Visual Forensics",
                "finding": f"DCT Ghost analysis detected double-compression artifacts. {pct_ghost:.1f}% of image blocks show re-compression signatures at quality {quality}, indicating the image was previously saved and re-edited.",
                "severity": "high",
                "score": 60,
            })

    except ImportError:
        pass  # cv2 not available
    except Exception as e:
        pass
    finally:
        for tf_path in temp_files:
            try:
                if os.path.exists(tf_path):
                    os.remove(tf_path)
            except Exception:
                pass

    return flags
