from __future__ import annotations

from typing import Any

from fastapi import HTTPException

from .models import ApiEnvelope, ErrorDetail, ErrorEnvelope, ResponseMeta, SourceMode, now_iso


def envelope(data: Any, *, capability_status="mock", source: SourceMode = SourceMode.MOCK, quality=0.98, trust=0.95):
    timestamp = now_iso()
    return ApiEnvelope(
        meta=ResponseMeta(
            event_time=timestamp,
            arrival_time=timestamp,
            source=source,
            quality_score=quality,
            trust_score=trust,
            replay_snapshot_id=None,
            capability_status=capability_status,
        ),
        data=data,
    )


def api_error(status_code: int, code: str, message: str, retryable: bool = False) -> HTTPException:
    detail = ErrorDetail(code=code, message=message, retryable=retryable).model_dump()
    return HTTPException(status_code=status_code, detail=detail)


def error_envelope(code: str, message: str, *, retryable: bool = False) -> dict:
    return ErrorEnvelope(error=ErrorDetail(code=code, message=message, retryable=retryable)).model_dump(mode="json")
