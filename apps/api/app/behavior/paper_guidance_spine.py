from __future__ import annotations

"""Public Paper Guidance facade for the M2 Decision Spine migration.

The original implementation is preserved in ``paper_guidance_spine_legacy`` and
the M2 orchestration implementation is preserved in ``paper_guidance_spine_m2_impl``.
This facade keeps the historical public import/monkeypatch surface stable while
routing ``run_paper_guidance_p1`` through the M2 implementation.
"""

from . import paper_guidance_spine_legacy as _legacy
from . import paper_guidance_spine_m2_impl as _m2
from .paper_guidance_spine_legacy import *  # noqa: F401,F403
from .decision_spine.paper_guidance_decision_context_adapter import (
    build_canonical_stage2_observations,
    build_paper_guidance_decision_context,
    decision_context_audit_summary,
)
from .decision_spine.stage2_integrity import build_stage2_integrity_report


def __getattr__(name: str):
    return getattr(_legacy, name)


def _sync_patchable_dependencies() -> None:
    """Honor existing public-module monkeypatch/test hooks without changing runtime semantics."""

    for name in (
        "compute_real_indicator_outputs_with_telemetry",
        "list_indicator_signal_history_records",
        "build_chart_reasoning_report",
    ):
        if name in globals():
            setattr(_legacy, name, globals()[name])

    # These M2 boundaries are intentionally patchable for fail-closed tests and
    # future fault-injection/replay harnesses.
    _m2.build_stage2_integrity_report = build_stage2_integrity_report
    _m2.build_canonical_stage2_observations = build_canonical_stage2_observations
    _m2.build_paper_guidance_decision_context = build_paper_guidance_decision_context
    _m2.decision_context_audit_summary = decision_context_audit_summary


def run_paper_guidance_p1(request, *, mode, kill_switch, config=None):
    _sync_patchable_dependencies()
    return _m2.run_paper_guidance_p1(
        request,
        mode=mode,
        kill_switch=kill_switch,
        config=config,
    )
