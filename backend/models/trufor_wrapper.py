from __future__ import annotations

import os
import subprocess
import tempfile
import zipfile
from pathlib import Path
from typing import Any, Dict, List, Optional

from loguru import logger

TRUFOR_DIR = Path(__file__).resolve().parent.parent.parent / "models" / "trufor"
TRUFOR_TRAIN_DIR = TRUFOR_DIR / "TruFor_train_test"
TRUFOR_REPO = "https://github.com/NorthGuard/TruFor.git"
TRUFOR_WEIGHTS_URL = "https://www.grip.unina.it/download/prog/TruFor/TruFor_weights.zip"
TRUFOR_AVAILABLE = False


def _ensure_repo() -> bool:
    if (TRUFOR_TRAIN_DIR / "test.py").exists():
        return True
    try:
        import shutil
        shutil.rmtree(str(TRUFOR_DIR), ignore_errors=True)
        TRUFOR_DIR.mkdir(parents=True, exist_ok=True)
        logger.info(f"Cloning TruFor repo to {TRUFOR_DIR}...")
        subprocess.check_call(
            ["git", "clone", "--depth", "1", TRUFOR_REPO, str(TRUFOR_DIR)],
            timeout=120,
        )
        return True
    except Exception as e:
        logger.warning(f"TruFor repo clone failed: {e}")
        return False


def _ensure_weights() -> bool:
    weights_dir = TRUFOR_TRAIN_DIR / "pretrained_models"
    weights_file = weights_dir / "trufor.pth.tar"
    if weights_file.exists():
        return True
    try:
        weights_dir.mkdir(parents=True, exist_ok=True)
        zip_path = weights_dir / "TruFor_weights.zip"
        logger.info("Downloading TruFor weights (~260MB)...")
        import urllib.request
        urllib.request.urlretrieve(TRUFOR_WEIGHTS_URL, str(zip_path))
        import zipfile
        with zipfile.ZipFile(str(zip_path), "r") as zf:
            zf.extractall(str(weights_dir))
        import glob, shutil
        for f in glob.glob(str(weights_dir / "weights" / "*")):
            shutil.move(f, str(weights_dir))
        shutil.rmtree(str(weights_dir / "weights"), ignore_errors=True)
        zip_path.unlink()
        logger.info("TruFor weights ready")
        return True
    except Exception as e:
        logger.warning(f"TruFor weights download failed: {e}")
        return False


def download_trufor() -> str:
    _ensure_repo()
    _ensure_weights()
    return str(TRUFOR_DIR)


def _get_python() -> str:
    import sys
    return sys.executable


def run_trufor(image) -> List[Dict[str, Any]]:
    flags: List[Dict[str, Any]] = []

    if not _ensure_repo() or not _ensure_weights():
        return flags

    temp_input = tempfile.mktemp(suffix=".png")
    temp_output = tempfile.mkdtemp()
    try:
        if hasattr(image, "save"):
            image.save(temp_input, format="PNG")
        else:
            from PIL import Image
            Image.open(str(image)).save(temp_input, format="PNG")

        test_script = TRUFOR_TRAIN_DIR / "test.py"
        model_file = TRUFOR_TRAIN_DIR / "pretrained_models" / "trufor.pth.tar"
        cmd = [
            _get_python(), str(test_script),
            "-g", "-1",
            "-in", temp_input,
            "-out", temp_output,
            "-exp", "trufor_ph3",
            "TEST.MODEL_FILE", str(model_file),
        ]
        env = os.environ.copy()

        result = subprocess.run(cmd, capture_output=True, text=True, timeout=300, env=env, cwd=str(TRUFOR_TRAIN_DIR))
        if result.returncode != 0:
            logger.warning(f"TruFor inference failed: {result.stderr[:500]}")
            return flags

        import glob as glob_mod
        out_files = glob_mod.glob(os.path.join(temp_output, "*.npz"))
        if not out_files:
            out_files = glob_mod.glob(os.path.join(temp_output, "*.png.npz"))
        if not out_files:
            out_files = glob_mod.glob(os.path.join(temp_output, "*"))
        if not out_files:
            logger.warning("TruFor: no output .npz found")
            return flags

        import numpy as np
        data = np.load(out_files[0])
        score_arr = data.get("score")
        if score_arr is not None:
            score = float(score_arr.flat[0]) if score_arr.size > 0 else 0.0
        else:
            score = 0.0

        if score > 0.3:
            flags.append({
                "layer": "Visual Forensics",
                "finding": f"TruFor forgery detection: integrity score {score:.3f} (0=pristine, 1=tampered). Pixel-level localization map available.",
                "severity": "high" if score > 0.6 else "medium",
                "score": int(score * 100),
            })

    except subprocess.TimeoutExpired:
        logger.warning("TruFor inference timed out after 300s")
    except Exception as e:
        logger.warning(f"TruFor inference error: {e}")
    finally:
        for p in [temp_input]:
            if os.path.exists(p):
                os.remove(p)
        import shutil
        if os.path.exists(temp_output):
            shutil.rmtree(temp_output, ignore_errors=True)

    return flags
