from __future__ import annotations

from datetime import date
from typing import Callable

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from .contracts import DerivativesIdentityError, PriceScenario
from .openalgo import OpenAlgoError
from .service import DerivativesService


class DerivativesAnalyzeRequest(BaseModel):
    underlying: str = Field(min_length=1, max_length=64)
    underlying_exchange: str = Field(default="NSE_INDEX", min_length=1, max_length=24)
    expiry_date: date
    strike_count: int | None = Field(default=25, ge=1, le=100)
    futures_symbol: str | None = Field(default=None, max_length=96)
    futures_expiry: date | None = None
    horizon_minutes: int = Field(default=30, ge=1, le=1440)
    scenario: PriceScenario | None = None
    auto_resolve_futures: bool = True


def router(service_provider: Callable[[], DerivativesService]) -> APIRouter:
    r = APIRouter(prefix="/api/v1/orb/derivatives", tags=["orb-derivatives"])

    @r.get("/health")
    def health():
        # G7: truthful readiness. Never unconditional "ready": report the profile
        # and whether the provider/store behind this mount actually constructed.
        # Any construction failure is reported (sanitized type name only), never raised.
        import os as _os

        base = {"engine_version": "orb-derivatives.v2.02", "research_only": True, "live_trading_blocked": True,
                "profile": _os.getenv("TRADEVISION_DERIVATIVES_PROFILE", "off").strip().lower()}
        try:
            svc = service_provider()
            provider_ready = svc.provider is not None
            store_ready = getattr(svc, "store", None) is not None
        except Exception as exc:  # noqa: BLE001 - readiness must never 500
            return {**base, "status": "degraded", "provider_ready": False, "store_ready": False,
                    "reason": f"{type(exc).__name__}_AT_CONSTRUCTION"}
        if provider_ready and store_ready:
            return {**base, "status": "ready", "provider_ready": True, "store_ready": True}
        return {**base, "status": "degraded", "provider_ready": bool(provider_ready), "store_ready": bool(store_ready),
                "reason": "PROVIDER_OR_STORE_NOT_READY"}

    @r.post("/analyze")
    def analyze(req: DerivativesAnalyzeRequest):
        try:
            bundle = service_provider().refresh(
                underlying=req.underlying, underlying_exchange=req.underlying_exchange,
                expiry_date=req.expiry_date, strike_count=req.strike_count,
                futures_symbol=req.futures_symbol, futures_expiry=req.futures_expiry,
                scenario=req.scenario, horizon_minutes=req.horizon_minutes,
                auto_resolve_futures=req.auto_resolve_futures,
            )
            return {
                "context": bundle.context.model_dump(mode="json"),
                "assessment": bundle.assessment.model_dump(mode="json") if bundle.assessment else None,
            }
        except DerivativesIdentityError as exc:
            # G5: caller-supplied scenario/context identity violation (not a provider
            # outage): 422, fail-closed, no assessment minted.
            raise HTTPException(status_code=422, detail=f"derivatives identity rejected: {exc}") from exc
        except OpenAlgoError as exc:
            raise HTTPException(status_code=503, detail=f"derivatives provider unavailable: {exc}") from exc

    return r
