from __future__ import annotations

import importlib.util
import subprocess
from pathlib import Path
from typing import Any


SCRIPT_PATH = Path(__file__).resolve().parents[3] / "scripts" / "verify_research_stack.py"
WRAPPER_PATH = Path(__file__).resolve().parents[3] / "scripts" / "verify-local-research-stack.ps1"
spec = importlib.util.spec_from_file_location("verify_research_stack", SCRIPT_PATH)
verify_module = importlib.util.module_from_spec(spec)
assert spec and spec.loader
spec.loader.exec_module(verify_module)


def test_research_stack_verifier_passes_clean_brokerless_payloads():
    def fake_get(url: str, headers: dict[str, str], _timeout_ms: int) -> tuple[int, dict[str, Any]]:
        if url.endswith("/health") and headers:
            assert "X-TradeVision-Signature" in headers
            return 200, {
                "ok": True,
                "broker_credentials_present": False,
                "broker_order_created": False,
                "order_routing_enabled": False,
                "live_trading_blocked": True,
            }
        if url.endswith("/health"):
            return 200, {"status": "alive", "order_routing_enabled": False, "live_trading_blocked": True}
        if url.endswith("/security/posture"):
            return 200, {"data": {"overall_status": "pass", "order_routing_enabled": False, "live_trading_blocked": True}}
        if url.endswith("/deployment/readiness"):
            return 200, {"data": {"ready": True, "fail_count": 0, "order_routing_enabled": False, "live_trading_blocked": True}}
        if url.endswith("/release/final-audit"):
            return 200, {"data": {"research_stack_ready": True, "fail_count": 0, "order_routing_enabled": False, "live_trading_blocked": True}}
        raise AssertionError(url)

    report = verify_module.verify_research_stack(shared_secret="secret", http_get=fake_get)

    assert report["passed"] is True
    assert report["failed_count"] == 0
    assert report["broker_order_created"] is False
    assert report["order_routing_enabled"] is False
    assert report["live_trading_blocked"] is True


def test_research_stack_verifier_requires_adapter_secret():
    def fake_get(url: str, _headers: dict[str, str], _timeout_ms: int) -> tuple[int, dict[str, Any]]:
        if url.endswith("/health"):
            return 200, {"status": "alive", "order_routing_enabled": False, "live_trading_blocked": True}
        return 200, {"data": {"order_routing_enabled": False, "live_trading_blocked": True}}

    report = verify_module.verify_research_stack(shared_secret="", http_get=fake_get)
    adapter = next(check for check in report["checks"] if check["check_id"] == "adapter_health")

    assert report["passed"] is False
    assert adapter["passed"] is False
    assert "TRADEVISION_ADAPTER_SHARED_SECRET" in adapter["evidence"]
    assert report["order_routing_enabled"] is False
    assert report["live_trading_blocked"] is True


def test_research_stack_verifier_fails_unsafe_payload():
    def fake_get(url: str, headers: dict[str, str], _timeout_ms: int) -> tuple[int, dict[str, Any]]:
        if url.endswith("/health") and headers:
            return 200, {"ok": True, "order_routing_enabled": False, "live_trading_blocked": True}
        if url.endswith("/security/posture"):
            return 200, {"data": {"overall_status": "pass", "order_routing_enabled": True, "live_trading_blocked": False}}
        return 200, {"data": {"order_routing_enabled": False, "live_trading_blocked": True}}

    report = verify_module.verify_research_stack(shared_secret="secret", http_get=fake_get)
    security = next(check for check in report["checks"] if check["check_id"] == "security_posture")

    assert report["passed"] is False
    assert security["passed"] is False
    assert "order_routing_enabled=True" in security["evidence"]
    assert "live_trading_blocked=False" in security["evidence"]


def test_research_stack_verifier_fails_endpoint_error_without_exception_escape():
    def fake_get(url: str, _headers: dict[str, str], _timeout_ms: int) -> tuple[int, dict[str, Any]]:
        if url.endswith("/deployment/readiness"):
            raise TimeoutError("deployment timed out")
        if url.endswith("/health"):
            return 200, {"ok": True, "order_routing_enabled": False, "live_trading_blocked": True}
        return 200, {"data": {"order_routing_enabled": False, "live_trading_blocked": True}}

    report = verify_module.verify_research_stack(shared_secret="secret", http_get=fake_get)
    readiness = next(check for check in report["checks"] if check["check_id"] == "deployment_readiness")

    assert report["passed"] is False
    assert readiness["passed"] is False
    assert "TimeoutError" in readiness["evidence"]
    assert report["broker_order_created"] is False
    assert report["live_trading_blocked"] is True


def test_research_stack_wrapper_reuses_existing_scripts_and_cleanup_guard():
    source = WRAPPER_PATH.read_text(encoding="utf-8")

    assert "start-research-stack.ps1" in source
    assert "verify_research_stack.py" in source
    assert "stop-research-stack.ps1" in source
    assert "finally" in source
    assert "$started" in source
    assert "TRADEVISION_ADAPTER_SHARED_SECRET" in source
    assert "place_order" not in source.lower()
    assert "submit_order" not in source.lower()
    assert "/intent-review" not in source.lower()
    assert "/api/v1/openalgo/transport/enqueue" not in source.lower()


def test_research_stack_wrapper_powershell_parser_has_no_errors():
    command = (
        "$errors=$null; "
        f"[System.Management.Automation.Language.Parser]::ParseFile('{WRAPPER_PATH}', [ref]$null, [ref]$errors) > $null; "
        "if ($errors.Count -gt 0) { $errors | ForEach-Object { Write-Output $_.Message }; exit 1 }"
    )
    result = subprocess.run(
        ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", command],
        text=True,
        capture_output=True,
        timeout=20,
    )

    assert result.returncode == 0, result.stdout + result.stderr
