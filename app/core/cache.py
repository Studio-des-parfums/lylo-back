import threading
import time
from typing import Any


class TTLCache:
    """
    Cache mémoire thread-safe avec expiration temporelle (TTL) et politique d'éviction LRU/FIFO.
    Zéro dépendance externe, temps d'accès sub-milliseconde.
    """

    def __init__(self, maxsize: int = 512, default_ttl: float = 60.0):
        self.maxsize = maxsize
        self.default_ttl = default_ttl
        self._cache: dict[str, tuple[float, Any]] = {}
        self._lock = threading.Lock()

    def get(self, key: str) -> Any:
        with self._lock:
            now = time.monotonic()
            entry = self._cache.get(key)
            if entry is not None:
                exp, val = entry
                if exp > now:
                    return val
                del self._cache[key]
            return None

    def set(self, key: str, value: Any, ttl: float | None = None) -> None:
        with self._lock:
            now = time.monotonic()
            if len(self._cache) >= self.maxsize:
                # Purge des entrées expirées
                expired = [k for k, (exp, _) in self._cache.items() if exp <= now]
                for k in expired:
                    del self._cache[k]
            if len(self._cache) >= self.maxsize:
                # Éviction de la plus ancienne entrée insérée
                oldest_key = next(iter(self._cache))
                del self._cache[oldest_key]
            exp = now + (ttl if ttl is not None else self.default_ttl)
            self._cache[key] = (exp, value)

    def delete(self, key: str) -> None:
        with self._lock:
            self._cache.pop(key, None)

    def clear(self) -> None:
        with self._lock:
            self._cache.clear()

    def invalidate_prefix(self, prefix: str) -> None:
        with self._lock:
            for k in list(self._cache.keys()):
                if k.startswith(prefix):
                    del self._cache[k]

    def size(self) -> int:
        with self._lock:
            return len(self._cache)


# Instance globale dédiée aux routes d'analyse (TTL par défaut : 60 secondes, max 256 clés)
analytics_cache = TTLCache(maxsize=256, default_ttl=60.0)
