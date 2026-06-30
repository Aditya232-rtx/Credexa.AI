from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List

from loguru import logger

from utils.model_registry import registry

try:
    import torch
    import torch.nn.functional as F
    from PIL import Image
    from utils.device import get_device

    _CLIP_AVAILABLE = False
    try:
        import open_clip
        _CLIP_AVAILABLE = True
    except ImportError:
        try:
            from transformers import CLIPProcessor, CLIPModel
            _HF_CLIP_AVAILABLE = True
        except ImportError:
            _HF_CLIP_AVAILABLE = False

    TORCH_AVAILABLE = True
except ImportError:
    TORCH_AVAILABLE = False
    _CLIP_AVAILABLE = False
    _HF_CLIP_AVAILABLE = False

ANOMALYCLIP_REPO = "zqhang/AnomalyCLIP"
ANOMALYCLIP_DIR = Path(__file__).resolve().parent.parent.parent / "models" / "anomalyclip"
ANOMALYCLIP_CKPT = ANOMALYCLIP_DIR / "anomalyclip_vit_large.pt"

_open_clip_model = None
_open_clip_preprocess = None
_open_clip_tokenizer = None
_hf_clip_model = None
_hf_clip_processor = None


def _load_open_clip_once():
    global _open_clip_model, _open_clip_preprocess, _open_clip_tokenizer
    if _open_clip_model is not None:
        return _open_clip_model, _open_clip_preprocess, _open_clip_tokenizer
    if not _CLIP_AVAILABLE:
        return None, None, None
    import os
    hf_cache = os.path.expanduser("~/.cache/huggingface/hub")
    if not any(f.startswith("models--laion") for f in os.listdir(hf_cache)) if os.path.isdir(hf_cache) else True:
        logger.info("OpenCLIP model not cached yet. Will download on first use.")
    try:
        device = get_device()
        model_name = "ViT-L-14"
        pretrained = "laion2b_s32b_b82k"
        _open_clip_model, _open_clip_preprocess, _open_clip_tokenizer = open_clip.create_model_and_transforms(
            model_name, pretrained=pretrained
        )
        _open_clip_model.to(device)
        _open_clip_model.eval()
        logger.info(f"OpenCLIP {model_name} loaded for zero-shot anomaly detection")
        return _open_clip_model, _open_clip_preprocess, _open_clip_tokenizer
    except Exception as e:
        logger.warning(f"OpenCLIP load failed: {e}")
        return None, None, None


def _load_open_clip():
    return registry.get(
        key="open_clip",
        loader=_load_open_clip_once,
        size_gb=1.5,
        group="forensics",
    )


def _load_hf_clip_once():
    global _hf_clip_model, _hf_clip_processor
    if _hf_clip_model is not None:
        return _hf_clip_model, _hf_clip_processor
    if not _HF_CLIP_AVAILABLE:
        return None, None
    try:
        device = get_device()
        _hf_clip_model = CLIPModel.from_pretrained("openai/clip-vit-large-patch14")
        _hf_clip_processor = CLIPProcessor.from_pretrained("openai/clip-vit-large-patch14")
        _hf_clip_model.to(device)
        _hf_clip_model.eval()
        logger.info("HF CLIP ViT-L/14 loaded for zero-shot anomaly detection")
        return _hf_clip_model, _hf_clip_processor
    except Exception as e:
        logger.warning(f"HF CLIP load failed: {e}")
        return None, None


def _load_hf_clip():
    return registry.get(
        key="hf_clip",
        loader=_load_hf_clip_once,
        size_gb=1.5,
        group="forensics",
    )


def _clip_zero_shot_anomaly(image: Image.Image) -> float:
    model, preprocess, tokenizer = _load_open_clip()
    device = get_device()
    if model is not None:
        try:
            normal_texts = [
                "a normal authentic document",
                "a genuine bank statement",
                "an unaltered official document",
                "a legitimate financial record",
            ]
            anomaly_texts = [
                "a tampered document with alterations",
                "a forged financial document",
                "a manipulated image with edits",
                "a suspicious altered record",
            ]
            all_texts = normal_texts + anomaly_texts
            text_tokens = tokenizer(all_texts).to(device)
            _use_amp = device not in ("cpu", "mps")
            with torch.no_grad(), torch.cuda.amp.autocast(enabled=_use_amp):
                text_features = model.encode_text(text_tokens)
                text_features = F.normalize(text_features, dim=-1)

                image_input = preprocess(image).unsqueeze(0).to(device)
                image_features = model.encode_image(image_input)
                image_features = F.normalize(image_features, dim=-1)

                similarity = (100.0 * image_features @ text_features.T).softmax(dim=-1)
                normal_prob = similarity[0, :4].sum().item()
                anomaly_prob = similarity[0, 4:].sum().item()
                return anomaly_prob / max(normal_prob + anomaly_prob, 1e-8)
        except Exception as e:
            logger.warning(f"OpenCLIP anomaly scoring failed: {e}")
            return 0.0

    hf_model, hf_processor = _load_hf_clip()
    if hf_model is not None:
        try:
            normal_texts = [
                "a normal authentic document",
                "a genuine bank statement",
                "an unaltered official document",
                "a legitimate financial record",
            ]
            anomaly_texts = [
                "a tampered document with alterations",
                "a forged financial document",
                "a manipulated image with edits",
                "a suspicious altered record",
            ]
            all_texts = normal_texts + anomaly_texts
            inputs = hf_processor(
                text=all_texts,
                images=image,
                return_tensors="pt",
                padding=True,
            )
            inputs = {k: v.to(device) for k, v in inputs.items()}
            with torch.no_grad():
                outputs = hf_model(**inputs)
                logits_per_image = outputs.logits_per_image
                probs = logits_per_image.softmax(dim=-1)
                normal_prob = probs[0, :4].sum().item()
                anomaly_prob = probs[0, 4:].sum().item()
                return anomaly_prob / max(normal_prob + anomaly_prob, 1e-8)
        except Exception as e:
            logger.warning(f"HF CLIP anomaly scoring failed: {e}")
            return 0.0

    return 0.0


def detect_anomalyclip(image: Image.Image) -> Dict[str, Any]:
    if not TORCH_AVAILABLE:
        return {"score": 0.0, "finding": "", "severity": "low"}

    anomaly_prob = _clip_zero_shot_anomaly(image)

    result: Dict[str, Any] = {"score": anomaly_prob}
    if anomaly_prob > 0.7:
        result["finding"] = f"AnomalyCLIP zero-shot detection: P(anomaly)={anomaly_prob:.2%}. Document visual features deviate from expected authentic patterns."
        result["severity"] = "high" if anomaly_prob > 0.85 else "medium"
    else:
        result["finding"] = ""
        result["severity"] = "low"

    return result
