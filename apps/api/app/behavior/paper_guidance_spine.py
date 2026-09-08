from __future__ import annotations

"""Public Paper Guidance facade for the Decision Spine migration.

The original implementation is preserved in ``paper_guidance_spine_legacy`` and
the canonical orchestration implementation is preserved in
``paper_guidance_spine_m2_impl`` while M3.1 migrates specialist families one at
a time. This facade keeps the historical public import/monkeypatch surface
stable.
"""

import inspect
from contextvars import ContextVar

from ..models import CandleAnatomyRequest
from . import paper_guidance_spine_legacy as _legacy
from . import paper_guidance_spine_m2_impl as _m2
from .paper_guidance_spine_legacy import *  # noqa: F401,F403
from .decision_spine.canonical_level_intelligence import (
    CanonicalLevelIntelligenceResult,
    build_canonical_level_intelligence,
)
from .decision_spine.decision_context import DecisionContextError
from .decision_spine.paper_guidance_decision_context_adapter import (
    build_canonical_stage2_observations as _build_canonical_stage2_observations,
    build_paper_guidance_decision_context,
    decision_context_audit_summary,
)
from .decision_spine.stage2_integrity import (
    Availability,
    EvidenceObservation,
    SourceMode,
    build_stage2_integrity_report,
)
from .real_indicator_adapter import (
    INDICATOR_EVIDENCE_VERSION,
    REAL_RUNTIME_PROMOTED_INDICATORS,
    build_indicator_evidence_summary,
)

# M3.1-B keeps the legacy module byte-preserved while allowing the migrated
# orchestration to construct the request contract through the compatibility
# namespace it already uses for all other Paper Guidance models.
_legacy.CandleAnatomyRequest = CandleAnatomyRequest

# The v1.88 helper predates calculator-style outputs and therefore does not
# recognize ``calculation_version``. Extend only the compatibility lookup so
# migrated deterministic calculators record their own version truthfully.
_legacy_engine_version = _legacy._engine_version


def _canonical_engine_version(value) -> str:
    calculation_version = getattr(value, "calculation_version", None)
    if calculation_version:
        return str(calculation_version)
    return _legacy_engine_version(value)


_legacy._engine_version = _canonical_engine_version

# M3.1-C reuses the exact feature-kernel object already built by M3.1-A/B. A
# ContextVar keeps request-local identity isolated across concurrent executions;
# it is cleared in ``finally`` so standalone legacy calls remain legacy calls.
_bound_feature_kernel: ContextVar[object | None] = ContextVar(
    "m31_bound_feature_kernel",
    default=None,
)
_legacy_level_context = _legacy.analyze_level_context
_legacy_run_engine = _legacy._run_engine
_legacy_snapshot_indicator_evidence = _legacy._snapshot_indicator_evidence


def __getattr__(name: str):
    return getattr(_legacy, name)


def build_canonical_stage2_observations(*, snapshot_hash: str, active_engine_ids):
    """Complete canonical inventory while preserving locked M0 migration facts."""

    observations = list(
        _build_canonical_stage2_observations(
            snapshot_hash=snapshot_hash,
            active_engine_ids=active_engine_ids,
        )
    )
    active = {str(item).strip().upper() for item in active_engine_ids if str(item).strip()}
    existing = {item.engine_id for item in observations}
    for engine_id, reason in (
        (
            "NINE_CANDLE_MEMORY",
            "Current 9C evidence is intentionally not D2-native in this Paper Guidance route; M3 migration is required.",
        ),
        (
            "PTA_MARKER_RUNTIME",
            "Current PTA marker runtime is intentionally not D2-native in this Paper Guidance route; M3 migration is required.",
        ),
    ):
        if engine_id in active or engine_id in existing:
            continue
        observations.append(
            EvidenceObservation(
                engine_id=engine_id,
                source_snapshot_hash=snapshot_hash,
                availability=Availability.SKIPPED,
                source_mode=SourceMode.UNKNOWN,
                identity_match=True,
                used_for_probability=False,
                neutral_default_substituted=False,
                final_band_claimed=False,
                future_leakage_detected=False,
                explanation_only=True,
                unavailable_reasons=(reason,),
                notes=("Locked M0 migration observation preserved by canonical Paper Guidance.",),
            )
        )
    return tuple(sorted(observations, key=lambda item: item.engine_id))


