"""
Credexa AI — EfficientNet-B4 Tamper Detection Training (Local PC)
=================================================================
Trains on CASIA dataset (Au + Tp images) for binary classification:
  - Class 0: Authentic
  - Class 1: Tampered / Spliced

Optimized for NVIDIA RTX 4090 (24GB VRAM) with mixed-precision training.

Usage:
    python scripts/train/train_visual_forensics.py

Saves `efficientnet_b4_tamper.pth` into `models/trained/efficientnet_b4_tamper/`.
"""

import os
import sys
import time
import random
import argparse
from pathlib import Path

import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import DataLoader, Dataset
from torch.amp import GradScaler, autocast
from torchvision import models, transforms
from PIL import Image
from tqdm import tqdm
import numpy as np

# ─── Resolve project root (2 levels up from this script) ─────────────────────
SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent.parent  # Credexa.AI-v1/

# ─── Argument parser ─────────────────────────────────────────────────────────
def parse_args():
    parser = argparse.ArgumentParser(
        description="Train EfficientNet-B4 for image tamper detection"
    )
    parser.add_argument(
        "--data-dir", type=str,
        default=str(PROJECT_ROOT / "dataset"),
        help="Path to dataset folder containing Au/ and Tp/ subdirectories"
    )
    parser.add_argument(
        "--model-dir", type=str,
        default=str(PROJECT_ROOT / "model"),
        help="Path to local pretrained EfficientNet-B4 weights folder"
    )
    parser.add_argument(
        "--output-dir", type=str,
        default=str(PROJECT_ROOT / "models" / "trained" / "efficientnet_b4_tamper"),
        help="Directory to save trained model and outputs"
    )
    parser.add_argument("--epochs", type=int, default=75, help="Number of training epochs")
    parser.add_argument("--batch-size", type=int, default=48, help="Batch size (48 fits well on RTX 4090 24GB)")
    parser.add_argument("--lr", type=float, default=1e-4, help="Learning rate")
    parser.add_argument("--weight-decay", type=float, default=1e-5, help="Weight decay for AdamW")
    parser.add_argument("--img-size", type=int, default=380, help="Input image size (EfficientNet-B4 native)")
    parser.add_argument("--num-workers", type=int, default=8, help="DataLoader workers")
    parser.add_argument("--val-split", type=float, default=0.2, help="Fraction of data for validation")
    parser.add_argument("--seed", type=int, default=42, help="Random seed for reproducibility")
    parser.add_argument("--resume", type=str, default=None, help="Path to checkpoint to resume training from")
    parser.add_argument("--no-amp", action="store_true", help="Disable mixed precision training")
    return parser.parse_args()


# ─── Dataset ──────────────────────────────────────────────────────────────────
class TamperDataset(Dataset):
    """
    Loads images from a flat directory structure:
        dataset/Au/  -> label 0 (authentic)
        dataset/Tp/  -> label 1 (tampered)
    """
    VALID_EXTENSIONS = {'.jpg', '.jpeg', '.png', '.tif', '.tiff', '.bmp'}

    def __init__(self, root, transform=None):
        self.samples = []
        self.transform = transform
        root = Path(root)

        for cls_name, label in [('Au', 0), ('Tp', 1)]:
            cls_dir = root / cls_name
            if not cls_dir.exists():
                print(f"  WARNING: {cls_dir} not found, skipping.")
                continue
            for fname in sorted(cls_dir.iterdir()):
                if fname.suffix.lower() in self.VALID_EXTENSIONS:
                    self.samples.append((str(fname), label))

        if len(self.samples) == 0:
            raise FileNotFoundError(
                f"No images found in {root}. Expected Au/ and Tp/ subdirectories."
            )

    def __len__(self):
        return len(self.samples)

    def __getitem__(self, idx):
        path, label = self.samples[idx]
        try:
            img = Image.open(path).convert('RGB')
        except Exception as e:
            print(f"  WARNING: Could not load {path}: {e}. Returning black image.")
            img = Image.new('RGB', (380, 380), (0, 0, 0))
        if self.transform:
            img = self.transform(img)
        return img, label


