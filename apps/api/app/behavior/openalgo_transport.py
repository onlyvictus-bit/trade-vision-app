from __future__ import annotations

import hashlib
import hmac
import json
import os
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timedelta, timezone
from threading import Lock
from time import perf_counter
from urllib.error import HTTPError, URLError
from urllib.parse import urlparse
from urllib.request import Request, urlopen
from uuid import NAMESPACE_URL, uuid4, uuid5

from .. import storage
from ..models import (
    ExecutorTransportAcknowledgement,
    ExecutorTransportDeliveryResult,
    ExecutorTransportEnqueueRequest,
    ExecutorTransportOutboxRecord,
    ExecutorTransportOperatorAction,
    ExecutorTransportStatus,
    ExecutorTransportTrace,
    ExecutorTransportWorkerRequest,
    ExecutorTransportWorkerRun,
    now_iso,
)


TRANSPORT_VERSION = "openalgo-adapter-transport.v0.53"
WORKER_VERSION = "openalgo-transport-recovery.v0.55"
DEFAULT_TIMEOUT_MS = 1200
CIRCUIT_FAILURE_THRESHOLD = 3
CIRCUIT_COOLDOWN_SECONDS = 30
MAX_RETRY_DELAY_SECONDS = 30

_circuit_lock = Lock()
_circuit_failure_count = 0
_circuit_open_until: datetime | None = None
_delivery_locks_guard = Lock()
_delivery_locks: dict[str, Lock] = {}


def enqueue_transport(request: ExecutorTransportEnqueueRequest) -> ExecutorTransportOutboxRecord:
    adapter_url = _adapter_url(request.adapter_url)
    idempotency_key = hashlib.sha256(
        f"{request.package.package_hash}:{adapter_url or 'unconfigured'}:{request.service_identity}".encode("utf-8")
    ).hexdigest()
    existing = storage.load_executor_transport_by_idempotency(idempotency_key)
    if existing is not None:
        return existing
    created_at = now_iso()
    delivery_id = str(uuid5(NAMESPACE_URL, f"tradevision:openalgo-transport:{idempotency_key}"))
    record = ExecutorTransportOutboxRecord(
        transport_version=TRANSPORT_VERSION,
        delivery_id=delivery_id,
        idempotency_key=idempotency_key,
        created_at=created_at,
        updated_at=created_at,
        adapter_url=adapter_url,
        service_identity=request.service_identity,
        package=request.package,
        status="pending",
        attempt_count=0,
        max_attempts=request.max_attempts,
        next_attempt_at=created_at,
        last_attempt_at=None,
        last_error=None,
        acknowledgement=None,
        automatic_execution_allowed=False,
        broker_credentials_present=False,
        broker_order_created=False,
        order_routing_enabled=False,
        live_trading_blocked=True,
    )
    storage.save_executor_transport_record(record)
    _trace(record, "enqueued", actor_id=request.service_identity)
    return record


def deliver_transport(
    delivery_id: str,
    *,
    timeout_ms: int = DEFAULT_TIMEOUT_MS,
) -> ExecutorTransportDeliveryResult:
    delivery_lock = _delivery_lock(delivery_id)
    if not delivery_lock.acquire(blocking=False):
        record = storage.load_executor_transport_record(delivery_id)
        if record is None:
            raise KeyError(delivery_id)
        return _result(
            record,
            "retry_wait",
            retryable=True,
            circuit_state=_circuit_state(),
            error_code="delivery_already_in_progress",
            error_message="A delivery attempt is already in progress for this outbox record.",
        )
    try:
        return _deliver_transport_locked(delivery_id, timeout_ms=timeout_ms)
    finally:
        delivery_lock.release()


