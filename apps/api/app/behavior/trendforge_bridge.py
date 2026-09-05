from __future__ import annotations

import hashlib
import hmac
import json
import os
import re
from datetime import datetime, timezone
from typing import Any
from urllib.parse import urlparse

import httpx


SCHEMA_VERSION = "trendforge-tradevision-evidence.v1"
SIGNATURE_VERSION = "trendforge-tradevision-hmac-sha256.v1"
BRIDGE_VERSION = "tradevision-trendforge-intake.v1"
LOCAL_HOSTS = {"127.0.0.1", "localhost", "::1"}
SYMBOL_PATTERN = re.compile(r"^[A-Z0-9&._ -]{1,80}$")


def _canonical_hash(value: Any) -> str:
    encoded = json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=True
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _parse_timestamp(value: Any) -> datetime:
    if not isinstance(value, str) or not value:
        raise ValueError("TrendForge evidence timestamp is missing")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValueError("TrendForge evidence timestamp is invalid") from exc
    if parsed.tzinfo is None:
        raise ValueError("TrendForge evidence timestamp must include timezone")
    return parsed.astimezone(timezone.utc)


def _verify_safety(evidence: dict[str, Any]) -> None:
    safety = evidence.get("safety")
    if not isinstance(safety, dict):
        raise ValueError("TrendForge evidence safety envelope is missing")
    safe = all(
        [
            safety.get("researchOnly") is True,
            safety.get("tradeAllowed") is False,
            safety.get("orderRoutingEnabled") is False,
            safety.get("brokerOrderCreated") is False,
            safety.get("liveTradingBlocked") is True,
        ]
    )
    if not safe:
        raise ValueError("TrendForge evidence attempts to cross the no-execution boundary")


def _candidate_counts(evidence: dict[str, Any]) -> tuple[int, int]:
    candidates = evidence.get("candidates")
    if not isinstance(candidates, list):
        raise ValueError("TrendForge candidates must be an array")
    reviewable = 0
    for row in candidates:
        if not isinstance(row, dict):
            raise ValueError("TrendForge candidate row is invalid")
        symbol = str(row.get("symbol") or "").upper()
        if not SYMBOL_PATTERN.fullmatch(symbol):
            raise ValueError("TrendForge candidate symbol is invalid")
        payload = row.get("payload")
        if not isinstance(payload, dict):
            raise ValueError("TrendForge candidate payload is missing")
        if payload.get("statusGroup") == "ready" and payload.get("state") in {
            "READY",
            "PRIORITY_RADAR",
        }:
            reviewable += 1
    return len(candidates), reviewable


