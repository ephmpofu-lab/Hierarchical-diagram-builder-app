"""Commits an approved Reasoning Pipeline proposal into the real tree (first UI phase for
the reasoning/governance backend). Mirrors backend/decomposition/commit.py's
commit_children exactly for the node-creation step -- same uuid-per-node, same
tree.add_node call, same per-node GovernanceDecision -- so the two commit paths can never
drift apart. Extends that pattern to also commit proposed_relationships (as real
References, resolving from_label/to_label through the just-created label->id map) and
proposed_risks (as real Risk rows), since a reasoning proposal -- unlike a decomposition
batch -- carries all three kinds of proposed content, not just nodes."""

import uuid
from datetime import datetime, timezone
from typing import List, Tuple

from .. import tree
from ..models import GovernanceDecision, Project, ReasoningResult, Risk


def commit_reasoning_proposal(
    project: Project, parent_id: str, result: ReasoningResult, actor: str
) -> Tuple[List[str], List[str]]:
    """Returns (committed_node_ids, committed_risk_ids). Any proposed_relationship whose
    from_label/to_label doesn't match a label just committed is skipped, not guessed --
    it means the pipeline proposed a relationship to something it never actually proposed
    as a node."""
    label_to_id: dict = {}
    committed_node_ids: List[str] = []

    for proposed in result.proposed_nodes:
        node_id = str(uuid.uuid4())
        tree.add_node(project, parent_id, proposed.label, node_id)
        committed = project.nodes[node_id]
        committed.node_type = proposed.node_type
        committed.notes = proposed.notes
        label_to_id[proposed.label] = node_id
        committed_node_ids.append(node_id)
        project.governance_decisions.append(
            GovernanceDecision(
                id=str(uuid.uuid4()),
                timestamp=datetime.now(timezone.utc).isoformat(),
                actor=actor,
                decision_type="Approve",
                target_node_id=node_id,
                rationale=f"Approved reasoning proposal for objective '{result.objective}'",
            )
        )

    for rel in result.proposed_relationships:
        from_id = label_to_id.get(rel.from_label)
        to_id = label_to_id.get(rel.to_label)
        if from_id is None or to_id is None:
            continue
        tree.add_reference(project, from_id, to_id, rel.label, rel.reference_type)

    committed_risk_ids: List[str] = []
    for proposed_risk in result.proposed_risks:
        risk_id = str(uuid.uuid4())
        project.risks.append(
            Risk(
                id=risk_id,
                description=proposed_risk.description,
                classification=proposed_risk.classification,
                initial_level=proposed_risk.initial_level,
            )
        )
        committed_risk_ids.append(risk_id)

    return committed_node_ids, committed_risk_ids
