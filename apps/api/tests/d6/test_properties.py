from dataclasses import replace
from decimal import Decimal as D
import pytest

from tradevision_d6.models import RISK_NAMES
from tools.property_audit import exhaustive_coarse_grid, ordered_grid, randomized


@pytest.mark.parametrize("case", ["LONG", "SHORT", "CONFLICT", "NO_PROOF", "NO_CAPITAL"])
def test_seeded_componentwise_and_joint_monotonicity(case):
    assert randomized(case) == 1500


def test_exhaustive_comparable_coarse_grid():
    assert exhaustive_coarse_grid() == 7533


@pytest.mark.parametrize("risk", RISK_NAMES)
def test_full_zero_to_one_risk_grid(risk):
    assert ordered_grid(risk) == 100


@pytest.mark.parametrize("risk", RISK_NAMES)
def test_cap_boundary_and_max_risk(engine, proven, risk):
    cap = getattr(proven.policy.risk_caps, risk)
    for value in (cap-D(".000000000000000001"), cap, cap+D(".000000000000000001"), D("1")):
        req = replace(proven, risks=replace(proven.risks, **{risk: value}))
        result = engine.evaluate(req)
        assert result.trade_permission <= engine.evaluate(proven).trade_permission
        assert result.long_evidence == D(".85") and result.short_evidence == D(".10")
        if value > cap:
            assert f"RISK_CAP_{risk.upper()}" in result.reasons
