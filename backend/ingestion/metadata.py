from __future__ import annotations

import json
import subprocess
from pathlib import Path
from typing import Any, Dict


def get_exif_metadata(file_path: str | Path) -> Dict[str, Any]:
    """Extract file metadata using ExifTool when available."""
    try:
        result = subprocess.run(["exiftool", "-j", str(file_path)], capture_output=True, text=True, check=True)
        data = json.loads(result.stdout or "[]")
        return data[0] if data else {}
    except Exception:
        return {}