# ─── TransformSubset (Defined globally so multiprocessing can pickle it) ──────
class TransformSubset(Dataset):
    def __init__(self, dataset, indices, transform):
        self.dataset = dataset
        self.indices = indices
        self.transform = transform

    def __len__(self):
        return len(self.indices)

    def __getitem__(self, idx):
        path, label = self.dataset.samples[self.indices[idx]]
        try:
            img = Image.open(path).convert('RGB')
        except Exception as e:
            print(f"  WARNING: Could not load {path}: {e}")
            img = Image.new('RGB', (380, 380), (0, 0, 0))
        if self.transform:
            img = self.transform(img)
        return img, label


# ─── Training & Validation ───────────────────────────────────────────────────
def train_one_epoch(model, loader, criterion, optimizer, scaler, device, use_amp, epoch, num_epochs):
    model.train()
    running_loss = 0.0
    correct = 0
    total = 0

    pbar = tqdm(loader, desc=f"Epoch {epoch+1}/{num_epochs} [train]", leave=False, ncols=120)
    for images, labels in pbar:
        images = images.to(device, non_blocking=True)
        labels = labels.to(device, non_blocking=True)

        optimizer.zero_grad(set_to_none=True)

        with autocast(device_type='cuda', enabled=use_amp):
            outputs = model(images)
            loss = criterion(outputs, labels)

        scaler.scale(loss).backward()
        scaler.unscale_(optimizer)
        torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
        scaler.step(optimizer)
        scaler.update()

        running_loss += loss.item()
        _, predicted = torch.max(outputs, 1)
        total += labels.size(0)
        correct += (predicted == labels).sum().item()

        pbar.set_postfix({
            'loss': f'{loss.item():.4f}',
            'acc': f'{correct/total:.3f}'
        })

    avg_loss = running_loss / len(loader)
    accuracy = correct / total
    return avg_loss, accuracy


@torch.no_grad()
def validate(model, loader, criterion, device, use_amp, epoch, num_epochs):
    model.eval()
    running_loss = 0.0
    correct = 0
    total = 0
    all_preds = []
    all_labels = []
    all_probs = []

    pbar = tqdm(loader, desc=f"Epoch {epoch+1}/{num_epochs} [val]  ", leave=False, ncols=120)
    for images, labels in pbar:
        images = images.to(device, non_blocking=True)
        labels = labels.to(device, non_blocking=True)

        with autocast(device_type='cuda', enabled=use_amp):
            outputs = model(images)
            loss = criterion(outputs, labels)

        running_loss += loss.item()
        probs = torch.softmax(outputs.float(), dim=1)
        _, predicted = torch.max(outputs, 1)
        total += labels.size(0)
        correct += (predicted == labels).sum().item()

        all_preds.extend(predicted.cpu().tolist())
        all_labels.extend(labels.cpu().tolist())
        all_probs.extend(probs[:, 1].cpu().tolist())

        pbar.set_postfix({'acc': f'{correct/total:.3f}'})

    avg_loss = running_loss / len(loader)
    accuracy = correct / total
    return avg_loss, accuracy, all_preds, all_labels, all_probs


# ─── Evaluation Report ───────────────────────────────────────────────────────
def print_evaluation_report(all_labels, all_preds, all_probs):
    """Print classification report, confusion matrix, and ROC-AUC."""
    try:
        from sklearn.metrics import classification_report, confusion_matrix, roc_auc_score
        print("\n" + "=" * 60)
        print("FINAL EVALUATION REPORT")
        print("=" * 60)
        print(classification_report(
            all_labels, all_preds,
            target_names=['Authentic (0)', 'Tampered (1)']
        ))

        cm = confusion_matrix(all_labels, all_preds)
        print("Confusion Matrix:")
        print(f"                Predicted")
        print(f"                Auth    Tamp")
        print(f"  Actual Auth  [{cm[0][0]:5d}  {cm[0][1]:5d}]")
        print(f"  Actual Tamp  [{cm[1][0]:5d}  {cm[1][1]:5d}]")

        auc = roc_auc_score(all_labels, all_probs)
        print(f"\nROC-AUC: {auc:.4f}")
        print(f"FPR (tampered as authentic): {cm[1][0] / max(sum(cm[1]), 1):.3f}")
        print(f"FNR (authentic as tampered): {cm[0][1] / max(sum(cm[0]), 1):.3f}")
    except ImportError:
        print("\n[INFO] Install scikit-learn for detailed classification metrics:")
        print("       pip install scikit-learn")


