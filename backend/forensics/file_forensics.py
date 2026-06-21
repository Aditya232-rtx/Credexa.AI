from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List

import pikepdf


def inspect_pdf(pdf_path: str | Path, metadata: Dict[str, Any]) -> List[Dict[str, Any]]:
    flags: List[Dict[str, Any]] = []
    try:
        pdf = pikepdf.Pdf.open(str(pdf_path))
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
