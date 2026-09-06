"""Clock-owned service boundary; decisions, receipts and approval are durable."""
from __future__ import annotations
import time
from typing import Callable
from .contracts import (PriorContext, SafetyState, APPROVAL_PHRASE, NS, day_of,
                        digest, evolve, clock_ns)
from .controller import Controller
from .runtime import (SessionState, EventBatch, new_session, advance_session, accept_proposal)
from .store import Store, Conflict
from .governance import ReviewedProof, verify_review


def view(state: SessionState) -> dict:
    """Public projection avoids repeating raw historical input on every reply."""
    return {"research_only": True, "trade_allowed": False, "live_trading_blocked": True,
            "order_routing_enabled": False, "session_date": state.session_date,
            "account_id": state.account_id, "policy_hash": state.policy_hash,
            "universe": list(state.universe), "watermark_ns": state.watermark_ns,
            "sequence": state.sequence, "last_action": state.last_action,
            "quarantine": list(state.quarantine), "approval_accepted": state.approval_accepted,
            "filled_entry_used": state.filled_entry_used,
            "proposal_hash": digest(state.active_proposal) if state.active_proposal else None,
            "active_proposal": state.active_proposal.model_dump(mode="json") if state.active_proposal else None,
            "position": state.position.model_dump(mode="json") if state.position else None,
            "decisions": {s: d.model_dump(mode="json") for s,d in state.decisions.items()}}


class Service:
    def __init__(self, store: Store, controller: Controller, *, safety: Callable[[], SafetyState],
                 clock: Callable[[], int] = time.time_ns, paper_enabled: bool = False,
                 review_provider: Callable[[], ReviewedProof | None] = lambda: None,
                 review_key: bytes = b"", historical_shadow: bool = False):
        self.store, self.controller, self.safety, self.clock = store, controller, safety, clock
        self.paper_enabled, self.review_provider, self.review_key = paper_enabled, review_provider, review_key
        self.historical_shadow = historical_shadow
        if historical_shadow and paper_enabled:
            raise ValueError("HISTORICAL_SHADOW_CANNOT_APPROVE_USER_PAPER")

    def _proof(self, state: SessionState, now: int) -> tuple[bool, str | None]:
        if not self.paper_enabled:
            return False, None
        if self.controller.data_guard is not None and not self.controller.data_guard.is_current():
            return False, None
        review = self.review_provider()  # reload: revocation/expiry is not cached
        if review is None:
            return False, None
        try:
            proof_hash = verify_review(review, self.review_key, self.controller.policy,
                                       self.controller.limits, state.universe, now, state.session_date)
            return True, proof_hash
        except ValueError:
            return False, None

    def _date(self, day: str, now: int):
        if not self.historical_shadow and day != day_of(now):
            raise ValueError("SESSION_DATE_DOES_NOT_MATCH_SERVER_CLOCK")

    def start(self, day: str, priors: tuple[PriorContext, ...], event_id: str) -> dict:
        now = self.clock()
        self._date(day, now)
        payload = {"kind": "SESSION_START", "priors": [p.model_dump(mode="json") for p in priors]}
        def transition(old):
            if old is not None:
                raise Conflict("ACCOUNT_SESSION_ALREADY_EXISTS_NO_ALLOWANCE_RESET")
            state = new_session(day, priors, self.controller.policy, self.controller.limits)
            return state, view(state)
        return self.store.transact(self.controller.limits.account_id, day, event_id, payload, transition)

    def ingest(self, day: str, event: EventBatch, *, _timer: bool = False) -> dict:
        now = self.clock()
        self._date(day, now)
        if event.available_ns > now:
            raise ValueError("EVENT_AVAILABLE_TIME_EXCEEDS_SERVER_CLOCK")
        if not self.historical_shadow and now-event.available_ns > self.controller.policy.max_feature_lag_seconds*NS:
            raise ValueError("DELIVERY_STALE_REPLAY_SEPARATELY")
        payload = {"kind": "TIMER"} if _timer else {"kind": "OBSERVATION", "event": event.model_dump(mode="json")}
        def transition(old):
            if old is None: raise Conflict("SESSION_NOT_STARTED")
            safety = self.safety()
            valid, proof_hash = self._proof(old, now)
            updated = advance_session(old, event, self.controller, safety,
                                      paper_authority=valid, proof_hash=proof_hash)
            return updated, view(updated)
        return self.store.transact(self.controller.limits.account_id, day, event.event_id, payload, transition)

    def approve(self, day: str, event_id: str, proposal_id: str, proposal_hash: str,
                quantity: int, phrase: str, actor: str) -> dict:
        now = self.clock()
        self._date(day, now)
        if phrase != APPROVAL_PHRASE:
            raise ValueError("EXPLICIT_HUMAN_APPROVAL_PHRASE_REQUIRED")
        payload = dict(kind="HUMAN_APPROVAL", proposal_id=proposal_id, proposal_hash=proposal_hash,
                       quantity=quantity, phrase=phrase, actor=actor)
        def transition(old):
            if old is None: raise Conflict("SESSION_NOT_STARTED")
            valid, proof_hash = self._proof(old, now)
            if not valid or not self.safety().allows_analysis:
                raise ValueError("CURRENT_EXACT_PROOF_AND_HOST_SAFETY_REQUIRED")
            if old.active_proposal is None:
                raise ValueError("NO_CURRENT_SERVER_OWNED_PROPOSAL")
            d = old.decisions[old.active_proposal.symbol]
            if d.public_ticket != "PAPER-CANDIDATE" or d.proof_hash != proof_hash:
                raise ValueError("PROPOSAL_IS_NOT_AUTHORIZED_BY_CURRENT_PROOF")
            # Required references must still be available at prospective fill.
            from .contracts import next_grid_ns
            fill_open = next_grid_ns(now+1, day, self.controller.policy.execution_minutes)
            caps = old.capabilities.get(old.active_proposal.symbol, ())
            for required in self.controller.policy.required_capabilities:
                if not any(c.name == required and c.status == "VALID" and c.available_ns <= now < fill_open < c.expires_ns for c in caps):
                    raise ValueError("REQUIRED_REFERENCE_EXPIRES_BEFORE_FILL")
            updated = accept_proposal(old, self.controller, proposal_id, proposal_hash, quantity, now, actor)
            return updated, view(updated)
        return self.store.transact(self.controller.limits.account_id, day, event_id, payload, transition)

    def timer(self, day: str, event_id: str) -> dict:
        # Time is always server-owned. It cannot be supplied in an approval.
        return self.ingest(day, EventBatch(event_id=event_id, available_ns=self.clock()), _timer=True)

    def inspect(self, day: str) -> dict:
        state = self.store.load(self.controller.limits.account_id, day)
        if state is None: raise KeyError("SESSION_NOT_FOUND")
        result = view(state)
        now = self.clock()
        valid, _ = self._proof(state, now)
        if state.active_proposal and (now >= state.active_proposal.expires_ns or not valid or not self.safety().allows_analysis):
            # Read-only presentation revocation; approval also checks atomically.
            result["active_proposal"] = None
            result["proposal_hash"] = None
            for decision in result["decisions"].values():
                if decision["public_ticket"] == "PAPER-CANDIDATE":
                    decision["public_ticket"] = "WATCH"
                    decision["internal_action"] = "CURRENT_PERMISSION_UNAVAILABLE_REFRESH_REQUIRED"
        return result
