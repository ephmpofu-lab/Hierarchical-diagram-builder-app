"""Change Impact Analysis (Phase 10 section 8) -- WP9. TOGAF's ADM Phase H, named back
in Phase 3 but explicitly deferred as content until now. Reuses the traceability model
exactly as designed (Phase 5 section 7, Phase 8 section 5) -- no new traversal mechanism.
A change proposed to one committed node ripples to its structural descendants and to any
other node traced to the same Requirement(s) as the changed node."""

from typing import List

from ..models import ChangeImpactFinding, Project


def analyze_impact(project: Project, node_id: str) -> List[ChangeImpactFinding]:
    findings: List[ChangeImpactFinding] = []
    seen = {node_id}

    stack = list(project.nodes[node_id].children)
    while stack:
        current_id = stack.pop()
        if current_id in seen:
            continue
        seen.add(current_id)
        current = project.nodes[current_id]
        findings.append(
            ChangeImpactFinding(
                node_id=current_id, label=current.label, reason="Structural descendant of the changed node"
            )
        )
        stack.extend(current.children)

    requirement_ids = {link.requirement_id for link in project.traceability_links if link.node_id == node_id}
    if requirement_ids:
        for link in project.traceability_links:
            if link.requirement_id in requirement_ids and link.node_id not in seen:
                traced_node = project.nodes.get(link.node_id)
                if traced_node is not None:
                    seen.add(link.node_id)
                    findings.append(
                        ChangeImpactFinding(
                            node_id=link.node_id,
                            label=traced_node.label,
                            reason=f"Traced to the same Requirement ({link.requirement_id}) as the changed node",
                        )
                    )
    return findings
