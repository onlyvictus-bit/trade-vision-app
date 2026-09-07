"""Canonical, lossless JSON plus a strict request boundary; no float coercion."""
from __future__ import annotations

from dataclasses import MISSING, fields, is_dataclass
from datetime import datetime, timezone
from decimal import Decimal
from enum import Enum
import hashlib
import json
from typing import Any, get_args, get_origin, get_type_hints

from .models import ContractError, Request

MAX_PAYLOAD_BYTES = 1_000_000


def primitive(value: Any) -> Any:
    if isinstance(value, Decimal):
        if not value.is_finite():
            raise ContractError("nonfinite serialization")
        out = format(value, "f")
        if "." in out:
            out = out.rstrip("0").rstrip(".")
        return "0" if value == 0 else out
    if isinstance(value, datetime):
        return value.astimezone(timezone.utc).isoformat(timespec="microseconds")
    if isinstance(value, Enum):
        return value.value
    if is_dataclass(value) and not isinstance(value, type):
        return {f.name: primitive(getattr(value, f.name)) for f in fields(value)}
    if isinstance(value, (tuple, list)):
        return [primitive(x) for x in value]
    if isinstance(value, dict):
        if not all(isinstance(k, str) for k in value):
            raise ContractError("JSON keys must be strings")
        return {k: primitive(v) for k, v in value.items()}
    if value is None or type(value) in (str, int, bool):
        return value
    raise ContractError(f"unsupported serialization type: {type(value).__name__}")


def canonical_json(value: Any) -> str:
    return json.dumps(primitive(value), sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def fingerprint(value: Any) -> str:
    return hashlib.sha256(canonical_json(value).encode("utf-8")).hexdigest()


def _reject_constant(value: str) -> None:
    raise ContractError(f"nonfinite JSON number: {value}")


def _unique_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for k, v in pairs:
        if k in out:
            raise ContractError("duplicate JSON field")
        out[k] = v
    return out


def _decode(cls: type, value: Any, depth: int = 0) -> Any:
    if depth > 16:
        raise ContractError("JSON nesting exceeds limit")
    if cls is Decimal:
        if isinstance(value, Decimal):
            return value
        if type(value) in (str, int):
            if len(str(value)) > 80:
                raise ContractError("numeric text too long")
            return Decimal(str(value))
        raise ContractError("Decimal expects decimal text or a JSON number")
    if cls is datetime:
        if not isinstance(value, str) or len(value) > 64:
            raise ContractError("ISO timestamp required")
        return datetime.fromisoformat(value)
    if cls in (str, bool, int):
        if type(value) is not cls:
            raise ContractError(f"{cls.__name__} required")
        return value
    if isinstance(cls, type) and issubclass(cls, Enum):
        return cls(value)
    if get_origin(cls) is tuple:
        if not isinstance(value, list):
            raise ContractError("JSON array required")
        if len(value) > 128:
            raise ContractError("JSON collection exceeds limit")
        element_type = get_args(cls)[0]
        return tuple(_decode(element_type, x, depth + 1) for x in value)
    if isinstance(cls, type) and is_dataclass(cls):
        if not isinstance(value, dict):
            raise ContractError("JSON object required")
        fs = {f.name: f for f in fields(cls)}
        if set(value) - set(fs):
            raise ContractError(f"unknown fields in {cls.__name__}")
        missing = [f.name for f in fs.values()
                   if f.name not in value and f.default is MISSING and f.default_factory is MISSING]
        if missing:
            raise ContractError(f"missing required fields in {cls.__name__}: {', '.join(missing)}")
        hints = get_type_hints(cls)
        return cls(**{name: _decode(hints[name], val, depth + 1) for name, val in value.items()})
    raise ContractError("unsupported schema type")


def decode_request(payload: str) -> Request:
    if not isinstance(payload, str) or len(payload.encode("utf-8")) > MAX_PAYLOAD_BYTES:
        raise ContractError("payload must be bounded JSON text")
    try:
        parsed = json.loads(payload, parse_float=Decimal, parse_constant=_reject_constant,
                            object_pairs_hook=_unique_object)
        return _decode(Request, parsed)
    except (ValueError, TypeError, ArithmeticError, RecursionError, OverflowError) as exc:
        if isinstance(exc, ContractError):
            raise
        raise ContractError("invalid request JSON or schema") from exc
