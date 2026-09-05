from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timezone
from hashlib import sha256
from threading import RLock
from time import monotonic
from typing import Any, Callable


JARVIS_EVIDENCE_CACHE_VERSION = "jarvis-evidence-cache.v1.28"
DEFAULT_EVIDENCE_CACHE_TTL_SECONDS = 15.0

_LOCK = RLock()
_CACHE: dict[str, dict[str, Any]] = {}


def build_evidence_cache_key(*, symbol: str, timeframe: str, rows: int, position: str, stale_after_seconds: int) -> str:
    raw = f"{symbol.upper()}|{timeframe}|{rows}|{position}|{stale_after_seconds}"
    return sha256(raw.encode("utf-8")).hexdigest()


def clear_jarvis_evidence_cache() -> None:
    with _LOCK:
        _CACHE.clear()


def get_or_build_cached_evidence_bundle(
    *,
    cache_key: str,
    builder: Callable[[], dict[str, Any]],
    ttl_seconds: float = DEFAULT_EVIDENCE_CACHE_TTL_SECONDS,
) -> dict[str, Any]:
    now = monotonic()
    with _LOCK:
        cached = _CACHE.get(cache_key)
        if cached:
            age_seconds = now - float(cached["created_monotonic"])
            if age_seconds <= ttl_seconds:
                bundle = deepcopy(cached["bundle"])
                bundle["cache"] = _cache_meta(
                    cache_key=cache_key,
                    status="hit",
                    age_seconds=age_seconds,
                    ttl_seconds=ttl_seconds,
                    created_at=cached["created_at"],
                )
                return bundle

        bundle = builder()
        created_at = datetime.now(timezone.utc).isoformat()
        _CACHE[cache_key] = {
            "created_monotonic": now,
            "created_at": created_at,
            "bundle": deepcopy(bundle),
        }
        bundle = deepcopy(bundle)
        bundle["cache"] = _cache_meta(
            cache_key=cache_key,
            status="miss",
            age_seconds=0.0,
            ttl_seconds=ttl_seconds,
            created_at=created_at,
        )
        return bundle


def build_evidence_cache_report(bundle: dict[str, Any]) -> dict[str, Any]:
    meta = dict(bundle.get("cache", {}))
    return {
        "cache_version": JARVIS_EVIDENCE_CACHE_VERSION,
        "cache_status": meta.get("cache_status", "uncached"),
        "cache_key_hash": meta.get("cache_key_hash"),
        "cache_age_seconds": meta.get("cache_age_seconds", 0.0),
        "cache_ttl_seconds": meta.get("cache_ttl_seconds", DEFAULT_EVIDENCE_CACHE_TTL_SECONDS),
        "cache_fresh": bool(meta.get("cache_fresh", False)),
        "cached_at": meta.get("cached_at"),
        "assembly_version": bundle.get("assembly_version"),
        "symbol": bundle.get("symbol"),
        "timeframe": bundle.get("timeframe"),
        "operator_message": (
            "Jarvis evidence cache is research-only. Cache hits may speed the decision room, "
            "but stale cache state must reduce confidence or show WAIT."
        ),
        "trade_allowed": False,
        "order_routing_enabled": False,
        "live_trading_blocked": True,
    }


def _cache_meta(*, cache_key: str, status: str, age_seconds: float, ttl_seconds: float, created_at: str) -> dict[str, Any]:
    return {
        "cache_version": JARVIS_EVIDENCE_CACHE_VERSION,
        "cache_status": status,
        "cache_key_hash": cache_key,
        "cache_age_seconds": round(age_seconds, 3),
        "cache_ttl_seconds": ttl_seconds,
        "cache_fresh": age_seconds <= ttl_seconds,
        "cached_at": created_at,
    }
