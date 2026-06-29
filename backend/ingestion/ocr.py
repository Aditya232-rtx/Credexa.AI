from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List

import fitz
import pdfplumber
import numpy as np
from PIL import Image
import tempfile

from loguru import logger

try:
    from rapidocr_onnxruntime import RapidOCR
    ocr_engine = RapidOCR()
except ImportError:
    ocr_engine = None

try:
    import torch
    from transformers import LayoutLMv3Processor, LayoutLMv3ForTokenClassification
    from utils.device import get_device, set_quantized_engine
    LAYOUTLM_AVAILABLE = True
except ImportError:
    LAYOUTLM_AVAILABLE = False

_processor = None
_model = None

def _get_layoutlmv3():
    global _processor, _model
    if _model is None and LAYOUTLM_AVAILABLE:
        import os
        set_quantized_engine()
        _processor = LayoutLMv3Processor.from_pretrained("nielsr/layoutlmv3-finetuned-funsd", apply_ocr=False)
        device = get_device()
        quantized_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "layoutlmv3_quantized.pt"))
        if os.path.exists(quantized_path):
            _model = torch.load(quantized_path, map_location=device, weights_only=True)
        else:
            _model = LayoutLMv3ForTokenClassification.from_pretrained("nielsr/layoutlmv3-finetuned-funsd")
        _model.to(device)
        _model.eval()
    return _processor, _model

def _apply_layoutlmv3(image: Image.Image, words: List[str], boxes: List[List[int]]) -> List[str]:
    processor, model = _get_layoutlmv3()
    if model is None or not words:
        return ["O"] * len(words)
        
    # LayoutLMv3 requires boxes to be in 0-1000 format
    width, height = image.size
    normalized_boxes = []
    for box in boxes:
        normalized_boxes.append([
            max(0, min(1000, int(1000 * (box[0] / width)))),
            max(0, min(1000, int(1000 * (box[1] / height)))),
            max(0, min(1000, int(1000 * (box[2] / width)))),
            max(0, min(1000, int(1000 * (box[3] / height)))),
        ])
    
    # Truncate to 512 tokens to avoid out of memory / tensor shape errors
    try:
        encoding = processor(image, words, boxes=normalized_boxes, return_tensors="pt", truncation=True, max_length=512)
        with torch.no_grad():
            outputs = model(**encoding)
        
        predictions = outputs.logits.argmax(-1).squeeze()
        if predictions.dim() == 0:
            predictions = predictions.unsqueeze(0)
        predictions = predictions.tolist()
        
        labels = []
        word_ids = encoding.word_ids(0)
        previous_word_idx = None
        
        for idx, word_idx in enumerate(word_ids):
            if word_idx is None:
                continue
            if word_idx != previous_word_idx:
                # Map the first subtoken's prediction to the entire word
                label = model.config.id2label[predictions[idx]] if isinstance(predictions, list) else model.config.id2label[predictions]
                labels.append(label)
            previous_word_idx = word_idx
            
        # If words were truncated, pad the rest with "O"
        while len(labels) < len(words):
            labels.append("O")
            
        return labels[:len(words)]
    except Exception as e:
        logger.warning(f"LayoutLMv3 Error: {e}")
        return ["O"] * len(words)

def _normalize_words(words: List[Dict[str, Any]], image: Image.Image, page_width: float, page_height: float) -> List[Dict[str, Any]]:
    scale_x = image.width / page_width
    scale_y = image.height / page_height
    normalized_words: List[Dict[str, Any]] = []
    for word in words:
        normalized_words.append(
            {
                "text": word["text"],
                "box": [word["x0"] * scale_x, word["top"] * scale_y, word["x1"] * scale_x, word["bottom"] * scale_y],
            }
        )
    return normalized_words

def _run_paddle_ocr(image: Image.Image):
    words = []
    boxes = []
    if ocr_engine is None:
        return words, boxes
        
    img_array = np.array(image)
    # rapidocr can handle RGB numpy arrays
    result, _ = ocr_engine(img_array)
    if result:
        for line in result:
            box, text, score = line
            left = int(min([pt[0] for pt in box]))
            top = int(min([pt[1] for pt in box]))
            right = int(max([pt[0] for pt in box]))
            bottom = int(max([pt[1] for pt in box]))
            words.append(text)
            boxes.append([left, top, right, bottom])
    return words, boxes


def extract_text_and_boxes_from_pdf(pdf_path: str | Path) -> List[Dict[str, Any]]:
    results: List[Dict[str, Any]] = []
    doc = fitz.open(str(pdf_path))
    with pdfplumber.open(str(pdf_path)) as pdf:
        for index, page in enumerate(pdf.pages):
            pixmap = doc[index].get_pixmap(matrix=fitz.Matrix(2, 2), alpha=False)
            image = Image.frombytes("RGB", (pixmap.width, pixmap.height), pixmap.samples)
            words = page.extract_words() or []

            if not words:
                words_list, boxes_list = _run_paddle_ocr(image)
                words = []
                for idx in range(len(words_list)):
                    words.append({
                        "text": words_list[idx],
                        "box": boxes_list[idx]
                    })
            else:
                words = _normalize_words(words, image, page.width, page.height)

            extracted_words = [word["text"] for word in words]
            extracted_boxes = [word["box"] for word in words]
            
            # Apply LayoutLMv3 Semantic Labelling
            labels = _apply_layoutlmv3(image, extracted_words, extracted_boxes)
            
            # Save image to temp file to avoid OOM
            temp_img_path = tempfile.mktemp(suffix=".jpg")
            image.save(temp_img_path, format="JPEG")

            results.append({
                "page_num": index + 1, 
                "image_path": temp_img_path, 
                "words": extracted_words, 
                "boxes": extracted_boxes,
                "labels": labels
            })
    return results


def extract_from_image(image_path: str | Path) -> List[Dict[str, Any]]:
    image = Image.open(str(image_path)).convert("RGB")
    words, boxes = _run_paddle_ocr(image)
        
    # Apply LayoutLMv3 Semantic Labelling
    labels = _apply_layoutlmv3(image, words, boxes)
    
    temp_img_path = tempfile.mktemp(suffix=".jpg")
    image.save(temp_img_path, format="JPEG")
    
    return [{
        "page_num": 1, 
        "image_path": temp_img_path, 
        "words": words, 
        "boxes": boxes,
        "labels": labels
    }]
