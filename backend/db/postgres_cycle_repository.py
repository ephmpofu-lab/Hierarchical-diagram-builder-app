"""Cycle persistence (Phase 11 sections 5-6, WP10) -- its own narrow table and direct
SQL, deliberately NOT folded into PostgresProjectRepository.load()/save(). A background
cycle updates its own row independently of the rest of the project; going through the
existing whole-project load-mutate-save pattern (repository.py's own documented "nothing
in this codebase diffs partial changes" semantics) would mean holding a long-lived
in-memory Project snapshot across a multi-stage AI run and overwriting the whole project
on save -- a real risk of clobbering an unrelated concurrent edit made while the cycle
runs. Cycle rows are looked up by their own uuid primary key throughout -- project_id is
stored for listing/ownership checks (it's nullable: a "reasoning" cycle wraps the existing
project-independent /api/intelligence/reason endpoint from WP5), not as a lookup key."""

import uuid
from typing import List, Optional

from psycopg.types.json import Jsonb

from ..models import Cycle, CycleEvent
from .connection import get_pool


def create_cycle(
    kind: str, project_id: Optional[str] = None, objective: Optional[str] = None, node_id: Optional[str] = None
) -> Cycle:
    cycle_id = str(uuid.uuid4())
    with get_pool().connection() as conn:
        conn.execute(
            """
            insert into cycles (id, project_id, kind, status, objective, node_id)
            values (%s, %s, %s, 'Running', %s, %s)
            """,
            (cycle_id, project_id, kind, objective, node_id),
        )
    return Cycle(id=cycle_id, project_id=project_id, kind=kind, status="Running", objective=objective, node_id=node_id)


def get_cycle(cycle_id: str) -> Optional[Cycle]:
    with get_pool().connection() as conn:
        row = conn.execute(
            "select id, project_id, kind, status, objective, node_id, error, events, result "
            "from cycles where id = %s",
            (cycle_id,),
        ).fetchone()
    return _row_to_cycle(row) if row else None


def list_cycles(project_id: str) -> List[Cycle]:
    with get_pool().connection() as conn:
        rows = conn.execute(
            "select id, project_id, kind, status, objective, node_id, error, events, result "
            "from cycles where project_id = %s order by created_at desc limit 50",
            (project_id,),
        ).fetchall()
    return [_row_to_cycle(r) for r in rows]


def append_event(cycle_id: str, event: CycleEvent) -> None:
    with get_pool().connection() as conn:
        conn.execute(
            "update cycles set events = events || %s::jsonb, updated_at = now() where id = %s",
            (Jsonb([event.model_dump()]), cycle_id),
        )


def complete_cycle(cycle_id: str, result: dict) -> None:
    with get_pool().connection() as conn:
        conn.execute(
            "update cycles set status = 'Completed', result = %s, updated_at = now() where id = %s",
            (Jsonb(result), cycle_id),
        )


def fail_cycle(cycle_id: str, error: str) -> None:
    with get_pool().connection() as conn:
        conn.execute(
            "update cycles set status = 'Failed', error = %s, updated_at = now() where id = %s",
            (error, cycle_id),
        )


def _row_to_cycle(row) -> Cycle:
    cid, project_id, kind, status, objective, node_id, error, events, result = row
    return Cycle(
        id=str(cid),
        project_id=str(project_id) if project_id else None,
        kind=kind,
        status=status,
        objective=objective,
        node_id=str(node_id) if node_id else None,
        error=error,
        events=[CycleEvent(**e) for e in (events or [])],
        result=result,
    )
