from __future__ import annotations

import asyncio
import hashlib
import hmac
import json
import os
import time
from collections import defaultdict, deque
from threading import Lock
from datetime import datetime, timezone
from typing import Any
from uuid import NAMESPACE_URL, uuid5

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from . import storage


ADAPTER_VERSION = "tradevision-openalgo-adapter.v0.54"
ACK_VERSION = "openalgo-adapter-ack.v0.54"
MAX_TIMESTAMP_SKEW_SECONDS = 30
MAX_REQUEST_BYTES = 2_000_000
RATE_LIMIT_PER_MINUTE = 120
_request_times: dict[str, deque[int]] = defaultdict(deque)
_rate_lock = Lock()

app = FastAPI(title="Trade Vision OpenAlgo Adapter Simulator", version="0.54.0")
storage.init_db()


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def error(status: int, code: str, message: str) -> JSONResponse:
    return JSONResponse(
        status_code=status,
        content={
            "error": {
                "code": code,
                "message": message,
                "retryable": status >= 500,
            },
            "broker_credentials_received": False,
            "broker_order_created": False,
            "order_routing_enabled": False,
            "live_trading_blocked": True,
        },
    )


def verify_identity(request: Request, body: bytes) -> tuple[str, str] | JSONResponse:
    active_secret = os.environ.get("TRADEVISION_ADAPTER_SHARED_SECRET", "")
    previous_secret = os.environ.get("TRADEVISION_ADAPTER_PREVIOUS_SECRET", "")
    if not active_secret:
        return error(503, "adapter_service_secret_missing", "Adapter service identity secret is not configured.")
    service_id = request.headers.get("X-TradeVision-Service-Id", "")
    timestamp = request.headers.get("X-TradeVision-Timestamp", "")
    supplied_hash = request.headers.get("X-TradeVision-Payload-SHA256", "")
    idempotency_key = request.headers.get("X-TradeVision-Idempotency-Key", "")
    nonce = request.headers.get("X-TradeVision-Nonce", "")
    supplied_signature = request.headers.get("X-TradeVision-Signature", "")
    if not all((service_id, timestamp, supplied_hash, idempotency_key, nonce, supplied_signature)):
        return error(401, "service_identity_headers_missing", "Required service identity headers are missing.")
    try:
        timestamp_value = int(timestamp)
    except ValueError:
        return error(401, "service_timestamp_invalid", "Service timestamp is not an integer.")
    if abs(int(time.time()) - timestamp_value) > MAX_TIMESTAMP_SKEW_SECONDS:
        return error(401, "service_timestamp_stale", "Service timestamp is outside the allowed skew window.")
    actual_hash = hashlib.sha256(body).hexdigest()
    if not hmac.compare_digest(actual_hash, supplied_hash):
        return error(401, "payload_hash_mismatch", "Payload SHA-256 does not match the request body.")
    signing_input = f"{timestamp}.{actual_hash}.{idempotency_key}.{nonce}".encode("utf-8")
    candidate_secrets = [secret for secret in (active_secret, previous_secret) if secret]
    valid_signature = any(
        hmac.compare_digest(
            hmac.new(secret.encode("utf-8"), signing_input, hashlib.sha256).hexdigest(),
            supplied_signature,
        )
        for secret in candidate_secrets
    )
    if not valid_signature:
        return error(401, "service_signature_invalid", "Service identity signature is invalid.")
    if not storage.claim_nonce(nonce, service_id, timestamp_value):
        return error(409, "service_nonce_replayed", "Service request nonce has already been used.")
    if not _rate_allowed(service_id, timestamp_value):
        return error(429, "service_rate_limited", "Service request rate limit exceeded.")
    return idempotency_key, service_id


@app.get("/health")
async def health(request: Request):
    verified = verify_identity(request, b"")
    if isinstance(verified, JSONResponse):
        return verified
    return {
        "ok": True,
        "adapter_version": ADAPTER_VERSION,
        "receipt_count": storage.receipt_count(),
        "broker_credentials_present": False,
        "broker_order_created": False,
        "order_routing_enabled": False,
        "live_trading_blocked": True,
    }