def _build_m31_guarded_decision_context(**kwargs):
    """Reject failed canonical dependencies before D6 can neutralize them."""

    receipts = {
        receipt.engine_id: receipt
        for receipt in kwargs.get("receipts", ())
        if getattr(receipt, "engine_id", None)
    }
    incomplete = [
        engine_id
        for engine_id in ("CANDLE_ANATOMY", "CANDLE_CONDITION", "CHART_REASONING")
        if engine_id not in receipts or receipts[engine_id].status != "completed"
    ]

    # LEVEL_CONTEXT may be DEGRADED when canonical sub-facts are truthfully
    # unavailable (for example no previous session in the bounded D2 lookback),
    # while its compatibility projection remains deterministic. A true engine
    # exception lacks the canonical marker and is blocked before D6.
    levels_receipt = receipts.get("LEVEL_CONTEXT")
    level_summary = getattr(levels_receipt, "output_summary", {}) if levels_receipt else {}
    canonical_level_present = bool(
        isinstance(level_summary, dict)
        and level_summary.get("canonical_level_intelligence") is True
    )
    if levels_receipt is None or not canonical_level_present:
        incomplete.append("LEVEL_CONTEXT")

    # M3.1-D: a degraded indicator receipt may be truthful (for example
    # insufficient warmup, dependency unavailable or slow-blocked). The block
    # is required only when the canonical normalization layer did not run at all
    # or did not bind its evidence to this D2 snapshot.
    indicator_receipt = receipts.get("SNAPSHOT_INDICATOR_RUNTIME")
    indicator_summary = (
        getattr(indicator_receipt, "output_summary", {}) if indicator_receipt else {}
    )
    canonical_indicator_present = bool(
        isinstance(indicator_summary, dict)
        and indicator_summary.get("canonical_indicator_intelligence") is True
        and indicator_summary.get("source_snapshot_hash")
        == getattr(indicator_receipt, "source_snapshot_hash", None)
    )
    if indicator_receipt is None or not canonical_indicator_present:
        incomplete.append("SNAPSHOT_INDICATOR_RUNTIME")

    if incomplete:
        detail = ", ".join(
            f"{engine_id}={getattr(receipts.get(engine_id), 'status', 'missing')}"
            for engine_id in incomplete
        )
        raise DecisionContextError(
            "M3.1 canonical dependency did not complete truthfully; D6 neutral substitution is forbidden: "
            + detail
        )
    return build_paper_guidance_decision_context(**kwargs)


def _canonical_level_context(request):
    kernel = _bound_feature_kernel.get()
    if kernel is None:
        return _legacy_level_context(request)
    return build_canonical_level_intelligence(request, feature_kernel=kernel)


def _canonical_run_engine(engine_id, stage, snapshot, runner, summarizer):
    if engine_id != "LEVEL_CONTEXT":
        return _legacy_run_engine(engine_id, stage, snapshot, runner, summarizer)

    # Mint the receipt only after the final canonical summary/status are known.
    # Mutating output_summary after _receipt() would break the output_hash ->
    # payload causal identity that DecisionContext relies on.
    try:
        result = runner()
        if not isinstance(result, CanonicalLevelIntelligenceResult):
            summary = summarizer(result)
            return result, _legacy._receipt(
                engine_id=engine_id,
                stage=stage,
                engine_version=_legacy._engine_version(result),
                snapshot=snapshot,
                status="completed",
                output_summary=summary,
            )

        summary = result.receipt_summary()
        summary["canonical_level_intelligence"] = True
        summary["canonical_status"] = (
            "AVAILABLE" if not result.missing_reasons else "DEGRADED"
        )
        warnings = list(result.missing_reasons)
        status = "completed" if not warnings else "degraded"
        return result, _legacy._receipt(
            engine_id=engine_id,
            stage=stage,
            engine_version=_legacy._engine_version(result),
            snapshot=snapshot,
            status=status,
            output_summary=summary,
            warnings=warnings,
        )
    except Exception as exc:
        warning = f"{engine_id} degraded safely: {type(exc).__name__}: {exc}"
        return None, _legacy._receipt(
            engine_id=engine_id,
            stage=stage,
            engine_version="unavailable",
            snapshot=snapshot,
            status="degraded",
            output_summary={"available": False},
            warnings=[warning],
        )


