from __future__ import annotations

import hashlib
import json
from datetime import datetime, timedelta, timezone
from uuid import NAMESPACE_URL, uuid5

from ..models import (
    ExecutionIntentPaperSafetyRequest,
    ExecutorHandoffAuditEnvelope,
    ExecutorHandoffAuditRequest,
    ExecutorHandoffEvidenceBinding,
    ExecutorHandoffImmutableReceipt,
    ExecutorHandoffIntentAuditRecord,
    PaperExecutorPermissionRequest,
)
from .execution_intent_paper_safety import build_execution_intent_paper_safety_report
from .paper_executor_permission import build_paper_executor_permission_report


VERSION = "executor-handoff-audit-envelope.v0.85"
RECEIPT_VERSION = "executor-handoff-immutable-receipt.v0.85"


def build_executor_handoff_audit_envelope(
    payload: ExecutorHandoffAuditRequest | None = None,
) -> ExecutorHandoffAuditEnvelope:
    payload = payload or ExecutorHandoffAuditRequest()
    generated_at = datetime.now(timezone.utc)
    paper_safety = build_execution_intent_paper_safety_report(
        ExecutionIntentPaperSafetyRequest(
            symbol=payload.symbol,
            exchange=payload.exchange,
            target_executor=payload.target_executor,
            seed=payload.seed,
        )
    )
    permission = build_paper_executor_permission_report(
        PaperExecutorPermissionRequest(
            symbol=payload.symbol,
            exchange=payload.exchange,
            target_executor=payload.target_executor,
            requested_mode=payload.requested_mode,
            external_human_approval_present=payload.external_human_approval_present,
            secondary_approval_present=payload.secondary_approval_present,
            risk_gate_passed=payload.risk_gate_passed,
            replay_determinism_passed=payload.replay_determinism_passed,
            paper_validation_passed=payload.paper_validation_passed,
            exchange_reconciliation_ready=payload.exchange_reconciliation_ready,
            requested_by=payload.requested_by,
            seed=payload.seed,
        )
    )
    valid_until = generated_at - timedelta(seconds=1) if payload.force_expired else generated_at + timedelta(minutes=10)
    permission_rejections = permission.rejection_reasons if permission.rejected else []
    intent = _intent_record(payload, permission.mode_permission, permission_rejections, valid_until)
    bindings = [
        _binding("paper_safety", "ExecutionIntentPaperSafetyReport", paper_safety.model_dump(mode="json")),
        _binding("permission_report", "PaperExecutorPermissionReport", permission.model_dump(mode="json")),
        _binding("intent", "ExecutorHandoffIntentAuditRecord", intent.model_dump(mode="json")),
    ]
    receipt = _receipt(payload, generated_at.isoformat(), bindings, intent)
    return ExecutorHandoffAuditEnvelope(
        audit_version=VERSION,
        generated_at=generated_at.isoformat(),
        symbol=payload.symbol.upper(),
        exchange=payload.exchange.upper(),
        target_executor=payload.target_executor,
        intent=intent,
        paper_safety=paper_safety,
        permission_report=permission,
        evidence_bindings=bindings,
        receipt=receipt,
        duplicate_key_preserved=len(intent.duplicate_key) == 64,
        expiry_preserved=intent.expiry_enforced and intent.valid_until == valid_until.isoformat(),
        rejection_reasons_preserved=bool(intent.rejection_reasons) == permission.rejected or intent.duplicate_intent_blocked or intent.expired,
        export_disabled_inside_trade_vision=True,
        broker_credentials_present=False,
        broker_order_created=False,
        trade_allowed=False,
        order_routing_enabled=False,
        live_trading_blocked=True,
        notes=[
            "v0.85 creates an immutable preflight receipt for external OpenAlgo/paper-bot review.",
            "The receipt binds the v0.83 paper simulator safety report, v0.84 permission matrix, and intent audit record.",
            "Duplicate-key, expiry, and rejection reasons are preserved in the receipt payload.",
            "Trade Vision still does not export an executable order or enable routing.",
        ],
    )


def _intent_record(
    payload: ExecutorHandoffAuditRequest,
    mode_permission: str,
    permission_rejections: list[str],
    valid_until: datetime,
) -> ExecutorHandoffIntentAuditRecord:
    intent_seed = {
        "symbol": payload.symbol.upper(),
        "exchange": payload.exchange.upper(),
        "target_executor": payload.target_executor,
        "requested_mode": payload.requested_mode,
        "seed": payload.seed,
    }
    duplicate_key = _hash({"duplicate": intent_seed})
    intent_id = str(uuid5(NAMESPACE_URL, f"tradevision:v085:intent:{duplicate_key}"))
    expired = valid_until <= datetime.now(timezone.utc)
    rejections = list(permission_rejections)
    if payload.seen_duplicate_key:
        rejections.append("Duplicate intent key detected.")
    if expired:
        rejections.append("Intent is expired.")
    if not rejections:
        rejections.append("External paper review audit is ready; execution still requires external executor checks.")
    export_status = "blocked_duplicate" if payload.seen_duplicate_key else "expired" if expired else "blocked_preflight" if permission_rejections else "audit_only"
    return ExecutorHandoffIntentAuditRecord(
        intent_id=intent_id,
        duplicate_key=duplicate_key,
        duplicate_intent_blocked=payload.seen_duplicate_key,
        valid_until=valid_until.isoformat(),
        expired=expired,
        expiry_enforced=True,
        rejection_reasons=rejections,
        mode_permission=mode_permission,
        export_status=export_status,  # type: ignore[arg-type]
    )


def _binding(binding_name: str, contract_name: str, value: object) -> ExecutorHandoffEvidenceBinding:
    return ExecutorHandoffEvidenceBinding(
        binding_name=binding_name,
        contract_name=contract_name,
        sha256=_hash(value),
        required=True,
        present=True,
    )


def _receipt(
    payload: ExecutorHandoffAuditRequest,
    created_at: str,
    bindings: list[ExecutorHandoffEvidenceBinding],
    intent: ExecutorHandoffIntentAuditRecord,
) -> ExecutorHandoffImmutableReceipt:
    canonical_payload = {
        "symbol": payload.symbol.upper(),
        "exchange": payload.exchange.upper(),
        "target_executor": payload.target_executor,
        "requested_by": payload.requested_by,
        "intent_id": intent.intent_id,
        "duplicate_key": intent.duplicate_key,
        "valid_until": intent.valid_until,
        "bindings": [binding.model_dump(mode="json") for binding in bindings],
        "export_disabled_inside_trade_vision": True,
        "broker_credentials_present": False,
        "broker_order_created": False,
        "order_routing_enabled": False,
        "live_trading_blocked": True,
    }
    canonical_hash = _hash(canonical_payload)
    receipt_id = str(uuid5(NAMESPACE_URL, f"tradevision:v085:receipt:{canonical_hash}"))
    receipt_hash = _hash({"receipt_id": receipt_id, "canonical_payload_hash": canonical_hash, "created_at": created_at})
    return ExecutorHandoffImmutableReceipt(
        receipt_version=RECEIPT_VERSION,
        receipt_id=receipt_id,
        created_at=created_at,
        algorithm="sha256-canonical-json",
        canonical_payload_hash=canonical_hash,
        receipt_hash=receipt_hash,
        immutable=True,
        bound_contracts=[binding.contract_name for binding in bindings],
        forbidden_fields_absent=True,
    )


def _hash(value: object) -> str:
    raw = json.dumps(value, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()
