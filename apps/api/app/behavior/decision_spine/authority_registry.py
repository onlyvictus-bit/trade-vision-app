from __future__ import annotations

from dataclasses import asdict, dataclass
from enum import Enum
from typing import Iterable


REGISTRY_VERSION = "decision-spine-authority-registry.v1"
FINAL_BAND_AUTHORITY = "FINAL_CONFLUENCE_ARBITER"


class EngineClassification(str, Enum):
    CALCULATOR = "calculator"
    EVIDENCE = "evidence"
    MEMORY = "memory"
    SCENARIO = "scenario"
    STRATEGY = "strategy"
    RISK = "risk"
    REVIEWER = "reviewer"
    ARBITER = "arbiter"
    COMPATIBILITY = "compatibility"
    PRESENTER = "presenter"


@dataclass(frozen=True, slots=True)
class EngineAuthority:
    engine_id: str
    module: str
    classification: EngineClassification
    may_propose: bool = False
    may_veto: bool = False
    may_downgrade: bool = False
    may_set_final_band: bool = False
    may_execute: bool = False
    authority_rank: int = 0
    canonical_consumer: str = "DecisionContext"
    lifecycle: str = "current"
    notes: str = ""

    def as_dict(self) -> dict[str, object]:
        payload = asdict(self)
        payload["classification"] = self.classification.value
        return payload


def _engine(
    engine_id: str,
    module: str,
    classification: EngineClassification,
    *,
    propose: bool = False,
    veto: bool = False,
    downgrade: bool = False,
    final: bool = False,
    rank: int = 0,
    consumer: str = "DecisionContext",
    lifecycle: str = "current",
    notes: str = "",
) -> EngineAuthority:
    return EngineAuthority(
        engine_id=engine_id,
        module=module,
        classification=classification,
        may_propose=propose,
        may_veto=veto,
        may_downgrade=downgrade,
        may_set_final_band=final,
        may_execute=False,
        authority_rank=rank,
        canonical_consumer=consumer,
        lifecycle=lifecycle,
        notes=notes,
    )


