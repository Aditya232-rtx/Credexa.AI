from __future__ import annotations

import math
import os
from pathlib import Path
from typing import Dict

from loguru import logger

from utils.model_registry import registry

try:
    import torch
    import torch.nn as nn
    from torch.amp import autocast
    import timm
    from transformers import AutoProcessor, SiglipVisionModel
    from peft import LoraConfig, get_peft_model
    from torchvision import transforms
    from huggingface_hub import hf_hub_download

    _BOMBEK1_AVAILABLE = True
except Exception:
    _BOMBEK1_AVAILABLE = False

MODEL_REPO = "Bombek1/ai-image-detector-siglip-dinov2"
MODEL_DIR = Path(__file__).resolve().parent.parent.parent / "models" / "trained" / "bombek1_ai_detector"


class LoRALinear(nn.Module):
    def __init__(self, original: nn.Linear, rank: int, alpha: float, dropout: float = 0.1):
        super().__init__()
        self.original = original
        self.scaling = alpha / rank
        for p in self.original.parameters():
            p.requires_grad = False
        self.lora_A = nn.Linear(original.in_features, rank, bias=False)
        self.lora_B = nn.Linear(rank, original.out_features, bias=False)
        self.dropout = nn.Dropout(dropout)
        nn.init.kaiming_uniform_(self.lora_A.weight, a=math.sqrt(5))
        nn.init.zeros_(self.lora_B.weight)

    def forward(self, x):
        return self.original(x) + self.lora_B(self.lora_A(self.dropout(x))) * self.scaling


class ClassificationHead(nn.Module):
    def __init__(self, input_dim: int, hidden_dim: int = 512, dropout: float = 0.3):
        super().__init__()
        self.head = nn.Sequential(
            nn.LayerNorm(input_dim),
            nn.Linear(input_dim, hidden_dim),
            nn.GELU(),
            nn.Dropout(dropout),
            nn.Linear(hidden_dim, hidden_dim // 2),
            nn.GELU(),
            nn.Dropout(dropout),
            nn.Linear(hidden_dim // 2, 1),
        )

    def forward(self, x):
        return self.head(x).squeeze(-1)


class EnsembleAIDetector(nn.Module):
    def __init__(self, siglip_model_name: str, dinov2_model_name: str, image_size: int = 392):
        super().__init__()
        self.siglip = SiglipVisionModel.from_pretrained(siglip_model_name, torch_dtype=torch.bfloat16)
        self.siglip_dim = self.siglip.config.hidden_size
        self.dinov2 = timm.create_model(dinov2_model_name, pretrained=True, num_classes=0, img_size=image_size)
        self.dinov2_dim = self.dinov2.num_features
        self.classifier = ClassificationHead(self.siglip_dim + self.dinov2_dim)

    def forward(self, siglip_pixels, dinov2_pixels):
        siglip_features = self.siglip(pixel_values=siglip_pixels).pooler_output
        dinov2_features = self.dinov2(dinov2_pixels)
        combined = torch.cat([siglip_features.float(), dinov2_features], dim=-1)
        logits = self.classifier(combined)
        return logits, siglip_features, dinov2_features


def _create_model_with_lora(
    siglip_model_name: str = "google/siglip2-so400m-patch14-384",
    dinov2_model_name: str = "vit_large_patch14_dinov2.lvd142m",
    image_size: int = 392,
    lora_rank: int = 32,
    lora_alpha: int = 64,
    lora_dropout: float = 0.1,
) -> EnsembleAIDetector:
    model = EnsembleAIDetector(siglip_model_name, dinov2_model_name, image_size)
    lora_config = LoraConfig(
        r=lora_rank,
        lora_alpha=lora_alpha,
        target_modules=["q_proj", "v_proj"],
        lora_dropout=lora_dropout,
        bias="none",
    )
    model.siglip = get_peft_model(model.siglip, lora_config)
    for name, module in model.dinov2.named_modules():
        if hasattr(module, "qkv") and isinstance(module.qkv, nn.Linear):
            module.qkv = LoRALinear(module.qkv, lora_rank, lora_alpha, lora_dropout)
    return model


def _create_transforms(image_size: int = 392):
    return transforms.Compose([
        transforms.Resize((image_size, image_size), interpolation=transforms.InterpolationMode.BICUBIC),
        transforms.ToTensor(),
        transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225]),
    ])


