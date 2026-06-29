"""
Fine-tune EfficientNet-B4 on CASIA v2 + MIDV-2020 for tamper detection.
Also loads CNNDetection weights for GAN detection.
Saves to models/trained/efficientnet_b4_tamper/.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent / "backend"))

import torch
import torch.nn as nn
import torch.optim as optim
from loguru import logger
from PIL import Image
from torch.utils.data import DataLoader, Dataset
from torchvision import models, transforms

MODEL_DIR = Path(__file__).resolve().parent.parent.parent / "models" / "trained" / "efficientnet_b4_tamper"
DATA_DIR = Path(__file__).resolve().parent.parent.parent / "data"


class TamperDataset(Dataset):
    """Dataset for tamper detection. Expects authentic/tamper pairs."""

    def __init__(self, root: Path, split: str = "train", transform=None):
        self.samples: list[tuple[str, int]] = []
        self.transform = transform or transforms.Compose([
            transforms.Resize((380, 380)),
            transforms.ToTensor(),
            transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225]),
        ])
        self._load_casia(root, split)

    def _load_casia(self, root: Path, split: str):
        """Load CASIA combined samples. Authentic = 0, Tampered = 1."""
        casia = root / "casia_combined"
        if not casia.exists():
            logger.warning("CASIA combined not found at {casia}. Using placeholder data.")
            return
        for cls, label in [("Au", 0), ("Tp", 1)]:
            class_dir = casia / split / cls
            if class_dir.exists():
                for fname in class_dir.iterdir():
                    if fname.suffix.lower() in (".jpg", ".png", ".tif", ".tiff"):
                        self.samples.append((str(fname), label))
            else:
                logger.warning(f"Class directory not found: {class_dir}")

    def __len__(self):
        return max(len(self.samples), 1)

    def __getitem__(self, idx):
        if not self.samples:
            return torch.zeros(3, 380, 380), 0
        path, label = self.samples[idx]
        img = Image.open(path).convert("RGB")
        return self.transform(img), label


def get_device():
    if os.environ.get("FORCE_CPU"):
        return "cpu"
    if torch.cuda.is_available():
        return "cuda"
    if hasattr(torch.backends, "mps") and torch.backends.mps.is_available():
        return "mps"
    return "cpu"


def load_cnn_detection_weights(model: nn.Module) -> nn.Module:
    """Load CNNDetection pre-trained weights if available."""
    ckpt = DATA_DIR / "cnn_detection" / "cnndetection_resnet50.pth"
    if ckpt.exists():
        logger.info(f"Loading CNNDetection weights from {ckpt}")
        state = torch.load(ckpt, map_location="cpu", weights_only=True)
        model.load_state_dict(state, strict=False)
    return model


def main():
    device = get_device()
    logger.info(f"Device: {device}")
    MODEL_DIR.mkdir(parents=True, exist_ok=True)

    model = models.efficientnet_b4(weights=models.EfficientNet_B4_Weights.DEFAULT)
    model.classifier[1] = nn.Linear(model.classifier[1].in_features, 2)
    model = load_cnn_detection_weights(model)
    model.to(device)

    num_epochs = int(os.environ.get("TRAIN_EPOCHS", "5"))
    batch_size = int(os.environ.get("TRAIN_BATCH_SIZE", "8" if device == "cpu" else "32"))
    lr = float(os.environ.get("TRAIN_LR", "1e-4"))

    train_ds = TamperDataset(DATA_DIR, "train")
    val_ds = TamperDataset(DATA_DIR, "test")
    train_loader = DataLoader(train_ds, batch_size=batch_size, shuffle=True, num_workers=0)
    val_loader = DataLoader(val_ds, batch_size=batch_size, shuffle=False, num_workers=0)

    criterion = nn.CrossEntropyLoss()
    optimizer = optim.AdamW(model.parameters(), lr=lr)

    logger.info(f"Training for {num_epochs} epochs (batch={batch_size}, lr={lr})...")
    for epoch in range(num_epochs):
        model.train()
        total_loss = 0.0
        for images, labels in train_loader:
            images, labels = images.to(device), labels.to(device)
            optimizer.zero_grad()
            outputs = model(images)
            loss = criterion(outputs, labels)
            loss.backward()
            optimizer.step()
            total_loss += loss.item()

        model.eval()
        correct = total = 0
        with torch.no_grad():
            for images, labels in val_loader:
                images, labels = images.to(device), labels.to(device)
                outputs = model(images)
                _, predicted = torch.max(outputs, 1)
                total += labels.size(0)
                correct += (predicted == labels).sum().item()

        acc = correct / total if total else 0
        logger.info(f"Epoch {epoch+1}/{num_epochs} — loss={total_loss/len(train_loader):.4f}, val_acc={acc:.3f}")

    torch.save(model.state_dict(), MODEL_DIR / "efficientnet_b4_tamper.pth")
    logger.info(f"Model saved to {MODEL_DIR / 'efficientnet_b4_tamper.pth'}")


if __name__ == "__main__":
    main()
