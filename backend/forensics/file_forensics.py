from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List

import pikepdf


def inspect_pdf(pdf_path: str | Path, metadata: Dict[str, Any]) -> List[Dict[str, Any]]:
    flags: List[Dict[str, Any]] = []
    try:
        with pikepdf.Pdf.open(str(pdf_path)) as pdf:
            producer = str(metadata.get("Producer", ""))
            creator = str(metadata.get("Creator", ""))

            suspicious_producers = ["Adobe Acrobat Pro", "Photoshop", "Illustrator", "GIMP", "iLovePDF", "Canva", "PDFelement"]
            for token in suspicious_producers:
                if token.lower() in producer.lower() or token.lower() in creator.lower():
                    flags.append({"layer": "File Forensics", "finding": f"Suspicious producer or creator metadata: {producer} / {creator}", "severity": "high", "score": 60})

            create_date = str(metadata.get("CreateDate", ""))
            modify_date = str(metadata.get("ModifyDate", ""))
            if create_date and modify_date and create_date != modify_date:
                flags.append({"layer": "File Forensics", "finding": f"Modified after creation (created {create_date}, modified {modify_date})", "severity": "medium", "score": 30})

            for page_index, page in enumerate(pdf.pages):
                resources = page.get("/Resources")
                if not isinstance(resources, pikepdf.Dictionary):
                    continue
                xobjects = resources.get("/XObject")
                if not isinstance(xobjects, pikepdf.Dictionary):
                    continue
                image_count = 0
                for _, obj in xobjects.items():
                    if isinstance(obj, pikepdf.Stream) and obj.get("/Subtype") == "/Image":
                        image_count += 1
                if image_count > 3:
                    flags.append({"layer": "File Forensics", "finding": f"Multiple image layers on page {page_index + 1} ({image_count} images). Possible overlay tampering.", "severity": "medium", "score": 40})
    except Exception:
        return flags
    return flags


def _extract_page_fonts(page) -> set:
    """Extract font names from a pikepdf page."""
    fonts = set()
    try:
        resources = page.get("/Resources")
        if not isinstance(resources, pikepdf.Dictionary):
            return fonts
        font_dict = resources.get("/Font")
        if not isinstance(font_dict, pikepdf.Dictionary):
            return fonts
        for font_name, font_obj in font_dict.items():
            if isinstance(font_obj, pikepdf.Dictionary):
                base_font = str(font_obj.get("/BaseFont", ""))
                if base_font:
                    # Strip subset prefix (e.g., ABCDEF+TimesNewRoman → TimesNewRoman)
                    if "+" in base_font:
                        base_font = base_font.split("+", 1)[1]
                    fonts.add(base_font)
            elif isinstance(font_obj, pikepdf.Stream):
                base_font = str(font_obj.get("/BaseFont", ""))
                if base_font:
                    if "+" in base_font:
                        base_font = base_font.split("+", 1)[1]
                    fonts.add(base_font)
    except Exception:
        pass
    return fonts


def inspect_pdf_fonts(pdf_path: str | Path) -> List[Dict[str, Any]]:
    """
    Check font consistency across PDF pages.
    
    Inconsistent fonts across pages — especially when page N uses fonts
    not present on page 1 — is a strong indicator that text was pasted
    or pages were spliced from different source documents.
    """
    flags: List[Dict[str, Any]] = []
    try:
        with pikepdf.Pdf.open(str(pdf_path)) as pdf:

            if len(pdf.pages) < 2:
                return flags

            page_fonts = []
            for page in pdf.pages:
                page_fonts.append(_extract_page_fonts(page))

            if not page_fonts or not page_fonts[0]:
                return flags

            # Reference: fonts on first page
            reference_fonts = page_fonts[0]
            mismatched_pages = []

            for i, fonts in enumerate(page_fonts[1:], start=2):
                if not fonts:
                    continue
                # Fonts on this page that are NOT on page 1
                extra_fonts = fonts - reference_fonts
                if extra_fonts:
                    mismatched_pages.append({
                        "page": i,
                        "extra_fonts": list(extra_fonts),
                    })

            if mismatched_pages:
                page_nums = [str(m["page"]) for m in mismatched_pages[:5]]
                extra = set()
                for m in mismatched_pages:
                    extra.update(m["extra_fonts"])
                flags.append({
                    "layer": "File Forensics",
                    "finding": f"Font inconsistency: pages {', '.join(page_nums)} use fonts not present on page 1 ({', '.join(list(extra)[:3])}). Text may have been pasted from a different document.",
                    "severity": "medium",
                    "score": 45,
                })

            # Check total unique font count — genuine docs usually have 2-5 fonts
            all_fonts = set()
            for fonts in page_fonts:
                all_fonts.update(fonts)
            if len(all_fonts) > 8:
                flags.append({
                    "layer": "File Forensics",
                    "finding": f"Excessive font variety: {len(all_fonts)} unique fonts across {len(pdf.pages)} pages. Genuine financial documents typically use 2-5 fonts.",
                    "severity": "low",
                    "score": 20,
                })

    except Exception:
        pass
    return flags


def inspect_office_file(file_path: str | Path, metadata: Dict[str, Any]) -> List[Dict[str, Any]]:
    flags: List[Dict[str, Any]] = []
    revision = metadata.get("revision", 0)
    if revision and str(revision).isdigit() and int(revision) > 3:
        flags.append({"layer": "File Forensics", "finding": f"High revision count ({revision}). Document edited multiple times.", "severity": "low", "score": 20})

    author = metadata.get("author") or metadata.get("creator")
    modified_by = metadata.get("last_modified_by")
    if author and modified_by and author != modified_by:
        flags.append({"layer": "File Forensics", "finding": f"Last modified by ({modified_by}) does not match creator ({author}).", "severity": "medium", "score": 40})

    return flags
