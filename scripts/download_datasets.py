"""
Download all public datasets and pre-trained weights for model fine-tuning.
Skips already-downloaded items. Designed for macOS/Linux.
"""
from __future__ import annotations

import os
import shutil
import tarfile
import urllib.request
import zipfile
from pathlib import Path

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
DATA_DIR.mkdir(parents=True, exist_ok=True)


def _download(url: str, dest: Path, desc: str = "") -> Path:
    dest.parent.mkdir(parents=True, exist_ok=True)
    if dest.exists() and dest.stat().st_size > 1024:
        print(f"  ✓ {desc or dest.name} already exists")
        return dest
    print(f"  ↓ {desc or dest.name} ...")
    urllib.request.urlretrieve(url, dest)
    print(f"  ✓ {desc or dest.name} downloaded ({dest.stat().st_size >> 20} MB)")
    return dest


def _unzip(path: Path, target: Path) -> Path:
    if target.exists():
        print(f"  ✓ {target.name} already extracted")
        return target
    print(f"  Extracting {path.name} ...")
    with zipfile.ZipFile(path, "r") as zf:
        zf.extractall(target)
    print(f"  ✓ Extracted to {target}")
    return target


def _untar(path: Path, target: Path) -> Path:
    if target.exists():
        print(f"  ✓ {target.name} already extracted")
        return target
    print(f"  Extracting {path.name} ...")
    with tarfile.open(path, "r:*") as tf:
        tf.extractall(target)
    print(f"  ✓ Extracted to {target}")
    return target


def download_rvl_cdip() -> Path:
    """RVL-CDIP: 400K document images, 16 classes. From chainyo/rvl-cdip on HuggingFace."""
    dest = DATA_DIR / "rvl_cdip"
    if (dest / "labels.csv").exists() or len(list(dest.glob("*"))) > 10:
        print("  ✓ RVL-CDIP already prepared")
        return dest
    print("  ↓ Loading RVL-CDIP via HuggingFace (chainyo/rvl-cdip, ~20 GB)...")
    try:
        from datasets import load_dataset
        ds = load_dataset("chainyo/rvl-cdip", split="train", trust_remote_code=True)
        dest.mkdir(parents=True, exist_ok=True)
        (dest / "labels.csv").write_text(
            "\n".join(f"{i},{r['label']}" for i, r in enumerate(ds))
        )
        print(f"  ✓ RVL-CDIP: {len(ds)} samples, labels saved")
    except Exception as e:
        print(f"  ⚠ RVL-CDIP download failed: {e}")
    return dest


def download_casia_v2() -> Path:
    """CASIA v2: 12.6K tampered images. From Kaggle sophatvathana/casia-dataset."""
    dest = DATA_DIR / "casia_v2"
    if (dest / "CASIA2").exists() or len(list(dest.glob("*"))) > 5:
        print("  ✓ CASIA v2 already prepared")
        return dest
    print("  ⚠ CASIA v2 requires Kaggle download:")
    print("    1. Visit https://www.kaggle.com/datasets/sophatvathana/casia-dataset")
    print("    2. Download and extract to data/casia_v2/")
    print("    Or use: kaggle datasets download sophatvathana/casia-dataset -p data/casia_v2/")
    print("  Also get corrected ground truth from:")
    print("    https://github.com/SunnyHaze/CASIA2.0-Corrected-Groundtruth")
    dest.mkdir(parents=True, exist_ok=True)
    return dest


def download_funsd() -> Path:
    """FUNSD: 199 forms, 9707 entities. From HuggingFace nielsr/funsd."""
    dest = DATA_DIR / "funsd"
    if (dest / "train.json").exists() or len(list(dest.glob("*.json"))) >= 2:
        print("  ✓ FUNSD already prepared")
        return dest
    print("  ↓ Loading FUNSD via HuggingFace...")
    try:
        from datasets import load_dataset
        ds = load_dataset("nielsr/funsd", trust_remote_code=True)
        dest.mkdir(parents=True, exist_ok=True)
        for split in ds:
            (dest / f"{split}.json").write_text(str(ds[split]))
        print(f"  ✓ FUNSD loaded ({len(ds['train'])} train, {len(ds['test'])} test)")
    except Exception as e:
        print(f"  ⚠ FUNSD download failed: {e}")
    return dest


