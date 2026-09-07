from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Sequence

from .calculators import atm_iv, build_context
from .contracts import DerivativesContext, DerivativesPolicy, PriceScenario, ScenarioAssessment, digest
from .openalgo import OpenAlgoDataProvider, OpenAlgoError
from .reasoning import DerivativesScenarioController
from .store import DerivativesStore


@dataclass(frozen=True, slots=True)
class AnalysisBundle:
    context: DerivativesContext
    assessment: ScenarioAssessment | None


class DerivativesService:
    def __init__(
        self,
        provider: OpenAlgoDataProvider,
        store: DerivativesStore,
        *,
        policy: DerivativesPolicy | None = None,
        interest_rate_pct: float = 0.0,
    ) -> None:
        self.provider = provider
        self.store = store
        self.policy = policy or DerivativesPolicy()
        self.interest_rate_pct = interest_rate_pct
        self.controller = DerivativesScenarioController(self.policy)

    def refresh(
        self,
        *,
        underlying: str,
        underlying_exchange: str,
        expiry_date: date,
        strike_count: int | None = 25,
        futures_symbol: str | None = None,
        futures_expiry: date | None = None,
        scenario: PriceScenario | None = None,
        now_ns: int | None = None,
        horizon_minutes: int = 30,
        fetch_next_expiry_term: bool = True,
        auto_resolve_futures: bool = True,
        # G12: True only when a proved policy requires derivatives evidence.
        # G9/G10 wiring will pass True; default preserves optional-shadow behavior.
        derivatives_required: bool = False,
    ) -> AnalysisBundle:
        chain = self.provider.option_chain(
            underlying=underlying, exchange=underlying_exchange, expiry_date=expiry_date,
            strike_count=strike_count, now_ns=now_ns,
        )
        prev_chain = self.store.previous_chain(chain.underlying, chain.expiry_date.isoformat(), chain.as_of_ns)
        if futures_symbol is None and auto_resolve_futures:
            try:
                resolved = self.provider.resolve_nearest_future(chain.underlying, chain.options_exchange, on_or_after=chain.expiry_date)
                if resolved is not None:
                    futures_symbol, futures_expiry = resolved
            except OpenAlgoError:
                futures_symbol = None
        futures = self.provider.quote(futures_symbol, chain.options_exchange, now_ns=now_ns, expiry_date=futures_expiry) if futures_symbol else None
        prev_futures = self.store.previous_futures(futures.symbol, futures.as_of_ns) if futures else None
        greeks = self.provider.greeks_for_chain(chain, interest_rate_pct=self.interest_rate_pct, forward_symbol=futures_symbol)

        next_iv = None
        next_expiry_hash = None
        if fetch_next_expiry_term:
            try:
                expiries = self.provider.expiries(underlying, chain.options_exchange, "options")
                next_dates = [d for d in expiries if d > expiry_date]
                if next_dates:
                    nxt = self.provider.option_chain(
                        underlying=underlying, exchange=underlying_exchange, expiry_date=next_dates[0],
                        strike_count=min(strike_count or 10, 10), now_ns=now_ns,
                    )
                    ng = self.provider.greeks_for_chain(nxt, interest_rate_pct=self.interest_rate_pct)
                    next_iv = atm_iv(ng, nxt.atm_strike)
                    next_expiry_hash = nxt.snapshot_hash
            except OpenAlgoError:
                # Term structure is optional; primary expiry must remain analyzable.
                next_iv = None

        history = self.store.iv_history(chain.underlying, before_ns=chain.as_of_ns)
        # G11: hash every raw input so replay can re-derive and compare each one.
        greeks_hash = digest([g.model_dump(mode="json") for g in greeks]) if greeks else None
        context = build_context(
            chain, greeks, previous_chain=prev_chain, futures=futures, previous_futures=prev_futures,
            next_expiry_atm_iv_pct=next_iv, iv_history=history, now_ns=now_ns,
            horizon_minutes=horizon_minutes, policy=self.policy,
            greeks_snapshot_hash=greeks_hash, next_expiry_snapshot_hash=next_expiry_hash,
        )
        # Persist AFTER computation to preserve previous-snapshot semantics.
        self.store.put_chain(chain)
        if futures:
            self.store.put_futures(futures)
        self.store.put_context(context)
        assessment = self.controller.evaluate(scenario, context, derivatives_required=derivatives_required) if scenario is not None else None
        return AnalysisBundle(context=context, assessment=assessment)
