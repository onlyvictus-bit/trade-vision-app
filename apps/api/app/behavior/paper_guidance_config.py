from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class PaperGuidanceConfig:
    minimum_data_quality_score: float = 0.85
    minimum_evidence_count: int = 30
    low_evidence_confidence_cap: float = 0.55
    p0_confidence_cap: float = 0.60
    maximum_input_bars: int = 5_000


@dataclass(frozen=True)
class PaperGuidanceStorageConfig:
    guidance_store_path: Path
    paper_store_path: Path
    outcome_store_path: Path
    maximum_ticket_age_seconds: int = 900
    retention_days: int = 365
    maximum_observation_bars: int = 500
    spread_bps: float = 1.0
    slippage_bps: float = 1.0
    impact_bps: float = 0.5
    brokerage_bps: float = 1.0
    feedback_minimum_samples: int = 30
    feedback_quarantine_win_rate: float = 0.35


def load_paper_guidance_config() -> PaperGuidanceConfig:
    return PaperGuidanceConfig(
        minimum_data_quality_score=_env_float(
            "TRADEVISION_PAPER_GUIDANCE_MIN_DATA_QUALITY",
            0.85,
            minimum=0.0,
            maximum=1.0,
        ),
        minimum_evidence_count=_env_int(
            "TRADEVISION_PAPER_GUIDANCE_MIN_EVIDENCE",
            30,
            minimum=1,
            maximum=100_000,
        ),
        low_evidence_confidence_cap=_env_float(
            "TRADEVISION_PAPER_GUIDANCE_LOW_EVIDENCE_CAP",
            0.55,
            minimum=0.0,
            maximum=1.0,
        ),
        p0_confidence_cap=_env_float(
            "TRADEVISION_PAPER_GUIDANCE_P0_CAP",
            0.60,
            minimum=0.0,
            maximum=1.0,
        ),
        maximum_input_bars=_env_int(
            "TRADEVISION_PAPER_GUIDANCE_MAX_BARS",
            5_000,
            minimum=1,
            maximum=100_000,
        ),
    )


def load_paper_guidance_storage_config() -> PaperGuidanceStorageConfig:
    project_root = Path(__file__).resolve().parents[4]
    data_root = Path(
        os.getenv(
            "TRADEVISION_PAPER_GUIDANCE_DATA_ROOT",
            str(project_root / "data"),
        )
    ).expanduser()
    return PaperGuidanceStorageConfig(
        guidance_store_path=_env_path(
            "TRADEVISION_PAPER_GUIDANCE_TICKET_STORE",
            data_root / "orb_guidance_tickets.json",
        ),
        paper_store_path=_env_path(
            "TRADEVISION_PAPER_GUIDANCE_LEDGER_STORE",
            data_root / "orb_paper_records.json",
        ),
        outcome_store_path=_env_path(
            "TRADEVISION_PAPER_GUIDANCE_OUTCOME_STORE",
            data_root / "orb_paper_outcomes.json",
        ),
        maximum_ticket_age_seconds=_env_int(
            "TRADEVISION_PAPER_GUIDANCE_TICKET_TTL_SECONDS",
            900,
            minimum=30,
            maximum=86_400,
        ),
        retention_days=_env_int(
            "TRADEVISION_PAPER_GUIDANCE_RETENTION_DAYS",
            365,
            minimum=1,
            maximum=3_650,
        ),
        maximum_observation_bars=_env_int(
            "TRADEVISION_PAPER_GUIDANCE_MAX_OBSERVATION_BARS",
            500,
            minimum=1,
            maximum=10_000,
        ),
        spread_bps=_env_float(
            "TRADEVISION_PAPER_GUIDANCE_SPREAD_BPS",
            1.0,
            minimum=0.0,
            maximum=1_000.0,
        ),
        slippage_bps=_env_float(
            "TRADEVISION_PAPER_GUIDANCE_SLIPPAGE_BPS",
            1.0,
            minimum=0.0,
            maximum=1_000.0,
        ),
        impact_bps=_env_float(
            "TRADEVISION_PAPER_GUIDANCE_IMPACT_BPS",
            0.5,
            minimum=0.0,
            maximum=1_000.0,
        ),
        brokerage_bps=_env_float(
            "TRADEVISION_PAPER_GUIDANCE_BROKERAGE_BPS",
            1.0,
            minimum=0.0,
            maximum=1_000.0,
        ),
        feedback_minimum_samples=_env_int(
            "TRADEVISION_ORB_FEEDBACK_MIN_SAMPLES",
            30,
            minimum=1,
            maximum=100_000,
        ),
        feedback_quarantine_win_rate=_env_float(
            "TRADEVISION_ORB_FEEDBACK_QUARANTINE_WIN_RATE",
            0.35,
            minimum=0.0,
            maximum=1.0,
        ),
    )


def _env_float(name: str, default: float, *, minimum: float, maximum: float) -> float:
    raw = os.getenv(name, "").strip()
    try:
        value = float(raw) if raw else default
    except ValueError:
        value = default
    return max(minimum, min(maximum, value))


def _env_int(name: str, default: int, *, minimum: int, maximum: int) -> int:
    raw = os.getenv(name, "").strip()
    try:
        value = int(raw) if raw else default
    except ValueError:
        value = default
    return max(minimum, min(maximum, value))


def _env_path(name: str, default: Path) -> Path:
    raw = os.getenv(name, "").strip()
    return Path(raw).expanduser() if raw else default