@app.post("/intent-review")
async def intent_review(request: Request):
    content_length = request.headers.get("content-length")
    if content_length:
        try:
            if int(content_length) > MAX_REQUEST_BYTES:
                return error(413, "request_too_large", f"Request exceeds {MAX_REQUEST_BYTES} bytes.")
        except ValueError:
            return error(400, "content_length_invalid", "Content-Length must be an integer.")
    body = await request.body()
    if len(body) > MAX_REQUEST_BYTES:
        return error(413, "request_too_large", f"Request exceeds {MAX_REQUEST_BYTES} bytes.")
    verified = verify_identity(request, body)
    if isinstance(verified, JSONResponse):
        return verified
    idempotency_key, _service_id = verified
    try:
        payload = json.loads(body)
    except json.JSONDecodeError:
        return error(400, "invalid_json", "Request body is not valid JSON.")
    validation_error = validate_review_payload(payload, idempotency_key)
    if validation_error:
        return validation_error

    scenario = os.environ.get("TRADEVISION_ADAPTER_SCENARIO", "normal")
    delay_ms = int(os.environ.get("TRADEVISION_ADAPTER_DELAY_MS", "0"))
    if scenario == "delay" and delay_ms > 0:
        await asyncio.sleep(delay_ms / 1000)
    if scenario == "server_error":
        return error(503, "simulated_adapter_failure", "Adapter failure scenario is active.")
    if scenario == "malformed_ack":
        return {"acknowledgement_version": ACK_VERSION, "delivery_id": payload["delivery_id"]}
    if scenario == "unsafe_ack":
        return {
            **build_receipt(payload, idempotency_key, duplicate=False),
            "broker_order_created": True,
            "order_routing_enabled": True,
            "live_trading_blocked": False,
        }

    existing = storage.load_receipt(idempotency_key)
    if existing:
        return {**existing, "duplicate": True}
    receipt = build_receipt(payload, idempotency_key, duplicate=False)
    inserted = storage.save_receipt(idempotency_key, receipt)
    if not inserted:
        concurrent_receipt = storage.load_receipt(idempotency_key)
        if concurrent_receipt:
            return {**concurrent_receipt, "duplicate": True}
    return receipt


def validate_review_payload(payload: dict[str, Any], idempotency_key: str) -> JSONResponse | None:
    required = {"transport_version", "delivery_id", "idempotency_key", "package"}
    missing = sorted(required - payload.keys())
    if missing:
        return error(422, "review_payload_missing_fields", f"Missing fields: {', '.join(missing)}")
    if payload["idempotency_key"] != idempotency_key:
        return error(409, "idempotency_key_mismatch", "Header and payload idempotency keys differ.")
    package = payload.get("package")
    if not isinstance(package, dict) or not package.get("package_hash"):
        return error(422, "package_hash_missing", "Dry-run package hash is required.")
    package_hash_fields = (
        package.get("package_sha256"),
        package.get("manifest_sha256"),
        package.get("package_id"),
    )
    if not all(isinstance(value, str) and value for value in package_hash_fields):
        return error(422, "package_integrity_fields_missing", "Package integrity fields are incomplete.")
    expected_package_hash = hashlib.sha256(
        f"{package_hash_fields[0]}:{package_hash_fields[1]}:{package_hash_fields[2]}".encode("utf-8")
    ).hexdigest()
    if not hmac.compare_digest(expected_package_hash, str(package["package_hash"])):
        return error(422, "package_hash_invalid", "Dry-run package combined hash is invalid.")
    package_unsafe = (
        not bool(package.get("dry_run_only"))
        or bool(package.get("broker_credentials_present"))
        or bool(package.get("broker_order_created"))
        or bool(package.get("trade_allowed"))
        or bool(package.get("order_routing_enabled"))
        or not bool(package.get("live_trading_blocked"))
    )
    if package_unsafe:
        return error(422, "unsafe_dry_run_package", "Dry-run package violates the no-execution boundary.")
    unsafe = (
        bool(payload.get("automatic_execution_allowed"))
        or bool(payload.get("broker_order_created"))
        or bool(payload.get("order_routing_enabled"))
        or not bool(payload.get("live_trading_blocked"))
    )
    if unsafe:
        return error(422, "unsafe_review_payload", "Research package violates the no-execution boundary.")
    return None


def build_receipt(payload: dict[str, Any], idempotency_key: str, *, duplicate: bool) -> dict[str, Any]:
    delivery_id = str(payload["delivery_id"])
    package_hash = str(payload["package"]["package_hash"])
    receipt_id = str(uuid5(NAMESPACE_URL, f"tradevision:adapter-receipt:{idempotency_key}"))
    return {
        "acknowledgement_version": ACK_VERSION,
        "delivery_id": delivery_id,
        "idempotency_key": idempotency_key,
        "adapter_name": "trade-vision-openalgo-adapter-simulator",
        "adapter_version": ADAPTER_VERSION,
        "receipt_id": receipt_id,
        "received_at": now_iso(),
        "accepted_for_external_review": True,
        "duplicate": duplicate,
        "package_hash": package_hash,
        "broker_credentials_received": False,
        "broker_order_created": False,
        "order_routing_enabled": False,
        "live_trading_blocked": True,
    }


def _rate_allowed(service_id: str, now_seconds: int) -> bool:
    with _rate_lock:
        window = _request_times[service_id]
        while window and window[0] <= now_seconds - 60:
            window.popleft()
        if len(window) >= RATE_LIMIT_PER_MINUTE:
            return False
        window.append(now_seconds)
        return True
