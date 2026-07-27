"""Validation Framework (Phase 10 section 4), scoped to WP6: structural and policy checks
against a WP5 ReasoningResult, before it is ever committed to a project. Deliberately
distinct from `tree.build_validation_report` (the existing structural scorer, Phase 1),
which is preserved unchanged and continues to score already-committed Project trees --
Phase 10 section 4's own table says so explicitly. A flat, not-yet-committed proposal has
no parent/child structure yet, so it needs its own, simpler structural check."""

from typing import List

from ..models import GovernanceFinding, ReasoningResult


def validate_structure(result: ReasoningResult) -> List[GovernanceFinding]:
    """Duplicate labels and dangling relationship references -- re-checked independently
    of WP5's own stage outputs (dependency_reasoning already filters these, but governance
    must never simply trust the reasoning stage's own bookkeeping)."""
    findings: List[GovernanceFinding] = []

    seen = set()
    for node in result.proposed_nodes:
        if node.label in seen:
            findings.append(
                GovernanceFinding(category="structural", severity="Critical", message=f"Duplicate node label: {node.label!r}")
            )
        seen.add(node.label)

    labels = {n.label for n in result.proposed_nodes}
    for rel in result.proposed_relationships:
        if rel.from_label not in labels or rel.to_label not in labels:
            findings.append(
                GovernanceFinding(
                    category="structural",
                    severity="Critical",
                    message=f"Relationship references an unknown node: {rel.from_label!r} -> {rel.to_label!r}",
                )
            )
    return findings


def validate_policy(result: ReasoningResult) -> List[GovernanceFinding]:
    """Policy compliance (Phase 10 section 5): a proposal is compliant only once every
    applicable GovernancePrinciple has been evaluated with no blocking violation. The
    semantic judgment of *whether* a principle is violated is the reasoning pipeline's own
    job (Phase 4 stage 6, WP5) -- duplicating that judgment here with a cruder heuristic
    would be a strictly weaker, redundant re-check, not genuine defense-in-depth. WP6's
    real job is enforcement: formalize whatever stage 6 already found into a governance
    gate, so an unresolved violation can never be silently waved through to commit."""
    return [
        GovernanceFinding(category="policy", severity="Critical", message=note) for note in result.governance_notes
    ]
