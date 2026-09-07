from __future__ import annotations

import os
from pathlib import Path
from threading import Lock

from fastapi import FastAPI

from .api import router
from .contracts import DerivativesPolicy
from .fixtures import FixtureDerivativesProvider
from .openalgo import OpenAlgoDataProvider
from .service import DerivativesService
from .store import DerivativesStore

_LOCK = Lock()
_SERVICE: DerivativesService | None = None


def _env_bool(name: str, default: bool) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


def build_service(project_root: Path) -> DerivativesService:
    global _SERVICE
    if _SERVICE is not None:
        return _SERVICE
    with _LOCK:
        if _SERVICE is not None:
            return _SERVICE
        # G6: replay resolves the provider WITHOUT credentials. The replay branch
        # must not read OPENALGO_* at all (P0-8: profile=replay + absent creds
        # previously crashed with KeyError at first analyze).
        profile = os.getenv("TRADEVISION_DERIVATIVES_PROFILE", "off").strip().lower()
        db_path = Path(os.getenv("TRADEVISION_DERIVATIVES_DB", str(project_root / "data" / "orb_derivatives.db")))
        policy = DerivativesPolicy(
            max_chain_age_seconds=int(os.getenv("TRADEVISION_DERIVATIVES_MAX_AGE_SECONDS", "20")),
            minimum_chain_rows=int(os.getenv("TRADEVISION_DERIVATIVES_MIN_CHAIN_ROWS", "11")),
            minimum_greeks_coverage=float(os.getenv("TRADEVISION_DERIVATIVES_MIN_GREEKS_COVERAGE", "0.65")),
            hard_block_on_stale=_env_bool("TRADEVISION_DERIVATIVES_HARD_BLOCK_STALE", True),
        )
        if profile == "replay":
            replay_dir = Path(os.getenv("TRADEVISION_DERIVATIVES_REPLAY_DIR",
                                        str(project_root / "data" / "orb_derivatives_replay")))
            provider = FixtureDerivativesProvider(replay_dir)
        else:
            base_url = os.environ["OPENALGO_BASE_URL"]
            api_key = os.environ["OPENALGO_API_KEY"]
            provider = OpenAlgoDataProvider(
                base_url=base_url,
                api_key=api_key,
                timeout_seconds=float(os.getenv("TRADEVISION_OPENALGO_TIMEOUT_SECONDS", "4.0")),
                max_retries=int(os.getenv("TRADEVISION_OPENALGO_MAX_RETRIES", "2")),
                source_instance=os.getenv("TRADEVISION_OPENALGO_INSTANCE", "default"),
            )
        _SERVICE = DerivativesService(
            provider,
            DerivativesStore(db_path),
            policy=policy,
            interest_rate_pct=float(os.getenv("TRADEVISION_DERIVATIVES_INTEREST_RATE_PCT", "0")),
        )
        return _SERVICE


def mount(app: FastAPI, project_root: Path) -> None:
    """Opt-in route mount. Default OFF; SHADOW is research-only.

    No broker credential is loaded while OFF, preserving existing host safety.
    There is deliberately no LIVE profile in this subsystem.
    """
    profile = os.getenv("TRADEVISION_DERIVATIVES_PROFILE", "off").strip().lower()
    if profile == "off":
        return
    if profile not in {"shadow", "replay"}:
        raise ValueError("DERIVATIVES_PROFILE_MUST_BE_OFF_SHADOW_OR_REPLAY")
    if profile == "shadow":
        # Fail startup if configuration is incomplete; never silently run a
        # supposedly available derivatives layer with no provider.
        if not os.getenv("OPENALGO_BASE_URL") or not os.getenv("OPENALGO_API_KEY"):
            raise ValueError("SHADOW_DERIVATIVES_REQUIRES_OPENALGO_BASE_URL_AND_API_KEY")
    app.include_router(router(lambda: build_service(project_root)))


def resolve_context_for_symbol(symbol: str, project_root: Path, *, underlying_exchange: str = "NSE_INDEX"):
    """G9: resolve a DerivativesContext for a v1.73-style caller, or None.

    Gated by TRADEVISION_V173_DERIVATIVES=on (default off → None, zero behavior
    change). Expiry = nearest options expiry on/after today UTC (provisional
    session mapping, documented; G0 may refine to exchange-calendar sessions).
    ANY failure (flag off, no provider, no expiry, fetch error) returns None so
    the caller keeps its hand-typed/unavailable path — never raises, never blocks.
    """
    from datetime import datetime, timezone

    if os.getenv("TRADEVISION_V173_DERIVATIVES", "off").strip().lower() != "on":
        return None
    try:
        svc = build_service(project_root)
        today = datetime.now(timezone.utc).date()
        expiries = svc.provider.expiries(symbol.upper(), underlying_exchange, "options")
        upcoming = [d for d in expiries if d >= today]
        if not upcoming:
            return None
        bundle = svc.refresh(underlying=symbol.upper(), underlying_exchange=underlying_exchange,
                             expiry_date=min(upcoming), strike_count=None, scenario=None,
                             auto_resolve_futures=False, fetch_next_expiry_term=False)
        return bundle.context
    except Exception:
        return None
