from __future__ import annotations

from dataclasses import dataclass

from .contracts import (
    DerivativesContext,
    DerivativesEvidence,
    DerivativesIdentityError,
    DerivativesPolicy,
    EvidenceRelation,
    PriceScenario,
    ScenarioAssessment,
    ScenarioBranch,
    ScenarioKind,
    Side,
    digest,
)


def _pct(a: float, b: float) -> float:
    return abs(a - b) / max(abs(b), 1e-12) * 100.0


@dataclass(frozen=True, slots=True)
class _Fact:
    family: str
    relation: EvidenceRelation
    code: str
    text: str
    failure: str | None = None
    block: bool = False


class DerivativesScenarioController:
    """Deterministic derivatives challenge layer for AFRE/ORB.

    It never creates a trade. It challenges an already-observed price scenario,
    groups independent evidence families, predicts concrete failure modes and
    caps guidance to WAIT/WATCH when structural conflicts are present.
    """

    def __init__(self, policy: DerivativesPolicy | None = None) -> None:
        self.policy = policy or DerivativesPolicy()

    def evaluate(self, scenario: PriceScenario, ctx: DerivativesContext, *,
                   derivatives_required: bool = False) -> ScenarioAssessment:
        # G5 admission gate: identity + PIT ordering are structural. Violations raise;
        # causality is never repaired by advancing the decision timestamp.
        self._admit(scenario, ctx)
        facts = self._facts(scenario, ctx, derivatives_required=derivatives_required)
        branches = self._branches(scenario, ctx, facts)
        support = tuple(sorted({f.family for f in facts if f.relation == EvidenceRelation.SUPPORT}))
        conflict = tuple(sorted({f.family for f in facts if f.relation in {EvidenceRelation.CONFLICT, EvidenceRelation.BLOCK}}))
        unknown = tuple(sorted({f.family for f in facts if f.relation == EvidenceRelation.UNKNOWN}))
        failures = tuple(dict.fromkeys(f.failure for f in facts if f.failure))
        blocks = [f for f in facts if f.block or f.relation == EvidenceRelation.BLOCK]
        # Precedence is intentionally conservative. Independent family count,
        # not raw fact count, prevents double-counting correlated indicators.
        if blocks:
            relation = EvidenceRelation.BLOCK
            cap = "WAIT"
        elif len(conflict) >= 2:
            relation = EvidenceRelation.CONFLICT
            cap = "WAIT"
        elif len(conflict) == 1:
            relation = EvidenceRelation.CONFLICT
            cap = "WATCH"
        elif support and not conflict:
            relation = EvidenceRelation.SUPPORT
            cap = "UNCHANGED"
        else:
            relation = EvidenceRelation.UNKNOWN
            cap = "WATCH" if ctx.status != "AVAILABLE" else "UNCHANGED"
        reasons = tuple(dict.fromkeys(f.code for f in facts))
        return ScenarioAssessment(
            symbol=scenario.symbol.upper(), as_of_ns=scenario.as_of_ns,
            scenario_kind=scenario.kind, relation=relation, public_ticket_cap=cap,
            reason_codes=reasons, branches=branches, support_families=support,
            conflict_families=conflict, unknown_families=unknown,
            predicted_failure_modes=failures,
        )

    @staticmethod
    def _admit(scenario: PriceScenario, ctx: DerivativesContext) -> None:
        if ctx.symbol.upper() != scenario.symbol.upper():
            raise DerivativesIdentityError(
                f"DERIVATIVES_SYMBOL_IDENTITY_MISMATCH: context={ctx.symbol} scenario={scenario.symbol}")
        if ctx.as_of_ns > scenario.as_of_ns:
            raise DerivativesIdentityError(
                "DERIVATIVES_CONTEXT_FROM_FUTURE: context.as_of_ns > scenario.as_of_ns")
        if scenario.expiry_date is not None and ctx.expiry_date != scenario.expiry_date:
            raise DerivativesIdentityError(
                f"DERIVATIVES_EXPIRY_MISMATCH: context={ctx.expiry_date} scenario={scenario.expiry_date}")

    def _facts(self, s: PriceScenario, c: DerivativesContext, *,
               derivatives_required: bool = False) -> tuple[_Fact, ...]:
        p = self.policy
        facts: list[_Fact] = []
        if c.status == "UNAVAILABLE":
            # G12 policy: REQUIRED-by-proved-policy blocks; OPTIONAL-shadow stays UNKNOWN
            # and contributes nothing (UNKNOWN is never support, conflict, or clean).
            if derivatives_required:
                return (_Fact("DATA_QUALITY", EvidenceRelation.BLOCK, "DERIVATIVES_REQUIRED_UNAVAILABLE",
                               "Derivatives required by policy but context unavailable", "no derivatives evidence", True),)
            return (_Fact("DATA_QUALITY", EvidenceRelation.UNKNOWN, "DERIVATIVES_UNAVAILABLE", "No usable derivatives context", block=False),)
        if c.status == "STALE":
            facts.append(_Fact("DATA_QUALITY", EvidenceRelation.BLOCK if p.hard_block_on_stale else EvidenceRelation.UNKNOWN,
                               "DERIVATIVES_STALE", f"Chain age {c.stale_seconds:.1f}s exceeds policy", "stale derivatives can invert apparent wall/OI state", p.hard_block_on_stale))
        elif c.status == "PARTIAL":
            facts.append(_Fact("DATA_QUALITY", EvidenceRelation.UNKNOWN, "DERIVATIVES_PARTIAL", "Derivatives context is partial"))

        if s.side is None or s.entry is None:
            facts.append(_Fact("SCENARIO_BINDING", EvidenceRelation.UNKNOWN, "NO_SIDE_OR_ENTRY", "Price scenario has no side/entry to challenge"))
            return tuple(facts)

        side = s.side
        entry = s.entry
        target = s.target
        obstruction = c.call_gamma_wall if side == Side.LONG else c.put_gamma_wall
        oi_obstruction = c.call_oi_wall if side == Side.LONG else c.put_oi_wall
        if obstruction is not None:
            ahead = obstruction.strike > entry if side == Side.LONG else obstruction.strike < entry
            dist = _pct(obstruction.strike, entry)
            if ahead and dist <= p.near_wall_pct:
                target_beyond = target is not None and ((target > obstruction.strike) if side == Side.LONG else (target < obstruction.strike))
                facts.append(_Fact("GAMMA_STRUCTURE", EvidenceRelation.CONFLICT,
                                   "GAMMA_WALL_AHEAD", f"{side} candidate has gamma-concentration wall {dist:.3f}% ahead",
                                   "breakout can stall/reject at nearby gamma concentration" + (" before target" if target_beyond else "")))
            else:
                facts.append(_Fact("GAMMA_STRUCTURE", EvidenceRelation.SUPPORT, "NO_NEAR_GAMMA_WALL_AHEAD", "No near gamma wall obstructs candidate"))
        else:
            facts.append(_Fact("GAMMA_STRUCTURE", EvidenceRelation.UNKNOWN, "GAMMA_WALL_UNKNOWN", "Gamma wall unavailable"))

        if oi_obstruction is not None:
            ahead = oi_obstruction.strike > entry if side == Side.LONG else oi_obstruction.strike < entry
            dist = _pct(oi_obstruction.strike, entry)
            if ahead and dist <= p.near_wall_pct and oi_obstruction.state in {"STRENGTHENING", "FORMING", "STABLE"}:
                facts.append(_Fact("OI_STRUCTURE", EvidenceRelation.CONFLICT, "OI_WALL_AHEAD",
                                   f"{side} candidate faces {oi_obstruction.state.lower()} OI wall {dist:.3f}% ahead",
                                   "price may reject or pin before the intended target"))
            elif oi_obstruction.state in {"UNWINDING", "WEAKENING"}:
                facts.append(_Fact("OI_STRUCTURE", EvidenceRelation.SUPPORT, "OI_WALL_WEAKENING", "Nearest opposing OI wall is weakening/unwinding"))

        if c.max_pain_distance_pct is not None:
            if s.expiry_day and c.max_pain_distance_pct <= p.pin_active_pct:
                facts.append(_Fact("EXPIRY_PINNING", EvidenceRelation.CONFLICT, "ACTIVE_MAX_PAIN_PIN",
                                   f"Expiry-day entry is {c.max_pain_distance_pct:.3f}% from max pain",
                                   "expiry pinning can suppress continuation and create two-sided chop"))
            elif c.max_pain_distance_pct <= p.pin_nearby_pct:
                facts.append(_Fact("EXPIRY_PINNING", EvidenceRelation.UNKNOWN, "MAX_PAIN_NEARBY", "Max pain is nearby but not an automatic directional signal"))

        if c.oi_concentration_pct is not None and s.expiry_day and c.oi_concentration_pct >= p.high_oi_concentration_pct:
            facts.append(_Fact("EXPIRY_PINNING", EvidenceRelation.CONFLICT, "HIGH_OI_CONCENTRATION_EXPIRY",
                               f"Top strikes hold {c.oi_concentration_pct:.1f}% of chain OI",
                               "concentrated expiry OI can increase pin/whipsaw risk"))

        if target is not None:
            target_move = _pct(target, entry)
            em = c.iv_horizon_expected_move_pct or c.atm_straddle_expected_move_pct
            if em is not None and target_move > em * p.expected_move_target_buffer:
                facts.append(_Fact("TARGET_FEASIBILITY", EvidenceRelation.CONFLICT, "TARGET_BEYOND_EXPECTED_MOVE",
                                   f"Target move {target_move:.3f}% exceeds expected-move allowance {em*p.expected_move_target_buffer:.3f}%",
                                   "target can be structurally valid but statistically stretched for the horizon"))
            elif em is not None:
                facts.append(_Fact("TARGET_FEASIBILITY", EvidenceRelation.SUPPORT, "TARGET_WITHIN_EXPECTED_MOVE", "Target is within expected-move allowance"))
            else:
                facts.append(_Fact("TARGET_FEASIBILITY", EvidenceRelation.UNKNOWN, "EXPECTED_MOVE_UNKNOWN", "Expected move unavailable"))

        if c.futures_state != "UNKNOWN":
            aligned = (side == Side.LONG and c.futures_state in {"LONG_BUILDUP", "SHORT_COVERING"}) or (
                side == Side.SHORT and c.futures_state in {"SHORT_BUILDUP", "LONG_UNWINDING"}
            )
            opposed = (side == Side.LONG and c.futures_state in {"SHORT_BUILDUP", "LONG_UNWINDING"}) or (
                side == Side.SHORT and c.futures_state in {"LONG_BUILDUP", "SHORT_COVERING"}
            )
            if aligned:
                facts.append(_Fact("FUTURES_POSITIONING", EvidenceRelation.SUPPORT, "FUTURES_POSITIONING_ALIGNED", f"Futures state {c.futures_state} aligns with {side}"))
            elif opposed:
                facts.append(_Fact("FUTURES_POSITIONING", EvidenceRelation.CONFLICT, "FUTURES_POSITIONING_OPPOSES", f"Futures state {c.futures_state} opposes {side}", "cash/ORB breakout can fail when futures positioning diverges"))

        if c.iv_percentile is not None and c.iv_percentile >= p.high_iv_percentile:
            facts.append(_Fact("VOLATILITY_REGIME", EvidenceRelation.UNKNOWN, "HIGH_IV_PERCENTILE", f"IV percentile {c.iv_percentile:.1f} is elevated; widen uncertainty, do not infer direction", "high IV can amplify both breakout and failure magnitude"))

        if c.pcr_oi is not None:
            if c.pcr_oi >= p.extreme_pcr_high or c.pcr_oi <= p.extreme_pcr_low:
                facts.append(_Fact("PCR", EvidenceRelation.UNKNOWN, "PCR_EXTREME", f"PCR-OI {c.pcr_oi:.3f} is extreme; treated as context, not a direction vote", "crowded option positioning can unwind nonlinearly"))

        if c.skew_25d_pct is not None and abs(c.skew_25d_pct) >= p.skew_tail_warning_pct:
            # Positive put-minus-call skew is downside-tail demand. Negative is upside-tail demand.
            against = (side == Side.LONG and c.skew_25d_pct > 0) or (side == Side.SHORT and c.skew_25d_pct < 0)
            facts.append(_Fact(
                "SKEW", EvidenceRelation.CONFLICT if against else EvidenceRelation.UNKNOWN,
                "SKEW_TAIL_RISK_AGAINST" if against else "SKEW_TAIL_RISK_PRESENT",
                f"25-delta put-minus-call IV skew is {c.skew_25d_pct:.3f} vol points",
                "asymmetric tail demand can precede rejection or accelerate an adverse break" if against else "tail demand is elevated but is not a standalone direction signal",
            ))

        if c.term_structure_spread_pct is not None and c.term_structure_spread_pct >= p.term_inversion_warning_pct:
            facts.append(_Fact(
                "TERM_STRUCTURE", EvidenceRelation.UNKNOWN, "TERM_STRUCTURE_INVERTED",
                f"Near-minus-next ATM IV is {c.term_structure_spread_pct:.3f} vol points",
                "event/expiry premium can create expansion followed by rapid IV crush",
            ))

        if c.futures_basis_pct is not None and abs(c.futures_basis_pct) >= p.futures_basis_warning_pct:
            opposed_basis = (side == Side.LONG and c.futures_basis_pct < 0) or (side == Side.SHORT and c.futures_basis_pct > 0)
            facts.append(_Fact(
                "FUTURES_BASIS", EvidenceRelation.CONFLICT if opposed_basis else EvidenceRelation.UNKNOWN,
                "FUTURES_BASIS_OPPOSES" if opposed_basis else "FUTURES_BASIS_EXTREME",
                f"Futures basis is {c.futures_basis_pct:.3f}% versus spot",
                "basis divergence can warn that the spot ORB is not confirmed by derivatives" if opposed_basis else "large basis requires context; carry and expiry effects can dominate",
            ))

        if c.call_gamma_wall is not None and c.put_gamma_wall is not None:
            inside = c.put_gamma_wall.strike < entry < c.call_gamma_wall.strike
            call_d = _pct(c.call_gamma_wall.strike, entry)
            put_d = _pct(c.put_gamma_wall.strike, entry)
            if inside and max(call_d, put_d) <= p.near_wall_pct:
                facts.append(_Fact(
                    "GAMMA_CONFINEMENT", EvidenceRelation.CONFLICT, "BETWEEN_NEAR_GAMMA_WALLS",
                    f"Entry is confined between put/call gamma walls ({put_d:.3f}%/{call_d:.3f}%)",
                    "two-sided gamma concentration can suppress expansion and increase chop",
                ))

        if s.kind in {ScenarioKind.CONTINUATION, ScenarioKind.RETEST, ScenarioKind.RECLAIM} and s.chop_risk:
            facts.append(_Fact("PRICE_STATE", EvidenceRelation.CONFLICT, "PRICE_CHOP_ALREADY_PRESENT", "Price engine already reports chop risk", "another breakout attempt can become a double-stop whipsaw"))
        return tuple(facts)

    def _branches(self, s: PriceScenario, c: DerivativesContext, facts: tuple[_Fact, ...]) -> tuple[ScenarioBranch, ...]:
        ids = {f.code: digest({"context": c.context_hash, "scenario": s.model_dump(mode="json"), "code": f.code}) for f in facts}
        def select(*families: str) -> tuple[_Fact, ...]:
            return tuple(f for f in facts if f.family in families)
        def branch(name: str, selected: tuple[_Fact, ...], failure: str, nxt: str, refute: str) -> ScenarioBranch:
            rels = {f.relation for f in selected}
            if EvidenceRelation.BLOCK in rels:
                state, rel = "BLOCKED", EvidenceRelation.BLOCK
            elif EvidenceRelation.CONFLICT in rels:
                state, rel = "CONFLICTED", EvidenceRelation.CONFLICT
            elif EvidenceRelation.SUPPORT in rels:
                state, rel = "SUPPORTED", EvidenceRelation.SUPPORT
            elif selected:
                state, rel = "UNKNOWN", EvidenceRelation.UNKNOWN
            else:
                state, rel = "POSSIBLE", EvidenceRelation.UNKNOWN
            return ScenarioBranch(
                branch_id=name, state=state, relation=rel,
                reason_codes=tuple(f.code for f in selected), evidence_ids=tuple(ids[f.code] for f in selected),
                predicted_failure_mode=failure if state in {"CONFLICTED", "BLOCKED"} else None,
                next_required=nxt, refute_on=refute,
            )
        return (
            branch("DERIVATIVES_SUPPORTED_CONTINUATION", select("FUTURES_POSITIONING", "TARGET_FEASIBILITY"),
                   "continuation lacks cross-market confirmation", "fresh futures/OI confirmation on next closed feature bar", "futures positioning reverses or target becomes stretched"),
            branch("WALL_REJECTION_FAILURE", select("GAMMA_STRUCTURE", "OI_STRUCTURE"),
                   "breakout rejects at nearby gamma/OI concentration", "accepted close through wall plus wall weakening", "wall unwinds or price accepts beyond it"),
            branch("GAMMA_CONFINEMENT_CHOP", select("GAMMA_CONFINEMENT"),
                   "price remains trapped between nearby gamma concentrations", "accepted close outside the wall range with fresh chain confirmation", "one wall decays or price holds beyond it"),
            branch("EXPIRY_PINNING_CHOP", select("EXPIRY_PINNING"),
                   "max-pain/OI concentration pins price into two-sided chop", "persistent acceptance away from pin zone", "distance from pin expands with supportive OI migration"),
            branch("TARGET_STRETCH_FAILURE", select("TARGET_FEASIBILITY"),
                   "price structure survives but target is unreachable inside the intended horizon", "expected move expands or target is recalibrated", "target returns inside the registered expected-move envelope"),
            branch("FUTURES_DIVERGENCE_FAILURE", select("FUTURES_POSITIONING", "FUTURES_BASIS"),
                   "spot ORB fails because futures positioning/basis does not confirm", "futures price/OI and basis reconverge with spot", "fresh futures state aligns with candidate"),
            branch("SKEW_TAIL_FAILURE", select("SKEW"),
                   "asymmetric tail demand precedes or magnifies an adverse reversal", "skew normalizes while price acceptance persists", "tail skew collapses without adverse price response"),
            branch("TERM_STRUCTURE_EVENT_RISK", select("TERM_STRUCTURE"),
                   "near-expiry/event volatility expands then crushes, invalidating static range assumptions", "term structure normalizes or event window passes", "near-minus-next IV spread falls below policy threshold"),
            branch("VOLATILITY_EXHAUSTION", select("VOLATILITY_REGIME", "PCR"),
                   "volatility/crowding produces overshoot then reversal", "continued acceptance without IV/OI contradiction", "volatility normalizes while price structure holds"),
            branch("PRICE_CHOP_DOUBLE_STOP", select("PRICE_STATE"),
                   "another breakout attempt becomes a two-sided double-stop whipsaw", "sustained accepted escape with lower overlap", "chop signature clears"),
            branch("DATA_QUALITY_FAILURE", select("DATA_QUALITY"),
                   "stale/partial derivatives context gives false confidence", "fresh complete chain and Greeks", "validated fresh replacement snapshot"),
            branch("UNKNOWN_DERIVATIVES_REGIME", select("SCENARIO_BINDING"),
                   "unregistered or insufficiently observed derivatives state", "new independently verified evidence without future leakage", "registered evidence makes the state observable"),
        )
