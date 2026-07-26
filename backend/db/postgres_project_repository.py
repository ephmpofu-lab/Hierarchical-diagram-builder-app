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
    GovernanceDecision,
    Node,
    Project,
    ProjectSummary,
    Reference,
    Requirement,
    Risk,
    RiskAssessment,
    TraceabilityLink,
    ValidationFinding,
)
from .connection import get_pool


class PostgresProjectRepository:
    def list_summaries(self, owner_id: str | None = None) -> List[ProjectSummary]:
        # Visible to a user: projects they own, plus legacy pre-auth projects (owner_id is
        # null) -- see Project.owner_id's own docstring. When owner_id isn't supplied
        # (e.g. an internal/administrative call), every project is listed, unfiltered.
        with get_pool().connection() as conn:
            if owner_id is None:
                rows = conn.execute(
                    """
                    select p.id, p.name, p.updated_at, count(n.id) as node_count
                    from projects p
                    left join nodes n on n.project_id = p.id
                    group by p.id
                    order by p.updated_at desc
                    """
                ).fetchall()
            else:
                rows = conn.execute(
                    """
                    select p.id, p.name, p.updated_at, count(n.id) as node_count
                    from projects p
                    left join nodes n on n.project_id = p.id
                    where p.owner_id = %s or p.owner_id is null
                    group by p.id
                    order by p.updated_at desc
                    """,
                    (owner_id,),
                ).fetchall()
        return [
            ProjectSummary(id=str(r[0]), name=r[1], updated_at=r[2].isoformat(), node_count=r[3])
            for r in rows
        ]

    def load(self, project_id: str) -> Project:
        with get_pool().connection() as conn:
            project_row = conn.execute(
                "select id, name, description, owner_id, created_at, updated_at from projects where id = %s",
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

            requirement_rows = conn.execute(
                "select id, parent_id, description, origin_node_id, status "
                "from requirements where project_id = %s",
                (project_id,),
            ).fetchall()

            traceability_rows = conn.execute(
                "select id, requirement_id, node_id, link_type "
                "from traceability_links where project_id = %s",
                (project_id,),
            ).fetchall()

            risk_rows = conn.execute(
                "select id, description, classification, initial_level, residual_level, "
                "status, target_node_id from risks where project_id = %s",
                (project_id,),
            ).fetchall()

            # GovernanceDecision/ValidationFinding/RiskAssessment are historical audit
            # records, same append-only read-time-window treatment as activity_log above --
            # never deleted on save(), so "most recent 200" is a read-time cap, not data loss.
            governance_decision_rows = list(
                reversed(
                    conn.execute(
                        'select id, "timestamp", actor, decision_type, target_node_id, rationale '
                        'from governance_decisions where project_id = %s '
                        'order by "timestamp" desc limit 200',
                        (project_id,),
                    ).fetchall()
                )
            )

            validation_finding_rows = list(
                reversed(
                    conn.execute(
                        'select id, "timestamp", category, severity, target_node_id '
                        'from validation_findings where project_id = %s '
                        'order by "timestamp" desc limit 200',
                        (project_id,),
                    ).fetchall()
                )
            )

            risk_assessment_rows = list(
                reversed(
                    conn.execute(
                        'select id, "timestamp", risk_id, assessment_type, level '
                        'from risk_assessments where project_id = %s '
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

        requirements = [
            Requirement(
                id=str(r[0]),
                parent_id=str(r[1]) if r[1] else None,
                description=r[2],
                origin_node_id=str(r[3]) if r[3] else None,
                status=r[4],
            )
            for r in requirement_rows
        ]

        traceability_links = [
            TraceabilityLink(id=str(r[0]), requirement_id=str(r[1]), node_id=str(r[2]), link_type=r[3])
            for r in traceability_rows
        ]

        risks = [
            Risk(
                id=str(r[0]),
                description=r[1],
                classification=r[2],
                initial_level=r[3],
                residual_level=r[4],
                status=r[5],
                target_node_id=str(r[6]) if r[6] else None,
            )
            for r in risk_rows
        ]

        governance_decisions = [
            GovernanceDecision(
                id=str(r[0]),
                timestamp=r[1].isoformat(),
                actor=r[2],
                decision_type=r[3],
                target_node_id=str(r[4]) if r[4] else None,
                rationale=r[5],
            )
            for r in governance_decision_rows
        ]

        validation_findings = [
            ValidationFinding(
                id=str(r[0]),
                timestamp=r[1].isoformat(),
                category=r[2],
                severity=r[3],
                target_node_id=str(r[4]) if r[4] else None,
            )
            for r in validation_finding_rows
        ]

        risk_assessments = [
            RiskAssessment(
                id=str(r[0]), timestamp=r[1].isoformat(), risk_id=str(r[2]), assessment_type=r[3], level=r[4]
            )
            for r in risk_assessment_rows
        ]

        return Project(
            id=str(project_row[0]),
            name=project_row[1],
            description=project_row[2],
            owner_id=str(project_row[3]) if project_row[3] else None,
            created_at=project_row[4].isoformat(),
            updated_at=project_row[5].isoformat(),
            nodes=nodes,
            references=references,
            activity_log=activity_log,
            concept_objects=concept_objects,
            requirements=requirements,
            traceability_links=traceability_links,
            risks=risks,
            governance_decisions=governance_decisions,
            validation_findings=validation_findings,
            risk_assessments=risk_assessments,
        )

    def save(self, project: Project) -> None:
        with get_pool().connection() as conn:
            with conn.transaction():
                conn.execute(
                    """
                    insert into projects (id, name, description, owner_id, created_at, updated_at)
                    values (%s, %s, %s, %s, %s, now())
                    on conflict (id) do update set
                        name = excluded.name, description = excluded.description, updated_at = now()
                    """,
                    # owner_id is deliberately NOT in the update clause -- ownership is set once,
                    # at create() time, and never silently reassigned by a later save().
                    (project.id, project.name, project.description, project.owner_id, project.created_at),
                )

                # Whole-project replace for the structural tables, matching the existing
                # file-based semantics exactly: nothing in this codebase diffs partial changes,
                # the full Project is always rewritten wholesale. Comments cascade-delete with
                # their parent node. activity_log is deliberately NOT deleted here -- it's a
                # true audit trail, appended-to below via ON CONFLICT DO NOTHING, never wiped.
                conn.execute("delete from nodes where project_id = %s", (project.id,))
                conn.execute("delete from project_references where project_id = %s", (project.id,))
                conn.execute("delete from concept_objects where project_id = %s", (project.id,))
                # Requirements form their own parallel tree (Phase 5 §6) -- same whole-list
                # replace as nodes/references/concept_objects. Child-before-parent delete
                # order (traceability_links, then requirements) even though the FKs would
                # cascade anyway, so this never depends on cascade ordering being implicit.
                conn.execute("delete from traceability_links where project_id = %s", (project.id,))
                conn.execute("delete from requirements where project_id = %s", (project.id,))
                conn.execute("delete from risks where project_id = %s", (project.id,))

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

                # Requirements insert in parent-before-child order (self-referencing FK),
                # mirroring the nodes DFS visit above.
                req_by_id = {r.id: r for r in project.requirements}
                req_order: list[str] = []
                req_seen: set[str] = set()

                def visit_requirement(req_id: str) -> None:
                    if req_id in req_seen or req_id not in req_by_id:
                        return
                    req_seen.add(req_id)
                    parent_id = req_by_id[req_id].parent_id
                    if parent_id:
                        visit_requirement(parent_id)
                    req_order.append(req_id)

                for req_id in req_by_id:
                    visit_requirement(req_id)

                for req_id in req_order:
                    req = req_by_id[req_id]
                    conn.execute(
                        """
                        insert into requirements (id, project_id, parent_id, description, origin_node_id, status)
                        values (%s, %s, %s, %s, %s, %s)
                        """,
                        (req.id, project.id, req.parent_id, req.description, req.origin_node_id, req.status),
                    )

                for link in project.traceability_links:
                    conn.execute(
                        """
                        insert into traceability_links (id, project_id, requirement_id, node_id, link_type)
                        values (%s, %s, %s, %s, %s)
                        """,
                        (link.id, project.id, link.requirement_id, link.node_id, link.link_type),
                    )

                for risk in project.risks:
                    conn.execute(
                        """
                        insert into risks (
                            id, project_id, description, classification, initial_level,
                            residual_level, status, target_node_id
                        ) values (%s, %s, %s, %s, %s, %s, %s, %s)
                        """,
                        (
                            risk.id,
                            project.id,
                            risk.description,
                            risk.classification,
                            risk.initial_level,
                            risk.residual_level,
                            risk.status,
                            risk.target_node_id,
                        ),
                    )

                # GovernanceDecision/ValidationFinding/RiskAssessment are historical audit
                # records -- append-only, same ON CONFLICT DO NOTHING pattern as activity_log,
                # never deleted above.
                for decision in project.governance_decisions:
                    conn.execute(
                        'insert into governance_decisions '
                        '(id, project_id, "timestamp", actor, decision_type, target_node_id, rationale) '
                        "values (%s, %s, %s, %s, %s, %s, %s) on conflict (id) do nothing",
                        (
                            decision.id,
                            project.id,
                            decision.timestamp,
                            decision.actor,
                            decision.decision_type,
                            decision.target_node_id,
                            decision.rationale,
                        ),
                    )

                for finding in project.validation_findings:
                    conn.execute(
                        'insert into validation_findings '
                        '(id, project_id, "timestamp", category, severity, target_node_id) '
                        "values (%s, %s, %s, %s, %s, %s) on conflict (id) do nothing",
                        (
                            finding.id,
                            project.id,
                            finding.timestamp,
                            finding.category,
                            finding.severity,
                            finding.target_node_id,
                        ),
                    )

                for assessment in project.risk_assessments:
                    conn.execute(
                        'insert into risk_assessments '
                        '(id, project_id, "timestamp", risk_id, assessment_type, level) '
                        "values (%s, %s, %s, %s, %s, %s) on conflict (id) do nothing",
                        (
                            assessment.id,
                            project.id,
                            assessment.timestamp,
                            assessment.risk_id,
                            assessment.assessment_type,
                            assessment.level,
                        ),
                    )

    def create(self, name: str, owner_id: str | None = None) -> Project:
        import uuid
        from datetime import datetime, timezone

        now = datetime.now(timezone.utc).isoformat()
        project_id = str(uuid.uuid4())
        root_id = str(uuid.uuid4())
        root_node = Node(id=root_id, label=name, parent_id=None, children=[], canvas_x=400, canvas_y=100)
        project = Project(
            id=project_id, name=name, owner_id=owner_id, created_at=now, updated_at=now, nodes={root_id: root_node}
        )
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