def save_training_plots(train_losses, val_losses, val_accs, best_acc, output_dir):
    """Save training curves as PNG."""
    try:
        import matplotlib
        matplotlib.use('Agg')  # Non-interactive backend
        import matplotlib.pyplot as plt

        fig, axes = plt.subplots(1, 3, figsize=(18, 5))

        # Training loss
        axes[0].plot(train_losses, color='#2196F3', linewidth=1.5)
        axes[0].set_title('Training Loss', fontsize=13)
        axes[0].set_xlabel('Epoch')
        axes[0].set_ylabel('Loss')
        axes[0].grid(True, alpha=0.3)

        # Validation loss
        axes[1].plot(val_losses, color='#FF5722', linewidth=1.5)
        axes[1].set_title('Validation Loss', fontsize=13)
        axes[1].set_xlabel('Epoch')
        axes[1].set_ylabel('Loss')
        axes[1].grid(True, alpha=0.3)

        # Validation accuracy
        axes[2].plot(val_accs, color='#4CAF50', linewidth=1.5)
        axes[2].axhline(y=best_acc, color='r', linestyle='--', alpha=0.7,
                        label=f'Best: {best_acc:.3f}')
        axes[2].set_title('Validation Accuracy', fontsize=13)
        axes[2].set_xlabel('Epoch')
        axes[2].set_ylabel('Accuracy')
        axes[2].legend()
        axes[2].grid(True, alpha=0.3)

        plt.tight_layout()
        plot_path = Path(output_dir) / 'training_curve.png'
        plt.savefig(plot_path, dpi=150)
        plt.close()
        print(f"Training curves saved to: {plot_path}")
    except ImportError:
        print("[INFO] Install matplotlib to save training plots:")
        print("       pip install matplotlib")


