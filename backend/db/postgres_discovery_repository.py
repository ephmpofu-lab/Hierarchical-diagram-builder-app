"""Discovery Session persistence (Journey 4, WP20) -- its own narrow table and direct SQL,
mirroring postgres_cycle_repository.py's own reasoning exactly: a session updates its own
row independently of any project (it's what eventually creates one), so folding this into
PostgresProjectRepository.load()/save()'s whole-project pattern would make no sense before
a project even exists. Rows are looked up by their own uuid primary key throughout."""

import uuid
from typing import List, Optional

from psycopg.types.json import Jsonb

from ..models import DiscoverySession, DiscoveryTurn
from .connection import get_pool


def create_session(owner_id: Optional[str] = None) -> DiscoverySession:
    session_id = str(uuid.uuid4())
    with get_pool().connection() as conn:
        conn.execute(
            "insert into discovery_sessions (id, owner_id, status) values (%s, %s, 'InProgress')",
            (session_id, owner_id),
        )
    return DiscoverySession(id=session_id, owner_id=owner_id, status="InProgress")


def get_session(session_id: str) -> Optional[DiscoverySession]:
    with get_pool().connection() as conn:
        row = conn.execute(
            "select id, owner_id, status, created_project_id, turns, topic_coverage, "
            "turn_count, report from discovery_sessions where id = %s",
            (session_id,),
        ).fetchone()
    return _row_to_session(row) if row else None


def list_sessions(owner_id: str) -> List[DiscoverySession]:
    with get_pool().connection() as conn:
        rows = conn.execute(
            "select id, owner_id, status, created_project_id, turns, topic_coverage, "
            "turn_count, report from discovery_sessions where owner_id = %s "
            "order by created_at desc limit 50",
            (owner_id,),
        ).fetchall()
    return [_row_to_session(r) for r in rows]


def append_turn(session_id: str, turn: DiscoveryTurn) -> None:
    with get_pool().connection() as conn:
        conn.execute(
            "update discovery_sessions set turns = turns || %s::jsonb, updated_at = now() where id = %s",
            (Jsonb([turn.model_dump()]), session_id),
        )


def update_coverage(session_id: str, topic_coverage: dict, turn_count: int, status: str) -> None:
    with get_pool().connection() as conn:
        conn.execute(
            "update discovery_sessions set topic_coverage = %s, turn_count = %s, status = %s, "
            "updated_at = now() where id = %s",
            (Jsonb(topic_coverage), turn_count, status, session_id),
        )


def set_report(session_id: str, report: dict, status: str) -> None:
    with get_pool().connection() as conn:
        conn.execute(
            "update discovery_sessions set report = %s, status = %s, updated_at = now() where id = %s",
            (Jsonb(report), status, session_id),
        )


def set_status(session_id: str, status: str, created_project_id: Optional[str] = None) -> None:
    with get_pool().connection() as conn:
        conn.execute(
            "update discovery_sessions set status = %s, created_project_id = %s, updated_at = now() where id = %s",
            (status, created_project_id, session_id),
        )


def _row_to_session(row) -> DiscoverySession:
    sid, owner_id, status, created_project_id, turns, topic_coverage, turn_count, report = row
    return DiscoverySession(
        id=str(sid),
        owner_id=str(owner_id) if owner_id else None,
        status=status,
        created_project_id=str(created_project_id) if created_project_id else None,
        turns=[DiscoveryTurn(**t) for t in (turns or [])],
        topic_coverage=topic_coverage or {},
        turn_count=turn_count,
        report=report,
    )
