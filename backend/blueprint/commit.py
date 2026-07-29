"""Commits an approved/held-override Implementation Blueprint proposal into the real
tree (Journey 3, WP19): sets milestone/schedule fields on the already-real Task nodes a
proposal references -- Blueprint enriches existing leaves, it never creates new nodes the
way Reasoning/Decomposition do -- and creates real Dependency References for the
proposed build order. Defaults planning_status to "Not Started" only when unset, never
overwriting a status a human already chose: the smallest touch that makes committed work
actually visible on the existing Kanban board, which shows nothing for a node with
planning_status=None. One GovernanceDecision per committed work package, matching
decomposition/commit.py::commit_children and intelligence/commit.py's own pattern."""

import uuid
from datetime import datetime, timezone
from typing import List, Tuple

from .. import tree
from ..models import BlueprintResult, GovernanceDecision, Project


def commit_blueprint(project: Project, result: BlueprintResult, actor: str) -> Tuple[List[str], List[str]]:
    """Returns (committed_work_package_node_ids, committed_dependency_ids). A proposed
    work package or dependency referencing a node id no longer in the project is
    skipped, not guessed -- same "skip, don't error" precedent commit_reasoning_proposal
    already established for unresolvable relationship labels."""
    committed_node_ids: List[str] = []
    for wp in result.proposed_work_packages:
        node = project.nodes.get(wp.node_id)
        if node is None:
            continue
        node.milestone = wp.milestone
        if wp.target_date is not None:
            node.target_date = wp.target_date
        if wp.duration_days is not None:
            node.duration_days = wp.duration_days
        if node.planning_status is None:
            node.planning_status = "Not Started"
        committed_node_ids.append(node.id)
        project.governance_decisions.append(
            GovernanceDecision(
                id=str(uuid.uuid4()),
                timestamp=datetime.now(timezone.utc).isoformat(),
                actor=actor,
                decision_type="Approve",
                target_node_id=node.id,
                rationale=f"Approved Implementation Blueprint work package (milestone '{wp.milestone}')",
            )
        )

    committed_dependency_ids: List[str] = []
    for dep in result.proposed_dependencies:
        if dep.from_node_id not in project.nodes or dep.to_node_id not in project.nodes:
            continue
        ref = tree.add_reference(project, dep.from_node_id, dep.to_node_id, dep.label, "Dependency")
        committed_dependency_ids.append(ref.id)

    return committed_node_ids, committed_dependency_ids
