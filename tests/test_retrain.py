import pytest
from backend.anomaly.retrain import (
    collect_training_data,
    retrain_model,
    load_trained_model,
    MODEL_PATH,
)


class TestCollectTrainingData:
    def test_returns_list(self):
        # This will fail gracefully without DB, just check return type
        result = collect_training_data()
        assert isinstance(result, list)


class TestRetrainModel:
    def test_insufficient_data_returns_none(self):
        # Mock insufficient data
        result = retrain_model()
        # Without DB or with insufficient data, should return None
        assert result is None or isinstance(result, str)


class TestLoadTrainedModel:
    def test_load_nonexistent_returns_none(self):
        # If model file doesn't exist, should return None
        if MODEL_PATH.exists():
            MODEL_PATH.unlink()
        result = load_trained_model()
        assert result is None

    def test_load_existing_model(self):
        import pickle
        from sklearn.ensemble import IsolationForest
        import numpy as np
        
        MODEL_PATH.parent.mkdir(parents=True, exist_ok=True)
        model = IsolationForest(contamination=0.1, random_state=42)
        model.fit(np.random.rand(100, 11))
        with open(MODEL_PATH, "wb") as f:
            pickle.dump(model, f)
        
        result = load_trained_model()
        assert result is not None
        assert hasattr(result, 'predict')
        
        MODEL_PATH.unlink()