def _deliver_transport_locked(
    delivery_id: str,
    *,
    timeout_ms: int,
) -> ExecutorTransportDeliveryResult:
    record = storage.load_executor_transport_record(delivery_id)
    if record is None:
        raise KeyError(delivery_id)
    if record.status == "acknowledged":
        return _result(record, "acknowledged", retryable=False, circuit_state=_circuit_state())
    if record.status == "manual_review":
        return _result(record, "manual_review", retryable=False, circuit_state=_circuit_state())
    if record.status == "dead_letter":
        return _result(record, "dead_letter", retryable=False, circuit_state=_circuit_state())
    if record.status == "cancelled":
        return _result(record, "cancelled", retryable=False, circuit_state=_circuit_state())
    if record.status == "retry_wait" and record.next_attempt_at:
        retry_at = datetime.fromisoformat(record.next_attempt_at)
        if datetime.now(timezone.utc) < retry_at:
            return _result(
                record,
                "retry_wait",
                retryable=True,
                circuit_state=_circuit_state(),
                error_code="retry_not_due",
                error_message=f"Retry is deferred until {record.next_attempt_at}.",
            )
    state = _circuit_state()
    if state == "open":
        return _result(
            record,
            "circuit_open",
            retryable=True,
            circuit_state="open",
            error_code="adapter_circuit_open",
            error_message="Adapter circuit is open after repeated transport failures.",
        )
    if not record.adapter_url:
        updated = _mark_manual_review(record, "adapter_url_not_configured")
        return _result(
            updated,
            "manual_review",
            retryable=False,
            circuit_state=state,
            error_code="adapter_url_not_configured",
            error_message="External adapter URL is not configured; intent remains available for manual review.",
        )
    secret = os.environ.get("TRADEVISION_ADAPTER_SHARED_SECRET", "")
    if not secret:
        updated = _mark_manual_review(record, "service_identity_secret_not_configured")
        return _result(
            updated,
            "manual_review",
            retryable=False,
            circuit_state=state,
            error_code="service_identity_secret_not_configured",
            error_message="Adapter service identity secret is not configured; delivery is blocked.",
        )
    attempt_count = record.attempt_count + 1
    attempted_at = now_iso()
    delivering = record.model_copy(
        update={
            "status": "delivering",
            "attempt_count": attempt_count,
            "updated_at": attempted_at,
            "last_attempt_at": attempted_at,
            "last_error": None,
        }
    )
    storage.save_executor_transport_record(delivering)
    started = perf_counter()
    _trace(delivering, "delivery_started", actor_id="transport_worker")
    payload = {
        "transport_version": TRANSPORT_VERSION,
        "delivery_id": record.delivery_id,
        "idempotency_key": record.idempotency_key,
        "package": record.package.model_dump(mode="json"),
        "automatic_execution_allowed": False,
        "broker_order_created": False,
        "order_routing_enabled": False,
        "live_trading_blocked": True,
    }
    try:
        response = _http_json(
            "POST",
            f"{record.adapter_url.rstrip('/')}/intent-review",
            payload=payload,
            timeout_ms=timeout_ms,
            service_identity=record.service_identity,
            shared_secret=secret,
            idempotency_key=record.idempotency_key,
        )
        acknowledgement = _validate_acknowledgement(record, response)
        _record_transport_success()
        updated = delivering.model_copy(
            update={
                "status": "acknowledged",
                "updated_at": now_iso(),
                "next_attempt_at": None,
                "last_error": None,
                "acknowledgement": acknowledgement,
            }
        )
        storage.save_executor_transport_record(updated)
        _trace(
            updated,
            "acknowledged",
            actor_id="transport_worker",
            latency_ms=round((perf_counter() - started) * 1000, 3),
        )
        return _result(updated, "acknowledged", retryable=False, circuit_state="closed")
    except TimeoutError:
        return _handle_failure(delivering, "adapter_timeout", "External adapter request timed out.")
    except (OSError, HTTPError, URLError, ValueError, KeyError) as exc:
        return _handle_failure(
            delivering,
            "adapter_delivery_failed",
            f"External adapter delivery failed: {type(exc).__name__}.",
        )


def transport_status(
    *,
    adapter_url: str | None = None,
    service_identity: str = "trade-vision-research",
    timeout_ms: int = DEFAULT_TIMEOUT_MS,
    check_health: bool = False,
) -> ExecutorTransportStatus:
    resolved_url = _adapter_url(adapter_url)
    secret = os.environ.get("TRADEVISION_ADAPTER_SHARED_SECRET", "")
    health_ok = False
    health_checked = False
    if check_health and resolved_url and secret and _circuit_state() != "open":
        health_checked = True
        try:
            payload = _http_json(
                "GET",
                f"{resolved_url.rstrip('/')}/health",
                timeout_ms=timeout_ms,
                service_identity=service_identity,
                shared_secret=secret,
                idempotency_key="health-check",
            )
            health_ok = bool(payload.get("ok")) and not bool(payload.get("order_routing_enabled", False))
        except (TimeoutError, OSError, HTTPError, URLError, ValueError):
            health_ok = False
    counts = storage.executor_transport_counts()
    open_until = _circuit_open_until_iso()
    return ExecutorTransportStatus(
        status_version=TRANSPORT_VERSION,
        generated_at=now_iso(),
        adapter_url=resolved_url,
        configured=bool(resolved_url),
        health_checked=health_checked,
        health_ok=health_ok,
        service_identity=service_identity,
        service_auth_configured=bool(secret),
        timeout_ms=timeout_ms,
        circuit_state=_circuit_state(),
        circuit_failure_count=_circuit_failures(),
        circuit_failure_threshold=CIRCUIT_FAILURE_THRESHOLD,
        circuit_open_until=open_until,
        pending_count=counts["pending"] + counts["delivering"],
        retry_wait_count=counts["retry_wait"],
        acknowledged_count=counts["acknowledged"],
        manual_review_count=counts["manual_review"],
        cancelled_count=counts["cancelled"],
        dead_letter_count=counts["dead_letter"],
        automatic_execution_allowed=False,
        broker_credentials_present=False,
        broker_order_created=False,
        order_routing_enabled=False,
        live_trading_blocked=True,
        notes=[
            "Transport delivers research intent packages for external review only.",
            "HMAC service identity is separate from broker credentials and is never persisted.",
            "Failures preserve the durable outbox record and force WAIT/manual review.",
        ],
    )


