"""
Fine-tune LayoutLMv3 on FUNSD + CORD v2 for NER extraction.
Saves to models/trained/layoutlmv3_ner/.
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent / "backend"))

import torch
from datasets import Dataset, load_dataset
from loguru import logger
from transformers import (
    LayoutLMv3ForTokenClassification,
    LayoutLMv3Processor,
    Trainer,
    TrainingArguments,
)

MODEL_DIR = Path(__file__).resolve().parent.parent.parent / "models" / "trained" / "layoutlmv3_ner"
DATA_DIR = Path(__file__).resolve().parent.parent.parent / "data"

FUNSD_LABELS = ["O", "B-HEADER", "I-HEADER", "B-QUESTION", "I-QUESTION", "B-ANSWER", "I-ANSWER"]


def get_device():
    if torch.cuda.is_available():
        return "cuda"
    if hasattr(torch.backends, "mps") and torch.backends.mps.is_available():
        return "mps"
    return "cpu"


def load_funsd(split: str = "train") -> Dataset:
    """Load FUNSD dataset from HuggingFace."""
    ds = load_dataset("nielsr/funsd", trust_remote_code=True, split=split)
    logger.info(f"FUNSD {split}: {len(ds)} samples")
    return ds


def load_cord(split: str = "train") -> Dataset | None:
    """Load CORD v2 dataset from HuggingFace."""
    try:
        ds = load_dataset("naver-clova-ix/cord-v2", trust_remote_code=True, split=split)
        logger.info(f"CORD v2 {split}: {len(ds)} samples")
        return ds
    except Exception as e:
        logger.warning(f"CORD v2 not available: {e}")
        return None


def main():
    device = get_device()
    logger.info(f"Device: {device}")
    MODEL_DIR.mkdir(parents=True, exist_ok=True)

    # Load datasets
    train_funsd = load_funsd("train")
    test_funsd = load_funsd("test")
    train_cord = load_cord("train")

    # Load processor and model
    processor = LayoutLMv3Processor.from_pretrained("nielsr/layoutlmv3-finetuned-funsd", apply_ocr=False)
    model = LayoutLMv3ForTokenClassification.from_pretrained(
        "nielsr/layoutlmv3-finetuned-funsd",
        num_labels=len(FUNSD_LABELS),
        label2id={l: i for i, l in enumerate(FUNSD_LABELS)},
        id2label={i: l for i, l in enumerate(FUNSD_LABELS)},
    )
    model.to(device)

    training_args = TrainingArguments(
        output_dir=str(MODEL_DIR),
        evaluation_strategy="steps",
        eval_steps=50,
        save_steps=100,
        logging_steps=25,
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

    def preprocess_funsd(examples):
        """Tokenize FUNSD examples for LayoutLMv3 token classification."""
        encoding = processor(
            [img.convert("RGB") for img in examples["image"]],
            [words for words in examples["words"]],
            boxes=[boxes for boxes in examples["bboxes"]],
            word_labels=[labels for labels in examples["ner_tags"]],
            truncation=True,
            padding="max_length",
            max_length=512,
            return_tensors="pt",
        )
        return encoding

    train_ds = train_funsd.map(preprocess_funsd, batched=True)
    eval_ds = test_funsd.map(preprocess_funsd, batched=True)

    trainer = Trainer(
        model=model,
        args=training_args,
        train_dataset=train_ds,
        eval_dataset=eval_ds,
    )

    logger.info("Starting NER fine-tuning...")
    trainer.train()

    logger.info(f"Saving model to {MODEL_DIR}")
    model.save_pretrained(str(MODEL_DIR))
    processor.save_pretrained(str(MODEL_DIR))
    logger.info("NER training complete!")


if __name__ == "__main__":
    main()