def _runtime_accepts_provenance(runtime) -> bool:
    try:
        params = inspect.signature(runtime).parameters.values()
    except (TypeError, ValueError):
        return False
    return any(param.kind is inspect.Parameter.VAR_KEYWORD for param in params) or {
        "source_snapshot_hash",
        "source_timeframe",
    }.issubset({param.name for param in params})


def _canonical_snapshot_indicator_evidence(request, snapshot):
    """Build bounded D2-bound canonical indicator evidence without D6 changes."""

    selected = sorted(
        set(request.indicator_ids)
        if request.indicator_ids
        else REAL_RUNTIME_PROMOTED_INDICATORS
    )
    unsupported = [item for item in selected if item not in REAL_RUNTIME_PROMOTED_INDICATORS]
    runnable = [item for item in selected if item in REAL_RUNTIME_PROMOTED_INDICATORS]
    snapshot_bars = snapshot.closed_ohlcv_bars
    compute_bars = snapshot_bars[-_legacy.SNAPSHOT_INDICATOR_WINDOW_BARS :]
    candles = [
        {
            "event_time": _legacy._iso_from_ns(bar.timestamp_ns),
            "open": bar.open,
            "high": bar.high,
            "low": bar.low,
            "close": bar.close,
            # Preserve missingness. M3.1-D must not silently turn None into 0.0.
            "volume": bar.volume,
        }
        for bar in compute_bars
    ]
    warnings = (
        [f"Indicators are not promoted for real snapshot runtime: {', '.join(unsupported)}."]
        if unsupported
        else []
    )

    try:
        runtime = compute_real_indicator_outputs_with_telemetry
        if _runtime_accepts_provenance(runtime):
            outputs, telemetry = runtime(
                candles,
                runnable,
                source_snapshot_hash=snapshot.snapshot_hash,
                source_timeframe=snapshot.timeframe,
            )
        else:
            # Existing tests and public monkeypatch hooks may still expose the
            # historical two-argument callable. Keep that surface working, but
            # classify the canonical normalization as degraded because those
            # test doubles do not provide per-indicator D2 provenance.
            outputs, telemetry = runtime(candles, runnable)

        canonical = build_indicator_evidence_summary(telemetry)
        canonical_accounting_complete = int(canonical.get("accounted_count", 0)) == len(runnable)
        degraded_ids = [
            str(item.get("indicator_id"))
            for item in telemetry
            if str(item.get("canonical_status") or item.get("status", "")).upper()
            not in {"COMPUTED", "SLOW_WARN"}
        ]
        if degraded_ids:
            warnings.append(
                f"Indicators without usable snapshot output: {', '.join(degraded_ids)}."
            )
        if not canonical_accounting_complete:
            warnings.append(
                "Canonical indicator accounting is incomplete because one or more runtime rows "
                "did not expose indicator-evidence.v1 observations."
            )

        summary = {
            "indicator_ids": selected,
            "promoted_indicator_ids": runnable,
            "computed_count": len(outputs),
            "telemetry": telemetry,
            "source_timeframe": snapshot.timeframe,
            "source_snapshot_hash": snapshot.snapshot_hash,
            "source_bar_count": snapshot.bar_count,
            "compute_window_bars": len(compute_bars),
            "canonical_indicator_intelligence": True,
            "canonical_status": (
                "AVAILABLE"
                if canonical_accounting_complete and not degraded_ids and not unsupported
                else "DEGRADED"
            ),
            "canonical": canonical,
            "used_for_final_vote": False,
            "used_for_probability": False,
            "trade_allowed": False,
            "order_routing_enabled": False,
            "live_trading_blocked": True,
        }
        status = (
            "completed"
            if summary["canonical_status"] == "AVAILABLE"
            else "degraded"
        )
    except Exception as exc:
        summary = {
            "indicator_ids": selected,
            "promoted_indicator_ids": runnable,
            "computed_count": 0,
            "telemetry": [],
            "source_timeframe": snapshot.timeframe,
            "source_snapshot_hash": snapshot.snapshot_hash,
            "source_bar_count": snapshot.bar_count,
            "compute_window_bars": len(compute_bars),
            "canonical_indicator_intelligence": False,
            "canonical_status": "ERROR",
            "canonical": {
                "calculation_version": INDICATOR_EVIDENCE_VERSION,
                "requested_count": len(selected),
                "accounted_count": 0,
                "status_counts": {"ERROR": len(selected)},
                "used_for_probability": False,
                "may_set_final_band": False,
                "may_execute": False,
            },
            "used_for_final_vote": False,
            "used_for_probability": False,
            "trade_allowed": False,
            "order_routing_enabled": False,
            "live_trading_blocked": True,
        }
        status = "degraded"
        warnings.append(f"Snapshot indicator runtime degraded safely: {type(exc).__name__}: {exc}")

    return summary, _legacy._receipt(
        engine_id="SNAPSHOT_INDICATOR_RUNTIME",
        stage="D3A_SETUP",
        engine_version=INDICATOR_EVIDENCE_VERSION,
        snapshot=snapshot,
        status=status,
        output_summary=summary,
        warnings=warnings,
    )


