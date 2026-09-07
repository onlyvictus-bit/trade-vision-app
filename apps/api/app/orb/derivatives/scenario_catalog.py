from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class FailureScenario:
    scenario_id: str
    family: str
    description: str
    observable_requirements: tuple[str, ...]
    defensive_action: str
    falsification: str


CATALOG: tuple[FailureScenario, ...] = (
    FailureScenario("WALL_REJECTION", "STRUCTURE", "ORB continuation runs directly into a persistent call/put OI or gamma concentration wall.",
                    ("entry", "wall_strike", "wall_state"), "WATCH_OR_REQUIRE_ACCEPTANCE_THROUGH_WALL", "wall unwinds or accepted closes hold beyond it"),
    FailureScenario("MAX_PAIN_PIN", "EXPIRY", "Expiry session remains magnetized near max pain and repeatedly mean-reverts.",
                    ("expiry_day", "max_pain_distance", "oi_concentration"), "WAIT_OR_TIGHTEN_TARGET", "price accepts away from pin while OI migrates"),
    FailureScenario("EXPECTED_MOVE_STRETCH", "VOLATILITY", "Target requires more movement than the horizon's implied move allowance.",
                    ("entry", "target", "horizon_expected_move"), "CAP_TARGET_OR_WAIT", "implied move expands or target compresses"),
    FailureScenario("FUTURES_DIVERGENCE", "CROSS_MARKET", "Cash/spot ORB direction conflicts with futures price/OI state.",
                    ("candidate_side", "futures_price_change", "futures_oi_change"), "WATCH_FOR_RECONVERGENCE", "futures state realigns"),
    FailureScenario("OI_WALL_STRENGTHENING", "POSITIONING", "Opposing wall adds OI while price approaches it.",
                    ("oi_wall", "oi_delta"), "DELAY_OR_REQUIRE_BREAK_AND_HOLD", "wall weakens/unwinds"),
    FailureScenario("OI_WALL_MIGRATION", "POSITIONING", "Dominant wall moves against the candidate between snapshots.",
                    ("previous_wall", "current_wall"), "WATCH", "migration reverses or price accepts beyond new wall"),
    FailureScenario("GAMMA_CONFINEMENT", "GAMMA", "Large two-sided gamma concentrations surround entry and can suppress range expansion.",
                    ("call_gamma_wall", "put_gamma_wall", "entry"), "WATCH_OR_REDUCE_TARGET", "one wall breaks/decays with acceptance"),
    FailureScenario("GAMMA_ACCELERATION", "GAMMA", "Price escapes concentrated gamma region and movement can accelerate rather than mean-revert.",
                    ("gamma_balance", "wall_break"), "DO_NOT_FADE_AUTOMATICALLY", "price re-enters wall range"),
    FailureScenario("IV_EXPANSION_SHOCK", "VOLATILITY", "Abrupt IV expansion widens realized movement and invalidates static stop/target assumptions.",
                    ("iv_history", "current_iv"), "WAIT_OR_RECALIBRATE_RISK", "IV stabilizes with price acceptance"),
    FailureScenario("IV_CRUSH", "VOLATILITY", "Post-event IV collapse reduces premium-implied movement and continuation range.",
                    ("prior_iv", "current_iv", "event_state"), "CAP_TARGET", "realized expansion persists despite crush"),
    FailureScenario("TERM_INVERSION_EVENT", "VOLATILITY", "Near-expiry IV materially exceeds next expiry, implying concentrated event/expiry risk.",
                    ("near_iv", "next_iv"), "WATCH", "term structure normalizes"),
    FailureScenario("SKEW_TAIL_RISK", "VOLATILITY", "25-delta skew shows asymmetric tail demand against the candidate.",
                    ("put_25d_iv", "call_25d_iv", "side"), "WATCH", "skew normalizes or price structure dominates"),
    FailureScenario("PCR_CROWDING_UNWIND", "POSITIONING", "Extreme PCR reflects crowding that can unwind nonlinearly; not a direct direction vote.",
                    ("pcr_oi",), "CONTEXT_ONLY", "PCR normalizes without adverse price response"),
    FailureScenario("BASIS_DIVERGENCE", "CROSS_MARKET", "Futures basis shifts sharply against spot ORB interpretation.",
                    ("spot", "futures", "prior_basis"), "WATCH", "basis normalizes"),
    FailureScenario("LIQUIDITY_FAKE_WALL", "DATA_QUALITY", "Sparse/illiquid strikes produce unstable OI/gamma wall estimates.",
                    ("bid_ask", "volume", "chain_coverage"), "IGNORE_UNRELIABLE_WALL", "liquidity/coverage recovers"),
    FailureScenario("STALE_CHAIN", "DATA_QUALITY", "Chain snapshot is older than decision freshness policy.",
                    ("as_of_ns", "decision_ns"), "BLOCK", "fresh complete snapshot arrives"),
    FailureScenario("PARTIAL_GREEKS", "DATA_QUALITY", "Too few usable Greek rows make gamma/skew conclusions unreliable.",
                    ("greeks_coverage",), "UNKNOWN_OR_BLOCK_IF_REQUIRED", "coverage passes policy"),
    FailureScenario("EXPIRY_METADATA_MISMATCH", "CONTRACT", "Expiry/tick/lot assumptions disagree with current exchange/provider master data.",
                    ("expiry", "tick", "lot"), "BLOCK_AFFECTED_CALCULATION", "current master metadata validates"),
    FailureScenario("STRIKE_UNIVERSE_SHIFT", "DATA_QUALITY", "Strikes are added/removed between snapshots; naive index-by-index ΔOI is wrong.",
                    ("current_strikes", "previous_strikes"), "ALIGN_BY_STRIKE", "aligned strike map succeeds"),
    FailureScenario("UNKNOWN_DERIVATIVES_REGIME", "UNKNOWN", "Observed state is not supported by the registered derivatives evidence families.",
                    ("snapshot",), "DO_NOT_INFER", "new independently verified rule is registered and proved"),
)


def scenario_ids() -> tuple[str, ...]:
    return tuple(x.scenario_id for x in CATALOG)
