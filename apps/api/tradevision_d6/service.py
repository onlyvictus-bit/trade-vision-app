"""Fail-closed service boundary and bounded safety counterfactuals."""
from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import datetime, timedelta, timezone
from typing import Callable
import logging

from .audit import AuditJournal
from .codec import decode_request
from .engine import D6Engine
from .models import ContractError, Decision, ONE, RISK_NAMES, Request, RiskVector, Status, boolean, integer, timestamp

logger = logging.getLogger(__name__)


class SafetyViolation(RuntimeError):
    pass


@dataclass(frozen=True, slots=True)
class ServiceResult:
    status: Status
    decision: Decision | None
    error_code: str | None
    audit_written: bool
    counterfactual_checks: int
    evaluation_mode: str


class DecisionService:
    """Always use this boundary, not the raw kernel, in an application endpoint.

    A maximum of seven evaluations run: base + five single-risk extremes + joint
    extreme. No retries search for a passing trade; no thresholds mutate in-loop.
    """
    def __init__(self, engine: D6Engine, journal: AuditJournal, *,
                 replay_mode: bool = False,
                 clock: Callable[[], datetime] | None = None,
                 max_evaluation_lag_seconds: int = 5) -> None:
        boolean(replay_mode, "replay_mode")
        integer(max_evaluation_lag_seconds, "max_evaluation_lag_seconds", low=1, high=60)
        self.engine, self.journal = engine, journal
        self.mode = "REPLAY" if replay_mode else "PAPER"
        self.clock = clock or (lambda: datetime.now(timezone.utc))
        self.max_evaluation_lag_seconds = max_evaluation_lag_seconds

    @staticmethod
    def _assert_nonincreasing(base: Decision, worse: Decision) -> None:
        if (base.long_evidence, base.short_evidence, base.preferred_side) != (
                worse.long_evidence, worse.short_evidence, worse.preferred_side):
            raise SafetyViolation("risk changed directional evidence or preference")
        if worse.trade_permission > base.trade_permission:
            raise SafetyViolation("risk improved final permission")
        for old, new in ((base.long, worse.long), (base.short, worse.short)):
            if new.quality > old.quality or new.permission > old.permission:
                raise SafetyViolation("risk improved side quality/permission")
            if not old.eligible and new.eligible:
                raise SafetyViolation("risk created side eligibility")
        if base.status is not Status.PAPER_CANDIDATE and worse.status is Status.PAPER_CANDIDATE:
            raise SafetyViolation("risk manufactured a paper candidate")
        if worse.selected_side is not None and worse.selected_side is not base.preferred_side:
            raise SafetyViolation("risk manufactured an opposite-side fallback")

    def evaluate(self, request: Request) -> ServiceResult:
        try:
            if not isinstance(request, Request):
                raise ContractError("Request required")
            if self.mode == "PAPER":
                now = self.clock()
                timestamp(now, "service_clock")
                lag = now - request.evaluation_at
                if not timedelta(0) <= lag <= timedelta(seconds=self.max_evaluation_lag_seconds):
                    return ServiceResult(Status.WAIT, None, "EVALUATION_TIME_UNTRUSTED", False, 0, self.mode)
                if any(p.key_id.startswith("SYNTHETIC-") for p in request.proofs):
                    return ServiceResult(Status.WAIT, None, "DEMO_PROOF_NOT_ALLOWED", False, 0, self.mode)
            base = self.engine.evaluate(request)
            checks = 0
            for name in RISK_NAMES:
                risks = replace(request.risks, **{name: ONE})
                self._assert_nonincreasing(base, self.engine.evaluate(replace(request, risks=risks)))
                checks += 1
            joint = RiskVector(*(ONE for _ in RISK_NAMES))
            self._assert_nonincreasing(base, self.engine.evaluate(replace(request, risks=joint)))
            checks += 1
            self.journal.record(request, base)
            if self.mode == "PAPER" and base.status is Status.PAPER_CANDIDATE:
                delivery_time = self.clock()
                timestamp(delivery_time, "service_clock")
                if delivery_time < now:
                    return ServiceResult(Status.WAIT, None, "CLOCK_MOVED_BACKWARDS", True, checks, self.mode)
                if base.valid_until is None or delivery_time >= base.valid_until:
                    return ServiceResult(Status.WAIT, None, "CANDIDATE_EXPIRED_BEFORE_DELIVERY", True, checks, self.mode)
            return ServiceResult(base.status, base, None, True, checks, self.mode)
        except ContractError:
            logger.warning("D6 input rejected")
            return ServiceResult(Status.WAIT, None, "INPUT_CONTRACT_INVALID", False, 0, self.mode)
        except SafetyViolation:
            logger.exception("D6 counterfactual safety failure")
            return ServiceResult(Status.WAIT, None, "SAFETY_INVARIANT_FAILED", False, 0, self.mode)
        except Exception:
            # At a service boundary an infrastructure/calculation error must not
            # escape as a stale cached approval. Details stay in service logs.
            logger.exception("D6 evaluation or audit failure")
            return ServiceResult(Status.WAIT, None, "EVALUATION_OR_AUDIT_FAILED", False, 0, self.mode)

    def evaluate_json(self, payload: str) -> ServiceResult:
        try:
            request = decode_request(payload)
        except Exception:
            logger.warning("D6 request JSON rejected")
            return ServiceResult(Status.WAIT, None, "INPUT_CONTRACT_INVALID", False, 0, self.mode)
        return self.evaluate(request)
