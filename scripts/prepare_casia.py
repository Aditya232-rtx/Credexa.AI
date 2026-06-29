"""
Prepare CASIA v1 + v2 dataset for tamper detection training.
Creates train/test splits at data/casia_combined/.
"""
from __future__ import annotations

import shutil
import sys
from pathlib import Path
from sklearn.model_selection import train_test_split

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "backend"))

from loguru import logger

# Path to the extracted CASIA dataset — change this to your local path
CASIA_ROOT = Path("data/casia") if Path("data/casia").exists() else Path.home() / "Downloads/archive/casia"
OUTPUT_DIR = Path(__file__).resolve().parent.parent / "data" / "casia_combined"

TRAIN_RATIO = 0.8
SEED = 42


def collect_samples() -> list[tuple[Path, int]]:
    samples: list[tuple[Path, int]] = []

    # CASIA v1: Au=0 (authentic), Sp=1 (spliced)
    v1_au = CASIA_ROOT / "CASIA1" / "Au"
    if v1_au.exists():
        for f in v1_au.iterdir():
            if f.suffix.lower() in (".jpg", ".png", ".tif", ".tiff"):
                samples.append((f, 0))

    v1_sp = CASIA_ROOT / "CASIA1" / "Sp"
    if v1_sp.exists():
        for f in v1_sp.iterdir():
            if f.suffix.lower() in (".jpg", ".png", ".tif", ".tiff"):
                samples.append((f, 1))

    # CASIA v2: Au=0 (authentic), Tp=1 (tampered)
    v2_au = CASIA_ROOT / "CASIA2" / "Au"
    if v2_au.exists():
        for f in v2_au.iterdir():
            if f.suffix.lower() in (".jpg", ".png", ".tif", ".tiff"):
                samples.append((f, 0))

    v2_tp = CASIA_ROOT / "CASIA2" / "Tp"
    if v2_tp.exists():
        for f in v2_tp.iterdir():
            if f.suffix.lower() in (".jpg", ".png", ".tif", ".tiff"):
                samples.append((f, 1))

    return samples


def main():
    samples = collect_samples()
    logger.info(f"Total samples collected: {len(samples)}")
    authentic = sum(1 for _, label in samples if label == 0)
    tampered = sum(1 for _, label in samples if label == 1)
    logger.info(f"  Authentic: {authentic}")
    logger.info(f"  Tampered: {tampered}")

    paths = [s[0] for s in samples]
    labels = [s[1] for s in samples]

    train_paths, test_paths, train_labels, test_labels = train_test_split(
        paths, labels, train_size=TRAIN_RATIO, random_state=SEED, stratify=labels
    )

    logger.info(f"Train: {len(train_paths)} samples")
    logger.info(f"Test:  {len(test_paths)} samples")

    for split_name, split_paths, split_labels in [
        ("train", train_paths, train_labels),
        ("test", test_paths, test_labels),
    ]:
        for cls_name, cls_label in [("Au", 0), ("Tp", 1)]:
            dest_dir = OUTPUT_DIR / split_name / cls_name
            dest_dir.mkdir(parents=True, exist_ok=True)

        for src_path, label in zip(split_paths, split_labels):
            cls_name = "Au" if label == 0 else "Tp"
            dest = OUTPUT_DIR / split_name / cls_name / src_path.name
            if not dest.exists():
                shutil.copy2(str(src_path), str(dest))

    logger.info(f"Dataset prepared at {OUTPUT_DIR}")
    logger.info(f"  train/Au: {len(list((OUTPUT_DIR/'train'/'Au').iterdir()))}")
    logger.info(f"  train/Tp: {len(list((OUTPUT_DIR/'train'/'Tp').iterdir()))}")
    logger.info(f"  test/Au: {len(list((OUTPUT_DIR/'test'/'Au').iterdir()))}")
    logger.info(f"  test/Tp: {len(list((OUTPUT_DIR/'test'/'Tp').iterdir()))}")


if __name__ == "__main__":
    main()
