from __future__ import annotations

import gc
import threading
from collections import OrderedDict
from dataclasses import dataclass, field
from typing import Any, Callable

import torch

from loguru import logger

try:
    import psutil
except ImportError:
    psutil = None


@dataclass
class _Entry:
    model: Any
    size_gb: float
    group: str

    def __repr__(self):
        return f"_Entry(group={self.group}, size_gb={self.size_gb})"


class ModelRegistry:
    BUDGET_GB = 11.5
    FORENSICS_CAP = 4
    _EXCLUSIVE = frozenset()  # No exclusive groups since VLM is now API-based

    def __init__(self):
        self._models: OrderedDict[str, _Entry] = OrderedDict()
        self._lock = threading.Lock()

    def get(self, key: str, loader: Callable, size_gb: float, group: str = "evictable") -> Any:
        with self._lock:
            if key in self._models:
                self._models.move_to_end(key)
                return self._models[key].model

            logger.debug(f"Registry loading: {key} ({size_gb} GB, group={group})")

            if group in self._EXCLUSIVE:
                self._evict_exclusive_conflict(group)

            if group == "forensics":
                self._enforce_forensics_cap()

            self._evict_until_budget(size_gb)

            if psutil and psutil.virtual_memory().percent > 80:
                self._evict_lru(n=2)

            model = loader()
            self._models[key] = _Entry(model=model, size_gb=size_gb, group=group)
            logger.debug(f"Registry loaded: {key} ({len(self._models)} models in pool)")
            return model

    def get_if_loaded(self, key: str) -> Any:
        entry = self._models.get(key)
        if entry is not None:
            self._models.move_to_end(key)
            return entry.model
        return None

    def drop(self, key: str) -> None:
        with self._lock:
            self._drop(key)

    def evict_group(self, group: str) -> None:
        with self._lock:
            victims = [k for k, v in self._models.items() if v.group == group]
            for k in victims:
                self._drop(k)

    def _evict_exclusive_conflict(self, new_group: str) -> None:
        conflict = self._EXCLUSIVE - {new_group}
        victims = [k for k, v in self._models.items() if v.group in conflict]
        for k in victims:
            logger.info(f"Evicting {k} ({self._models[k].group}) — exclusive conflict with {new_group}")
            self._drop(k)

    def _enforce_forensics_cap(self) -> None:
        forensics_keys = [k for k, v in self._models.items() if v.group == "forensics"]
        while len(forensics_keys) >= self.FORENSICS_CAP:
            victim = forensics_keys.pop(0)
            logger.info(f"Evicting {victim} — forensics cap ({self.FORENSICS_CAP})")
            self._drop(victim)

    def _evict_until_budget(self, needed_gb: float) -> None:
        evictable = [k for k, v in self._models.items() if v.group not in ("pinned",)]
        for k in evictable:
            if self._used_gb() + needed_gb <= self.BUDGET_GB:
                break
            logger.info(f"Evicting {k} — budget ({self._used_gb():.1f} + {needed_gb} > {self.BUDGET_GB})")
            self._drop(k)

    def _evict_lru(self, n: int) -> None:
        evictable = [k for k, v in self._models.items() if v.group not in ("pinned",)]
        for k in evictable[:n]:
            logger.info(f"Evicting {k} — safety evict ({n})")
            self._drop(k)

    def _drop(self, key: str) -> None:
        entry = self._models.pop(key, None)
        if entry is not None:
            logger.debug(f"Registry dropped: {key} ({entry.group}, {entry.size_gb} GB)")
            del entry
        gc.collect()
        if torch.backends.mps.is_available():
            torch.mps.empty_cache()

    def _used_gb(self) -> float:
        return sum(e.size_gb for e in self._models.values())

    @property
    def summary(self) -> str:
        parts = [f"{k}: {v.group} {v.size_gb}GB" for k, v in self._models.items()]
        return f"Registry [{self._used_gb():.1f}/{self.BUDGET_GB} GB]: " + ", ".join(parts)


registry = ModelRegistry()
