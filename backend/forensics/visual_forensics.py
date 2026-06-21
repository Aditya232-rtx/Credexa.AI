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
