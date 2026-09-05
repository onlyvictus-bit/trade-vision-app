from __future__ import annotations

import json
import os
import time
from collections.abc import Callable
from contextlib import contextmanager
from pathlib import Path
from threading import RLock
from typing import TypeVar


T = TypeVar("T")
_PROCESS_LOCK = RLock()


class AtomicJsonStoreError(RuntimeError):
    """Base error for the fail-closed local JSON persistence boundary."""


class AtomicJsonCorruptionError(AtomicJsonStoreError):
    """Raised when persisted JSON is malformed or has the wrong root shape."""


class AtomicJsonStoreBusyError(AtomicJsonStoreError):
    """Raised when another process holds the store lock beyond the budget."""


def load_record_map(path: Path) -> dict[str, dict]:
    with _PROCESS_LOCK, _exclusive_file_lock(path):
        return _read_record_map(path, allow_recovery=True)


def update_record_map(
    path: Path,
    update: Callable[[dict[str, dict]], tuple[dict[str, dict], T]],
) -> T:
    with _PROCESS_LOCK, _exclusive_file_lock(path):
        records = _read_record_map(path, allow_recovery=True)
        updated, result = update(dict(records))
        _validate_record_map(updated, path)
        _atomic_write(path, updated)
        return result


def replace_record_map(path: Path, records: dict[str, dict]) -> None:
    with _PROCESS_LOCK, _exclusive_file_lock(path):
        _validate_record_map(records, path)
        _atomic_write(path, records)


def store_monitor(path: Path) -> dict[str, object]:
    try:
        records = load_record_map(path)
    except AtomicJsonStoreError as exc:
        return {
            "path": str(path),
            "exists": path.exists(),
            "integrity": "CORRUPT",
            "record_count": 0,
            "error": str(exc),
        }
    return {
        "path": str(path),
        "exists": path.exists(),
        "integrity": "PASS",
        "record_count": len(records),
        "error": None,
    }


def _read_record_map(path: Path, *, allow_recovery: bool) -> dict[str, dict]:
    temporary = _temporary_path(path)
    if not path.exists():
        if allow_recovery and temporary.exists():
            recovered = _decode_record_map(temporary)
            path.parent.mkdir(parents=True, exist_ok=True)
            temporary.replace(path)
            return recovered
        return {}
    return _decode_record_map(path)


def _decode_record_map(path: Path) -> dict[str, dict]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise AtomicJsonCorruptionError(
            f"Atomic JSON store {path} is unreadable; persistence is blocked."
        ) from exc
    _validate_record_map(payload, path)
    return payload


def _validate_record_map(payload: object, path: Path) -> None:
    if not isinstance(payload, dict):
        raise AtomicJsonCorruptionError(
            f"Atomic JSON store {path} must contain an object keyed by record id."
        )
    if not all(isinstance(key, str) and isinstance(value, dict) for key, value in payload.items()):
        raise AtomicJsonCorruptionError(
            f"Atomic JSON store {path} contains an invalid record map."
        )


def _atomic_write(path: Path, records: dict[str, dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = _temporary_path(path)
    try:
        with temporary.open("w", encoding="utf-8", newline="\n") as handle:
            json.dump(
                records,
                handle,
                sort_keys=True,
                indent=2,
                ensure_ascii=True,
                allow_nan=False,
            )
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        temporary.replace(path)
    except (OSError, ValueError, TypeError) as exc:
        raise AtomicJsonStoreError(
            f"Atomic JSON store {path} could not be written safely."
        ) from exc


def _temporary_path(path: Path) -> Path:
    return path.with_suffix(path.suffix + ".tmp")


@contextmanager
def _exclusive_file_lock(
    path: Path,
    *,
    timeout_seconds: float = 5.0,
    poll_seconds: float = 0.01,
):
    path.parent.mkdir(parents=True, exist_ok=True)
    lock_path = path.with_suffix(path.suffix + ".lock")
    deadline = time.monotonic() + timeout_seconds
    descriptor: int | None = None
    while descriptor is None:
        try:
            descriptor = os.open(
                lock_path,
                os.O_CREAT | os.O_EXCL | os.O_WRONLY,
            )
            os.write(
                descriptor,
                f"pid={os.getpid()} acquired_ns={time.time_ns()}\n".encode("ascii"),
            )
        except FileExistsError as exc:
            if time.monotonic() >= deadline:
                raise AtomicJsonStoreBusyError(
                    f"Atomic JSON store {path} is busy; no write was attempted."
                ) from exc
            time.sleep(poll_seconds)
    try:
        yield
    finally:
        if descriptor is not None:
            os.close(descriptor)
        try:
            lock_path.unlink()
        except FileNotFoundError:
            pass