def _validate_acknowledgement(
    record: ExecutorTransportOutboxRecord,
    payload: dict[str, object],
) -> ExecutorTransportAcknowledgement:
    acknowledgement = ExecutorTransportAcknowledgement.model_validate(payload)
    if acknowledgement.delivery_id != record.delivery_id:
        raise ValueError("Acknowledgement delivery_id mismatch.")
    if acknowledgement.idempotency_key != record.idempotency_key:
        raise ValueError("Acknowledgement idempotency_key mismatch.")
    if acknowledgement.package_hash != record.package.package_hash:
        raise ValueError("Acknowledgement package_hash mismatch.")
    if acknowledgement.broker_credentials_received:
        raise ValueError("Adapter acknowledgement reports broker credentials.")
    if acknowledgement.broker_order_created or acknowledgement.order_routing_enabled:
        raise ValueError("Adapter acknowledgement reports unsafe order execution or routing.")
    if not acknowledgement.live_trading_blocked:
        raise ValueError("Adapter acknowledgement does not preserve the live-trading block.")
    return acknowledgement


def _handle_failure(
    record: ExecutorTransportOutboxRecord,
    error_code: str,
    error_message: str,
) -> ExecutorTransportDeliveryResult:
    circuit_state = _record_transport_failure()
    exhausted = record.attempt_count >= record.max_attempts
    if exhausted:
        updated = record.model_copy(
            update={
                "status": "dead_letter",
                "updated_at": now_iso(),
                "next_attempt_at": None,
                "last_error": f"{error_code}: {error_message}",
            }
        )
        status = "dead_letter"
        retryable = False
    else:
        delay_seconds = min(MAX_RETRY_DELAY_SECONDS, 2 ** record.attempt_count)
        next_attempt_at = (datetime.now(timezone.utc) + timedelta(seconds=delay_seconds)).isoformat()
        updated = record.model_copy(
            update={
                "status": "retry_wait",
                "updated_at": now_iso(),
                "next_attempt_at": next_attempt_at,
                "last_error": f"{error_code}: {error_message}",
            }
        )
        status = "retry_wait"
        retryable = True
    storage.save_executor_transport_record(updated)
    _trace(
        updated,
        "dead_lettered" if exhausted else "retry_scheduled",
        actor_id="transport_worker",
        error_code=error_code,
    )
    return _result(
        updated,
        status,
        retryable=retryable,
        circuit_state=circuit_state,
        error_code=error_code,
        error_message=error_message,
    )


def _mark_manual_review(
    record: ExecutorTransportOutboxRecord,
    error_code: str,
) -> ExecutorTransportOutboxRecord:
    updated = record.model_copy(
        update={
            "status": "manual_review",
            "updated_at": now_iso(),
            "next_attempt_at": None,
            "last_error": error_code,
        }
    )
    storage.save_executor_transport_record(updated)
    _trace(updated, "manual_review", actor_id="transport_worker", error_code=error_code)
    return updated


