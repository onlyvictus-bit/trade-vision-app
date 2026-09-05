from __future__ import annotations

from fastapi import Request

from .models import OperatorIdentity, RbacDecision


ROLE_PERMISSIONS = {
    "viewer": ["read:system", "read:market", "read:replay"],
    "operator": ["read:system", "read:market", "read:replay", "simulate:order", "trigger:killswitch"],
    "risk_manager": ["read:system", "read:market", "read:replay", "simulate:order", "trigger:killswitch", "reset:killswitch"],
    "admin": ["read:system", "read:market", "read:replay", "simulate:order", "trigger:killswitch", "reset:killswitch"],
}

ROLE_RANK = {"viewer": 0, "operator": 1, "risk_manager": 2, "admin": 3}


def identity_from_request(request: Request) -> OperatorIdentity:
    actor_id = request.headers.get("X-TradeVision-Actor", "local_operator")
    role = request.headers.get("X-TradeVision-Role", "operator")
    if role not in ROLE_PERMISSIONS:
        role = "viewer"
    return OperatorIdentity(
        actor_id=actor_id[:80],
        role=role,
        auth_mode="mock_header",
        permissions=ROLE_PERMISSIONS[role],
        live_trading_allowed=False,
    )


def authorize(identity: OperatorIdentity, required_roles: list[str]) -> RbacDecision:
    required_rank = min(ROLE_RANK[role] for role in required_roles)
    allowed = ROLE_RANK[identity.role] >= required_rank
    return RbacDecision(
        allowed=allowed,
        required_roles=required_roles,
        actor=identity,
        reason="role accepted" if allowed else f"role {identity.role} cannot perform this action",
    )
