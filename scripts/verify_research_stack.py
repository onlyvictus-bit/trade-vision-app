from __future__ import annotations

import argparse
import hashlib
import hmac
import json
import os
import sys
import time
from typing import Any, Callable
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen
from uuid import uuid4


DEFAULT_API_BASE = "http://127.0.0.1:8000"
DEFAULT_ADAPTER_URL = "http://127.0.0.1:8011"
DEFAULT_SERVICE_ID = "trade-vision-research"
DEFAULT_TIMEOUT_MS = 2500
UNSAFE_FLAGS = (
    ("broker_credentials_present", True),
    ("broker_credentials_received", True),
    ("broker_order_created", True),
    ("order_routing_enabled", True),
    ("live_trading_blocked", False),
)

HttpGet = Callable[[str, dict[str, str], int], tuple[int, dict[str, Any]]]


def verify_research_stack(
    *,
    api_base: str = DEFAULT_API_BASE,
    adapter_url: str = DEFAULT_ADAPTER_URL,
    service_id: str = DEFAULT_SERVICE_ID,
    shared_secret: str | None = None,
    timeout_ms: int = DEFAULT_TIMEOUT_MS,
    http_get: HttpGet | None = None,
) -> dict[str, Any]:
    getter = http_get or _http_get_json
    checks: list[dict[str, Any]] = []
    secret = shared_secret if shared_secret is not None else os.environ.get("TRADEVISION_ADAPTER_SHARED_SECRET", "")

    checks.append(_api_check("api_health", f"{api_base.rstrip('/')}/health", getter, timeout_ms))
    if secret:
        checks.append(
            _adapter_health_check(
                f"{adapter_url.rstrip('/')}/health",
                service_id=service_id,
                shared_secret=secret,
                getter=getter,
                timeout_ms=timeout_ms,
            )
        )
    else:
        checks.append(
            _check_result(
                "adapter_health",
                False,
                "TRADEVISION_ADAPTER_SHARED_SECRET is required for signed adapter health.",
                status_code=None,
                payload={},
            )
        )
    checks.append(_api_check("security_posture", f"{api_base.rstrip('/')}/api/v1/openalgo/security/posture", getter, timeout_ms))
    checks.append(_api_check("deployment_readiness", f"{api_base.rstrip('/')}/api/v1/deployment/readiness", getter, timeout_ms))
    checks.append(_api_check("final_release_audit", f"{api_base.rstrip('/')}/api/v1/release/final-audit", getter, timeout_ms))

    failed = [item for item in checks if not item["passed"]]
    return {
        "verifier_version": "research-stack-verifier.v1",
        "api_base": api_base,
        "adapter_url": adapter_url,
        "service_id": service_id,
        "timeout_ms": timeout_ms,
        "passed": not failed,
        "check_count": len(checks),
        "failed_count": len(failed),
        "checks": checks,
        "broker_credentials_present": False,
        "broker_order_created": False,
        "order_routing_enabled": False,
        "live_trading_blocked": True,
    }


def _api_check(check_id: str, url: str, getter: HttpGet, timeout_ms: int) -> dict[str, Any]:
    try:
        status_code, payload = getter(url, {}, timeout_ms)
    except Exception as exc:
        return _check_result(check_id, False, f"{type(exc).__name__}: {exc}", status_code=None, payload={})
    data = _payload_data(payload)
    unsafe = _unsafe_reasons(data)
    passed = 200 <= status_code < 300 and not unsafe
    evidence = "ok" if passed else "; ".join(unsafe) or f"status_code={status_code}"
    return _check_result(check_id, passed, evidence, status_code=status_code, payload=data)


def _adapter_health_check(
    url: str,
    *,
    service_id: str,
    shared_secret: str,
    getter: HttpGet,
    timeout_ms: int,
) -> dict[str, Any]:
    headers = _signed_health_headers(service_id, shared_secret)
    try:
        status_code, payload = getter(url, headers, timeout_ms)
    except Exception as exc:
        return _check_result("adapter_health", False, f"{type(exc).__name__}: {exc}", status_code=None, payload={})
    unsafe = _unsafe_reasons(payload)
    passed = 200 <= status_code < 300 and bool(payload.get("ok")) and not unsafe
    evidence = "signed health ok" if passed else "; ".join(unsafe) or f"status_code={status_code}; ok={payload.get('ok')}"
    return _check_result("adapter_health", passed, evidence, status_code=status_code, payload=payload)


