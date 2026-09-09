from __future__ import annotations

import pytest

from app.behavior import final_release_audit


@pytest.fixture(autouse=True)
def _isolate_process_global_release_audit_cache():
    """Prevent process-global release-audit cache state from leaking between tests.

    The release audit intentionally caches expensive readiness evidence for a short
    TTL in production. Tests frequently monkeypatch its dependency functions and
    environment, so cached evidence from one test must never be visible to the
    next test. Resetting both before and after every test makes the test suite
    order-independent while preserving the production cache behavior unchanged.
    """

    final_release_audit.clear_final_release_audit_cache()
    try:
        yield
    finally:
        final_release_audit.clear_final_release_audit_cache()