def run_due_worker(request: ExecutorTransportWorkerRequest) -> ExecutorTransportWorkerRun:
    started_at = now_iso()
    run_id = str(uuid4())
    effective_limit = max(request.limit, 1000) if str(storage.DB_PATH) == ":memory:" else request.limit
    stale_before = (datetime.now(timezone.utc) - timedelta(seconds=request.stale_after_seconds)).isoformat()
    stale = storage.list_stale_delivering_records(stale_before, effective_limit)
    for record in stale:
        recovered = record.model_copy(
            update={
                "status": "retry_wait",
                "updated_at": now_iso(),
                "next_attempt_at": now_iso(),
                "last_error": "recovered_stale_inflight_delivery",
            }
        )
        storage.save_executor_transport_record(recovered)
        _trace(recovered, "recovered", actor_id=request.actor_id, error_code="stale_inflight")

    due = storage.list_due_executor_transport_records(now_iso(), effective_limit)
    results: list[ExecutorTransportDeliveryResult] = []
    with ThreadPoolExecutor(max_workers=request.concurrency, thread_name_prefix="openalgo-transport") as pool:
        futures = {pool.submit(deliver_transport, record.delivery_id): record.delivery_id for record in due}
        for future in as_completed(futures):
            try:
                results.append(future.result())
            except Exception as exc:
                delivery_id = futures[future]
                record = storage.load_executor_transport_record(delivery_id)
                if record is not None:
                    results.append(
                        _result(
                            record,
                            "manual_review",
                            retryable=False,
                            circuit_state=_circuit_state(),
                            error_code="worker_unhandled_failure",
                            error_message=f"Worker isolated {type(exc).__name__}.",
                        )
                    )

    return ExecutorTransportWorkerRun(
        worker_version=WORKER_VERSION,
        run_id=run_id,
        started_at=started_at,
        completed_at=now_iso(),
        actor_id=request.actor_id,
        concurrency=request.concurrency,
        recovered_count=len(stale),
        due_count=len(due),
        processed_count=len(results),
        acknowledged_count=sum(item.status == "acknowledged" for item in results),
        retry_wait_count=sum(item.status == "retry_wait" for item in results),
        manual_review_count=sum(item.status == "manual_review" for item in results),
        dead_letter_count=sum(item.status == "dead_letter" for item in results),
        circuit_open_count=sum(item.status == "circuit_open" for item in results),
        results=results,
    )


def operator_retry(delivery_id: str, action: ExecutorTransportOperatorAction) -> ExecutorTransportOutboxRecord:
    record = storage.load_executor_transport_record(delivery_id)
    if record is None:
        raise KeyError(delivery_id)
    if record.status not in {"manual_review", "dead_letter", "retry_wait"}:
        raise ValueError(f"Record status {record.status} cannot be retried.")
    updated = record.model_copy(
        update={
            "status": "pending",
            "updated_at": now_iso(),
            "next_attempt_at": now_iso(),
            "last_error": f"operator_retry: {action.reason}",
        }
    )
    storage.save_executor_transport_record(updated)
    _trace(updated, "operator_retry", actor_id=action.actor_id, details={"reason": action.reason})
    return updated


def operator_cancel(delivery_id: str, action: ExecutorTransportOperatorAction) -> ExecutorTransportOutboxRecord:
    record = storage.load_executor_transport_record(delivery_id)
    if record is None:
        raise KeyError(delivery_id)
    if record.status in {"acknowledged", "cancelled"}:
        raise ValueError(f"Record status {record.status} cannot be cancelled.")
    updated = record.model_copy(
        update={
            "status": "cancelled",
            "updated_at": now_iso(),
            "next_attempt_at": None,
            "last_error": f"operator_cancelled: {action.reason}",
        }
    )
    storage.save_executor_transport_record(updated)
    _trace(updated, "cancelled", actor_id=action.actor_id, details={"reason": action.reason})
    return updated


