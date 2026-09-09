from __future__ import annotations

from app.behavior import final_release_audit
from app.behavior import transport_resilience


def test_final_release_audit_cache_invalidates_when_resilience_dependency_changes(monkeypatch):
    """A cached healthy audit must never survive a changed resilience dependency.

    Regression for the full-tree order-dependent failure where the cache key stored
    ``id(callable)`` integers. After monkeypatch teardown/allocation churn, CPython
    could reuse a released callable address and make a different dependency appear
    identical to the still-live cache entry. The cache key now retains strong
    callable references, so dependency replacement necessarily changes the key.
    """

    monkeypatch.setenv("TRADEVISION_ADAPTER_SHARED_SECRET", "cache-isolation-active-secret")
    monkeypatch.setenv("TRADEVISION_ADAPTER_PREVIOUS_SECRET", "cache-isolation-previous-secret")

    baseline = transport_resilience.build_resilience_report()
    healthy = baseline.model_copy(update={"overall_status": "healthy", "alerts": []})
    critical = baseline.model_copy(update={"overall_status": "critical"})

    final_release_audit.clear_final_release_audit_cache()

    monkeypatch.setattr(final_release_audit, "build_resilience_report", lambda: healthy)
    first = final_release_audit.build_final_release_audit(force_refresh=True)
    assert first.transport_resilience_status == "healthy"

    # Change only the dependency while the previous cache entry remains inside its
    # TTL. A correct dependency-aware cache must recompute rather than return the
    # previously cached healthy audit.
    monkeypatch.setattr(final_release_audit, "build_resilience_report", lambda: critical)
    second = final_release_audit.build_final_release_audit()

    assert second.transport_resilience_status == "critical"
    assert second.research_stack_ready is False
    assert second.production_research_release_candidate is False
    assert any(
        gate.gate_id == "transport_resilience"
        and gate.status == "fail"
        and gate.blocks_release
        for gate in second.gates
    )

    final_release_audit.clear_final_release_audit_cache()
