from __future__ import annotations

from pathlib import Path
from typing import Any, Dict

from .metadata import get_exif_metadata
from .ocr import extract_from_image, extract_text_and_boxes_from_pdf
from .office_reader import read_office_file

IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".tif", ".tiff", ".bmp", ".webp"}
PDF_EXTENSIONS = {".pdf"}
OFFICE_EXTENSIONS = {".docx", ".xlsx", ".csv"}


def read_document(file_path: str | Path) -> Dict[str, Any]:
    path = Path(file_path)
    suffix = path.suffix.lower()

    if suffix in PDF_EXTENSIONS:
        pages = extract_text_and_boxes_from_pdf(str(path))
        text = "\n".join(" ".join(page.get("words", [])) for page in pages)
        return {
            "file_path": str(path),
            "file_type": suffix,
            "text": text,
            "tables": [],
            "pages": pages,
            "metadata": get_exif_metadata(str(path)),
        }

    if suffix in IMAGE_EXTENSIONS:
        pages = extract_from_image(str(path))
        text = "\n".join(" ".join(page.get("words", [])) for page in pages)
        return {
            "file_path": str(path),
            "file_type": suffix,
            "text": text,
            "tables": [],
            "pages": pages,
            "metadata": get_exif_metadata(str(path)),
        }

    if suffix in OFFICE_EXTENSIONS:
        office = read_office_file(str(path))
        return {
            "file_path": str(path),
            "file_type": suffix,
            "text": office.get("text", ""),
            "tables": office.get("tables", []),
            "pages": [],
            "metadata": office.get("metadata", {}),
        }

    return {
        "file_path": str(path),
        "file_type": suffix or "unknown",
        "text": "",
        "tables": [],
        "pages": [],
        "metadata": get_exif_metadata(str(path)),
    }
