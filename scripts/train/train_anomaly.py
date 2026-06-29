"""
Train anomaly detection models: Isolation Forest, ECOD, and Autoencoder.
Saves models to models/trained/anomaly/.
"""
from __future__ import annotations

import json
import os
import pickle
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent / "backend"))

import numpy as np
from loguru import logger
from sklearn.ensemble import IsolationForest

MODEL_DIR = Path(__file__).resolve().parent.parent.parent / "models" / "trained" / "anomaly"
DATA_DIR = Path(__file__).resolve().parent.parent.parent / "data"

try:
    from pyod.models.ecod import ECOD
except ImportError:
    ECOD = None

try:
    import torch
    import torch.nn as nn
    import torch.optim as optim

    TORCH_AVAILABLE = True
except ImportError:
    TORCH_AVAILABLE = False


class AnomalyAutoencoder(nn.Module):
    def __init__(self, input_dim: int = 11, encoding_dim: int = 4):
        super().__init__()
        self.encoder = nn.Sequential(
            nn.Linear(input_dim, 8),
            nn.ReLU(),
            nn.Linear(8, encoding_dim),
            nn.ReLU(),
        )
        self.decoder = nn.Sequential(
            nn.Linear(encoding_dim, 8),
            nn.ReLU(),
            nn.Linear(8, input_dim),
        )

    def forward(self, x):
        return self.decoder(self.encoder(x))


def generate_synthetic_training_data(n_samples: int = 2000) -> np.ndarray:
    rng = np.random.default_rng(42)
    data = np.zeros((n_samples, 11))
    data[:, 0] = rng.exponential(2000, n_samples)       # text_length
    data[:, 1] = rng.poisson(2, n_samples).astype(float) # flag_count
    data[:, 2] = rng.poisson(3, n_samples).astype(float) # table_count
    data[:, 3] = rng.poisson(5, n_samples).astype(float) # page_count
    data[:, 4] = rng.exponential(500000, n_samples)      # file_size
    data[:, 5] = rng.poisson(6, n_samples).astype(float) # metadata_count
    data[:, 6] = rng.beta(1, 5, n_samples) * 100         # pct_round_numbers
    data[:, 7] = rng.exponential(50, n_samples)           # flag_score_sum
    data[:, 8] = rng.beta(8, 2, n_samples) * 100          # ocr_confidence_avg
    data[:, 9] = rng.exponential(400, n_samples)          # text_density
    data[:, 10] = rng.poisson(15, n_samples).astype(float) # amount_count
    return data


def fit_scaler(data: np.ndarray):
    from sklearn.preprocessing import StandardScaler
    scaler = StandardScaler()
    scaler.fit(data)
    return scaler


def train_isolation_forest(data: np.ndarray) -> IsolationForest:
    logger.info(f"Training Isolation Forest on {len(data)} samples...")
    model = IsolationForest(
        contamination=0.05,
        n_estimators=200,
        random_state=42,
    )
    model.fit(data)
    return model


def train_ecod(data: np.ndarray):
    if ECOD is None:
        logger.warning("pyod not installed. Skipping ECOD training.")
        return None
    logger.info(f"Training ECOD on {len(data)} samples...")
    model = ECOD(contamination=0.05)
    model.fit(data)
    return model


def train_autoencoder(data: np.ndarray, input_dim: int = 11) -> AnomalyAutoencoder | None:
    if not TORCH_AVAILABLE:
        logger.warning("PyTorch not available. Skipping autoencoder training.")
        return None

    device = "cuda" if torch.cuda.is_available() else "cpu"
    logger.info(f"Training Autoencoder on {len(data)} samples (device={device})...")

    model = AnomalyAutoencoder(input_dim=input_dim).to(device)
    criterion = nn.MSELoss()
    optimizer = optim.AdamW(model.parameters(), lr=1e-3)

    dataset = torch.FloatTensor(data).to(device)
    batch_size = 64
    n_epochs = 50

    for epoch in range(n_epochs):
        permutation = torch.randperm(len(dataset))
        total_loss = 0.0
        for i in range(0, len(dataset), batch_size):
            indices = permutation[i:i + batch_size]
            batch = dataset[indices]
            optimizer.zero_grad()
            output = model(batch)
            loss = criterion(output, batch)
            loss.backward()
            optimizer.step()
            total_loss += loss.item()
        if (epoch + 1) % 10 == 0:
            logger.info(f"  AE Epoch {epoch+1}/{n_epochs}: loss={total_loss:.6f}")

    return model


def main():
    MODEL_DIR.mkdir(parents=True, exist_ok=True)
    logger.info(f"Model directory: {MODEL_DIR}")

    data = generate_synthetic_training_data(2000)

    feature_names = [
        "text_length", "flag_count", "table_count", "page_count",
        "file_size", "metadata_count", "pct_round_numbers",
        "flag_score_sum", "ocr_confidence_avg", "text_density", "amount_count",
    ]
    (MODEL_DIR / "feature_names.json").write_text(json.dumps(feature_names))

    scaler = fit_scaler(data)
    with open(MODEL_DIR / "scaler.pkl", "wb") as f:
        pickle.dump(scaler, f)
    data_scaled = scaler.transform(data)

    if_model = train_isolation_forest(data_scaled)
    with open(MODEL_DIR / "isolation_forest.pkl", "wb") as f:
        pickle.dump(if_model, f)
    logger.info(f"  Saved Isolation Forest ({len(data)} samples)")

    ecod_model = train_ecod(data_scaled)
    if ecod_model:
        with open(MODEL_DIR / "ecod.pkl", "wb") as f:
            pickle.dump(ecod_model, f)
        logger.info("  Saved ECOD model")

    ae_model = train_autoencoder(data_scaled, input_dim=11)
    if ae_model:
        torch.save(ae_model.state_dict(), MODEL_DIR / "autoencoder.pth")
        logger.info("  Saved Autoencoder weights")

    logger.info("All anomaly models trained and saved.")


if __name__ == "__main__":
    main()
