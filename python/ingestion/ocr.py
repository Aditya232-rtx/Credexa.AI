from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List

import fitz
import pdfplumber
import pytesseract
from PIL import Image


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

            results.append({"page_num": index + 1, "image": image, "words": [word["text"] for word in words], "boxes": [word["box"] for word in words]})
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
    return [{"page_num": 1, "image": image, "words": words, "boxes": boxes}]
