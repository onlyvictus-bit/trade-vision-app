from dataclasses import FrozenInstanceError, replace
from datetime import datetime
from decimal import Decimal as D
import json

import pytest

from tradevision_d6 import (
    ContractError, DirectionalEvidence, GroupSpec, Horizon, RiskVector, Side,
    SourceSpec, StressScenario, canonical_json, decode_request,
)
from tradevision_d6.codec import primitive
from tradevision_d6.models import RISK_NAMES


@pytest.mark.parametrize("name", RISK_NAMES)
@pytest.mark.parametrize("value", [D("-0.001"), D("1.001"), D("NaN"), D("Infinity"), D("-Infinity"), .2, True, None])
def test_invalid_risk_is_not_silently_clamped(request_base, name, value):
    with pytest.raises(ContractError):
        replace(request_base.risks, **{name: value})


@pytest.mark.parametrize("value", [D("NaN"), D("Infinity"), D("-1"), D("1.01"), .1, None])
def test_bad_evidence(value):
    with pytest.raises(ContractError):
        DirectionalEvidence("source", value, D("0"))


@pytest.mark.parametrize("name", ["bar_is_closed", "data_complete", "corporate_actions_checked", "event_feed_ok", "session_entry_allowed", "instrument_eligible", "short_eligible"])
@pytest.mark.parametrize("value", ["false", 1, None])
def test_flags_require_real_booleans(request_base, name, value):
    with pytest.raises(ContractError):
        replace(request_base.snapshot, **{name: value})


@pytest.mark.parametrize("name", ["bar_opened_at", "bar_closed_at", "data_received_at", "feature_available_at", "feature_cutoff_at", "quote_at"])
def test_naive_time_rejected(request_base, name):
    with pytest.raises(ContractError):
        replace(request_base.snapshot, **{name: datetime(2026, 9, 4)})


@pytest.mark.parametrize("name", ["entry", "stop", "target"])
@pytest.mark.parametrize("value", [D("0"), D("-1"), D("1e19"), D("1e-19"), D("1.1111111111111111111111111111111")])
def test_prices_bounded(request_base, name, value):
    with pytest.raises(ContractError):
        replace(request_base.plans[0], **{name: value})


@pytest.mark.parametrize("side", [Side.LONG, Side.SHORT])
def test_bad_geometry(request_base, side):
    plan = next(p for p in request_base.plans if p.side is side)
    with pytest.raises(ContractError):
        replace(plan, stop=plan.entry)
    with pytest.raises(ContractError):
        replace(plan, target=plan.entry)
    with pytest.raises(ContractError):
        replace(plan, stop=plan.target, target=plan.stop)


@pytest.mark.parametrize("name", ["round_trip_per_unit", "gap_allowance_per_unit"])
def test_costs_cannot_be_missing_or_zero(request_base, name):
    with pytest.raises(ContractError):
        replace(request_base.plans[0].costs, **{name: D("0")})


def test_frozen_inputs(request_base):
    with pytest.raises(FrozenInstanceError):
        request_base.risks.event = D("0")


def test_registry_contract(request_base):
    p = request_base.policy
    for replacement in (
        {"sources": ()}, {"groups": ()}, {"scenarios": ()},
        {"sources": p.sources + p.sources[:1]}, {"groups": p.groups + p.groups[:1]},
        {"scenarios": p.scenarios + p.scenarios[:1]},
        {"sources": (SourceSpec("x", "unknown", D("1")),)},
        {"risk_caps": None}, {"minimum_evidence": D("0")},
        {"minimum_validation_samples": 29}, {"minimum_validation_confidence": D("1")},
        {"scenarios": (StressScenario("BASE", D("1"), D("1")),)},
        {"scenarios": (StressScenario("ADVERSE", D("2"), D("3")),)},
        {"scenarios": (StressScenario("BASE", D("1"), D("1")), StressScenario("COST", D("2"), D("1")))},
        {"max_quote_age_seconds": 0}, {"sources": list(p.sources)},
    ):
        with pytest.raises(ContractError):
            replace(p, **replacement)
    with pytest.raises(ContractError):
        SourceSpec("x", "trend", D("-1"))
    with pytest.raises(ContractError):
        GroupSpec("x", D("0"))


