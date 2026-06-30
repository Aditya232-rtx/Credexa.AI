from __future__ import annotations

import os
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any, Dict, List, Optional

from loguru import logger

from utils.model_registry import registry

MANTRANET_DIR = Path(__file__).resolve().parent.parent.parent / "models" / "mantranet"
MANTRANET_MODULE_DIR = MANTRANET_DIR / "MantraNet"
MANTRANET_REPO = "https://github.com/RonyAbecidan/ManTraNet-pytorch.git"
MANTRANET_AVAILABLE = False
_mantranet_model = None


def _ensure_repo() -> bool:
    if (MANTRANET_MODULE_DIR / "mantranet.py").exists():
        return True
    try:
        import shutil
        shutil.rmtree(str(MANTRANET_DIR), ignore_errors=True)
        MANTRANET_DIR.mkdir(parents=True, exist_ok=True)
        logger.info(f"Cloning ManTraNet repo to {MANTRANET_DIR}...")
        subprocess.check_call(
            ["git", "clone", "--depth", "1", MANTRANET_REPO, str(MANTRANET_DIR)],
            timeout=60,
        )
        return True
    except Exception as e:
        logger.warning(f"ManTraNet repo clone failed: {e}")
        return False


def _load_model_once() -> Any:
    global _mantranet_model, MANTRANET_AVAILABLE
    if not _ensure_repo():
        return None
    try:
        import os as _os
        old_cwd = _os.getcwd()
        _os.chdir(str(MANTRANET_MODULE_DIR))
        sys.path.insert(0, str(MANTRANET_MODULE_DIR))
        from mantranet import device, pre_trained_model
        _mantranet_model = pre_trained_model()
        _mantranet_model.to(device)
        _mantranet_model.eval()
        _os.chdir(old_cwd)
        MANTRANET_AVAILABLE = True
        logger.info("ManTraNet loaded (3.9M params)")
        return _mantranet_model
    except Exception as e:
        _os.chdir(old_cwd)
        logger.warning(f"ManTraNet model load failed: {e}")
        return None


def _load_model():
    return registry.get(
        key="mantranet",
        loader=_load_model_once,
        size_gb=0.5,
        group="forensics",
    )


def download_mantranet() -> str:
    _ensure_repo()
    return str(MANTRANET_DIR)


def run_mantranet(image) -> List[Dict[str, Any]]:
    flags: List[Dict[str, Any]] = []

    model = _load_model()
    if model is None:
        return flags

    try:
        import torch
        from PIL import Image
        import numpy as np

        if hasattr(image, "convert"):
            pil_img = image.convert("RGB")
        else:
            pil_img = Image.open(str(image)).convert("RGB")

        temp_path = tempfile.mktemp(suffix=".png")
        try:
            pil_img.save(temp_path, format="PNG")

            from mantranet import device
            sys.path.insert(0, str(MANTRANET_MODULE_DIR))

            im = Image.open(temp_path)
            im_np = np.array(im)
            im_tensor = torch.Tensor(im_np)
            im_tensor = im_tensor.unsqueeze(0)
            im_tensor = im_tensor.transpose(2, 3).transpose(1, 2)
            im_tensor = im_tensor.to(device)

            with torch.no_grad():
                output = model(im_tensor)
                if isinstance(output, (list, tuple)):
                    output = output[0]

            anomaly_mask = output[0][0].cpu().detach().numpy()
            score = float(anomaly_mask.mean())

            if score > 0.3:
                flags.append({
                    "layer": "Visual Forensics",
                    "finding": f"ManTraNet forgery detection: mean anomaly={score:.3f}. Detects copy-move, splicing, removal, and enhancement manipulations.",
                    "severity": "high" if score > 0.6 else "medium",
                    "score": int(score * 100),
                })
        finally:
            if os.path.exists(temp_path):
                os.remove(temp_path)

    except Exception as e:
        logger.warning(f"ManTraNet inference error: {e}")

    return flags