def download_cord() -> Path:
    """CORD v2: 11K receipts, key-value. From HuggingFace."""
    dest = DATA_DIR / "cord"
    if (dest / "train.json").exists():
        print("  ✓ CORD v2 already prepared")
        return dest
    print("  ↓ Loading CORD v2 via HuggingFace...")
    try:
        from datasets import load_dataset
        ds = load_dataset("naver-clova-ix/cord-v2", trust_remote_code=True)
        dest.mkdir(parents=True, exist_ok=True)
        for split in ds:
            (dest / f"{split}.json").write_text(str(ds[split]))
        print(f"  ✓ CORD v2: {len(ds['train'])} train, {len(ds['validation'])} val")
    except Exception as e:
        print(f"  ⚠ CORD v2 download failed: {e}")
    return dest


def download_midv_2020() -> Path:
    """MIDV-2020: 1000 clips, 50 doc types. From ftp://smartengines.com/midv-2020."""
    dest = DATA_DIR / "midv_2020"
    if (dest / "images").exists() or len(list(dest.glob("*"))) > 5:
        print("  ✓ MIDV-2020 already prepared")
        return dest
    print("  ⚠ MIDV-2020 requires FTP download:")
    print("    ftp://smartengines.com/midv-2020")
    print("    Use: wget -r ftp://smartengines.com/midv-2020/ -P data/midv_2020/")
    print("    Or manually download and extract to data/midv_2020/")
    dest.mkdir(parents=True, exist_ok=True)
    return dest


def download_cnn_detection() -> Path:
    """CNNDetection weights (Wang et al.): ResNet-50 GAN detector."""
    dest = DATA_DIR / "cnn_detection"
    dest.mkdir(parents=True, exist_ok=True)
    weights = dest / "cnndetection_resnet50.pth"
    # Try known URLs for the pretrained weights
    urls = [
        "https://github.com/PeterWang512/CNNDetection/releases/download/v1.0/pretrained_weights.zip",
        "https://web.eecs.umich.edu/~wangpeter/CNNDetection/pretrained_weights/full_resnet18.pth",
    ]
    for url in urls:
        try:
            _download(url, weights, "CNNDetection weights")
            return dest
        except Exception:
            continue
    print("  ⚠ CNNDetection auto-download failed.")
    print("    Get weights from: https://github.com/PeterWang512/CNNDetection")
    print("    Place .pth file at: data/cnn_detection/cnndetection_resnet50.pth")
    return dest


def download_defacto() -> Path:
    """DEFACTO: 229K forgery images. From https://defactodataset.github.io."""
    dest = DATA_DIR / "defacto"
    if (dest / "images").exists() or len(list(dest.glob("*"))) > 5:
        print("  ✓ DEFACTO already prepared")
        return dest
    print("  ⚠ DEFACTO requires manual download:")
    print("    Visit https://defactodataset.github.io")
    print("    Download and extract to data/defacto/")
    dest.mkdir(parents=True, exist_ok=True)
    return dest


def download_sroie() -> Path:
    """SROIE: 1000 scanned receipts. From ICDAR 2019."""
    dest = DATA_DIR / "sroie"
    zip_dest = dest / "sroie.zip"
    if (dest / "train").exists():
        print("  ✓ SROIE already extracted")
        return dest
    url = "https://github.com/zzzDavid/ICDAR-2019-SROIE/archive/master.zip"
    try:
        _download(url, zip_dest, "SROIE")
        _unzip(zip_dest, dest)
    except Exception as e:
        print(f"  ⚠ SROIE download failed: {e}")
    return dest


