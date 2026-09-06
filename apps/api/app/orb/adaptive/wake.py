"""Timer wakeups independent of price arrivals; no self-debate loop."""
from __future__ import annotations
import asyncio
import logging
from contextlib import asynccontextmanager
from .contracts import MINUTE, NS, clock_ns, day_of

LOG=logging.getLogger(__name__)


def next_deadline(state, policy) -> int | None:
    deadlines=[]
    cutoff=clock_ns(state.session_date,policy.last_entry_minute)
    if state.watermark_ns<cutoff:
        deadlines.append(cutoff)
    if state.active_proposal:
        deadlines.append(state.active_proposal.expires_ns)
    if state.position and state.position.status in {"PENDING","OPEN"}:
        deadlines.append(state.position.expected_open_ns+policy.execution_minutes*MINUTE+policy.max_feature_lag_seconds*NS+1)
    for values in state.capabilities.values():
        deadlines.extend(c.expires_ns for c in values if c.expires_ns>state.watermark_ns)
    return min(deadlines) if deadlines else None


async def timer_loop(service, *, interval_seconds: float = 1.0):
    """A server-owned timer checks durable state; errors never grant authority.

    Only due state transitions are journaled, not every poll. Market producers
    post newly available bars through the existing authenticated event route.
    No provider/network polling or fake prices are supplied by this task.
    """
    while True:
        try:
            now=service.clock()
            day=day_of(now)
            state=await asyncio.to_thread(service.store.load,service.controller.limits.account_id,day)
            due=next_deadline(state,service.controller.policy) if state else None
            if due is not None and now>=due:
                await asyncio.to_thread(service.timer,day,f"scheduled-deadline:{due}")
        except asyncio.CancelledError:
            raise
        except Exception:
            LOG.exception("AFRE deadline processing failed closed; inspect persistence and source health")
        await asyncio.sleep(interval_seconds)


def install_timer_lifespan(app,service):
    previous=app.router.lifespan_context
    @asynccontextmanager
    async def lifespan(application):
        async with previous(application) as existing_state:
            task=asyncio.create_task(timer_loop(service),name="afre-durable-deadlines")
            try:
                yield existing_state
            finally:
                task.cancel()
                try: await task
                except asyncio.CancelledError: pass
    app.router.lifespan_context=lifespan
