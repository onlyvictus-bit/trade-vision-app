"""Entirely SYNTHETIC demonstration. Not market data, calibrated evidence or advice."""
from __future__ import annotations

import argparse
from dataclasses import replace
from datetime import datetime, timedelta, timezone
from decimal import Decimal as D
from pathlib import Path

from . import (
    AuditJournal, Costs, D6Engine, DecisionService, DirectionalEvidence, GroupSpec,
    Horizon, Policy, Portfolio, ProofVerifier, Request, RiskVector, Side, Snapshot,
    SourceSpec, StressScenario, TradePlan, ValidationProof, binding_digest,
    canonical_json, sign_proof,
)
from .models import REQUIRED_CHECKS

# PUBLIC, UNSAFE, DEMO-ONLY: production must inject a fresh secret from a secret
# manager and must not accept this issuer. Never import this fixture into live code.
DEMO_KEY_ID = "SYNTHETIC-DEMO-DO-NOT-TRUST"
DEMO_KEY = b"public-synthetic-demo-key-not-for-real-validation-2026"


def sample_request(*, with_proof: bool = False) -> Request:
    """Defaults to no proof -> WATCH, never an automatic candidate."""
    now = datetime(2026, 9, 4, 4, 30, 2, tzinfo=timezone.utc)
    close = now - timedelta(seconds=2)
    policy = Policy(
        revision="SYNTHETIC-POLICY-NOT-CALIBRATED-v1", horizon=Horizon.INTRADAY,
        sources=(SourceSpec("trend", "trend", D("1")),
                 SourceSpec("structure", "structure", D("1")),
                 SourceSpec("volume", "participation", D("1")),
                 SourceSpec("history", "historical", D("1"))),
        groups=(GroupSpec("trend", D("0.3")), GroupSpec("structure", D("0.3")),
                GroupSpec("participation", D("0.2")), GroupSpec("historical", D("0.2"))),
        scenarios=(StressScenario("BASE", D("1"), D("1")),
                   StressScenario("COST_SHOCK", D("2"), D("1")),
                   StressScenario("GAP_SHOCK", D("1"), D("3"))),
        risk_caps=RiskVector(*(D("0.8") for _ in range(5))),
        minimum_evidence=D("0.65"), minimum_direction_margin=D("0.10"),
        minimum_quality=D("0.50"), minimum_net_reward_risk=D("1.5"),
        minimum_modeled_expectancy=D("0.10"), risk_per_trade_fraction=D("0.005"),
        portfolio_risk_fraction=D("0.02"), daily_loss_fraction=D("0.02"),
        weekly_loss_fraction=D("0.05"), max_bar_age_seconds=600,
        max_quote_age_seconds=5, max_portfolio_age_seconds=5, max_cost_age_seconds=10,
        max_entry_drift_bps=D("10"), minimum_validation_samples=100,
        minimum_validation_confidence=D("0.95"),
        validation_embargo_seconds=86400, max_validation_age_seconds=90*86400,
        max_proof_lifetime_seconds=60,
        validation_method="SYNTHETIC-DEPENDENCE-AWARE-LCB-DEMO",
    )
    snapshot = Snapshot(
        snapshot_id="synthetic-bar-001", symbol="NSE:DEMO", session_id="SYNTHETIC-2026-09-04",
        horizon=Horizon.INTRADAY, bar_opened_at=close-timedelta(minutes=5),
        bar_closed_at=close, data_received_at=close+timedelta(milliseconds=100),
        feature_available_at=close+timedelta(milliseconds=200), feature_cutoff_at=close,
        quote_at=now-timedelta(seconds=1), feature_digest="a"*64, data_revision="synthetic-1",
        bid=D("99.95"), ask=D("100.05"), tick_size=D("0.05"), lot_size=1, capacity_units=1000,
        bar_is_closed=True, data_complete=True, corporate_actions_checked=True,
        event_feed_ok=True, session_entry_allowed=True, instrument_eligible=True,
        short_eligible=True,
    )
    portfolio = Portfolio("PAPER-DEMO", "synthetic-account-1", now-timedelta(seconds=1),
                          D("100000"), D("80000"), D("100"), D("0"), D("0"), False, False, True)
    costs = Costs(D("0.20"), D("0.20"), "SYNTHETIC-COSTS", now-timedelta(seconds=1), 1, 1000)
    plans = (TradePlan(Side.LONG, "synthetic-breakout", "b"*64, D("100"), D("98"), D("106"), D("0.95"), costs),
             TradePlan(Side.SHORT, "synthetic-breakdown", "c"*64, D("100"), D("102"), D("94"), D("0.95"), costs))
    evidence = tuple(DirectionalEvidence(s.name, D("0.85"), D("0.10")) for s in policy.sources)
    req = Request(now, snapshot, portfolio, policy, evidence, plans,
                  RiskVector(*(D("0.05") for _ in range(5))))
    return attach_synthetic_proofs(req) if with_proof else req


def attach_synthetic_proofs(request: Request, probability: D = D("0.65")) -> Request:
    proofs = []
    for plan in request.plans:
        proof = ValidationProof(
            side=plan.side, binding_digest=binding_digest(request, plan), report_digest="d"*64,
            key_id=DEMO_KEY_ID, issued_at=request.evaluation_at-timedelta(seconds=1),
            expires_at=request.evaluation_at+timedelta(seconds=30),
            validation_data_end_at=request.evaluation_at-timedelta(days=7),
            independent_samples=300, target_probability_lower_bound=probability,
            confidence_level=D("0.95"), valid_risk_envelope=request.policy.risk_caps,
            method=request.policy.validation_method, passed_checks=REQUIRED_CHECKS, signature="",
        )
        proofs.append(sign_proof(proof, DEMO_KEY))
    return replace(request, proofs=tuple(proofs))


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--audit", default="synthetic_d6_audit.sqlite3")
    parser.add_argument("--synthetic-proof", action="store_true",
                        help="Enable publicly signed SYNTHETIC demo evidence; not real validation")
    parser.add_argument("--request-out", help="Write the synthetic request JSON")
    args = parser.parse_args()
    request = sample_request(with_proof=args.synthetic_proof)
    if args.request_out:
        Path(args.request_out).write_text(canonical_json(request) + "\n", encoding="utf-8")
    engine = D6Engine(ProofVerifier({DEMO_KEY_ID: DEMO_KEY}))
    result = DecisionService(engine, AuditJournal(args.audit), replay_mode=True).evaluate(request)
    print(canonical_json({"warning": "SYNTHETIC ONLY - NO REAL SIGNAL OR VALIDATION", "result": result}))


if __name__ == "__main__":
    main()
