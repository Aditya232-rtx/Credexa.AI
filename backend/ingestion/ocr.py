from __future__ import annotations

import os
import re
import tempfile
from pathlib import Path
from typing import Any, Dict, List

import fitz
import pdfplumber
import numpy as np
from PIL import Image

from loguru import logger

try:
    from rapidocr_onnxruntime import RapidOCR
    ocr_engine = RapidOCR()
except ImportError:
    ocr_engine = None


def _has_devanagari(text: str) -> bool:
    devanagari_range = range(0x0900, 0x0980)
    return any(ord(c) in devanagari_range for c in text)


def _run_ocr(image: Image.Image) -> tuple[List[str], List[List[int]]]:
    words: List[str] = []
    boxes: List[List[int]] = []
    if ocr_engine is None:
        return words, boxes

    img_array = np.array(image)
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


def _run_sarvam_ocr(image_path: str) -> tuple[List[str], List[List[int]]]:
    try:
        from services.sarvam_service import sarvam_extract_text
        with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as tf:
            clean_path = tf.name
        try:
            Image.open(image_path).convert("RGB").save(clean_path, "JPEG", quality=95)
            text = sarvam_extract_text(clean_path)
        finally:
            if os.path.exists(clean_path):
                os.remove(clean_path)
        if text:
            # Strip base64-embedded images from markdown output
            text = re.sub(r"!\[.*?\]\(data:image/[^;]+;base64,[^)]+\)", "", text)
            # Collapse whitespace and split into lines/words
            lines = [l.strip() for l in text.replace("\r\n", "\n").split("\n") if l.strip()]
            words = []
            for line in lines:
                words.extend(w.strip() for w in line.split() if w.strip())
            boxes = [[0, 0, 0, 0]] * len(words)
            return words, boxes
    except Exception as e:
        logger.debug(f"Sarvam OCR unavailable: {e}")
    return [], []


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
                words_list, boxes_list = _run_sarvam_ocr(str(pdf_path))
                if not words_list:
                    words_list, boxes_list = _run_ocr(image)
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

            temp_img_path = tempfile.mktemp(suffix=".jpg")
            image.save(temp_img_path, format="JPEG")

            results.append({
                "page_num": index + 1,
                "image_path": temp_img_path,
                "words": extracted_words,
                "boxes": extracted_boxes,
                "labels": ["O"] * len(extracted_words),
            })
    return results


def extract_from_image(image_path: str | Path) -> List[Dict[str, Any]]:
    image = Image.open(str(image_path)).convert("RGB")
    words, boxes = _run_sarvam_ocr(str(image_path))
    if not words:
        words, boxes = _run_ocr(image)

    temp_img_path = tempfile.mktemp(suffix=".jpg")
    image.save(temp_img_path, format="JPEG")

    return [{
        "page_num": 1,
        "image_path": temp_img_path,
        "words": words,
        "boxes": boxes,
        "labels": ["O"] * len(words),
    }]
