from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Optional

from loguru import logger

from utils.model_registry import registry

AIDE_DIR = Path(__file__).resolve().parent.parent.parent / "models" / "aide"
AIDE_REPO = "meet4150/AIDE_image_detector"

_aide_model = None
_aide_preprocess = None


def _load_aide_once():
    global _aide_model, _aide_preprocess
    try:
        import torch
        import sys
        import importlib.util
        from pathlib import Path

        if not (AIDE_DIR / "inference.py").exists():
            from huggingface_hub import snapshot_download
            AIDE_DIR.mkdir(parents=True, exist_ok=True)
            snapshot_download(
                repo_id=AIDE_REPO,
                local_dir=str(AIDE_DIR),
                local_dir_use_symlinks=False,
            )

        old_path = sys.path.copy()
        old_modules = {k: v for k, v in sys.modules.items() if k == 'models' or k.startswith('models.')}
        for k in old_modules:
            sys.modules.pop(k, None)
        _backend_root = str(Path(__file__).resolve().parent.parent)
        sys.path = [str(AIDE_DIR), str(AIDE_DIR / "data"), str(AIDE_DIR / "models")] + [p for p in sys.path if not p.startswith(_backend_root)]
        spec = importlib.util.spec_from_file_location("aide_inference", str(AIDE_DIR / "inference.py"))
        aide_inference = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(aide_inference)
        sys.path = old_path
        for k, v in old_modules.items():
            sys.modules[k] = v
        _aide_preprocess = aide_inference
        _aide_model = aide_inference.load_model(AIDE_DIR)
        logger.info("AIDE detector loaded (54.4M params)")
        return _aide_model, _aide_preprocess
    except Exception as e:
        logger.warning(f"AIDE model load failed: {e}. Use 'python -m models.aide_wrapper --download' to fetch weights.")
        return None, None


def _load_aide():
    return registry.get(
        key="aide",
        loader=_load_aide_once,
        size_gb=0.5,
        group="forensics",
    )


def _load_aide():
    return registry.get(
        key="aide",
        loader=_load_aide_once,
        size_gb=0.5,
        group="forensics",
    )


def run_aide(image) -> List[Dict[str, Any]]:
    flags: List[Dict[str, Any]] = []
    result = _load_aide()
    if not result or result[0] is None:
        return flags
    model, preprocess_fn = result

    try:
        from PIL import Image

        if not isinstance(image, Image.Image):
            image = Image.open(str(image)).convert("RGB")

        result = preprocess_fn.predict_pil_images(model, [image])
        if result and isinstance(result, list) and len(result) > 0:
            prob = float(result[0].get("fake_probability", 0.0))
            if prob > 0.5:
                flags.append({
                    "layer": "Visual Forensics",
                    "finding": f"AIDE AI-generated image detector: P(fake)={prob:.2%}",
                    "severity": "high" if prob > 0.8 else "medium",
                    "score": int(prob * 100),
                })
    except Exception as e:
        logger.warning(f"AIDE inference failed: {e}")

    return flags


def download_aide() -> str:
    from huggingface_hub import snapshot_download
    AIDE_DIR.mkdir(parents=True, exist_ok=True)
    target = snapshot_download(
        repo_id=AIDE_REPO,
        local_dir=str(AIDE_DIR),
        local_dir_use_symlinks=False,
    )
    logger.info(f"AIDE weights downloaded to {target}")
    return target


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--download", action="store_true", help="Download AIDE weights")
    parser.add_argument("--image", type=str, help="Run inference on image")
    args = parser.parse_args()
    if args.download:
        download_aide()
    elif args.image:
        from PIL import Image
        img = Image.open(args.image)
        flags = run_aide(img)
        print(json.dumps(flags, indent=2))
    else:
        print("Use --download to fetch weights or --image <path> to run inference")