def _trace(
    record: ExecutorTransportOutboxRecord,
    event_type: str,
    *,
    actor_id: str,
    latency_ms: float | None = None,
    error_code: str | None = None,
    details: dict[str, object] | None = None,
) -> None:
    previous = storage.latest_executor_transport_trace(record.delivery_id)
    trace_id = str(uuid4())
    event_time = now_iso()
    previous_hash = previous.trace_hash if previous and previous.trace_hash else None
    canonical = {
        "trace_id": trace_id,
        "delivery_id": record.delivery_id,
        "event_time": event_time,
        "event_type": event_type,
        "status": record.status,
        "attempt_count": record.attempt_count,
        "latency_ms": latency_ms,
        "error_code": error_code,
        "actor_id": actor_id,
        "details": details or {},
        "previous_trace_hash": previous_hash,
    }
    trace_hash = hashlib.sha256(
        json.dumps(canonical, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()
    storage.save_executor_transport_trace(
        ExecutorTransportTrace(**canonical, trace_hash=trace_hash)  # type: ignore[arg-type]
    )


def _result(
    record: ExecutorTransportOutboxRecord,
    status: str,
    *,
    retryable: bool,
    circuit_state: str,
    error_code: str | None = None,
    error_message: str | None = None,
) -> ExecutorTransportDeliveryResult:
    return ExecutorTransportDeliveryResult(
        delivery_version=TRANSPORT_VERSION,
        delivered_at=now_iso(),
        delivery_id=record.delivery_id,
        idempotency_key=record.idempotency_key,
        status=status,  # type: ignore[arg-type]
        attempt_count=record.attempt_count,
        retryable=retryable,
        next_attempt_at=record.next_attempt_at,
        acknowledgement=record.acknowledgement,
        error_code=error_code,
        error_message=error_message,
        circuit_state=circuit_state,  # type: ignore[arg-type]
        wait_required=True,
        promotion_allowed=False,
        broker_credentials_present=False,
        broker_order_created=False,
        order_routing_enabled=False,
        live_trading_blocked=True,
    )


def _adapter_url(explicit: str | None) -> str | None:
    value = explicit or os.environ.get("TRADEVISION_OPENALGO_ADAPTER_URL")
    if not value:
        return None
    normalized = value.rstrip("/")
    if not normalized.startswith(("http://", "https://")):
        raise ValueError("Adapter URL must use http:// or https://.")
    parsed = urlparse(normalized)
    if parsed.username or parsed.password:
        raise ValueError("Adapter URL must not contain credentials.")
    hostname = (parsed.hostname or "").lower()
    allowed = _allowed_adapter_hosts()
    if not any(hostname == item or (item.startswith(".") and hostname.endswith(item)) for item in allowed):
        raise ValueError(f"Adapter host is not allowlisted: {hostname}.")
    if parsed.scheme != "https" and hostname not in {"127.0.0.1", "localhost"} and not hostname.endswith(".test"):
        raise ValueError("Non-loopback adapter URLs must use HTTPS.")
    return normalized


def _allowed_adapter_hosts() -> list[str]:
    configured = os.environ.get("TRADEVISION_ADAPTER_ALLOWED_HOSTS", "127.0.0.1,localhost,.test")
    return [item.strip().lower() for item in configured.split(",") if item.strip()]


def _delivery_lock(delivery_id: str) -> Lock:
    with _delivery_locks_guard:
        return _delivery_locks.setdefault(delivery_id, Lock())


def _http_json(
    method: str,
    url: str,
    *,
    timeout_ms: int,
    service_identity: str,
    shared_secret: str,
    idempotency_key: str,
    payload: dict[str, object] | None = None,
) -> dict[str, object]:
    body = json.dumps(payload, sort_keys=True).encode("utf-8") if payload is not None else None
    payload_hash = hashlib.sha256(body or b"").hexdigest()
    timestamp = str(int(datetime.now(timezone.utc).timestamp()))
    nonce = str(uuid4())
    signing_input = f"{timestamp}.{payload_hash}.{idempotency_key}.{nonce}".encode("utf-8")
    signature = hmac.new(shared_secret.encode("utf-8"), signing_input, hashlib.sha256).hexdigest()
    request = Request(
        url,
        data=body,
        method=method,
        headers={
            "Content-Type": "application/json",
            "X-TradeVision-Service-Id": service_identity,
            "X-TradeVision-Timestamp": timestamp,
            "X-TradeVision-Payload-SHA256": payload_hash,
            "X-TradeVision-Idempotency-Key": idempotency_key,
            "X-TradeVision-Nonce": nonce,
            "X-TradeVision-Signature": signature,
        },
    )
    try:
        with urlopen(request, timeout=max(0.001, timeout_ms / 1000.0)) as response:
            return json.loads(response.read().decode("utf-8"))
    except TimeoutError:
        raise


def _record_transport_success() -> None:
    global _circuit_failure_count, _circuit_open_until
    with _circuit_lock:
        _circuit_failure_count = 0
        _circuit_open_until = None


def _record_transport_failure() -> str:
    global _circuit_failure_count, _circuit_open_until
    with _circuit_lock:
        _circuit_failure_count += 1
        if _circuit_failure_count >= CIRCUIT_FAILURE_THRESHOLD:
            _circuit_open_until = datetime.now(timezone.utc) + timedelta(seconds=CIRCUIT_COOLDOWN_SECONDS)
            return "open"
        return "closed"


def _circuit_state() -> str:
    global _circuit_failure_count, _circuit_open_until
    with _circuit_lock:
        if _circuit_open_until is None:
            return "closed"
        if datetime.now(timezone.utc) < _circuit_open_until:
            return "open"
        _circuit_open_until = None
        _circuit_failure_count = 0
        return "half_open"


def _circuit_failures() -> int:
    with _circuit_lock:
        return _circuit_failure_count


def _circuit_open_until_iso() -> str | None:
    with _circuit_lock:
        return _circuit_open_until.isoformat() if _circuit_open_until else None


def reset_transport_circuit() -> None:
    _record_transport_success()
