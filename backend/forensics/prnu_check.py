"""
PRNU (Photo Response Non-Uniformity) Fingerprinting.

Detects whether an identity document photo (Aadhaar, PAN) was captured
by a real camera sensor or is a re-photograph / screen capture of a genuine
document — a very common identity forgery technique.

Each camera sensor has a unique noise fingerprint (PRNU). A re-photographed
or screen-captured document will have a different noise pattern than the
original capture, or will show print-screen artifacts.
"""
from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Dict, List

import numpy as np
from PIL import Image

from loguru import logger


def _extract_noise_residual(image: Image.Image) -> np.ndarray:
    """
    Extract the noise residual from an image using a simplified wavelet
    denoising approach. The noise residual = original - denoised.
    """
    try:
        import cv2
    except ImportError:
        logger.warning("OpenCV not available for PRNU analysis")
        return np.array([])

    img_array = np.array(image.convert("RGB"), dtype=np.float32)

    # Apply Gaussian blur as a simple denoising proxy
    # (A full implementation would use BM3D or wavelet denoising)
    denoised = cv2.GaussianBlur(img_array, (3, 3), 0.8)

    # Noise residual
    noise = img_array - denoised
    return noise


def _compute_noise_statistics(noise: np.ndarray) -> Dict[str, float]:
    """Compute statistical features from the noise residual."""
    if noise.size == 0:
        return {"std": 0.0, "kurtosis": 0.0, "mean_abs": 0.0}

    flat = noise.flatten()
    std = float(np.std(flat))
    mean_abs = float(np.mean(np.abs(flat)))

    # Kurtosis (excess) — natural images have specific noise distributions
    n = len(flat)
    if n > 4 and std > 0:
        kurtosis = float(np.mean(((flat - np.mean(flat)) / std) ** 4) - 3.0)
    else:
        kurtosis = 0.0

    return {"std": std, "kurtosis": kurtosis, "mean_abs": mean_abs}


def _detect_screen_capture_artifacts(image: Image.Image) -> bool:
    """
    Detect moiré patterns typical of screen captures or re-photography.
    Uses FFT to find periodic artifacts.
    """
    try:
        import cv2
    except ImportError:
        return False

    gray = np.array(image.convert("L"), dtype=np.float32)

    # Compute 2D FFT
    f_transform = np.fft.fft2(gray)
    f_shift = np.fft.fftshift(f_transform)
    magnitude = np.log1p(np.abs(f_shift))

    # Check for periodic peaks (moiré patterns) in the frequency domain
    # Real photos have smooth, radially symmetric frequency distributions
    # Screen captures show sharp periodic peaks from pixel grid
    h, w = magnitude.shape
    center_h, center_w = h // 2, w // 2

    # Sample a ring around the center (mid-frequency range where moiré appears)
    ring_start = min(h, w) // 6
    ring_end = min(h, w) // 3

    ring_values = []
    for r in range(ring_start, ring_end):
        for angle in np.linspace(0, 2 * np.pi, 72):
            y = int(center_h + r * np.sin(angle))
            x = int(center_w + r * np.cos(angle))
            if 0 <= y < h and 0 <= x < w:
                ring_values.append(magnitude[y, x])

    if not ring_values:
        return False

    ring_arr = np.array(ring_values)
    # High coefficient of variation in the ring = periodic peaks = screen capture
    cv = float(np.std(ring_arr) / (np.mean(ring_arr) + 1e-10))
    return cv > 0.35


def analyze_prnu(image_source: str | Path | Image.Image) -> List[Dict[str, Any]]:
    """
    Run PRNU analysis on an identity document image.
    Returns fraud flags if re-photography or screen-capture is detected.
    """
    flags: List[Dict[str, Any]] = []

    try:
        if isinstance(image_source, Image.Image):
            image = image_source.convert("RGB")
        else:
            image = Image.open(str(image_source)).convert("RGB")

        # 1. Extract noise residual and compute statistics
        noise = _extract_noise_residual(image)
        stats = _compute_noise_statistics(noise)

        # Natural camera photos have a characteristic noise standard deviation
        # Re-photographed documents tend to have either very low noise (printed/screen)
        # or abnormal kurtosis (multiple compression stages)
        if stats["std"] < 0.5 and stats["mean_abs"] < 0.3:
            flags.append({
                "layer": "PRNU Forensics",
                "finding": "Abnormally low sensor noise — image may be a synthetic render or heavily processed scan, not a direct camera capture.",
                "severity": "medium",
                "score": 40,
            })

        if abs(stats["kurtosis"]) > 8.0:
            flags.append({
                "layer": "PRNU Forensics",
                "finding": f"Abnormal noise kurtosis ({stats['kurtosis']:.1f}), suggesting multiple compression stages or digital manipulation of identity document.",
                "severity": "high",
                "score": 55,
            })

        # 2. Screen capture / moiré detection
        if _detect_screen_capture_artifacts(image):
            flags.append({
                "layer": "PRNU Forensics",
                "finding": "Moiré pattern detected in frequency domain — image appears to be a photograph of a screen or printed document, not an original capture.",
                "severity": "high",
                "score": 70,
            })

    except Exception as e:
        logger.warning(f"PRNU analysis failed: {e}")

    return flags
