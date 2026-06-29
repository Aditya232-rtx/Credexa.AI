"""
Colab training script for Credexa AI — EfficientNet-B4 tamper detection on CASIA.

Usage in Colab:
    !pip install torchvision tqdm matplotlib seaborn scikit-learn
    !python colab_train_visual_forensics.py

Dataset expected at: /content/data/casia_combined/train/{Au,Tp} and test/{Au,Tp}
Model saved to: /content/drive/MyDrive/credexa_models/efficientnet_b4_tamper.pth
"""
import os
from pathlib import Path

DATA_DIR = Path("/content/data")
MODEL_DIR = Path("/content/drive/MyDrive/credexa_models")
MODEL_DIR.mkdir(parents=True, exist_ok=True)

NUM_EPOCHS = int(os.environ.get("TRAIN_EPOCHS", "75"))
BATCH_SIZE = int(os.environ.get("TRAIN_BATCH_SIZE", "32"))
LEARNING_RATE = float(os.environ.get("TRAIN_LR", "1e-4"))
IMG_SIZE = 380

import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import DataLoader, Dataset
from torchvision import models, transforms
from PIL import Image
from tqdm.auto import tqdm

device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
print(f"Device: {device}")


class TamperDataset(Dataset):
    def __init__(self, root, split="train", transform=None):
        self.samples = []
        self.transform = transform
        casia = Path(root) / "casia_combined"
        for cls, label in [("Au", 0), ("Tp", 1)]:
            class_dir = casia / split / cls
            if class_dir.exists():
                for fname in class_dir.iterdir():
                    if fname.suffix.lower() in (".jpg", ".png", ".tif", ".tiff"):
                        self.samples.append((str(fname), label))

    def __len__(self):
        return len(self.samples)

    def __getitem__(self, idx):
        path, label = self.samples[idx]
        img = Image.open(path).convert("RGB")
        if self.transform:
            img = self.transform(img)
        return img, label


train_transform = transforms.Compose([
    transforms.Resize((IMG_SIZE, IMG_SIZE)),
    transforms.RandomHorizontalFlip(p=0.3),
    transforms.RandomRotation(5),
    transforms.ColorJitter(brightness=0.1, contrast=0.1, saturation=0.05),
    transforms.ToTensor(),
    transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225]),
])

val_transform = transforms.Compose([
    transforms.Resize((IMG_SIZE, IMG_SIZE)),
    transforms.ToTensor(),
    transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225]),
])

train_ds = TamperDataset(DATA_DIR, "train", train_transform)
val_ds = TamperDataset(DATA_DIR, "test", val_transform)

train_loader = DataLoader(train_ds, batch_size=BATCH_SIZE, shuffle=True, num_workers=4, pin_memory=True)
val_loader = DataLoader(val_ds, batch_size=BATCH_SIZE, shuffle=False, num_workers=4, pin_memory=True)

print(f"Train: {len(train_ds)} samples ({len(train_loader)} batches)")
print(f"Val:   {len(val_ds)} samples ({len(val_loader)} batches)")

model = models.efficientnet_b4(weights=models.EfficientNet_B4_Weights.IMAGENET1K_V1)
model.classifier[1] = nn.Linear(model.classifier[1].in_features, 2)
model = model.to(device)

criterion = nn.CrossEntropyLoss()
optimizer = optim.AdamW(model.parameters(), lr=LEARNING_RATE, weight_decay=1e-5)
scheduler = optim.lr_scheduler.CosineAnnealingLR(optimizer, T_max=NUM_EPOCHS)

best_acc = 0.0
print(f"Training for {NUM_EPOCHS} epochs (batch={BATCH_SIZE}, lr={LEARNING_RATE})...")

for epoch in range(NUM_EPOCHS):
    model.train()
    running_loss = 0.0
    for images, labels in tqdm(train_loader, desc=f"Epoch {epoch+1}/{NUM_EPOCHS}", leave=False):
        images, labels = images.to(device, non_blocking=True), labels.to(device, non_blocking=True)
        optimizer.zero_grad()
        outputs = model(images)
        loss = criterion(outputs, labels)
        loss.backward()
        torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
        optimizer.step()
        running_loss += loss.item()

    avg_loss = running_loss / len(train_loader)

    model.eval()
    correct = total = 0
    with torch.no_grad():
        for images, labels in val_loader:
            images, labels = images.to(device, non_blocking=True), labels.to(device, non_blocking=True)
            outputs = model(images)
            _, predicted = torch.max(outputs, 1)
            total += labels.size(0)
            correct += (predicted == labels).sum().item()

    acc = correct / total
    scheduler.step()

    print(f"Epoch {epoch+1:2d}/{NUM_EPOCHS} — loss={avg_loss:.4f} — val_acc={acc:.4f}")

    if acc > best_acc:
        best_acc = acc
        torch.save(model.state_dict(), MODEL_DIR / "efficientnet_b4_tamper.pth")
        print(f"  >> New best: {acc:.4f}")

print(f"\nDone! Best val_acc: {best_acc:.4f}")
print(f"Model: {MODEL_DIR / 'efficientnet_b4_tamper.pth'}")
print(f"Size:  {(MODEL_DIR / 'efficientnet_b4_tamper.pth').stat().st_size / 1e6:.1f} MB")
