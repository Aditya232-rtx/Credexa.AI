from __future__ import annotations

import torch


def get_device() -> str:
    if torch.cuda.is_available():
        return "cuda"
    if hasattr(torch.backends, "mps") and torch.backends.mps.is_available():
        return "mps"
    return "cpu"


def get_device_map() -> dict:
    device = get_device()
    if device == "cpu":
        return {"map_location": "cpu"}
    return {}


def set_quantized_engine() -> bool:
    try:
        import torch
        if get_device() == "cpu":
            torch.backends.quantized.engine = "qnnpack"
        return True
    except Exception:
        return False
