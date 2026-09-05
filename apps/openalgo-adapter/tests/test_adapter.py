from __future__ import annotations

import hashlib
import hmac
import json
import time
from uuid import uuid4

from fastapi.testclient import TestClient

from adapter_app.main import app


SECRET = "adapter-test-secret"
client = TestClient(app)


def signed_headers(
    body: bytes,
    idempotency_key: str,
    *,
    secret: str = SECRET,
    timestamp: int | None = None,
    nonce: str | None = None,
):
    timestamp_text = str(timestamp if timestamp is not None else int(time.time()))
    payload_hash = hashlib.sha256(body).hexdigest()
    nonce_value = nonce or str(uuid4())
    signing_input = f"{timestamp_text}.{payload_hash}.{idempotency_key}.{nonce_value}".encode()
    signature = hmac.new(secret.encode(), signing_input, hashlib.sha256).hexdigest()
    return {
        "Content-Type": "application/json",
        "X-TradeVision-Service-Id": "trade-vision-adapter-test",
        "X-TradeVision-Timestamp": timestamp_text,
        "X-TradeVision-Payload-SHA256": payload_hash,
        "X-TradeVision-Idempotency-Key": idempotency_key,
        "X-TradeVision-Nonce": nonce_value,
        "X-TradeVision-Signature": signature,
    }


def review_payload(idempotency_key: str = "idem-001"):
    package_sha = "b" * 64
    manifest_sha = "c" * 64
    package_id = "package-001"
    package_hash = hashlib.sha256(f"{package_sha}:{manifest_sha}:{package_id}".encode()).hexdigest()
    return {
        "transport_version": "openalgo-adapter-transport.v0.53",
        "delivery_id": "delivery-001",
        "idempotency_key": idempotency_key,
        "package": {
            "package_id": package_id,
            "package_sha256": package_sha,
            "manifest_sha256": manifest_sha,
            "package_hash": package_hash,
            "dry_run_only": True,
            "broker_credentials_present": False,
            "broker_order_created": False,
            "trade_allowed": False,
            "order_routing_enabled": False,
            "live_trading_blocked": True,
        },
        "automatic_execution_allowed": False,
        "broker_order_created": False,
        "order_routing_enabled": False,
        "live_trading_blocked": True,
    }


def test_health_requires_valid_service_identity(monkeypatch):
    monkeypatch.setenv("TRADEVISION_ADAPTER_SHARED_SECRET", SECRET)
    denied = client.get("/health")
    assert denied.status_code == 401
    body = b""
    accepted = client.get("/health", headers=signed_headers(body, "health-check"))
    assert accepted.status_code == 200
    data = accepted.json()
    assert data["ok"] is True
    assert data["broker_order_created"] is False
    assert data["order_routing_enabled"] is False
    assert data["live_trading_blocked"] is True


def test_intent_review_persists_idempotent_receipt(monkeypatch, tmp_path):
    monkeypatch.setenv("TRADEVISION_ADAPTER_SHARED_SECRET", SECRET)
    monkeypatch.setenv("TRADEVISION_ADAPTER_DB", str(tmp_path / "adapter.db"))
    monkeypatch.setenv("TRADEVISION_ADAPTER_SCENARIO", "normal")
    from adapter_app import storage

    storage.init_db()
    payload = review_payload()
    body = json.dumps(payload, sort_keys=True).encode()
    first = client.post("/intent-review", content=body, headers=signed_headers(body, payload["idempotency_key"]))
    second = client.post("/intent-review", content=body, headers=signed_headers(body, payload["idempotency_key"]))
    assert first.status_code == 200
    assert second.status_code == 200
    a = first.json()
    b = second.json()
    assert a["receipt_id"] == b["receipt_id"]
    assert a["duplicate"] is False
    assert b["duplicate"] is True
    assert b["broker_credentials_received"] is False
    assert b["broker_order_created"] is False
    assert b["order_routing_enabled"] is False
    assert b["live_trading_blocked"] is True


