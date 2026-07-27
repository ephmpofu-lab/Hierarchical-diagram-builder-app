"""Knowledge retrieval and context-building (Phase 4 section 4). The Enterprise
Intelligence Engine never queries the Knowledge Base directly -- only through WP3's
Knowledge Layer, per the mandatory separation established since the Blueprint."""

from .. import storage
from ..knowledge import lifecycle
from ..knowledge.retrieval import retrieve


def assemble_reasoning_context(objective: str) -> str:
    active_concepts = storage.list_knowledge_concepts(status=lifecycle.RETRIEVABLE_STATUS)
    relationships = storage.list_all_knowledge_relationships()
    matched_concepts = retrieve(objective, active_concepts, relationships)

    principles = storage.list_governance_principles()
    objective_tokens = set(objective.lower().split())
    matched_principles = [p for p in principles if objective_tokens & set(p.statement.lower().split())]

    if not matched_concepts and not matched_principles:
        # Honest about an empty/thin Knowledge Base rather than silently reasoning as if it
        # had content -- the engine must never hard-code EA knowledge itself (Phase 2/4's
        # standing principle), so when nothing is retrieved it says so explicitly instead of
        # pretending curated guidance exists.
        return (
            "No matching KnowledgeConcepts or GovernancePrinciples were retrieved from the "
            "Knowledge Base for this objective (the Knowledge Base may not yet have relevant "
            "curated content ingested). Reason from your own general enterprise-architecture "
            "knowledge, and note explicitly where you are doing so."
        )

    lines = []
    if matched_concepts:
        lines.append("Retrieved Knowledge Concepts:")
        for c in matched_concepts:
            lines.append(f"- [{c.concept_id}] {c.name} ({c.category}): {c.definition}")
    if matched_principles:
        lines.append("Retrieved Governance Principles:")
        for p in matched_principles:
            domain_note = f" (domain: {p.applies_to_domain})" if p.applies_to_domain else ""
            lines.append(f"- {p.statement}{domain_note}")
    return "\n".join(lines)
