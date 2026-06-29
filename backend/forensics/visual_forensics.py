from __future__ import annotations

import os
import tempfile
from pathlib import Path
from typing import Any, Dict, List

import numpy as np
from PIL import Image, ImageChops

MODEL_DIR = Path(__file__).resolve().parent.parent.parent / "models" / "trained" / "efficientnet_b4_tamper"

try:
    import torch
    import torch.nn as nn
    from torchvision import models, transforms
    from utils.device import get_device

    _device = get_device()
    _efficientnet = None
    _cnn_detection = None
    _hf_ai_detector = None
    _hf_ai_processor = None

    def _load_tamper_model():
        global _efficientnet
        if _efficientnet is not None:
            return _efficientnet
        weights_path = MODEL_DIR / "efficientnet_b4_tamper.pth"
        model = models.efficientnet_b4(weights=None)
        model.classifier[1] = nn.Linear(model.classifier[1].in_features, 2)
        if weights_path.exists():
            state = torch.load(weights_path, map_location=_device, weights_only=True)
            model.load_state_dict(state, strict=False)
        else:
            model = models.efficientnet_b4(weights=models.EfficientNet_B4_Weights.DEFAULT)
            model.classifier[1] = nn.Linear(model.classifier[1].in_features, 2)
        model.to(_device)
        model.eval()
        _efficientnet = model
        return model

    def _load_cnn_detection():
        global _cnn_detection
        if _cnn_detection is not None:
            return _cnn_detection
        ckpt = MODEL_DIR.parent.parent / "data" / "cnn_detection" / "cnndetection_resnet50.pth"
        model = models.resnet50(weights=None)
        if ckpt.exists():
            state = torch.load(ckpt, map_location=_device, weights_only=True)
            model.load_state_dict(state, strict=False)
        else:
            model = models.resnet50(weights=models.ResNet50_Weights.DEFAULT)
        model.to(_device)
        model.eval()
        _cnn_detection = model
        return model

    def _load_hf_ai_detector():
        global _hf_ai_detector, _hf_ai_processor
        if _hf_ai_detector is not None:
            return _hf_ai_detector, _hf_ai_processor
        from transformers import ViTImageProcessor, AutoModelForImageClassification
        _hf_ai_processor = ViTImageProcessor.from_pretrained(
            "NYUAD-ComNets/NYUAD_AI-generated_images_detector"
        )
        _hf_ai_detector = AutoModelForImageClassification.from_pretrained(
            "NYUAD-ComNets/NYUAD_AI-generated_images_detector"
        )
        _hf_ai_detector.to(_device)
        _hf_ai_detector.eval()
        return _hf_ai_detector, _hf_ai_processor

    TORCH_AVAILABLE = True
except Exception:
    _device = "cpu"
    _efficientnet = None
    _cnn_detection = None
    _hf_ai_detector = None
    _hf_ai_processor = None
    TORCH_AVAILABLE = False


def _run_hf_ai_detector(image: Image.Image) -> float:
    try:
        detector, processor = _load_hf_ai_detector()
        if detector is None:
            return 0.0
        inputs = processor(image, return_tensors="pt")
        inputs = {k: v.to(_device) for k, v in inputs.items()}
        import torch
        with torch.no_grad():
            outputs = detector(**inputs)
        probs = torch.softmax(outputs.logits, dim=-1)[0]
        labels = detector.config.id2label
        ai_prob = sum(float(probs[i]) for i in labels if labels[i].lower() != "real")
        return ai_prob
    except Exception:
        return 0.0


def _get_transform():
    return transforms.Compose([
        transforms.Resize((380, 380)),
        transforms.ToTensor(),
        transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225]),
    ])


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
        tamper_prob = 0.0
        cnn_score = 0.0
        hf_ai_prob = 0.0

        if TORCH_AVAILABLE and anomaly_percentage > 0.5:
            transform = _get_transform()
            input_tensor = transform(diff).unsqueeze(0).to(_device)
            with torch.no_grad():
                efnet = _load_tamper_model()
                ef_output = efnet(input_tensor)
                tamper_prob = float(torch.softmax(ef_output, dim=-1)[0, 1].item())

                cnn_model = _load_cnn_detection()
                cnn_transform = transforms.Compose([
                    transforms.Resize((224, 224)),
                    transforms.ToTensor(),
                    transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225]),
                ])
                cnn_input = cnn_transform(diff).unsqueeze(0).to(_device)
                cnn_out = cnn_model(cnn_input)
                cnn_score = float(torch.sigmoid(cnn_out).mean().item())

        # HuggingFace AI image detector (GAN/deepfake detection on original image)
        hf_ai_prob = _run_hf_ai_detector(original)

        final_score = max(anomaly_percentage, tamper_prob * 100, cnn_score * 100, hf_ai_prob * 100)

        if final_score > 2.0:
            finding_parts = []
            if anomaly_percentage > 5.0:
                finding_parts.append(f"ELA anomaly {anomaly_percentage:.1f}%")
            if tamper_prob > 0.5:
                finding_parts.append(f"EfficientNet tamper prob {tamper_prob:.2%}")
            if cnn_score > 0.65:
                finding_parts.append(f"CNNDetection GAN signal {cnn_score:.2%}")
            if hf_ai_prob > 0.65:
                finding_parts.append(f"HF AI detector signal {hf_ai_prob:.2%}")
            finding = "Visual tamper evidence: " + "; ".join(finding_parts) if finding_parts else "Suspicious compression artifacts detected."
            flags.append({
                "layer": "Visual Forensics",
                "finding": finding,
                "severity": "high" if final_score > 5.0 else "medium",
                "score": int(min(100, final_score * 12)),
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
