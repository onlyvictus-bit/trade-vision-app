"""Seeded and exhaustive D6 invariants. Uses SYNTHETIC fixtures, not market data."""
from __future__ import annotations

from dataclasses import replace
from decimal import Decimal as D
from itertools import product
import json
import random
from time import perf_counter

from tradevision_d6 import D6Engine, ProofVerifier, RiskVector
from tradevision_d6.demo import DEMO_KEY, DEMO_KEY_ID, attach_synthetic_proofs, sample_request
from tradevision_d6.models import RISK_NAMES
from tradevision_d6.service import DecisionService


def compare(base, worse):
    DecisionService._assert_nonincreasing(base, worse)
    assert worse.long.quantity <= base.long.quantity
    assert worse.short.quantity <= base.short.quantity


def scenario_request(name):
    req = sample_request(with_proof=True)
    if name == "SHORT":
        req = replace(req, evidence=tuple(replace(e, long=e.short, short=e.long) for e in req.evidence))
        req = attach_synthetic_proofs(req)
    elif name == "CONFLICT":
        req = replace(req, evidence=tuple(replace(e, short=e.long) for e in req.evidence))
        req = attach_synthetic_proofs(req)
    elif name == "NO_PROOF":
        req = replace(req, proofs=())
    elif name == "NO_CAPITAL":
        req = replace(req, portfolio=replace(req.portfolio, available_notional=D("0")))
    return req


def randomized(name, samples=250):
    engine = D6Engine(ProofVerifier({DEMO_KEY_ID: DEMO_KEY}))
    req, rng, count = scenario_request(name), random.Random(640206), 0
    for _ in range(samples):
        values = {key: D(rng.randrange(0, 2001))/D("10000") for key in RISK_NAMES}
        base_req = replace(req, risks=RiskVector(**values))
        base = engine.evaluate(base_req)
        worsening = {}
        for key in RISK_NAMES:
            fraction = D(rng.randrange(1, 10001))/D("10000")
            worsening[key] = values[key] + (D("1")-values[key])*fraction
            worse = engine.evaluate(replace(base_req, risks=replace(base_req.risks, **{key: worsening[key]})))
            compare(base, worse)
            count += 1
        joint = engine.evaluate(replace(base_req, risks=RiskVector(**worsening)))
        compare(base, joint)
        count += 1
    return count


def exhaustive_coarse_grid():
    engine = D6Engine(ProofVerifier({DEMO_KEY_ID: DEMO_KEY}))
    req = sample_request(with_proof=True)
    levels = (D("0"), D(".1"), D(".5"))
    vectors = tuple(product(levels, repeat=5))
    results = {v: engine.evaluate(replace(req, risks=RiskVector(*v))) for v in vectors}
    count = 0
    for old in vectors:
        for new in vectors:
            if old != new and all(a <= b for a, b in zip(old, new)):
                compare(results[old], results[new])
                count += 1
    return count


def ordered_grid(name):
    engine = D6Engine(ProofVerifier({DEMO_KEY_ID: DEMO_KEY}))
    req = sample_request(with_proof=True)
    previous = engine.evaluate(replace(req, risks=replace(req.risks, **{name: D("0")})))
    count = 0
    for i in range(1, 101):
        result = engine.evaluate(replace(req, risks=replace(req.risks, **{name: D(i)/D("100")})))
        compare(previous, result)
        previous = result
        count += 1
    return count


def run():
    start = perf_counter()
    random_counts = {name: randomized(name) for name in ("LONG", "SHORT", "CONFLICT", "NO_PROOF", "NO_CAPITAL")}
    coarse = exhaustive_coarse_grid()
    ordered = sum(ordered_grid(name) for name in RISK_NAMES)
    return {
        "fixture": "SYNTHETIC ONLY", "seed": 640206,
        "randomized_comparisons_by_case": random_counts,
        "exhaustive_coarse_nonidentical_comparable_pairs": coarse,
        "ordered_grid_comparisons": ordered,
        "total_comparisons": sum(random_counts.values())+coarse+ordered,
        "violations": 0, "elapsed_seconds": round(perf_counter()-start, 4),
    }


if __name__ == "__main__":
    print(json.dumps(run(), indent=2))