def validate_trendforge_packet(
    packet: dict[str, Any],
    *,
    shared_secret: str,
    max_age_seconds: int = 120,
    now: datetime | None = None,
) -> dict[str, Any]:
    if not shared_secret.strip():
        raise ValueError("TrendForge shared secret is not configured")
    if packet.get("schemaVersion") != SCHEMA_VERSION:
        raise ValueError("Unsupported TrendForge evidence schema")
    if packet.get("signatureVersion") != SIGNATURE_VERSION:
        raise ValueError("Unsupported TrendForge signature version")
    if packet.get("transportReady") is not True:
        raise ValueError("TrendForge transport is not authenticated")
    evidence = packet.get("evidence")
    if not isinstance(evidence, dict):
        raise ValueError("TrendForge evidence payload is missing")
    expected_hash = _canonical_hash(evidence)
    supplied_hash = str(packet.get("payloadSha256") or "")
    if not hmac.compare_digest(expected_hash, supplied_hash):
        raise ValueError("TrendForge payload SHA-256 does not match evidence")
    packet_id = str(packet.get("packetId") or "")
    evidence_as_of = str(packet.get("evidenceAsOf") or "")
    signing_input = (
        f"{SIGNATURE_VERSION}.{packet_id}.{evidence_as_of}.{supplied_hash}"
    ).encode("utf-8")
    expected_signature = hmac.new(
        shared_secret.encode("utf-8"), signing_input, hashlib.sha256
    ).hexdigest()
    signature = str(packet.get("serviceSignature") or "")
    if not hmac.compare_digest(expected_signature, signature):
        raise ValueError("TrendForge service signature is invalid")
    producer = evidence.get("producer")
    if not isinstance(producer, dict) or producer.get("service") != "trendforge-api":
        raise ValueError("TrendForge producer identity is invalid")
    _verify_safety(evidence)
    candidate_count, review_count = _candidate_counts(evidence)
    observed_at = now or datetime.now(timezone.utc)
    source_time = _parse_timestamp(evidence_as_of)
    age_seconds = (observed_at.astimezone(timezone.utc) - source_time).total_seconds()
    if age_seconds < -30:
        raise ValueError("TrendForge evidence timestamp is in the future")
    stale = age_seconds > max_age_seconds
    intake_state = (
        "WAIT_STALE_TRENDFORGE_EVIDENCE" if stale else "ACCEPTED_RESEARCH_ONLY"
    )
    result = {
        "bridgeVersion": BRIDGE_VERSION,
        "intakeId": f"trendforge-intake:{packet_id}",
        "packetId": packet_id,
        "payloadSha256": supplied_hash,
        "evidenceAsOf": evidence_as_of,
        "receivedAt": observed_at.astimezone(timezone.utc).isoformat(),
        "ageSeconds": max(0.0, round(age_seconds, 3)),
        "intakeState": intake_state,
        "candidateCount": candidate_count,
        "reviewCandidateCount": 0 if stale else review_count,
        "researchReviewAllowed": not stale and candidate_count > 0,
        "openalgoHandoffAllowed": False,
        "automaticExecutionAllowed": False,
        "brokerCredentialsPresent": False,
        "brokerOrderCreated": False,
        "orderRoutingEnabled": False,
        "liveTradingBlocked": True,
        "packet": packet,
    }
    result["intakeHash"] = _canonical_hash(result)
    return result


def pull_and_validate_latest(
    *,
    base_url: str | None = None,
    shared_secret: str | None = None,
    timeout_seconds: float = 10.0,
    max_age_seconds: int = 120,
) -> dict[str, Any]:
    configured_url = (
        base_url
        or os.getenv("TRADEVISION_TRENDFORGE_URL")
        or "http://127.0.0.1:8001"
    ).rstrip("/")
    parsed = urlparse(configured_url)
    allow_remote = os.getenv("TRADEVISION_TRENDFORGE_ALLOW_REMOTE", "").lower() in {
        "1",
        "true",
        "yes",
        "on",
    }
    if parsed.scheme not in {"http", "https"} or not parsed.hostname:
        raise ValueError("TrendForge URL must be absolute HTTP(S)")
    if parsed.username or parsed.password or parsed.query or parsed.fragment:
        raise ValueError("TrendForge URL cannot contain credentials, query, or fragment")
    if not allow_remote and parsed.hostname.lower() not in LOCAL_HOSTS:
        raise ValueError("Remote TrendForge URL is blocked")
    secret = shared_secret or os.getenv("TRADEVISION_TRENDFORGE_SHARED_SECRET", "")
    try:
        response = httpx.get(
            f"{configured_url}/api/integrations/trade-vision/evidence/latest",
            timeout=timeout_seconds,
        )
        response.raise_for_status()
        packet = response.json()
    except (httpx.HTTPError, json.JSONDecodeError) as exc:
        raise ValueError(f"TrendForge pull failed: {type(exc).__name__}") from exc
    if not isinstance(packet, dict):
        raise ValueError("TrendForge returned a non-object packet")
    return validate_trendforge_packet(
        packet,
        shared_secret=secret,
        max_age_seconds=max_age_seconds,
    )