# Registry entries intentionally include the exact engine IDs emitted by the
# current Paper Guidance spine plus specialist engines that must be migrated
# into the future DecisionContext. Registering an engine does not activate it.
ENGINE_AUTHORITIES: tuple[EngineAuthority, ...] = (
    _engine("CHART_REASONING", "app.behavior.chart_reasoning_volatility", EngineClassification.EVIDENCE, rank=20),
    _engine("CANDLE_ANATOMY", "app.behavior.candle_anatomy", EngineClassification.CALCULATOR, rank=10),
    _engine("CANDLE_CONDITION", "app.behavior.condition_classifier", EngineClassification.EVIDENCE, veto=True, downgrade=True, rank=30, notes="May block clearly unsafe/fakeout/chop conditions; never sets product final band."),
    _engine("LEVEL_CONTEXT", "app.behavior.context_engines", EngineClassification.EVIDENCE, veto=True, downgrade=True, rank=30),
    _engine("SNAPSHOT_INDICATOR_RUNTIME", "app.behavior.paper_guidance_spine", EngineClassification.EVIDENCE, rank=20, notes="Snapshot-native indicator evidence only."),
    _engine("REAL_INDICATOR_RUNTIME", "app.behavior.real_indicator_adapter", EngineClassification.EVIDENCE, rank=20, lifecycle="migration", notes="Legacy/runtime adapter identity; synthetic fallback must stay non-authoritative."),
    _engine("MTF_CONFIRMATION", "app.behavior.context_engines", EngineClassification.EVIDENCE, downgrade=True, rank=30),
    _engine("PERSISTED_INDICATOR_MEMORY", "app.behavior.paper_guidance_spine", EngineClassification.MEMORY, downgrade=True, rank=25, notes="Only PIT-valid completed history may count as evidence."),
    _engine("CANONICAL_MEMORY_EPISODE_FREEZER", "app.behavior.decision_spine.canonical_memory_intelligence", EngineClassification.MEMORY, rank=0, notes="M3.3 evidence freezer only. No proposal, veto, downgrade, final-band, or execution authority."),
    _engine("CANONICAL_MEMORY_CORPUS", "app.behavior.decision_spine.memory_corpus", EngineClassification.MEMORY, rank=0, notes="PIT corpus and delayed-label evidence only; statistically honest independent counts."),
    _engine("CANONICAL_ANALOG_RETRIEVAL", "app.behavior.decision_spine.canonical_analog_memory", EngineClassification.MEMORY, rank=0, notes="Analog evidence only; raw-neighbor and independent-analog counts remain separate."),
    _engine("CANONICAL_MEMORY_WORLD", "app.behavior.decision_spine.canonical_memory_world", EngineClassification.MEMORY, rank=0, notes="Canonical M3.3 memory receipt; evidence-only and explicitly non-authoritative."),
    _engine("CANONICAL_MEMORY_RETENTION", "app.behavior.decision_spine.memory_retention", EngineClassification.MEMORY, rank=0, notes="Audit-preserving retention view; cannot change decision authority."),
    _engine("CANONICAL_PERSISTED_MEMORY_ADAPTER", "app.behavior.decision_spine.canonical_persisted_memory_adapter", EngineClassification.MEMORY, rank=0, notes="Single-query persisted-memory adapter; never converts correlated indicator rows into fake independent evidence."),
    _engine("CANONICAL_RELIABILITY_MEMORY", "app.behavior.decision_spine.canonical_reliability_memory", EngineClassification.MEMORY, rank=0, notes="Real labelled-history outcome distribution only; fixture fallback and strategy-probability authority are forbidden."),
    _engine("HISTORICAL_SESSION_MEMORY", "app.behavior.decision_spine.canonical_session_memory", EngineClassification.MEMORY, rank=0, notes="Historical session-conditioned memory only; M3.2 remains owner of current session state."),
    _engine("CANONICAL_PATTERN_MEMORY", "app.behavior.decision_spine.canonical_pattern_memory", EngineClassification.MEMORY, rank=0, notes="Day-shape v2 historical pattern evidence only; bounded retrieval and explicit missingness."),
    _engine("CANONICAL_NINE_CANDLE_MEMORY", "app.behavior.decision_spine.canonical_nine_candle_memory", EngineClassification.MEMORY, rank=0, notes="Snapshot-native 9C historical evidence only; no mock packet or synthetic fallback."),
    _engine("CANONICAL_PTA_MARKER_RUNTIME", "app.behavior.decision_spine.canonical_pta_marker_runtime", EngineClassification.EVIDENCE, rank=0, notes="D2-bound bounded PTA marker explanation evidence only."),
    _engine("M33_MEMORY_WIRING", "app.behavior.decision_spine.m3_3_memory_wiring", EngineClassification.COMPATIBILITY, rank=0, notes="Receipt transport only; cannot create authority or execute D6."),
    _engine("MARKET_STRUCTURE_LIQUIDITY", "app.behavior.market_structure_liquidity", EngineClassification.EVIDENCE, veto=True, downgrade=True, rank=40),
    _engine("MARKET_REGIME", "app.behavior.regime_gate", EngineClassification.EVIDENCE, downgrade=True, rank=30, lifecycle="migration"),
    _engine("RELATIVE_STRENGTH", "app.behavior.context_engines", EngineClassification.EVIDENCE, downgrade=True, rank=30, lifecycle="migration"),
    _engine("SECTOR_CONTEXT", "app.behavior.context_engines", EngineClassification.EVIDENCE, downgrade=True, rank=30, lifecycle="migration"),
    _engine("INDEX_CONTEXT", "app.behavior.context_engines", EngineClassification.EVIDENCE, downgrade=True, rank=30, lifecycle="migration"),
    _engine("SESSION_MEMORY", "app.behavior.session_memory", EngineClassification.MEMORY, downgrade=True, rank=25, lifecycle="migration"),
    _engine("PATTERN_MEMORY", "app.behavior.pattern_memory", EngineClassification.MEMORY, downgrade=True, rank=25, lifecycle="migration"),
    _engine("ANALOG_MEMORY", "app.behavior.analog_research", EngineClassification.MEMORY, downgrade=True, rank=25, lifecycle="migration"),
    _engine("NINE_CANDLE_MEMORY", "app.behavior.nine_candle_hybrid", EngineClassification.MEMORY, downgrade=True, rank=25, lifecycle="migration", notes="Compatibility identity; canonical 9C source is separately registered and remains zero-authority."),
    _engine("PTA_MARKER_RUNTIME", "app.behavior.real_indicator_adapter", EngineClassification.EVIDENCE, rank=10, lifecycle="migration", notes="Compatibility identity; canonical PTA evidence is separately registered and never probability or trade authority."),
    _engine("HYPOTHESIS_ENGINE", "app.behavior.hypothesis_engine", EngineClassification.SCENARIO, propose=True, downgrade=True, rank=35, lifecycle="migration"),
    _engine("ORB_CORE", "app.orb.core", EngineClassification.STRATEGY, propose=True, veto=True, downgrade=True, rank=50, lifecycle="migration"),
    _engine("AFRE", "app.orb.adaptive", EngineClassification.STRATEGY, propose=True, veto=True, downgrade=True, rank=55, lifecycle="migration", notes="Confirmed variant never bypasses proof/paper gates."),
    _engine("DERIVATIVES", "app.orb.adaptive.derivatives", EngineClassification.EVIDENCE, veto=True, downgrade=True, rank=45, lifecycle="migration", notes="Evidence/risk only; no standalone BUY/SELL authority."),
    _engine("RISK_CONTEXT", "app.orb.adaptive.risk_context", EngineClassification.RISK, veto=True, downgrade=True, rank=60, lifecycle="migration"),
    _engine("FAILURE_DETECTOR", "app.orb.adaptive.scenario_detection", EngineClassification.RISK, veto=True, downgrade=True, rank=65, lifecycle="migration"),
    _engine("EXECUTION_EVENT_OI_RISK", "app.behavior.execution_event_oi_risk", EngineClassification.RISK, veto=True, downgrade=True, rank=70),
    _engine("BEHAVIOR_RISK", "app.behavior.risk_engine", EngineClassification.RISK, veto=True, downgrade=True, rank=75, lifecycle="migration"),
    _engine("PORTFOLIO_COOLDOWN", "app.behavior.position_portfolio_cooldown", EngineClassification.RISK, veto=True, downgrade=True, rank=75, lifecycle="migration"),
    _engine("BEHAVIOR_DECISION", "app.behavior.decision_engine", EngineClassification.COMPATIBILITY, propose=True, veto=True, downgrade=True, rank=35, lifecycle="migration", notes="Legacy specialist decision evidence during migration; never canonical final authority."),
    _engine("KRONOS", "app.behavior.kronos_proxy", EngineClassification.REVIEWER, downgrade=True, rank=20, lifecycle="migration", notes="Reviewer/prior only; cannot upgrade a hard WAIT/NO_TRADE."),
    _engine("GEMINI", "app.behavior.gemini_provider", EngineClassification.REVIEWER, downgrade=True, rank=15, lifecycle="migration", notes="External AI reviewer; never safety authority."),
    _engine("GROK", "app.behavior.grok_provider", EngineClassification.REVIEWER, downgrade=True, rank=15, lifecycle="migration", notes="External AI reviewer; never safety authority."),
    _engine("OPENALGO_REPORT", "app.behavior.openalgo_report_importer", EngineClassification.REVIEWER, downgrade=True, rank=10, lifecycle="migration", notes="Imported advisory report only; no handoff or execution authority in Decision Spine."),
    _engine("TWIN_ARBITER", "app.behavior.twin_arbiter", EngineClassification.REVIEWER, downgrade=True, rank=30, lifecycle="migration", notes="Conflict evidence only after Decision Spine migration."),
    _engine("JARVIS_ARBITER", "app.behavior.jarvis_decision_arbiter", EngineClassification.COMPATIBILITY, downgrade=True, rank=20, lifecycle="migration", notes="Compatibility safety wrapper; cannot upgrade canonical final."),
    _engine("JARVIS_FUSION", "app.behavior.jarvis_decision_fusion", EngineClassification.COMPATIBILITY, downgrade=True, rank=15, lifecycle="migration", notes="Aggregation/presentation evidence during migration only."),
    _engine("JARVIS_MASTER_PANEL", "app.behavior.jarvis_master_panel", EngineClassification.PRESENTER, rank=0, consumer="Jarvis", lifecycle="migration"),
    _engine(
        FINAL_BAND_AUTHORITY,
        "app.behavior.final_confluence_arbiter",
        EngineClassification.ARBITER,
        propose=True,
        veto=True,
        downgrade=True,
        final=True,
        rank=100,
        consumer="FinalDecision",
        notes="Sole product final-band authority.",
    ),
    _engine("JARVIS_TRADING_DECISION_OUTPUT", "app.behavior.jarvis_trading_decision_output", EngineClassification.PRESENTER, rank=0, consumer="UI", lifecycle="migration", notes="Read-only presentation target; cannot originate a competing final decision."),
)


