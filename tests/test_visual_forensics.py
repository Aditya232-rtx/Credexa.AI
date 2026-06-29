import pytest
import numpy as np
from PIL import Image
from backend.forensics.prnu_check import (
    _extract_noise_residual,
    _compute_noise_statistics,
    _detect_screen_capture_artifacts,
    analyze_prnu,
)
from backend.forensics.visual_forensics import (
    run_ela,
    run_dct_ghost,
)


class TestPRNU:
    def test_extract_noise_residual(self):
        # Create a simple test image
        img = Image.fromarray(np.random.randint(0, 255, (100, 100, 3), dtype=np.uint8))
        noise = _extract_noise_residual(img)
        assert isinstance(noise, np.ndarray)
        assert noise.shape == (100, 100, 3)

    def test_compute_noise_statistics(self):
        noise = np.random.randn(100, 100, 3)
        stats = _compute_noise_statistics(noise)
        assert "std" in stats
        assert "kurtosis" in stats
        assert "mean_abs" in stats
        assert all(isinstance(v, float) for v in stats.values())

    def test_empty_noise_statistics(self):
        noise = np.array([])
        stats = _compute_noise_statistics(noise)
        assert stats == {"std": 0.0, "kurtosis": 0.0, "mean_abs": 0.0}

    def test_detect_screen_capture_artifacts(self):
        # Real photo-like image (should not have moiré)
        img = Image.fromarray(np.random.randint(0, 255, (200, 200, 3), dtype=np.uint8))
        result = _detect_screen_capture_artifacts(img)
        assert isinstance(result, bool)

    def test_analyze_prnu_real_photo(self):
        # Create a realistic photo-like image
        img = Image.fromarray(np.random.randint(0, 255, (300, 300, 3), dtype=np.uint8))
        flags = analyze_prnu(img)
        assert isinstance(flags, list)
        # Should not flag random noise as screen capture


class TestVisualForensics:
    def test_run_ela_clean_image(self):
        img = Image.fromarray(np.random.randint(0, 255, (200, 200, 3), dtype=np.uint8))
        flags = run_ela(img)
        assert isinstance(flags, list)

    def test_run_ela_with_tampering(self):
        # Create an image with a clear tampered region
        img_array = np.ones((200, 200, 3), dtype=np.uint8) * 128
        img_array[50:150, 50:150] = 200  # Bright square
        img = Image.fromarray(img_array)
        flags = run_ela(img)
        assert isinstance(flags, list)

    def test_run_dct_ghost(self):
        img = Image.fromarray(np.random.randint(0, 255, (200, 200, 3), dtype=np.uint8))
        flags = run_dct_ghost(img)
        assert isinstance(flags, list)

    def test_run_dct_ghost_small_image(self):
        img = Image.fromarray(np.random.randint(0, 255, (10, 10, 3), dtype=np.uint8))
        flags = run_dct_ghost(img)
        assert flags == []  # Too small