def _sync_patchable_dependencies():
    """Honor public monkeypatch/test hooks without changing runtime semantics."""

    for name in (
        "compute_real_indicator_outputs_with_telemetry",
        "list_indicator_signal_history_records",
        "build_chart_reasoning_report",
    ):
        if name in globals():
            setattr(_legacy, name, globals()[name])

    _legacy._snapshot_indicator_evidence = _canonical_snapshot_indicator_evidence
    _m2.build_stage2_integrity_report = build_stage2_integrity_report
    _m2.build_canonical_stage2_observations = build_canonical_stage2_observations
    _m2.build_paper_guidance_decision_context = _build_m31_guarded_decision_context
    _m2.decision_context_audit_summary = decision_context_audit_summary


def run_paper_guidance_p1(request, *, mode, kill_switch, config=None):
    _sync_patchable_dependencies()

    # Preserve monkeypatchability of the M3.1-A kernel builder while adding one
    # request-local binding operation. The delegated builder remains the sole
    # calculation; canonical levels reuse its returned object.
    delegated_kernel_builder = _m2.build_snapshot_feature_kernel

    def build_and_bind_kernel(snapshot):
        kernel = delegated_kernel_builder(snapshot)
        _bound_feature_kernel.set(kernel)
        return kernel

    _m2.build_snapshot_feature_kernel = build_and_bind_kernel
    _legacy.analyze_level_context = _canonical_level_context
    _legacy._run_engine = _canonical_run_engine
    _legacy._snapshot_indicator_evidence = _canonical_snapshot_indicator_evidence
    _bound_feature_kernel.set(None)
    try:
        return _m2.run_paper_guidance_p1(
            request,
            mode=mode,
            kill_switch=kill_switch,
            config=config,
        )
    finally:
        _bound_feature_kernel.set(None)
        _m2.build_snapshot_feature_kernel = delegated_kernel_builder
        _legacy._snapshot_indicator_evidence = _legacy_snapshot_indicator_evidence
