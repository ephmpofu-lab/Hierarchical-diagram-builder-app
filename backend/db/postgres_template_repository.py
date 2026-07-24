"""Postgres-backed TemplateRepository. Templates are stored with their whole `root`
TemplateNode tree as a single JSONB column -- a small, recursive, rarely-queried snapshot
with no independent query need, unlike the live project data in postgres_project_repository."""

from typing import List

from fastapi import HTTPException
from psycopg.types.json import Jsonb

from ..models import Template, TemplateNode, TemplateSummary
from .connection import get_pool


def _count_template_nodes(node: TemplateNode) -> int:
    return 1 + sum(_count_template_nodes(c) for c in node.children)


class PostgresTemplateRepository:
    def list_summaries(self) -> List[TemplateSummary]:
        with get_pool().connection() as conn:
            rows = conn.execute(
                "select id, name, created_at, root from templates order by created_at desc"
            ).fetchall()
        summaries = []
        for tid, name, created_at, root in rows:
            template_root = TemplateNode.model_validate(root)
            summaries.append(
                TemplateSummary(
                    id=str(tid),
                    name=name,
                    created_at=created_at.isoformat(),
                    node_count=_count_template_nodes(template_root),
                )
            )
        return summaries

    def load(self, template_id: str) -> Template:
        with get_pool().connection() as conn:
            row = conn.execute(
                "select id, name, created_at, root from templates where id = %s",
                (template_id,),
            ).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Template not found")
        tid, name, created_at, root = row
        return Template(
            id=str(tid), name=name, created_at=created_at.isoformat(), root=TemplateNode.model_validate(root)
        )

    def save_new(self, name: str, root: TemplateNode) -> Template:
        import uuid
        from datetime import datetime, timezone

        template = Template(id=str(uuid.uuid4()), name=name, created_at=datetime.now(timezone.utc).isoformat(), root=root)
        with get_pool().connection() as conn:
            conn.execute(
                "insert into templates (id, name, created_at, root) values (%s, %s, %s, %s)",
                (template.id, template.name, template.created_at, Jsonb(template.root.model_dump())),
            )
        return template

    def delete(self, template_id: str) -> None:
        with get_pool().connection() as conn:
            result = conn.execute("delete from templates where id = %s", (template_id,))
            if result.rowcount == 0:
                raise HTTPException(status_code=404, detail="Template not found")
