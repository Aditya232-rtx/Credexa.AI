from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List

import fitz
import pdfplumber
import pytesseract
from PIL import Image

try:
    import torch
    from transformers import LayoutLMv3Processor, LayoutLMv3ForTokenClassification
    LAYOUTLM_AVAILABLE = True
except ImportError:
    LAYOUTLM_AVAILABLE = False

_processor = None
_model = None

def _get_layoutlmv3():
    global _processor, _model
    if _model is None and LAYOUTLM_AVAILABLE:
        # Load the FUNSD fine-tuned LayoutLMv3 model for Key-Value (Header, Question, Answer) extraction
        _processor = LayoutLMv3Processor.from_pretrained("nielsr/layoutlmv3-finetuned-funsd", apply_ocr=False)
        _model = LayoutLMv3ForTokenClassification.from_pretrained("nielsr/layoutlmv3-finetuned-funsd")
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
        
        predictions = outputs.logits.argmax(-1).squeeze().tolist()
        
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
        print(f"LayoutLMv3 Error: {e}")
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


def extract_text_and_boxes_from_pdf(pdf_path: str | Path) -> List[Dict[str, Any]]:
    results: List[Dict[str, Any]] = []
    doc = fitz.open(str(pdf_path))
    with pdfplumber.open(str(pdf_path)) as pdf:
        for index, page in enumerate(pdf.pages):
            pixmap = doc[index].get_pixmap(matrix=fitz.Matrix(2, 2), alpha=False)
            image = Image.frombytes("RGB", (pixmap.width, pixmap.height), pixmap.samples)
            words = page.extract_words() or []

            if not words:
                ocr_data = pytesseract.image_to_data(image, output_type=pytesseract.Output.DICT)
                words = []
                for offset in range(len(ocr_data["text"])):
                    text = ocr_data["text"][offset].strip()
                    if not text:
                        continue
                    left = ocr_data["left"][offset]
                    top = ocr_data["top"][offset]
                    width = ocr_data["width"][offset]
                    height = ocr_data["height"][offset]
                    words.append({"text": text, "box": [left, top, left + width, top + height]})
            else:
                words = _normalize_words(words, image, page.width, page.height)

            extracted_words = [word["text"] for word in words]
            extracted_boxes = [word["box"] for word in words]
            
            # Apply LayoutLMv3 Semantic Labelling
            labels = _apply_layoutlmv3(image, extracted_words, extracted_boxes)

            results.append({
                "page_num": index + 1, 
                "image": image, 
                "words": extracted_words, 
                "boxes": extracted_boxes,
                "labels": labels
            })
    return results


def extract_from_image(image_path: str | Path) -> List[Dict[str, Any]]:
    image = Image.open(str(image_path)).convert("RGB")
    ocr_data = pytesseract.image_to_data(image, output_type=pytesseract.Output.DICT)
    words: List[str] = []
    boxes: List[List[int]] = []
    for index in range(len(ocr_data["text"])):
        text = ocr_data["text"][index].strip()
        if not text:
            continue
        left = ocr_data["left"][index]
        top = ocr_data["top"][index]
        width = ocr_data["width"][index]
        height = ocr_data["height"][index]
        words.append(text)
        boxes.append([left, top, left + width, top + height])
        
    # Apply LayoutLMv3 Semantic Labelling
    labels = _apply_layoutlmv3(image, words, boxes)
    
    return [{
        "page_num": 1, 
        "image": image, 
        "words": words, 
        "boxes": boxes,
        "labels": labels
    }]
