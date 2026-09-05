from __future__ import annotations

import hashlib
import hmac
import json
from datetime import datetime, timedelta, timezone

import pytest

from app import storage
from app.behavior.trendforge_bridge import (
    SCHEMA_VERSION,
    SIGNATURE_VERSION,
    pull_and_validate_latest,
    validate_trendforge_packet,
)


SECRET = "trendforge-bridge-test-secret"


def _packet(*, age_seconds: int = 0) -> dict:
    evidence_as_of = (datetime.now(timezone.utc) - timedelta(seconds=age_seconds)).isoformat()
    evidence = {
        "producer": {"service": "trendforge-api", "mode": "guarded-research"},
        "run": {"id": 11, "runHash": "run-hash", "status": "COMPLETE"},
        "commandBar": {"system": "RESEARCH_ONLY", "safety": "GREEN"},
        "candidates": [
            {
                "recordId": 1,
                "symbol": "RELIANCE",
                "state": "WAIT_DATA_WEAK",
                "createdAt": evidence_as_of,
                "payload": {
                    "symbol": "RELIANCE",
                    "statusGroup": "reject",
                    "state": "WAIT_DATA_WEAK",
                    "risk": [{"label": "Executable", "value": "NO"}],
                },
            }
        ],
        "gateDecisions": [
            {
                "symbol": "RELIANCE",
                "gate_key": "G13_OI_CONFIRMS",
                "decision": "DO_NOT_PASS_READY",
                "state": "WAIT_MWPL_PERCENTAGES",
            }
        ],
        "sourceLineage": [
            {
                "sourceKey": "nse_fo_bhavcopy",
                "snapshotId": 309,
                "contentHash": "a" * 64,
                "parserState": "PARSED_STRUCTURED",
                "dataDate": "2026-07-10",
            }
        ],
        "safety": {
            "researchOnly": True,
            "tradeAllowed": False,
            "orderRoutingEnabled": False,
            "brokerOrderCreated": False,
            "liveTradingBlocked": True,
        },
    }
    payload_hash = hashlib.sha256(
        json.dumps(evidence, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()
    packet_id = "packet-001"
    signing_input = (
        f"{SIGNATURE_VERSION}.{packet_id}.{evidence_as_of}.{payload_hash}"
    ).encode()
    signature = hmac.new(SECRET.encode(), signing_input, hashlib.sha256).hexdigest()
    return {
        "schemaVersion": SCHEMA_VERSION,
        "signatureVersion": SIGNATURE_VERSION,
        "packetId": packet_id,
        "generatedAt": datetime.now(timezone.utc).isoformat(),
        "evidenceAsOf": evidence_as_of,
        "payloadSha256": payload_hash,
        "serviceSignature": signature,
        "transportReady": True,
        "evidence": evidence,
    }


def test_valid_packet_is_accepted_for_research_and_blocked_from_openalgo() -> None:
    result = validate_trendforge_packet(_packet(), shared_secret=SECRET)

    assert result["intakeState"] == "ACCEPTED_RESEARCH_ONLY"
    assert result["candidateCount"] == 1
    assert result["reviewCandidateCount"] == 0
    assert result["openalgoHandoffAllowed"] is False
    assert result["brokerOrderCreated"] is False
    assert result["orderRoutingEnabled"] is False
    assert result["liveTradingBlocked"] is True


def test_tampered_or_unsigned_packets_fail_closed() -> None:
    tampered = _packet()
    tampered["evidence"]["candidates"][0]["symbol"] = "TCS"
    with pytest.raises(ValueError, match="payload SHA-256"):
        validate_trendforge_packet(tampered, shared_secret=SECRET)
    with pytest.raises(ValueError, match="shared secret"):
        validate_trendforge_packet(_packet(), shared_secret="")


def test_stale_packet_is_saved_context_but_not_reviewable() -> None:
    result = validate_trendforge_packet(
        _packet(age_seconds=3600), shared_secret=SECRET, max_age_seconds=120
    )

    assert result["intakeState"] == "WAIT_STALE_TRENDFORGE_EVIDENCE"
    assert result["reviewCandidateCount"] == 0
    assert result["openalgoHandoffAllowed"] is False


def test_intake_persistence_is_idempotent(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(storage, "DB_PATH", tmp_path / "tradevision.db")
    storage._INITIALIZED_DB_TARGETS.clear()
    result = validate_trendforge_packet(_packet(), shared_secret=SECRET)

    storage.save_trendforge_intake(result)
    storage.save_trendforge_intake(result)
    rows = storage.list_trendforge_intakes(limit=10)

    assert len(rows) == 1
    assert rows[0]["packetId"] == "packet-001"


def test_loopback_pull_uses_trendforge_export_endpoint(monkeypatch) -> None:
    calls = []

    class Response:
        def raise_for_status(self):
            return None

        def json(self):
            return _packet()

    def fake_get(url, timeout):
        calls.append((url, timeout))
        return Response()

    monkeypatch.setattr("app.behavior.trendforge_bridge.httpx.get", fake_get)
    result = pull_and_validate_latest(shared_secret=SECRET)

    assert result["intakeState"] == "ACCEPTED_RESEARCH_ONLY"
    assert calls == [
        (
            "http://127.0.0.1:8001/api/integrations/trade-vision/evidence/latest",
            10.0,
        )
    ]


def test_remote_trendforge_pull_is_blocked_by_default(monkeypatch) -> None:
    monkeypatch.delenv("TRADEVISION_TRENDFORGE_ALLOW_REMOTE", raising=False)
    with pytest.raises(ValueError, match="Remote TrendForge URL is blocked"):
        pull_and_validate_latest(
            base_url="https://trendforge.example", shared_secret=SECRET
        )