def test_signature_hash_timestamp_and_unsafe_payload_are_rejected(monkeypatch):
    monkeypatch.setenv("TRADEVISION_ADAPTER_SHARED_SECRET", SECRET)
    payload = review_payload("idem-security")
    body = json.dumps(payload, sort_keys=True).encode()

    bad_signature = client.post(
        "/intent-review",
        content=body,
        headers=signed_headers(body, payload["idempotency_key"], secret="wrong-secret"),
    )
    assert bad_signature.status_code == 401
    assert bad_signature.json()["error"]["code"] == "service_signature_invalid"

    stale = client.post(
        "/intent-review",
        content=body,
        headers=signed_headers(body, payload["idempotency_key"], timestamp=int(time.time()) - 60),
    )
    assert stale.status_code == 401
    assert stale.json()["error"]["code"] == "service_timestamp_stale"

    unsafe_payload = {**payload, "order_routing_enabled": True}
    unsafe_body = json.dumps(unsafe_payload, sort_keys=True).encode()
    unsafe = client.post(
        "/intent-review",
        content=unsafe_body,
        headers=signed_headers(unsafe_body, payload["idempotency_key"]),
    )
    assert unsafe.status_code == 422
    assert unsafe.json()["error"]["code"] == "unsafe_review_payload"
    assert unsafe.json()["broker_order_created"] is False
    assert unsafe.json()["order_routing_enabled"] is False

    tampered_package = {
        **payload,
        "package": {**payload["package"], "package_hash": "0" * 64},
    }
    tampered_body = json.dumps(tampered_package, sort_keys=True).encode()
    tampered = client.post(
        "/intent-review",
        content=tampered_body,
        headers=signed_headers(tampered_body, payload["idempotency_key"]),
    )
    assert tampered.status_code == 422
    assert tampered.json()["error"]["code"] == "package_hash_invalid"


def test_controlled_fault_scenarios_never_create_orders(monkeypatch):
    monkeypatch.setenv("TRADEVISION_ADAPTER_SHARED_SECRET", SECRET)
    payload = review_payload("idem-fault")
    body = json.dumps(payload, sort_keys=True).encode()

    monkeypatch.setenv("TRADEVISION_ADAPTER_SCENARIO", "server_error")
    failed = client.post("/intent-review", content=body, headers=signed_headers(body, payload["idempotency_key"]))
    assert failed.status_code == 503
    assert failed.json()["broker_order_created"] is False
    assert failed.json()["order_routing_enabled"] is False

    monkeypatch.setenv("TRADEVISION_ADAPTER_SCENARIO", "malformed_ack")
    malformed = client.post("/intent-review", content=body, headers=signed_headers(body, payload["idempotency_key"]))
    assert malformed.status_code == 200
    assert set(malformed.json()) == {"acknowledgement_version", "delivery_id"}


def test_nonce_replay_and_previous_rotation_key(monkeypatch):
    monkeypatch.setenv("TRADEVISION_ADAPTER_SHARED_SECRET", "new-active-secret")
    monkeypatch.setenv("TRADEVISION_ADAPTER_PREVIOUS_SECRET", SECRET)
    payload = review_payload("idem-rotation")
    body = json.dumps(payload, sort_keys=True).encode()
    nonce = str(uuid4())
    headers = signed_headers(body, payload["idempotency_key"], secret=SECRET, nonce=nonce)
    accepted = client.post("/intent-review", content=body, headers=headers)
    assert accepted.status_code == 200
    assert accepted.json()["broker_order_created"] is False

    replayed = client.post("/intent-review", content=body, headers=headers)
    assert replayed.status_code == 409
    assert replayed.json()["error"]["code"] == "service_nonce_replayed"


def test_oversized_request_is_rejected_before_processing(monkeypatch):
    monkeypatch.setenv("TRADEVISION_ADAPTER_SHARED_SECRET", SECRET)
    response = client.post(
        "/intent-review",
        content=b"{}",
        headers={"Content-Length": "2000001"},
    )
    assert response.status_code == 413
    assert response.json()["error"]["code"] == "request_too_large"
    assert response.json()["order_routing_enabled"] is False
