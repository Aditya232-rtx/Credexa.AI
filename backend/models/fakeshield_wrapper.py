from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List

from loguru import logger


def run_fakeshield(image) -> List[Dict[str, Any]]:
    flags: List[Dict[str, Any]] = []

    try:
        from models.trufor_wrapper import run_trufor
        trufor_flags = run_trufor(image)
        flags.extend(trufor_flags)
        if trufor_flags:
            logger.info(f"TruFor returned {len(trufor_flags)} flags")
    except Exception as e:
        logger.debug(f"TruFor skipped: {e}")

    try:
        from models.mantranet_wrapper import run_mantranet
        mantranet_flags = run_mantranet(image)
        flags.extend(mantranet_flags)
        if mantranet_flags:
            logger.info(f"ManTraNet returned {len(mantranet_flags)} flags")
    except Exception as e:
        logger.debug(f"ManTraNet skipped: {e}")

    return flags