def test_request_duplicates_unknown_sources_and_horizon(request_base, proven):
    for replacement in (
        {"evidence": request_base.evidence + request_base.evidence[:1]},
        {"evidence": (DirectionalEvidence("unregistered", D("1"), D("0")),)},
        {"plans": (request_base.plans[0], request_base.plans[0])},
        {"proofs": (proven.proofs[0], proven.proofs[0])},
        {"plans": (), "proofs": proven.proofs},
        {"snapshot": replace(request_base.snapshot, horizon=Horizon.SWING)},
        {"risks": None}, {"evidence": list(request_base.evidence)},
    ):
        with pytest.raises(ContractError):
            replace(request_base, **replacement)


def test_snapshot_and_portfolio_validation(request_base):
    s, a = request_base.snapshot, request_base.portfolio
    for replacement in ({"symbol": "bad symbol"}, {"feature_digest": "bad"}, {"session_id": ""},
                        {"data_revision": "bad\nrevision"}, {"bid": D("101")},
                        {"lot_size": True}, {"capacity_units": -1}, {"horizon": "INTRADAY"}):
        with pytest.raises(ContractError):
            replace(s, **replacement)
    for replacement in ({"equity": D("0")}, {"kill_switch": "false"}, {"daily_loss": D("-1")},
                        {"observed_at": datetime(2026, 9, 4)}, {"account_id": ""}):
        with pytest.raises(ContractError):
            replace(a, **replacement)


def test_codec_roundtrip_and_semantic_decimal(request_base, proven):
    assert decode_request(canonical_json(proven)) == proven
    assert decode_request(canonical_json(request_base)) == request_base
    assert canonical_json(D("0.10")) == canonical_json(D("0.1"))
    assert canonical_json(D("-0.0")) == '"0"'


@pytest.mark.parametrize("payload", ['{}', '{"x":1,"x":2}', 'NaN', 'Infinity', 'null', '[]', '{', 'true', '"text"'])
def test_bad_json(payload):
    with pytest.raises(ContractError):
        decode_request(payload)


@pytest.mark.parametrize("mutation", ["unknown", "missing", "bool", "fractional_integer", "float_nan", "extra_risk", "no_timezone", "huge_number", "list_limit", "wrong_object", "wrong_array"])
def test_json_fail_closed(request_base, mutation):
    obj = primitive(request_base)
    if mutation == "unknown": obj["autotrade"] = True
    if mutation == "missing": del obj["snapshot"]["bar_is_closed"]
    if mutation == "bool": obj["snapshot"]["bar_is_closed"] = "false"
    if mutation == "fractional_integer": obj["snapshot"]["lot_size"] = .5
    if mutation == "float_nan": obj["risks"]["event"] = "NaN"
    if mutation == "extra_risk": obj["evidence"][0]["risk_penalty"] = "-1"
    if mutation == "no_timezone": obj["evaluation_at"] = "2026-09-04T09:00:00"
    if mutation == "huge_number": obj["risks"]["event"] = "1" * 81
    if mutation == "list_limit": obj["evidence"] = obj["evidence"] * 33
    if mutation == "wrong_object": obj["risks"] = []
    if mutation == "wrong_array": obj["evidence"] = {}
    with pytest.raises(ContractError):
        decode_request(json.dumps(obj))


def test_payload_limit_and_unsupported_serialization():
    with pytest.raises(ContractError): decode_request(" " * 1_000_001)
    with pytest.raises(ContractError): decode_request(b"{}")
    with pytest.raises(ContractError): canonical_json(float("nan"))
    with pytest.raises(ContractError): canonical_json(D("NaN"))
    with pytest.raises(ContractError): canonical_json({1: "bad"})


def test_probability_cannot_claim_certainty(proven):
    with pytest.raises(ContractError):
        replace(proven.proofs[0], target_probability_lower_bound=D("1"))


def test_native_json_decimal_numbers(request_base):
    obj = primitive(request_base)
    obj["risks"]["event"] = .125
    obj["risks"]["trap"] = 0
    parsed = decode_request(json.dumps(obj))
    assert parsed.risks.event == D(".125") and parsed.risks.trap == D("0")
    obj["risks"]["event"] = False
    with pytest.raises(ContractError): decode_request(json.dumps(obj))
    obj["evaluation_at"] = "x"*65
    with pytest.raises(ContractError): decode_request(json.dumps(obj))


def test_nested_member_types_and_cost_type(request_base):
    with pytest.raises(ContractError): replace(request_base, evidence=(None,))
    with pytest.raises(ContractError): replace(request_base.plans[0], costs=None)
