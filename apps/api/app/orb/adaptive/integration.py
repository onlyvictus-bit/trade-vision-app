"""Opt-in mount for the existing FastAPI application.

OFF (default): no state/database/provider imports, no changed old routes.
SHADOW: existing controls unchanged; new AFRE proposals cannot approve paper.
EXCLUSIVE-PAPER: explicit operator isolation; blocks other mutating HTTP paths
so a second legacy paper endpoint cannot bypass AFRE's account/session budget.
Do not run a separate legacy-writing process against this paper account.
"""
from __future__ import annotations
import os
from pathlib import Path
from .contracts import Policy, AccountLimits, SafetyState
from .controller import Controller
from .store import Store
from .service import Service
from .governance import ReviewedProof
from .api import router, BodyLimit
from .adapters import RepositoryDataGuard


def host_safety() -> SafetyState:
    try:
        from ... import state
        mode=state.SYSTEM_MODE
        kill=state.storage.load_kill_switch()
        allowed=bool(kill and kill.state=="armed" and not kill.blocks_order_paths and
                     not mode.allows_live_orders and not mode.allows_broker_credentials and mode.mode.value!="LIVE")
        return SafetyState(mode="PAPER" if mode.mode.value=="PAPER" else "MOCK",
                           kill_switch_armed=allowed,data_gate_passed=allowed,
                           reason_codes=() if allowed else ("HOST_MODE_OR_KILL_SWITCH_BLOCKED",))
    except Exception:
        return SafetyState(mode="MOCK",kill_switch_armed=False,data_gate_passed=False,
                           reason_codes=("HOST_SAFETY_UNAVAILABLE",))


def host_kill():
    from ... import state, models
    kill=models.KillSwitchState(state="triggered",reason="AFRE operator halt",source="afre-local-operator",
                               actor_id="local-research-operator",triggered_at=models.now_iso(),blocks_order_paths=True)
    state.storage.save_kill_switch(kill)
    state.KILL_SWITCH=kill
    return {"kill_switch":"triggered","new_entries_blocked":True,"exit_accounting_continues":True}


class ExclusivePaperBoundary:
    def __init__(self,app): self.app=app
    async def __call__(self,scope,receive,send):
        if scope["type"]=="http" and scope.get("method") not in {"GET","HEAD","OPTIONS"} and not scope.get("path", "").startswith("/api/v1/orb/adaptive/"):
            await send({"type":"http.response.start","status":423,"headers":[(b"content-type",b"application/json")]})
            await send({"type":"http.response.body","body":b'{"detail":"Exclusive AFRE paper profile: legacy writes disabled"}'})
            return
        return await self.app(scope,receive,send)


def load_controller(policy_path: str, limits_path: str, *, forecast_path: str | None=None,
                    value_path: str | None=None) -> Controller:
    policy=Policy.model_validate_json(Path(policy_path).read_text(encoding="utf-8"))
    limits=AccountLimits.model_validate_json(Path(limits_path).read_text(encoding="utf-8"))
    forecaster, values=None,None
    if forecast_path:
        from .forecasting import FrequencyModel, FrequencyForecaster
        forecaster=FrequencyForecaster(FrequencyModel.model_validate_json(Path(forecast_path).read_text(encoding="utf-8")),policy.rules_hash)
    if value_path:
        from .value import ValueModel, EmpiricalActionValue
        from .contracts import digest
        values=EmpiricalActionValue(ValueModel.model_validate_json(Path(value_path).read_text(encoding="utf-8")),policy.rules_hash,digest(limits))
    guard=RepositoryDataGuard(policy.host_d1_source_hash) if policy.host_d1_source_hash else None
    return Controller(policy,limits,forecaster,values,data_guard=guard)


def mount(app) -> None:
    profile=os.getenv("TRADEVISION_AFRE_PROFILE","off").lower()
    if profile=="off": return
    if profile not in {"shadow","exclusive-paper"}:
        raise ValueError("AFRE_PROFILE_MUST_BE_OFF_SHADOW_OR_EXCLUSIVE_PAPER")
    token=os.environ["TRADEVISION_AFRE_TOKEN"]
    if len(token)<32: raise ValueError("AFRE_TOKEN_TOO_SHORT")
    controller=load_controller(os.environ["TRADEVISION_AFRE_POLICY"],os.environ["TRADEVISION_AFRE_LIMITS"],
                               forecast_path=os.getenv("TRADEVISION_AFRE_FORECAST_MODEL"),value_path=os.getenv("TRADEVISION_AFRE_VALUE_MODEL"))
    paper=profile=="exclusive-paper"
    key=b""
    review_path=os.getenv("TRADEVISION_AFRE_REVIEW")
    if paper:
        if not controller.policy.host_d1_source_hash:
            raise ValueError("PAPER_PROFILE_REQUIRES_HOST_D1_BOUND_IN_RESEARCH_AND_RUNTIME_POLICY")
        if os.getenv("TRADEVISION_AFRE_ACCOUNT_EXCLUSIVE_CONFIRMED")!="1":
            raise ValueError("CONFIRM_NO_OTHER_PROCESS_OR_LEDGER_CAN_TRADE_THIS_ACCOUNT")
        from ...behavior.simulated_paper_ledger import list_simulated_paper_trades
        from .contracts import day_of
        import time
        today=day_of(time.time_ns())
        # Existing records are not deleted or migrated automatically. Approval
        # today in any legacy ledger prevents a fresh AFRE allowance.
        for record in list_simulated_paper_trades():
            from datetime import datetime
            approved=int(datetime.fromisoformat(record.approved_at.replace("Z","+00:00")).timestamp()*1e9)
            if day_of(approved)==today:
                raise ValueError("LEGACY_PAPER_ACTIVITY_TODAY_REQUIRES_RECONCILIATION")
        key=Path(os.environ["TRADEVISION_AFRE_REVIEW_KEY_FILE"]).read_bytes()
        if len(key)<32 or not review_path:
            raise ValueError("REVIEW_KEY_AND_VALIDATED_REVIEW_ARTIFACT_REQUIRED")
        app.add_middleware(ExclusivePaperBoundary)
    def review_provider():
        if not review_path or not Path(review_path).exists(): return None
        try: return ReviewedProof.model_validate_json(Path(review_path).read_text(encoding="utf-8"))
        except (ValueError,OSError): return None
    service=Service(Store(os.environ["TRADEVISION_AFRE_DB"]),controller,safety=host_safety,
                    paper_enabled=paper,review_provider=review_provider,review_key=key)
    r=router(service,token)
    # In exclusive profile the authenticated halt remains reachable even while
    # older mutating routes are locked. No reset/unlock or live enable route.
    @r.post("/safety/kill")
    def kill(): return host_kill()
    app.add_middleware(BodyLimit)
    app.include_router(r)
    app.state.afre_service=service
    from .wake import install_timer_lifespan
    install_timer_lifespan(app,service)
