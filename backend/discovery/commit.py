"""Commits an approved Project Initiation Report into a freshly-created project (Journey 4,
WP20). Mirrors decomposition/commit.py::commit_children and intelligence/commit.py's own
node-creation shape exactly (same uuid-per-node, same tree.add_node call, same per-node
GovernanceDecision), scaled to one decision per top-level workspace rather than per node --
consistent with commit_blueprint's own "one per meaningful commit unit" convention.

This is also the first real writer of Requirement/TraceabilityLink anywhere in this app --
both models have had full DB round-trip support since early on, with zero API surface until
now. Any parent_label/origin_node_label a proposal references that was never actually
proposed is skipped, not guessed -- the same "skip unresolvable reference, don't error"
precedent intelligence/commit.py and blueprint/service.py already established."""

import uuid
from datetime import datetime, timezone
from typing import Dict, List

from .. import tree
from ..models import (
    GovernanceDecision,
    Project,
    ProjectInitiationReport,
    Requirement,
    TraceabilityLink,
)


def commit_initiation_report(project: Project, report: ProjectInitiationReport, actor: str) -> dict:
    root_id = tree.find_root_id(project)
    root = project.nodes[root_id]

    label_to_id: Dict[str, str] = {}
    committed_node_ids: List[str] = []

    # Pass 1: top-level Recommended Initial Workspaces (parent_label is None) -- direct
    # children of the root. Pass 2: Engineering Activities nesting under a workspace just
    # created in pass 1. Anything whose parent_label never resolves (references a workspace
    # that wasn't itself proposed) is skipped, not guessed at.
    top_level = [n for n in report.proposed_operations_model if n.parent_label is None]
    nested = [n for n in report.proposed_operations_model if n.parent_label is not None]

    for item in top_level:
        node_id = str(uuid.uuid4())
        tree.add_node(project, root_id, item.label, node_id)
        committed = project.nodes[node_id]
        committed.classification = item.classification
        committed.node_type = item.node_type
        committed.notes = item.notes
        label_to_id[item.label] = node_id
        committed_node_ids.append(node_id)
        project.governance_decisions.append(
            GovernanceDecision(
                id=str(uuid.uuid4()),
                timestamp=datetime.now(timezone.utc).isoformat(),
                actor=actor,
                decision_type="Approve",
                target_node_id=node_id,
                rationale=f"Approved Project Initiation Report workspace '{item.label}'",
            )
        )

    for item in nested:
        parent_id = label_to_id.get(item.parent_label)
        if parent_id is None:
            continue
        node_id = str(uuid.uuid4())
        tree.add_node(project, parent_id, item.label, node_id)
        committed = project.nodes[node_id]
        committed.classification = item.classification
        committed.node_type = item.node_type
        committed.notes = item.notes
        label_to_id[item.label] = node_id
        committed_node_ids.append(node_id)

    # Requirements: same two-pass parent resolution (self-referential sub-requirements),
    # origin_node_label resolved against the operations-model label map above.
    description_to_id: Dict[str, str] = {}
    committed_requirement_ids: List[str] = []
    committed_traceability_link_ids: List[str] = []

    top_level_reqs = [r for r in report.proposed_requirements if r.parent_label is None]
    nested_reqs = [r for r in report.proposed_requirements if r.parent_label is not None]

    def _commit_requirement(item) -> None:
        req_id = str(uuid.uuid4())
        parent_id = description_to_id.get(item.parent_label) if item.parent_label else None
        origin_node_id = label_to_id.get(item.origin_node_label) if item.origin_node_label else None
        project.requirements.append(
            Requirement(
                id=req_id,
                description=item.description,
                parent_id=parent_id,
                origin_node_id=origin_node_id,
                status="Draft",
            )
        )
        description_to_id[item.description] = req_id
        committed_requirement_ids.append(req_id)
        if origin_node_id is not None:
            link_id = str(uuid.uuid4())
            project.traceability_links.append(
                TraceabilityLink(id=link_id, requirement_id=req_id, node_id=origin_node_id, link_type="satisfies")
            )
            committed_traceability_link_ids.append(link_id)

    for item in top_level_reqs:
        _commit_requirement(item)
    for item in nested_reqs:
        _commit_requirement(item)

    for activity_text in report.recommended_engineering_activities:
        tree.log_activity(project, activity_text)

    prose_sections = [
        ("Known Risks", report.known_risks),
        ("Knowledge Gaps", report.knowledge_gaps),
        ("Suggested Knowledge Sources", report.suggested_knowledge_sources),
        ("Suggested Evidence Collection", report.suggested_evidence_collection),
        ("Recommended Architecture Patterns", report.recommended_architecture_patterns),
        ("Recommended Next Steps", report.recommended_next_steps),
    ]
    prose_block = "\n\n".join(
        f"{title}:\n" + "\n".join(f"- {line}" for line in items) for title, items in prose_sections if items
    )
    if prose_block:
        root.notes = (root.notes + "\n\n" if root.notes else "") + prose_block

    return {
        "committed_node_ids": committed_node_ids,
        "committed_requirement_ids": committed_requirement_ids,
        "committed_traceability_link_ids": committed_traceability_link_ids,
    }
