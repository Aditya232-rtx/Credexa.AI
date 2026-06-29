"""
Fine-tune LayoutLMv3-base on RVL-CDIP for document classification.
Saves to models/trained/layoutlmv3_router/.
Uses subset of data when running on CPU.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent / "backend"))

import torch
from datasets import load_dataset
from loguru import logger
from transformers import (
    LayoutLMv3ForSequenceClassification,
    LayoutLMv3Processor,
    Trainer,
    TrainingArguments,
)

MODEL_DIR = Path(__file__).resolve().parent.parent.parent / "models" / "trained" / "layoutlmv3_router"
DATA_DIR = Path(__file__).resolve().parent.parent.parent / "data" / "rvl_cdip"


def get_device():
    if torch.cuda.is_available():
        return "cuda"
    if hasattr(torch.backends, "mps") and torch.backends.mps.is_available():
        return "mps"
    return "cpu"


def prepare_dataset(num_samples: int | None = None):
    logger.info(f"Loading RVL-CDIP (subset={num_samples or 'full'})...")
    ds = load_dataset("rvl_cdip", trust_remote_code=True)
    if num_samples:
        ds["train"] = ds["train"].select(range(min(num_samples, len(ds["train"]))))
        ds["test"] = ds["test"].select(range(min(num_samples // 5, len(ds["test"]))))
    return ds


def main():
    device = get_device()
    logger.info(f"Device: {device}")
    logger.info(f"Model dir: {MODEL_DIR}")

    num_samples = int(os.environ.get("TRAIN_SAMPLES", "0"))
    if device == "cpu" and num_samples == 0:
        num_samples = 8000
        logger.warning(f"CPU detected, limiting to {num_samples} samples. Set TRAIN_SAMPLES for full training.")

    ds = prepare_dataset(num_samples or None)
    MODEL_DIR.mkdir(parents=True, exist_ok=True)

    processor = LayoutLMv3Processor.from_pretrained("microsoft/layoutlmv3-base", apply_ocr=False)
    model = LayoutLMv3ForSequenceClassification.from_pretrained(
        "microsoft/layoutlmv3-base",
        num_labels=16,
        label2id={str(i): i for i in range(16)},
        id2label={i: str(i) for i in range(16)},
    )
    model.to(device)

    training_args = TrainingArguments(
        output_dir=str(MODEL_DIR),
        evaluation_strategy="steps",
        eval_steps=100,
        save_steps=200,
        logging_steps=50,
        per_device_train_batch_size=2 if device == "cpu" else 8,
        per_device_eval_batch_size=2 if device == "cpu" else 8,
        num_train_epochs=3,
        learning_rate=2e-5,
        warmup_ratio=0.1,
        fp16=device == "cuda",
        save_total_limit=2,
        remove_unused_columns=False,
        report_to="none",
    )

    def preprocess(examples):
        return processor(
            images=[img.convert("RGB") if hasattr(img, "convert") else img for img in examples.get("image", [])],
            text=examples.get("text", [""] * len(examples["image"])),
            truncation=True,
            max_length=512,
            padding="max_length",
            return_tensors="pt",
        )

    train_ds = ds["train"].map(preprocess, batched=True)
    eval_ds = ds["test"].map(preprocess, batched=True)

    trainer = Trainer(
        model=model,
        args=training_args,
        train_dataset=train_ds,
        eval_dataset=eval_ds,
    )

    logger.info("Starting training...")
    trainer.train()

    logger.info(f"Saving model to {MODEL_DIR}")
    model.save_pretrained(str(MODEL_DIR))
    processor.save_pretrained(str(MODEL_DIR))
    logger.info("Training complete!")


if __name__ == "__main__":
    main()
