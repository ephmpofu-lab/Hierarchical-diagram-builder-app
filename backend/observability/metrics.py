"""Observability (Phase 11 section 13, WP13b) -- the technical substrate underneath
Phase 10 section 10's Governance Performance Monitoring (a business/process concern,
still out of scope per WP6's own scope line: "not requested"). This WP lays the metrics
themselves -- AI service call latency/retries and agent invocation success/failure rates
-- not a monitoring dashboard that reads them.

Recording happens at exactly two chokepoints, both already the sole entry point for their
kind of call (no new instrumentation scattered across callers): backend/ai/service.py's
complete() (every AI call, any provider, per ADR-002) and backend/agents/orchestrator.py's
Orchestrator methods (every agent dispatch, per Phase 7's hub-and-spoke design)."""

import uuid
from typing import Optional

from ..db.connection import get_pool


def record_event(
    event_type: str,
    subject: str,
    success: bool,
    duration_ms: Optional[int] = None,
    retries: Optional[int] = None,
    error_type: Optional[str] = None,
    project_id: Optional[str] = None,
) -> None:
    with get_pool().connection() as conn:
        conn.execute(
            """
            insert into metrics_events
                (id, event_type, subject, project_id, success, duration_ms, retries, error_type)
            values (%s, %s, %s, %s, %s, %s, %s, %s)
            """,
            (str(uuid.uuid4()), event_type, subject, project_id, success, duration_ms, retries, error_type),
        )


def record_ai_call(
    model: str, success: bool, duration_ms: int, retries: int = 0, error_type: Optional[str] = None
) -> None:
    record_event("ai_call", model, success, duration_ms=duration_ms, retries=retries, error_type=error_type)


def record_agent_invocation(
    agent_name: str, success: bool, project_id: Optional[str] = None, error_type: Optional[str] = None
) -> None:
    record_event("agent_invocation", agent_name, success, project_id=project_id, error_type=error_type)


def summarize(hours: int = 24) -> list:
    """Per (event_type, subject): call count, success rate, average duration (ai_call
    only), average retries (ai_call only) -- exactly the two signals Phase 11 section 13
    names, aggregated over a recent rolling window rather than all-time totals so a
    long-lived deployment's dashboard reflects current health, not historical noise."""
    with get_pool().connection() as conn:
        rows = conn.execute(
            """
            select
                event_type,
                subject,
                count(*) as total,
                count(*) filter (where success) as successes,
                avg(duration_ms) filter (where duration_ms is not null) as avg_duration_ms,
                avg(retries) filter (where retries is not null) as avg_retries
            from metrics_events
            where created_at > now() - (%s || ' hours')::interval
            group by event_type, subject
            order by event_type, subject
            """,
            (hours,),
        ).fetchall()
    return [
        {
            "event_type": event_type,
            "subject": subject,
            "total": total,
            "successes": successes,
            "success_rate": round(successes / total, 4) if total else None,
            "avg_duration_ms": round(float(avg_duration_ms), 1) if avg_duration_ms is not None else None,
            "avg_retries": round(float(avg_retries), 2) if avg_retries is not None else None,
        }
        for event_type, subject, total, successes, avg_duration_ms, avg_retries in rows
    ]