def download_docbank() -> Path:
    """DocBank: 500K pages with layout labels. From HuggingFace."""
    dest = DATA_DIR / "docbank"
    if (dest / "labels.csv").exists():
        print("  ✓ DocBank already prepared")
        return dest
    hf_datasets = ["liminghao1630/DocBank", "astrologos/docbank-layout"]
    for hf_name in hf_datasets:
        print(f"  ↓ Loading DocBank via HuggingFace ({hf_name})...")
        try:
            from datasets import load_dataset
            ds = load_dataset(hf_name, trust_remote_code=True, split="train[:500]")
            dest.mkdir(parents=True, exist_ok=True)
            (dest / "labels.csv").write_text(
                "\n".join(f"{i},{r.get('label','?')}" for i, r in enumerate(ds))
            )
            print(f"  ✓ DocBank subset: {len(ds)} samples")
            return dest
        except Exception as e:
            print(f"  ⚠ {hf_name}: {e}")
            continue
    return dest


def download_publaynet() -> Path:
    """PubLayNet: 360K pages. From IBM Research."""
    dest = DATA_DIR / "publaynet"
    if (dest / "train").exists() or len(list(dest.glob("*"))) > 5:
        print("  ✓ PubLayNet already prepared")
        return dest
    urls = {
        "train": "https://dax-cdn.cdn.appdomain.cloud/dax-publaynet/1.0.0/publaynet.tar.gz",
    }
    for split, url in urls.items():
        try:
            tpath = dest / f"{split}.tar.gz"
            _download(url, tpath, f"PubLayNet {split}")
            _untar(tpath, dest)
        except Exception as e:
            print(f"  ⚠ PubLayNet {split}: {e}")
            break
    # If direct download fails, instruct user
    if not (dest / "train").exists():
        print("  ⚠ PubLayNet auto-download failed.")
        print("    Visit: https://github.com/ibm-aur-nlp/PubLayNet")
        print("    Or: https://dax-cdn.cdn.appdomain.cloud/dax-publaynet/1.0.0/PubLayNet.html")
    return dest


def download_kaggle_cc_fraud() -> Path:
    """Credit Card Fraud dataset (ULB). From Kaggle or TF mirror."""
    dest = DATA_DIR / "kaggle_cc_fraud"
    csv_path = dest / "creditcard.csv"
    if csv_path.exists():
        print("  ✓ Kaggle CC Fraud already downloaded")
        return dest
    dest.mkdir(parents=True, exist_ok=True)
    # Try TensorFlow mirror first
    url = "https://storage.googleapis.com/download.tensorflow.org/data/creditcard.csv"
    try:
        _download(url, csv_path, "Kaggle CC Fraud")
        return dest
    except Exception:
        pass
    print("  ⚠ Kaggle CC Fraud auto-download failed.")
    print("    Visit: https://www.kaggle.com/datasets/mlg-ulb/creditcardfraud")
    print("    Download creditcard.csv to data/kaggle_cc_fraud/")
    return dest


def main():
    print("=" * 60)
    print("Credexa AI — Dataset Downloader")
    print("=" * 60)
    print(f"Data directory: {DATA_DIR}")
    print(f"Available disk: {shutil.disk_usage(DATA_DIR).free >> 30} GB\n")

    steps = [
        ("RVL-CDIP (400K docs, 20+ GB)", download_rvl_cdip),
        ("CASIA v2 (12.6K tamper images)", download_casia_v2),
        ("FUNSD (199 forms, NER)", download_funsd),
        ("CORD v2 (11K receipts, key-value)", download_cord),
        ("MIDV-2020 (1K ID doc clips)", download_midv_2020),
        ("CNNDetection (GAN detector weights)", download_cnn_detection),
        ("DEFACTO (229K forgery images)", download_defacto),
        ("SROIE (1K scanned receipts)", download_sroie),
        ("DocBank (500K layout pages, subset)", download_docbank),
        ("PubLayNet (360K pages, subset)", download_publaynet),
        ("Kaggle CC Fraud (284K transactions)", download_kaggle_cc_fraud),
    ]

    for name, func in steps:
        print(f"\n▶ {name}")
        try:
            func()
        except Exception as e:
            print(f"  ✗ Failed: {e}")

    print("\n" + "=" * 60)
    print("Download complete. Check above for any failures.")
    print("=" * 60)


if __name__ == "__main__":
    main()
