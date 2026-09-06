"""Authenticated local research routes; no broker or model-deployment routes."""
from __future__ import annotations
import hmac
from typing import Annotated
from fastapi import APIRouter, Depends, FastAPI, Header, HTTPException
from pydantic import Field
from .contracts import Frozen, Identifier, PriorContext
from .runtime import EventBatch
from .service import Service
from .store import Conflict, StoreError
from .registry import source_registry


class StartBody(Frozen):
    event_id: Identifier
    priors: Annotated[tuple[PriorContext, ...], Field(min_length=1, max_length=100)]


class ApproveBody(Frozen):
    event_id: Identifier
    proposal_id: Identifier
    proposal_hash: Annotated[str, Field(pattern=r"^[0-9a-f]{64}$")]
    quantity: Annotated[int, Field(strict=True, gt=0)]
    approval_phrase: str


class TimerBody(Frozen):
    event_id: Identifier


def router(service: Service, token: str, *, operator_id: str = "local-research-operator") -> APIRouter:
    if len(token) < 32:
        raise ValueError("LOCAL_API_BEARER_TOKEN_REQUIRES_AT_LEAST_32_CHARACTERS")
    def authenticate(authorization: str = Header(default="")):
        if not hmac.compare_digest(authorization.encode("utf-8"), ("Bearer " + token).encode("utf-8")):
            raise HTTPException(401, "Local research authentication required")
    r = APIRouter(prefix="/api/v1/orb/adaptive", tags=["Adaptive ORB research"], dependencies=[Depends(authenticate)])
    def invoke(fn, *args):
        try: return fn(*args)
        except Conflict as exc: raise HTTPException(409, str(exc)) from exc
        except StoreError as exc: raise HTTPException(503, "Persistence unavailable; no authorization granted") from exc
        except KeyError as exc: raise HTTPException(404, "Session not found") from exc
        except ValueError as exc: raise HTTPException(422, str(exc)) from exc
    @r.get("/status")
    def status():
        return {"research_only": True, "trade_allowed": False, "live_trading_blocked": True,
                "paper_enabled": service.paper_enabled, "policy_hash": service.controller.policy.policy_hash,
                "account_id": service.controller.limits.account_id,
                "source_scenarios": len(source_registry()), "controller_cases": 20,
                "production_certified": False}
    @r.post("/sessions/{day}")
    def start(day: str, body: StartBody):
        return invoke(service.start, day, body.priors, body.event_id)
    @r.post("/sessions/{day}/events")
    def event(day: str, body: EventBatch):
        return invoke(service.ingest, day, body)
    @r.post("/sessions/{day}/approve")
    def approve(day: str, body: ApproveBody):
        return invoke(service.approve, day, body.event_id, body.proposal_id, body.proposal_hash,
                      body.quantity, body.approval_phrase, operator_id)
    @r.post("/sessions/{day}/timer")
    def timer(day: str, body: TimerBody):
        return invoke(service.timer, day, body.event_id)
    @r.get("/sessions/{day}")
    def inspect(day: str):
        return invoke(service.inspect, day)
    @r.get("/sessions/{day}/audit")
    def audit(day: str):
        return invoke(service.store.audit, service.controller.limits.account_id, day)
    @r.get("/scenario-registry")
    def scenarios():
        return {"source_claims_status": "UNVERIFIED_SOURCE_PROPOSALS", "scenarios": source_registry()}
    return r


class BodyLimit:
    """ASGI byte cap before JSON parsing (including chunked request bodies)."""
    def __init__(self, app, maximum_bytes: int = 2_000_000):
        self.app, self.maximum_bytes = app, maximum_bytes
    async def __call__(self, scope, receive, send):
        if scope["type"] != "http" or not scope.get("path", "").startswith("/api/v1/orb/adaptive"):
            return await self.app(scope, receive, send)
        data, total = [], 0
        while True:
            message = await receive()
            if message["type"] == "http.disconnect": return
            data.append(message)
            total += len(message.get("body", b""))
            if total > self.maximum_bytes:
                await send({"type":"http.response.start","status":413,"headers":[(b"content-type",b"application/json")]})
                await send({"type":"http.response.body","body":b'{"detail":"AFRE request too large"}'})
                return
            if not message.get("more_body", False): break
        index = 0
        async def buffered_receive():
            nonlocal index
            if index < len(data):
                value = data[index]; index += 1; return value
            return await receive()
        return await self.app(scope, buffered_receive, send)


def create_app(service: Service, token: str) -> FastAPI:
    app = FastAPI(title="Trade Vision AFRE local research", docs_url=None, redoc_url=None)
    app.add_middleware(BodyLimit)
    app.include_router(router(service, token))
    return app
