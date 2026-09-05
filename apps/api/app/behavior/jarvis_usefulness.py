from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from typing import Any
from uuid import NAMESPACE_URL, uuid5


JARVIS_USEFULNESS_VERSION = "jarvis-usefulness-tracker.v0.96"


def build_jarvis_usefulness_record(room: dict[str, Any]) -> dict[str, Any]:
    created_at = datetime.now(timezone.utc).isoformat()
    packet = room.get("packet_metadata", {})
    widgets = room.get("extended_widgets", {})
    trust = widgets.get("trust_score_dashboard", {})
    paper = room.get("paper_reality_check", {})
    arbiter = room.get("decision_arbiter", {})
    similar = room.get("similar_history", {})
    safety = room.get("safety_summary", {})
    score = _usefulness_score(room)
    payload = {
        "symbol": room.get("symbol"),
        "timeframe": room.get("timeframe"),
        "packet_id": packet.get("packet_id"),
        "final_action": room.get("final_action"),
        "trust": trust.get("trust_score_pct"),
        "paper": paper.get("jarvis_effect", {}).get("effect"),
        "arbiter": arbiter.get("arbiter_state"),
        "matches": similar.get("total_matches_found"),
        "score": score,
    }
    record_hash = hashlib.sha256(json.dumps(payload, sort_keys=True, default=str).encode("utf-8")).hexdigest()
    usefulness_id = str(uuid5(NAMESPACE_URL, f"tradevision:jarvis-usefulness:{record_hash}"))
    return {
        "usefulness_version": JARVIS_USEFULNESS_VERSION,
        "usefulness_id": usefulness_id,
        "created_at": created_at,
        "symbol": str(room.get("symbol", "UNKNOWN")).upper(),
        "timeframe": str(room.get("timeframe", "unknown")),
        "packet_id": packet.get("packet_id"),
        "final_action": room.get("final_action", "WAIT"),
        "arbiter_state": arbiter.get("arbiter_state", "unknown"),
        "scenario_label": room.get("trade_vision_decision", {}).get("scenario_label", "unknown"),
        "trust_label": trust.get("trust_label", "unknown"),
        "trust_score_pct": int(trust.get("trust_score_pct", 0) or 0),
        "similar_match_count": int(similar.get("total_matches_found", 0) or 0),
        "minimum_sample_pass": bool(similar.get("minimum_sample_pass")),
        "paper_reality_effect": paper.get("jarvis_effect", {}).get("effect", "unknown"),
        "paper_adjusted_rr": paper.get("adjusted_risk_reward"),
        "openalgo_report_id": room.get("openalgo_summary", {}).get("latest_report_id"),
        "warning_count": len(safety.get("warning_gates", [])) + len(paper.get("jarvis_effect", {}).get("reasons", [])),
        "block_count": len(safety.get("blocking_gates", [])),
        "usefulness_score": score,
        "usefulness_label": _usefulness_label(score),
        "pending_outcome_label": True,
        "outcome_label": None,
        "manual_review_required": True,
        "trade_allowed": False,
        "order_routing_enabled": False,
        "live_trading_blocked": True,
        "record_hash": record_hash,
        "notes": [
            "v0.96 persists a Jarvis usefulness snapshot for later outcome calibration.",
            "This record is not a trade permission and cannot route orders.",
            "Outcome labels can later update usefulness, but live trading remains blocked.",
        ],
    }


def build_jarvis_usefulness_summary(*, symbol: str, records: list[dict[str, Any]]) -> dict[str, Any]:
    normalized = symbol.upper()
    scores = [float(record.get("usefulness_score", 0.0) or 0.0) for record in records]
    avg = round(sum(scores) / len(scores), 4) if scores else 0.0
    pending = sum(1 for record in records if record.get("pending_outcome_label", True))
    label_counts: dict[str, int] = {}
    for record in records:
        label = str(record.get("usefulness_label", "unknown"))
        label_counts[label] = label_counts.get(label, 0) + 1
    return {
        "summary_version": JARVIS_USEFULNESS_VERSION,
        "symbol": normalized,
        "record_count": len(records),
        "average_usefulness_score": avg,
        "average_usefulness_pct": int(round(avg * 100)),
        "pending_outcome_count": pending,
        "usefulness_label_counts": label_counts,
        "latest_records": records[:10],
        "calibration_status": "PENDING_OUTCOMES" if pending else "OUTCOME_LINKED",
        "minimum_history_pass": len(records) >= 30,
        "trade_allowed": False,
        "order_routing_enabled": False,
        "live_trading_blocked": True,
    }


def _usefulness_score(room: dict[str, Any]) -> float:
    widgets = room.get("extended_widgets", {})
    trust = widgets.get("trust_score_dashboard", {})
    paper = room.get("paper_reality_check", {})
    arbiter = room.get("decision_arbiter", {})
    similar = room.get("similar_history", {})
    score = float(trust.get("trust_score_pct", 0.0) or 0.0) / 100.0
    if similar.get("minimum_sample_pass"):
        score += 0.10
    paper_effect = paper.get("jarvis_effect", {}).get("effect", "REVIEW_ONLY")
    if paper_effect == "WAIT":
        score -= 0.18
    if paper_effect == "NO_TRADE":
        score -= 0.45
    if arbiter.get("arbiter_state") in {"SAFETY_BLOCK", "TV_NO_TRADE_AUTHORITY"}:
        score -= 0.35
    if room.get("final_action") in {"WATCH_ONLY", "WAIT"}:
        score += 0.05
    return round(max(0.0, min(score, 1.0)), 4)


def _usefulness_label(score: float) -> str:
    if score >= 0.70:
        return "high_research_usefulness"
    if score >= 0.40:
        return "medium_research_usefulness"
    return "low_research_usefulness"