_BY_ID = {item.engine_id: item for item in ENGINE_AUTHORITIES}


def get_engine_authority(engine_id: str) -> EngineAuthority | None:
    return _BY_ID.get(str(engine_id).upper())


def all_engine_authorities() -> tuple[EngineAuthority, ...]:
    return ENGINE_AUTHORITIES


def authority_manifest() -> dict[str, object]:
    return {
        "registry_version": REGISTRY_VERSION,
        "final_band_authority": FINAL_BAND_AUTHORITY,
        "engine_count": len(ENGINE_AUTHORITIES),
        "engines": [item.as_dict() for item in ENGINE_AUTHORITIES],
        "trade_allowed": False,
        "order_routing_enabled": False,
        "live_trading_blocked": True,
    }


def validate_authority_registry(entries: Iterable[EngineAuthority] = ENGINE_AUTHORITIES) -> tuple[str, ...]:
    rows = tuple(entries)
    errors: list[str] = []
    ids = [item.engine_id for item in rows]
    if len(ids) != len(set(ids)):
        errors.append("DUPLICATE_ENGINE_ID")

    finalizers = [item.engine_id for item in rows if item.may_set_final_band]
    if finalizers != [FINAL_BAND_AUTHORITY]:
        errors.append("FINAL_BAND_AUTHORITY_MUST_BE_D6_ONLY")

    if any(item.may_execute for item in rows):
        errors.append("EXECUTION_AUTHORITY_FORBIDDEN")

    for item in rows:
        if item.classification is EngineClassification.PRESENTER and (
            item.may_propose or item.may_veto or item.may_downgrade or item.may_set_final_band or item.may_execute
        ):
            errors.append(f"PRESENTER_HAS_DECISION_AUTHORITY:{item.engine_id}")
        if item.classification is EngineClassification.REVIEWER and item.may_set_final_band:
            errors.append(f"REVIEWER_HAS_FINAL_AUTHORITY:{item.engine_id}")
    return tuple(errors)


_REGISTRY_ERRORS = validate_authority_registry()
if _REGISTRY_ERRORS:
    raise RuntimeError("Invalid Decision Spine authority registry: " + ", ".join(_REGISTRY_ERRORS))