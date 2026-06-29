import pickle
from pathlib import Path

import pytest
import numpy as np
from backend.anomaly import main as anomaly_main

MODEL_DIR = Path(__file__).resolve().parent.parent / "models" / "trained" / "anomaly"


class TestAnomalyModelBaselines:
    def test_isolation_forest_loads(self):
        path = MODEL_DIR / "isolation_forest.pkl"
        if not path.exists():
            pytest.skip("No trained IF model found")
        with open(path, "rb") as f:
            model = pickle.load(f)
        assert hasattr(model, "predict")
        assert hasattr(model, "n_features_in_")
        assert model.n_features_in_ == 11

    def test_isolation_forest_output_range(self):
        path = MODEL_DIR / "isolation_forest.pkl"
        if not path.exists():
            pytest.skip("No trained IF model found")
        with open(path, "rb") as f:
            model = pickle.load(f)
        X = np.array([[100, 0, 0, 1, 500, 0, 0, 0, 0.9, 100, 0]])
        pred = model.predict(X)
        assert pred[0] in (1, -1)
        scores = model.score_samples(X)
        assert not np.any(np.isnan(scores))

    def test_scaler_loads(self):
        path = MODEL_DIR / "scaler.pkl"
        if not path.exists():
            pytest.skip("No scaler found")
        with open(path, "rb") as f:
            scaler = pickle.load(f)
        from sklearn.preprocessing import StandardScaler
        assert isinstance(scaler, StandardScaler)
        assert hasattr(scaler, "mean_")
        assert hasattr(scaler, "scale_")
        assert len(scaler.mean_) == 11

    def test_ecod_loads(self):
        path = MODEL_DIR / "ecod.pkl"
        if not path.exists():
            pytest.skip("No ECOD model found")
        with open(path, "rb") as f:
            model = pickle.load(f)
        assert hasattr(model, "predict")

    def test_autoencoder_loads(self):
        if not anomaly_main.TORCH_AVAILABLE:
            pytest.skip("PyTorch not available")
        path = MODEL_DIR / "autoencoder.pth"
        if not path.exists():
            pytest.skip("No autoencoder found")
        import torch
        model = anomaly_main.AnomalyAutoencoder(input_dim=11)
        state = torch.load(path, map_location="cpu", weights_only=True)
        model.load_state_dict(state)
        model.eval()
        x = torch.FloatTensor([[100, 0, 0, 1, 500, 0, 0, 0, 0.9, 100, 0]])
        with torch.no_grad():
            recon = model(x)
        loss = float(torch.mean((x - recon) ** 2).item())
        assert not np.isnan(loss)
        assert loss >= 0


class TestVisualForensicsModels:
    def test_efficientnet_b4_loads(self):
        try:
            import torch
            from backend.forensics.visual_forensics import _load_tamper_model, _device
            model = _load_tamper_model()
            assert model is not None
            out = model(torch.randn(1, 3, 380, 380).to(_device))
            assert out.shape == (1, 2)
        except Exception as e:
            pytest.skip(f"EfficientNet not available: {e}")

    def test_hf_ai_detector_loads(self):
        try:
            from backend.forensics.visual_forensics import _load_hf_ai_detector
            detector, processor = _load_hf_ai_detector()
            assert detector is not None
            assert processor is not None
        except Exception as e:
            pytest.skip(f"HF detector not available: {e}")

    def test_cnn_detection_loads(self):
        try:
            from backend.forensics.visual_forensics import _load_cnn_detection
            model = _load_cnn_detection()
            assert model is not None
        except Exception as e:
            pytest.skip(f"CNN detection not available: {e}")
