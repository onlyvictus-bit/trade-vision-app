"""Frozen action-conditional empirical value, in COMMON daily-budget units.

Records must come from registered complete action policies, including their
waiting/no-entry rules. This module does not manufacture optimal retests.
"""
from __future__ import annotations
from collections import defaultdict
import random
from statistics import mean
from typing import Literal
from .contracts import Candidate, Frozen, MarketSnapshot, Template, digest, evolve
from .forecasting import context_key


class ActionOutcome(Frozen):
    symbol: str
    limits_hash: str
    snapshot_hash: str
    action_policy_hash: str
    row_id: str
    session_date: str
    action: Template
    context_key: str
    issued_ns: int
    label_available_ns: int
    net_budget_units: float | None
    source_origin: Literal["REAL_ATTESTED", "SYNTHETIC"]
    rules_hash: str


class ValueCell(Frozen):
    action: Template
    context_key: str
    unique_dates: int
    mean: float
    lower_bound: float


class ValueModel(Frozen):
    symbols: tuple[str, ...]
    limits_hash: str
    pipeline_code_hash: str
    rules_hash: str
    validated_through_ns: int
    cells: tuple[ValueCell, ...]
    status: Literal["SUPPORTED_BY_DECLARED_TESTS", "UNSUPPORTED"]
    minimum_dates: int
    validation_report: dict
    model_hash: str


def lower_mean_bound(values: tuple[float, ...], *, seed: int = 193, repetitions: int = 512) -> float:
    if not values:
        raise ValueError("EMPTY_BOOTSTRAP")
    rng = random.Random(seed)
    block = min(5, len(values))
    def sample_mean():
        drawn = []
        while len(drawn) < len(values):
            start = rng.randrange(len(values))
            drawn.extend(values[(start+i) % len(values)] for i in range(block))
        return mean(drawn[:len(values)])
    means = sorted(sample_mean() for _ in range(repetitions))
    return means[int(.025*(repetitions-1))]


def fit_value_model(train: tuple[ActionOutcome, ...], test: tuple[ActionOutcome, ...], *, minimum_dates: int = 30) -> ValueModel:
    if not train or not test or minimum_dates < 2:
        raise ValueError("TRAIN_AND_HELD_LATER_TEST_REQUIRED")
    if max(r.session_date for r in train) >= min(r.session_date for r in test) or max(r.label_available_ns for r in train) >= min(r.issued_ns for r in test):
        raise ValueError("ACTION_LABELS_CROSS_CHRONOLOGICAL_BOUNDARY")
    if len({(r.rules_hash,r.limits_hash) for r in train+test}) != 1:
        raise ValueError("MIXED_ACTION_POLICY_DEFINITIONS")
    if any(r.label_available_ns <= r.issued_ns for r in train+test):
        raise ValueError("NON_CAUSAL_ACTION_LABEL")
    # One action/cell/date only. Do not treat correlated shadow paths as dates.
    for segment in (train,test):
        keys = [(r.session_date,r.action,r.context_key) for r in segment]
        if len(set(keys)) != len(keys):
            raise ValueError("SHADOW_PATHS_ARE_NOT_INDEPENDENT_DATE_SAMPLES")
    groups, held = defaultdict(list), defaultdict(list)
    missing = sum(r.net_budget_units is None for r in train+test)
    for r in train:
        if r.net_budget_units is not None:
            groups[(r.action,r.context_key)].append(r.net_budget_units)
    for r in test:
        if r.net_budget_units is not None:
            held[(r.action,r.context_key)].append(r.net_budget_units)
    cells, reports = [], []
    for key, vals in sorted(groups.items()):
        later = held[key]
        ok = len(vals) >= minimum_dates and len(later) >= minimum_dates
        lower = lower_mean_bound(tuple(vals))
        # A supported positive preference must also remain positive held-later.
        passed = ok and (lower <= 0 or lower_mean_bound(tuple(later)) > 0)
        reports.append({"action":key[0].value,"context":key[1],"train_dates":len(vals),"test_dates":len(later),"passed":passed})
        if passed:
            cells.append(ValueCell(action=key[0], context_key=key[1], unique_dates=len(vals),
                                   mean=mean(vals), lower_bound=lower))
    real = all(r.source_origin=="REAL_ATTESTED" for r in train+test)
    from .governance import code_fingerprint
    payload = dict(symbols=tuple(sorted(sym for sym in {r.symbol for r in train} if len({r.session_date for r in train if r.symbol==sym})>=minimum_dates and len({r.session_date for r in test if r.symbol==sym})>=minimum_dates)), limits_hash=train[0].limits_hash,
                   pipeline_code_hash=code_fingerprint(),rules_hash=train[0].rules_hash, validated_through_ns=max(r.label_available_ns for r in test),
                   cells=[c.model_dump(mode="json") for c in cells],
                   status="SUPPORTED_BY_DECLARED_TESTS" if real and not missing and cells else "UNSUPPORTED",
                   minimum_dates=minimum_dates, validation_report={"cells":reports,"unknown_outcomes":missing,
                   "interval_method":"Deterministic circular date-block percentile bootstrap (block <= 5 dates); simulation-conditional, not a universal guarantee."})
    return ValueModel(**payload, model_hash=digest(payload))


class EmpiricalActionValue:
    def __init__(self, model: ValueModel, rules_hash: str, limits_hash: str):
        if digest(model.model_dump(mode="json",exclude={"model_hash"})) != model.model_hash or rules_hash != model.rules_hash:
            raise ValueError("VALUE_MODEL_INTEGRITY_OR_RULE_BINDING_FAILED")
        from .governance import code_fingerprint
        if model.limits_hash != limits_hash or model.pipeline_code_hash != code_fingerprint():
            raise ValueError("VALUE_BUDGET_OR_PIPELINE_BINDING_FAILED")
        self.model, self.model_hash = model, model.model_hash
        self.limits_hash = limits_hash

    def annotate(self, candidate: Candidate, snapshot: MarketSnapshot, features: dict) -> Candidate:
        if candidate.status != "FEASIBLE":
            return candidate
        if self.model.status != "SUPPORTED_BY_DECLARED_TESTS" or self.model.validated_through_ns >= snapshot.as_of_ns or snapshot.prior.symbol not in self.model.symbols:
            return evolve(candidate, action_value_status="UNSUPPORTED")
        cell = next((c for c in self.model.cells if c.action == candidate.template and c.context_key == context_key(features)),None)
        if not cell:
            return evolve(candidate, action_value_status="OUT_OF_SUPPORT")
        return evolve(candidate, action_value_status="ESTIMATED", expected_net_budget_units=cell.mean,
                      lower_bound=cell.lower_bound)
