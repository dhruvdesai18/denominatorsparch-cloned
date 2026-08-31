import hashlib
import json
from pathlib import Path
from typing import Any


class CacheManager:
    """Disk-backed cache for expensive/LLM agent outputs.

    Every LLM call in the pipeline must be cached so demo day can replay
    the full workflow offline at zero API cost.
    """

    def __init__(self, cache_dir: str | Path = "cache"):
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)

    def _key_to_path(self, key: str) -> Path:
        digest = hashlib.sha256(key.encode("utf-8")).hexdigest()
        return self.cache_dir / f"{digest}.json"

    def get(self, key: str) -> Any | None:
        path = self._key_to_path(key)
        if not path.exists():
            return None
        with path.open("r", encoding="utf-8") as f:
            return json.load(f)

    def set(self, key: str, value: Any) -> None:
        path = self._key_to_path(key)
        with path.open("w", encoding="utf-8") as f:
            json.dump(value, f, indent=2)

    def has(self, key: str) -> bool:
        return self._key_to_path(key).exists()

    def clear(self) -> None:
        for path in self.cache_dir.glob("*.json"):
            path.unlink()
