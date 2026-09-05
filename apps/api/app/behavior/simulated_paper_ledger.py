from __future__ import annotations

from uuid import NAMESPACE_URL, uuid5

from ..models import (
    SimulatedPaperRecordApprovalRequest,
    SimulatedPaperTradeRecord,
    now_iso,
)
from .atomic_json_store import load_record_map, update_record_map
from .orb_guidance import load_guidance_ticket
from .paper_guidance_config import load_paper_guidance_storage_config


SIMULATED_PAPER_RECORD_VERSION = "orb-simulated-paper-record.v1.93"
SIMULATED_PAPER_STORE_PATH = load_paper_guidance_storage_config().paper_store_path


def record_simulated_paper_trade(
    request: SimulatedPaperRecordApprovalRequest,
) -> SimulatedPaperTradeRecord:
    ticket = load_guidance_ticket(request.guidance_id, require_fresh=True)
    if ticket is None:
        raise KeyError(f"ORB guidance {request.guidance_id} was not found")
    if ticket.source_snapshot_hash != request.source_snapshot_hash:
        raise ValueError("Source snapshot hash does not match the server guidance ticket")
    if not ticket.can_record_paper or ticket.final_band != "ENTER_PAPER":
        raise ValueError("Guidance is not eligible for simulated paper recording")
    if (
        ticket.entry_plan is None
        or ticket.signal is None
        or ticket.playbook_id is None
        or ticket.proof_id is None
        or ticket.proof_hash is None
    ):
        raise ValueError("Guidance ticket is missing proof-backed paper fields")

    record_id = str(
        uuid5(
            NAMESPACE_URL,
            "tradevision:simulated-paper:v1.93:"
            + ticket.guidance_id
            + ":"
            + ticket.source_snapshot_hash
        )
    )
    record = SimulatedPaperTradeRecord(
        record_version=SIMULATED_PAPER_RECORD_VERSION,
        paper_record_id=record_id,
        guidance_id=ticket.guidance_id,
        symbol=ticket.symbol,
        timeframe=ticket.timeframe,
        source_snapshot_hash=ticket.source_snapshot_hash,
        playbook_id=ticket.playbook_id,
        proof_id=ticket.proof_id,
        proof_hash=ticket.proof_hash,
        signal_type=ticket.signal.signal_type,
        side=ticket.entry_plan.side,
        entry=ticket.entry_plan.entry,
        stop=ticket.entry_plan.stop,
        target=ticket.entry_plan.target,
        invalidation=ticket.entry_plan.invalidation,
        risk_reward_ratio=ticket.entry_plan.r_ratio,
        quantity=request.quantity,
        approved_by=request.approved_by,
        approved_at=now_iso(),
        note=request.note,
    )

    def _insert(records: dict[str, dict]):
        existing = records.get(record_id)
        if existing is not None:
            return records, SimulatedPaperTradeRecord.model_validate(existing)
        records[record_id] = record.model_dump(mode="json")
        return records, record

    return update_record_map(SIMULATED_PAPER_STORE_PATH, _insert)


def list_simulated_paper_trades(
    *, symbol: str | None = None, timeframe: str | None = None
) -> list[SimulatedPaperTradeRecord]:
    rows = [
        SimulatedPaperTradeRecord.model_validate(payload)
        for payload in _load_records().values()
    ]
    return sorted(
        [
            item
            for item in rows
            if (symbol is None or item.symbol == symbol.upper())
            and (timeframe is None or item.timeframe == timeframe)
        ],
        key=lambda item: (item.approved_at, item.paper_record_id),
        reverse=True,
    )


def load_simulated_paper_trade(
    paper_record_id: str,
) -> SimulatedPaperTradeRecord | None:
    payload = _load_records().get(paper_record_id)
    return (
        None
        if payload is None
        else SimulatedPaperTradeRecord.model_validate(payload)
    )


def simulated_paper_store_rows() -> dict[str, dict]:
    return _load_records()


def _load_records() -> dict[str, dict]:
    return load_record_map(SIMULATED_PAPER_STORE_PATH)
