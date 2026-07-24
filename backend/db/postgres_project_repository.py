"""Postgres-backed ProjectRepository. load() reassembles the exact same nested Project shape
tree.py/concept.py already operate on; save() replaces the project's rows in one transaction,
mirroring the current JSON-file semantics where the whole project is always treated as one
atomic unit (nothing in this codebase diffs partial changes -- it never has)."""

from typing import List

from fastapi import HTTPException

from ..models import (
    ActivityEntry,
    Comment,
    ConceptObject,
    Node,
    Project,
    ProjectSummary,
    Reference,
)
from .connection import get_pool


class PostgresProjectRepository:
    def list_summaries(self) -> List[ProjectSummary]:
        with get_pool().connection() as conn:
            rows = conn.execute(
                """
                select p.id, p.name, p.updated_at, count(n.id) as node_count
                from projects p
                left join nodes n on n.project_id = p.id
                group by p.id
                order by p.updated_at desc
                """
            ).fetchall()
        return [
            ProjectSummary(id=str(r[0]), name=r[1], updated_at=r[2].isoformat(), node_count=r[3])
            for r in rows
        ]

    def load(self, project_id: str) -> Project:
        with get_pool().connection() as conn:
            project_row = conn.execute(
                "select id, name, description, created_at, updated_at from projects where id = %s",
                (project_id,),
            ).fetchone()
            if not project_row:
                raise HTTPException(status_code=404, detail="Project not found")

            node_rows = conn.execute(
                """
                select id, parent_id, sort_order, label, notes, canvas_x, canvas_y, collapsed,
                       node_type, status, priority, complexity, risk_level, tags, owner, shape,
                       group_children, is_group, classification, custom_color, planning_status,
                       locked
                from nodes where project_id = %s order by parent_id, sort_order
                """,
                (project_id,),
            ).fetchall()

            comment_rows = conn.execute(
                """
                select c.node_id, c.id, c.text, c.created_at
                from comments c join nodes n on n.id = c.node_id
                where n.project_id = %s order by c.created_at
                """,
                (project_id,),
            ).fetchall()

            ref_rows = conn.execute(
                """
                select id, from_id, to_id, label, reference_type, custom_color, thickness,
                       direction, animated, connector_hidden, line_style, opacity,
                       show_arrowhead, curve_style, animation_speed
                from project_references where project_id = %s
                """,
                (project_id,),
            ).fetchall()

            object_rows = conn.execute(
                """
                select id, type, x, y, width, height, rotation, text, color, border_style,
                       z_index, locked, group_id
                from concept_objects where project_id = %s
                """,
                (project_id,),
            ).fetchall()

            # Full history is never deleted from the table (see save()) -- this is a read-time
            # window for the in-memory Project object, not a destructive cap. Fetch the most
            # recent 200 (matches the app's existing "recent changes" footer needs), then
            # reverse back to the chronological-ascending order the rest of the app expects.
            activity_rows = list(
                reversed(
                    conn.execute(
                        'select id, "timestamp", message from activity_log where project_id = %s '
                        'order by "timestamp" desc limit 200',
                        (project_id,),
                    ).fetchall()
                )
            )

        comments_by_node: dict[str, list[Comment]] = {}
        for node_id, cid, text, created_at in comment_rows:
            comments_by_node.setdefault(str(node_id), []).append(
                Comment(id=str(cid), text=text, created_at=created_at.isoformat())
            )

        nodes: dict[str, Node] = {}
        for row in node_rows:
            (
                nid, parent_id, _sort_order, label, notes, canvas_x, canvas_y, collapsed,
                node_type, status, priority, complexity, risk_level, tags, owner, shape,
                group_children, is_group, classification, custom_color, planning_status, locked,
            ) = row
            node_id = str(nid)
            nodes[node_id] = Node(
                id=node_id,
                label=label,
                parent_id=str(parent_id) if parent_id else None,
                children=[],
                notes=notes,
                canvas_x=canvas_x,
                canvas_y=canvas_y,
                collapsed=collapsed,
                node_type=node_type,
                status=status,
                priority=priority,
                complexity=complexity,
                risk_level=risk_level,
                tags=list(tags or []),
                owner=owner,
                comments=comments_by_node.get(node_id, []),
                shape=shape,
                group_children=group_children,
                is_group=is_group,
                classification=classification,
                custom_color=custom_color,
                planning_status=planning_status,
                locked=locked,
            )
        # Rebuild each parent's children array from every node's own parent_id + sort_order,
        # in a separate pass -- simpler than trying to append in the right order during a
        # single scan, and correct regardless of how the SQL happened to order the rows.
        ordered_by_parent: dict[str, list[tuple[int, str]]] = {}
        for row in node_rows:
            nid, parent_id = str(row[0]), (str(row[1]) if row[1] else None)
            sort_order = row[2]
            if parent_id:
                ordered_by_parent.setdefault(parent_id, []).append((sort_order, nid))
        for parent_id, children in ordered_by_parent.items():
            if parent_id in nodes:
                children.sort(key=lambda t: t[0])
                nodes[parent_id].children = [nid for _, nid in children]

        references = [
            Reference(
                id=str(r[0]),
                from_=str(r[1]),
                to=str(r[2]),
                label=r[3],
                reference_type=r[4],
                custom_color=r[5],
                thickness=r[6],
                direction=r[7],
                animated=r[8],
                connector_hidden=r[9],
                line_style=r[10],
                opacity=r[11],
                show_arrowhead=r[12],
                curve_style=r[13],
                animation_speed=r[14],
            )
            for r in ref_rows
        ]

        concept_objects = [
            ConceptObject(
                id=str(r[0]),
                type=r[1],
                x=r[2],
                y=r[3],
                width=r[4],
                height=r[5],
                rotation=r[6],
                text=r[7],
                color=r[8],
                border_style=r[9],
                z_index=r[10],
                locked=r[11],
                group_id=r[12],
            )
            for r in object_rows
        ]

        activity_log = [
            ActivityEntry(id=str(r[0]), timestamp=r[1].isoformat(), message=r[2])
            for r in activity_rows
        ]

        return Project(
            id=str(project_row[0]),
            name=project_row[1],
            description=project_row[2],
            created_at=project_row[3].isoformat(),
            updated_at=project_row[4].isoformat(),
            nodes=nodes,
            references=references,
            activity_log=activity_log,
            concept_objects=concept_objects,
        )

    def save(self, project: Project) -> None:
        with get_pool().connection() as conn:
            with conn.transaction():
                conn.execute(
                    """
                    insert into projects (id, name, description, created_at, updated_at)
                    values (%s, %s, %s, %s, now())
                    on conflict (id) do update set
                        name = excluded.name, description = excluded.description, updated_at = now()
                    """,
                    (project.id, project.name, project.description, project.created_at),
                )

                # Whole-project replace for the structural tables, matching the existing
                # file-based semantics exactly: nothing in this codebase diffs partial changes,
                # the full Project is always rewritten wholesale. Comments cascade-delete with
                # their parent node. activity_log is deliberately NOT deleted here -- it's a
                # true audit trail, appended-to below via ON CONFLICT DO NOTHING, never wiped.
                conn.execute("delete from nodes where project_id = %s", (project.id,))
                conn.execute("delete from project_references where project_id = %s", (project.id,))
                conn.execute("delete from concept_objects where project_id = %s", (project.id,))

                # Insert nodes in parent-before-child order (root first) so the self-referencing
                # parent_id foreign key is always satisfied at insert time.
                order: list[str] = []
                seen: set[str] = set()

                def visit(node_id: str) -> None:
                    if node_id in seen or node_id not in project.nodes:
                        return
                    seen.add(node_id)
                    order.append(node_id)
                    for child_id in project.nodes[node_id].children:
                        visit(child_id)

                root_id = next((n.id for n in project.nodes.values() if n.parent_id is None), None)
                if root_id:
                    visit(root_id)
                for node_id in project.nodes:  # catch any unreachable/orphaned nodes too
                    visit(node_id)

                # sort_order per node = its index within its parent's own children array.
                sort_order_by_id: dict[str, int] = {}
                for node in project.nodes.values():
                    for index, child_id in enumerate(node.children):
                        sort_order_by_id[child_id] = index

                for node_id in order:
                    node = project.nodes[node_id]
                    conn.execute(
                        """
                        insert into nodes (
                            id, project_id, parent_id, sort_order, label, notes, canvas_x,
                            canvas_y, collapsed, node_type, status, priority, complexity,
                            risk_level, tags, owner, shape, group_children, is_group,
                            classification, custom_color, planning_status, locked
                        ) values (
                            %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
                            %s, %s, %s, %s, %s, %s
                        )
                        """,
                        (
                            node.id,
                            project.id,
                            node.parent_id,
                            sort_order_by_id.get(node_id, 0),
                            node.label,
                            node.notes,
                            node.canvas_x,
                            node.canvas_y,
                            node.collapsed,
                            node.node_type,
                            node.status,
                            node.priority,
                            node.complexity,
                            node.risk_level,
                            node.tags,
                            node.owner,
                            node.shape,
                            node.group_children,
                            node.is_group,
                            node.classification,
                            node.custom_color,
                            node.planning_status,
                            node.locked,
                        ),
                    )

                for node in project.nodes.values():
                    for comment in node.comments:
                        conn.execute(
                            "insert into comments (id, node_id, text, created_at) values (%s, %s, %s, %s)",
                            (comment.id, node.id, comment.text, comment.created_at),
                        )

                for ref in project.references:
                    conn.execute(
                        """
                        insert into project_references (
                            id, project_id, from_id, to_id, label, reference_type,
                            custom_color, thickness, direction, animated, connector_hidden,
                            line_style, opacity, show_arrowhead, curve_style, animation_speed
                        ) values (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                        """,
                        (
                            ref.id,
                            project.id,
                            ref.from_,
                            ref.to,
                            ref.label,
                            ref.reference_type,
                            ref.custom_color,
                            ref.thickness,
                            ref.direction,
                            ref.animated,
                            ref.connector_hidden,
                            ref.line_style,
                            ref.opacity,
                            ref.show_arrowhead,
                            ref.curve_style,
                            ref.animation_speed,
                        ),
                    )

                for obj in project.concept_objects:
                    conn.execute(
                        """
                        insert into concept_objects (
                            id, project_id, type, x, y, width, height, rotation, text, color,
                            border_style, z_index, locked, group_id
                        ) values (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                        """,
                        (
                            obj.id,
                            project.id,
                            obj.type,
                            obj.x,
                            obj.y,
                            obj.width,
                            obj.height,
                            obj.rotation,
                            obj.text,
                            obj.color,
                            obj.border_style,
                            obj.z_index,
                            obj.locked,
                            obj.group_id,
                        ),
                    )

                for entry in project.activity_log:
                    conn.execute(
                        'insert into activity_log (id, project_id, "timestamp", message) '
                        "values (%s, %s, %s, %s) on conflict (id) do nothing",
                        (entry.id, project.id, entry.timestamp, entry.message),
                    )

    def create(self, name: str) -> Project:
        import uuid
        from datetime import datetime, timezone

        now = datetime.now(timezone.utc).isoformat()
        project_id = str(uuid.uuid4())
        root_id = str(uuid.uuid4())
        root_node = Node(id=root_id, label=name, parent_id=None, children=[], canvas_x=400, canvas_y=100)
        project = Project(id=project_id, name=name, created_at=now, updated_at=now, nodes={root_id: root_node})
        self.save(project)
        return project

    def delete(self, project_id: str) -> None:
        with get_pool().connection() as conn:
            result = conn.execute("delete from projects where id = %s", (project_id,))
            if result.rowcount == 0:
                raise HTTPException(status_code=404, detail="Project not found")

    def rename(self, project_id: str, name: str) -> Project:
        project = self.load(project_id)
        project.name = name
        self.save(project)
        return project