class AIImageDetector:
    def __init__(self, device: str | None = None):
        if device is None:
            device = "cuda" if torch.cuda.is_available() else "cpu"
        self.device = torch.device(device)

        MODEL_DIR.mkdir(parents=True, exist_ok=True)
        ckpt_path = MODEL_DIR / "pytorch_model.pt"

        if not ckpt_path.exists():
            logger.warning("Bombek1 model checkpoint not found. Set BOMBEK1_DOWNLOAD=1 to auto-download (2.1 GB).")
            raise FileNotFoundError(f"Bombek1 checkpoint not found at {ckpt_path}")

        logger.info(f"Loading Bombek1 model checkpoint from {ckpt_path}...")
        checkpoint = torch.load(ckpt_path, map_location=self.device, weights_only=False)
        config = checkpoint.get("config", {})

        self.model = _create_model_with_lora(
            siglip_model_name=config.get("siglip_model", "google/siglip2-so400m-patch14-384"),
            dinov2_model_name=config.get("dinov2_model", "vit_large_patch14_dinov2.lvd142m"),
            image_size=config.get("image_size", 392),
            lora_rank=config.get("lora_rank", 32),
            lora_alpha=config.get("lora_alpha", 64),
            lora_dropout=config.get("lora_dropout", 0.1),
        )

        self.model.load_state_dict(checkpoint["model_state_dict"])
        self.model.to(self.device)
        self.model.eval()

        self.siglip_processor = AutoProcessor.from_pretrained("google/siglip2-so400m-patch14-384")
        self.dinov2_transform = _create_transforms(config.get("image_size", 392))
        logger.info(f"Bombek1 AI Image Detector loaded on {self.device}")

    @torch.no_grad()
    def predict(self, image) -> Dict:
        if isinstance(image, str):
            image = Image.open(image)
        if image.mode != "RGB":
            image = image.convert("RGB")

        siglip_inputs = self.siglip_processor(images=image, return_tensors="pt")
        siglip_pixels = siglip_inputs["pixel_values"].to(self.device)
        dinov2_pixels = self.dinov2_transform(image).unsqueeze(0).to(self.device)

        with autocast("cuda", enabled=self.device.type == "cuda"):
            logits, _, _ = self.model(siglip_pixels, dinov2_pixels)

        probability = torch.sigmoid(logits).item()
        return {
            "probability": probability,
            "prediction": "ai-generated" if probability > 0.5 else "real",
            "confidence": probability if probability > 0.5 else 1 - probability,
        }


_detector_instance = None


def _load_bombek1_once():
    global _detector_instance
    if _detector_instance is not None:
        return _detector_instance
    if not _BOMBEK1_AVAILABLE:
        return None
    ckpt_path = MODEL_DIR / "pytorch_model.pt"
    if not ckpt_path.exists():
        if os.environ.get("BOMBEK1_DOWNLOAD", "").strip() in ("1", "true", "yes"):
            try:
                MODEL_DIR.mkdir(parents=True, exist_ok=True)
                logger.info(f"Downloading Bombek1 model checkpoint (2.1 GB) to {ckpt_path}...")
                downloaded = hf_hub_download(
                    repo_id=MODEL_REPO,
                    filename="pytorch_model.pt",
                    local_dir=MODEL_DIR,
                    local_dir_use_symlinks=False,
                    resume_download=True,
                )
                ckpt_path = Path(downloaded)
            except Exception as e:
                logger.warning(f"Bombek1 download failed: {e}")
                return None
        else:
            logger.info("Bombek1 model not loaded (set BOMBEK1_DOWNLOAD=1 to download 2.1 GB checkpoint)")
            return None
    try:
        _detector_instance = AIImageDetector()
        return _detector_instance
    except Exception as e:
        logger.warning(f"Failed to load Bombek1 AI detector: {e}")
        return None


def get_bombek1_detector():
    return registry.get(
        key="bombek1",
        loader=_load_bombek1_once,
        size_gb=2.5,
        group="forensics",
    )


def run_bombek1_inference(image: Image.Image) -> float:
    detector = get_bombek1_detector()
    if detector is None:
        return 0.0
    try:
        result = detector.predict(image)
        return result["probability"]
    except Exception:
        return 0.0
