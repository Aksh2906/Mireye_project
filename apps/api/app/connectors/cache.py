from __future__ import annotations

import time
from copy import deepcopy
from typing import Any


class EvidenceCache:
    """Small process cache; keys include coordinates, requested fields, and dataset vintage."""

    def __init__(self, ttl_seconds: int = 3600) -> None:
        self.ttl = ttl_seconds
        self._values: dict[str, tuple[float, Any]] = {}

    def get(self, key: str) -> Any | None:
        item = self._values.get(key)
        if not item or item[0] < time.monotonic():
            self._values.pop(key, None)
            return None
        return deepcopy(item[1])

    def set(self, key: str, value: Any) -> None:
        self._values[key] = (time.monotonic() + self.ttl, deepcopy(value))


geocode_cache = EvidenceCache(ttl_seconds=86_400)
provider_cache = EvidenceCache(ttl_seconds=3_600)