def _signed_health_headers(service_id: str, shared_secret: str) -> dict[str, str]:
    body_hash = hashlib.sha256(b"").hexdigest()
    timestamp = str(int(time.time()))
    idempotency_key = "verify-research-stack-health"
    nonce = str(uuid4())
    signing_input = f"{timestamp}.{body_hash}.{idempotency_key}.{nonce}".encode("utf-8")
    signature = hmac.new(shared_secret.encode("utf-8"), signing_input, hashlib.sha256).hexdigest()
    return {
        "X-TradeVision-Service-Id": service_id,
        "X-TradeVision-Timestamp": timestamp,
        "X-TradeVision-Payload-SHA256": body_hash,
        "X-TradeVision-Idempotency-Key": idempotency_key,
        "X-TradeVision-Nonce": nonce,
        "X-TradeVision-Signature": signature,
    }


def _http_get_json(url: str, headers: dict[str, str], timeout_ms: int) -> tuple[int, dict[str, Any]]:
    request = Request(url, headers=headers, method="GET")
    try:
        with urlopen(request, timeout=max(timeout_ms / 1000.0, 0.1)) as response:
            body = response.read().decode("utf-8")
            return int(response.status), json.loads(body) if body else {}
    except HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        try:
            payload = json.loads(body) if body else {}
        except json.JSONDecodeError:
            payload = {"raw_body": body}
        return int(exc.code), payload
    except URLError as exc:
        raise ConnectionError(str(exc.reason)) from exc


def _payload_data(payload: dict[str, Any]) -> dict[str, Any]:
    data = payload.get("data")
    return data if isinstance(data, dict) else payload


def _unsafe_reasons(payload: dict[str, Any]) -> list[str]:
    reasons: list[str] = []
    for flag, unsafe_value in UNSAFE_FLAGS:
        if payload.get(flag) is unsafe_value:
            reasons.append(f"{flag}={unsafe_value}")
    return reasons


def _check_result(
    check_id: str,
    passed: bool,
    evidence: str,
    *,
    status_code: int | None,
    payload: dict[str, Any],
) -> dict[str, Any]:
    return {
        "check_id": check_id,
        "passed": passed,
        "status_code": status_code,
        "evidence": evidence,
        "payload_summary": {
            "status": payload.get("status") or payload.get("overall_status") or payload.get("ready") or payload.get("research_stack_ready"),
            "fail_count": payload.get("fail_count"),
            "broker_credentials_present": bool(payload.get("broker_credentials_present", False)),
            "broker_order_created": bool(payload.get("broker_order_created", False)),
            "order_routing_enabled": bool(payload.get("order_routing_enabled", False)),
            "live_trading_blocked": bool(payload.get("live_trading_blocked", True)),
        },
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Verify the local Trade Vision brokerless research stack.")
    parser.add_argument("--api-base", default=os.environ.get("TRADEVISION_API_BASE", DEFAULT_API_BASE))
    parser.add_argument("--adapter-url", default=os.environ.get("TRADEVISION_OPENALGO_ADAPTER_URL", DEFAULT_ADAPTER_URL))
    parser.add_argument("--service-id", default=os.environ.get("TRADEVISION_ADAPTER_SERVICE_ID", DEFAULT_SERVICE_ID))
    parser.add_argument("--timeout-ms", type=int, default=int(os.environ.get("TRADEVISION_VERIFY_TIMEOUT_MS", DEFAULT_TIMEOUT_MS)))
    args = parser.parse_args(argv)

    report = verify_research_stack(
        api_base=args.api_base,
        adapter_url=args.adapter_url,
        service_id=args.service_id,
        timeout_ms=args.timeout_ms,
    )
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
