from __future__ import annotations

import json
import logging
import time
from uuid import uuid4

from fastapi import Request, Response

from .models import RequestLogRecord, SystemModeValue, now_iso
from . import storage


LOGGER_NAME = "tradevision.api"
logger = logging.getLogger(LOGGER_NAME)


def configure_logging() -> None:
    """Configure a compact JSON logger once for local operational visibility."""

    if logger.handlers:
        return
    handler = logging.StreamHandler()
    handler.setFormatter(JsonLogFormatter())
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)
    logger.propagate = False


class JsonLogFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload = {
            "timestamp": now_iso(),
            "level": record.levelname.lower(),
            "logger": record.name,
            "message": record.getMessage(),
        }
        extra = getattr(record, "tradevision", None)
        if isinstance(extra, dict):
            payload.update(extra)
        return json.dumps(payload, sort_keys=True, separators=(",", ":"))


def new_run_id() -> str:
    return f"run_{uuid4()}"


def new_decision_id(path: str) -> str | None:
    if any(key in path for key in ("/decision", "/behavior", "/execution")):
        return f"dec_{uuid4()}"
    return None


async def record_request(request: Request, call_next) -> Response:
    configure_logging()
    request_id = str(uuid4())
    run_id = request.headers.get("X-TradeVision-Run-Id") or new_run_id()
    decision_id = request.headers.get("X-TradeVision-Decision-Id") or new_decision_id(request.url.path)
    actor_id = request.headers.get("X-TradeVision-Actor", "local_operator")
    role = request.headers.get("X-TradeVision-Role", "operator")
    started = time.perf_counter()
    status_code = 500
    error_code: str | None = None
    response: Response | None = None
    try:
        response = await call_next(request)
        status_code = response.status_code
        error_code = response.headers.get("X-TradeVision-Error-Code")
        return response
    except Exception as exc:
        error_code = exc.__class__.__name__
        raise
    finally:
        latency_ms = round((time.perf_counter() - started) * 1000, 3)
        record = RequestLogRecord(
            request_id=request_id,
            run_id=run_id,
            decision_id=decision_id,
            timestamp=now_iso(),
            method=request.method,
            path=request.url.path,
            status_code=status_code,
            latency_ms=latency_ms,
            actor_id=actor_id,
            role=role,
            mode=SystemModeValue.MOCK,
            error_code=error_code,
        )
        storage.save_request_log(record)
        logger.info(
            "request_complete",
            extra={
                "tradevision": record.model_dump(mode="json"),
            },
        )
        if response is not None:
            response.headers["X-TradeVision-Request-Id"] = request_id
            response.headers["X-TradeVision-Run-Id"] = run_id
            if decision_id is not None:
                response.headers["X-TradeVision-Decision-Id"] = decision_id

