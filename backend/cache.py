"""
cache.py - file-based JSON cache with TTL support.
MVP: JSON files on disk keyed by MD5 hash.
Production: swap for Redis with TTL-based expiry.

TTLs per spec:
  - Scraped + extracted profiles: 86400s (24h)
  - SerpAPI search results:       21600s (6h)
  - Embedding vectors:            None (permanent, until source cache expires)
  - User sessions:                never cached
"""
import hashlib
import json
import os
import time
from typing import Any, Optional

CACHE_DIR = os.path.join(os.path.dirname(__file__), ".cache")
os.makedirs(CACHE_DIR, exist_ok=True)

TTL_PROFILES   = 86400     # 24 hours
TTL_SERP       = 21600     # 6 hours
TTL_EMBEDDINGS = None      # permanent


def _key_path(raw_key: str) -> str:
    digest = hashlib.md5(raw_key.encode()).hexdigest()
    return os.path.join(CACHE_DIR, f"{digest}.json")


def get(raw_key: str, ttl_seconds: Optional[int]) -> Optional[Any]:
    """Return cached value if it exists and hasn't expired, else None."""
    path = _key_path(raw_key)
    if not os.path.exists(path):
        return None
    try:
        with open(path, "r", encoding="utf-8") as f:
            record = json.load(f)
        if ttl_seconds is not None:
            age = time.time() - record["timestamp"]
            if age > ttl_seconds:
                os.remove(path)
                return None
        return record["value"]
    except Exception:
        return None


def set(raw_key: str, value: Any) -> None:
    """Write value to cache with current timestamp."""
    path = _key_path(raw_key)
    record = {"timestamp": time.time(), "value": value}
    try:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(record, f, ensure_ascii=False)
    except Exception:
        pass


def invalidate(raw_key: str) -> None:
    path = _key_path(raw_key)
    if os.path.exists(path):
        os.remove(path)