# ─── Main ─────────────────────────────────────────────────────────────────────
def main():
    args = parse_args()

    # Seed everything
    random.seed(args.seed)
    np.random.seed(args.seed)
    torch.manual_seed(args.seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(args.seed)

    # ─── Device setup ─────────────────────────────────────────────────────
    device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
    use_amp = torch.cuda.is_available() and not args.no_amp

    print("=" * 60)
    print("Credexa AI - EfficientNet-B4 Tamper Detection Training")
    print("=" * 60)
    print(f"Device:          {device}")
    if torch.cuda.is_available():
        print(f"GPU:             {torch.cuda.get_device_name(0)}")
        print(f"VRAM:            {torch.cuda.get_device_properties(0).total_memory / 1024**3:.1f} GB")
    print(f"Mixed Precision: {'Enabled' if use_amp else 'Disabled'}")
    print(f"Data Dir:        {args.data_dir}")
    print(f"Model Dir:       {args.model_dir}")
    print(f"Output Dir:      {args.output_dir}")
    print(f"Epochs:          {args.epochs}")
    print(f"Batch Size:      {args.batch_size}")
    print(f"Learning Rate:   {args.lr}")
    print(f"Image Size:      {args.img_size}")
    print(f"Val Split:       {args.val_split}")
    print()

    # ─── Output directory ─────────────────────────────────────────────────
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    # ─── Transforms ───────────────────────────────────────────────────────
    train_transform = transforms.Compose([
        transforms.Resize((args.img_size, args.img_size)),
        transforms.RandomHorizontalFlip(p=0.3),
        transforms.RandomVerticalFlip(p=0.1),
        transforms.RandomRotation(10),
        transforms.ColorJitter(brightness=0.15, contrast=0.15, saturation=0.1, hue=0.02),
        transforms.RandomAffine(degrees=0, translate=(0.05, 0.05)),
        transforms.ToTensor(),
        transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225]),
        transforms.RandomErasing(p=0.1, scale=(0.02, 0.1)),
    ])

    val_transform = transforms.Compose([
        transforms.Resize((args.img_size, args.img_size)),
        transforms.ToTensor(),
        transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225]),
    ])

    # ─── Load dataset & split ─────────────────────────────────────────────
    print("Loading dataset...")
    full_dataset = TamperDataset(args.data_dir, transform=None)  # No transform yet

    num_authentic = sum(1 for _, l in full_dataset.samples if l == 0)
    num_tampered = sum(1 for _, l in full_dataset.samples if l == 1)
    print(f"  Total:     {len(full_dataset)} images")
    print(f"  Authentic: {num_authentic}")
    print(f"  Tampered:  {num_tampered}")

    # Stratified split: keep class proportions in train/val
    auth_indices = [i for i, (_, l) in enumerate(full_dataset.samples) if l == 0]
    tamp_indices = [i for i, (_, l) in enumerate(full_dataset.samples) if l == 1]
    random.shuffle(auth_indices)
    random.shuffle(tamp_indices)

    val_auth = int(len(auth_indices) * args.val_split)
    val_tamp = int(len(tamp_indices) * args.val_split)

    val_indices = auth_indices[:val_auth] + tamp_indices[:val_tamp]
    train_indices = auth_indices[val_auth:] + tamp_indices[val_tamp:]
    random.shuffle(train_indices)
    random.shuffle(val_indices)

    # Instantiate datasets using global class
    train_ds = TransformSubset(full_dataset, train_indices, train_transform)
    val_ds = TransformSubset(full_dataset, val_indices, val_transform)

    print(f"\n  Train: {len(train_ds)} samples")
    print(f"  Val:   {len(val_ds)} samples")

    train_loader = DataLoader(
        train_ds, batch_size=args.batch_size, shuffle=True,
        num_workers=args.num_workers, pin_memory=True,
        persistent_workers=True if args.num_workers > 0 else False,
        drop_last=True,
    )
    val_loader = DataLoader(
        val_ds, batch_size=args.batch_size, shuffle=False,
        num_workers=args.num_workers, pin_memory=True,
        persistent_workers=True if args.num_workers > 0 else False,
    )

    print(f"  Train batches: {len(train_loader)}")
    print(f"  Val batches:   {len(val_loader)}")

    # ─── Build model ──────────────────────────────────────────────────────
    print("\nBuilding model...")

    # Load pretrained EfficientNet-B4 from local weights if available,
    # otherwise fall back to torchvision pretrained weights
    model_dir = Path(args.model_dir)
    local_weights = model_dir / 'pytorch_model.bin'

    if local_weights.exists():
        print(f"  Loading local pretrained weights from: {local_weights}")
        model = models.efficientnet_b4(weights=None)
        try:
            state_dict = torch.load(str(local_weights), map_location='cpu', weights_only=False)
            model.load_state_dict(state_dict, strict=False)
            print("  Local weights loaded (partial match may occur with HF format).")
        except Exception as e:
            print(f"  Could not load local weights ({e}). Using torchvision ImageNet weights.")
            model = models.efficientnet_b4(weights=models.EfficientNet_B4_Weights.IMAGENET1K_V1)
    else:
        print("  No local weights found. Downloading torchvision ImageNet pretrained weights...")
        model = models.efficientnet_b4(weights=models.EfficientNet_B4_Weights.IMAGENET1K_V1)

    # Replace classifier head for binary classification
    in_features = model.classifier[1].in_features
    model.classifier[1] = nn.Linear(in_features, 2)
    model = model.to(device)

    total_params = sum(p.numel() for p in model.parameters())
    trainable_params = sum(p.numel() for p in model.parameters() if p.requires_grad)
    print(f"  Model:     EfficientNet-B4")
    print(f"  Params:    {total_params:,}")
    print(f"  Trainable: {trainable_params:,}")

    # ─── Loss, optimizer, scheduler ───────────────────────────────────────
    # Use weighted loss to handle class imbalance
    weight_authentic = len(full_dataset.samples) / (2 * num_authentic) if num_authentic > 0 else 1.0
    weight_tampered = len(full_dataset.samples) / (2 * num_tampered) if num_tampered > 0 else 1.0
    class_weights = torch.tensor([weight_authentic, weight_tampered], dtype=torch.float32).to(device)
    print(f"  Class weights: Au={weight_authentic:.3f}, Tp={weight_tampered:.3f}")

    criterion = nn.CrossEntropyLoss(weight=class_weights)
    optimizer = optim.AdamW(model.parameters(), lr=args.lr, weight_decay=args.weight_decay)
    scheduler = optim.lr_scheduler.CosineAnnealingLR(optimizer, T_max=args.epochs)
    
    # Modern PyTorch uses torch.amp.GradScaler instead of torch.cuda.amp.GradScaler
    scaler = GradScaler('cuda', enabled=use_amp)

    # ─── Resume from checkpoint ───────────────────────────────────────────
    start_epoch = 0
    best_acc = 0.0
    train_losses = []
    val_losses = []
    val_accs = []

    if args.resume:
        resume_path = Path(args.resume)
        if resume_path.exists():
            print(f"\n  Resuming from checkpoint: {resume_path}")
            checkpoint = torch.load(str(resume_path), map_location=device, weights_only=False)
            model.load_state_dict(checkpoint['model_state_dict'])
            optimizer.load_state_dict(checkpoint['optimizer_state_dict'])
            start_epoch = checkpoint['epoch'] + 1
            best_acc = checkpoint.get('val_acc', 0.0)
            train_losses = checkpoint.get('train_losses', [])
            val_losses = checkpoint.get('val_losses', [])
            val_accs = checkpoint.get('val_accs', [])
            print(f"  Resumed at epoch {start_epoch}, best_acc={best_acc:.4f}")
        else:
            print(f"  WARNING: Checkpoint not found at {resume_path}, starting fresh.")

    # ─── Training loop ────────────────────────────────────────────────────
    print("\n" + "=" * 60)
    print("TRAINING STARTED")
    print("=" * 60)
    total_start = time.time()

    for epoch in range(start_epoch, args.epochs):
        epoch_start = time.time()

        # Train
        train_loss, train_acc = train_one_epoch(
            model, train_loader, criterion, optimizer, scaler,
            device, use_amp, epoch, args.epochs
        )
        train_losses.append(train_loss)

        # Validate
        val_loss, val_acc, all_preds, all_labels, all_probs = validate(
            model, val_loader, criterion, device, use_amp, epoch, args.epochs
        )
        val_losses.append(val_loss)
        val_accs.append(val_acc)

        # Step scheduler
        scheduler.step()
        current_lr = scheduler.get_last_lr()[0]

        epoch_time = time.time() - epoch_start
        print(
            f"Epoch {epoch+1:3d}/{args.epochs} | "
            f"train_loss={train_loss:.4f} | train_acc={train_acc:.4f} | "
            f"val_loss={val_loss:.4f} | val_acc={val_acc:.4f} | "
            f"lr={current_lr:.2e} | {epoch_time:.1f}s"
        )

        # Save best model
        if val_acc > best_acc:
            best_acc = val_acc
            best_path = output_dir / 'efficientnet_b4_tamper.pth'
            torch.save(model.state_dict(), best_path)
            print(f"  >> New best model saved (acc={val_acc:.4f})")

        # Save checkpoint every 10 epochs
        if (epoch + 1) % 10 == 0:
            ckpt_path = output_dir / f'checkpoint_epoch_{epoch+1}.pt'
            torch.save({
                'epoch': epoch,
                'model_state_dict': model.state_dict(),
                'optimizer_state_dict': optimizer.state_dict(),
                'scheduler_state_dict': scheduler.state_dict(),
                'scaler_state_dict': scaler.state_dict(),
                'val_acc': val_acc,
                'best_acc': best_acc,
                'loss': train_loss,
                'train_losses': train_losses,
                'val_losses': val_losses,
                'val_accs': val_accs,
            }, ckpt_path)
            print(f"  >> Checkpoint saved: {ckpt_path}")

    total_time = time.time() - total_start
    print("\n" + "=" * 60)
    print("TRAINING COMPLETE")
    print("=" * 60)
    print(f"Total time:  {total_time/60:.1f} minutes ({total_time/3600:.1f} hours)")
    print(f"Best val_acc: {best_acc:.4f}")
    print(f"Model saved:  {output_dir / 'efficientnet_b4_tamper.pth'}")

    # ─── Final evaluation with best model ─────────────────────────────────
    best_model_path = output_dir / 'efficientnet_b4_tamper.pth'
    if best_model_path.exists():
        print("\nRunning final evaluation with best model...")
        model.load_state_dict(torch.load(str(best_model_path), map_location=device, weights_only=True))
        _, _, final_preds, final_labels, final_probs = validate(
            model, val_loader, criterion, device, use_amp, 0, 1
        )
        print_evaluation_report(final_labels, final_preds, final_probs)

    # ─── Save training plots ──────────────────────────────────────────────
    save_training_plots(train_losses, val_losses, val_accs, best_acc, output_dir)

    # ─── Model size info ──────────────────────────────────────────────────
    model_size = best_model_path.stat().st_size / (1024 * 1024)
    print(f"\nModel size: {model_size:.1f} MB")

    print("\n=== Deployment Instructions ===")
    print(f"1. Model saved at: {best_model_path}")
    print(f"2. It's already in the correct location for Credexa backend.")
    print(f"3. Restart the Credexa backend to load the new model.")
    print(f"4. The visual_forensics pipeline will auto-load it.")


if __name__ == '__main__':
    main()
