"""Commits an approved batch of decomposition children into the real tree (Phase 5
section 2 step 5) -- shared by the synchronous decompose endpoint (WP8) and the
asynchronous decomposition Cycle runner (WP10) so the two paths can never drift apart."""

import uuid
from datetime import datetime, timezone
from typing import List

from .. import tree
from ..models import GovernanceDecision, Node, Project, ProposedNode


def commit_children(project: Project, node: Node, children: List[ProposedNode], strategy_name: str, actor: str) -> List[str]:
    committed_ids = []
    for child in children:
        child_id = str(uuid.uuid4())
        tree.add_node(project, node.id, child.label, child_id)
        committed = project.nodes[child_id]
        committed.classification = strategy_name
        committed.node_type = child.node_type
        committed.notes = child.notes
        committed_ids.append(child_id)
        project.governance_decisions.append(
            GovernanceDecision(
                id=str(uuid.uuid4()),
                timestamp=datetime.now(timezone.utc).isoformat(),
                actor=actor,
                decision_type="Approve",
                target_node_id=child_id,
                rationale=f"Auto-approved {strategy_name} decomposition of '{node.label}'",
            )
        )
    return committed_ids
