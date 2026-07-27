"""Enterprise reasoning pipeline orchestration (Phase 4 sections 2-3) -- WP5's
synchronous, single-pass MVP. Explicitly out of scope for this WP, owned by later work
packages: recursive decomposition across levels (Phase 5, WP8), the automated
structural/policy Governance Service (WP6), multi-agent orchestration (Phase 7, WP7), and
committing anything to the Enterprise Repository -- Phase 4's own lifecycle only commits
after a governance checkpoint this WP does not implement. This produces proposals only,
for a human (or a later WP) to review and commit."""

from typing import Tuple

from ..models import ProposedRisk, ReasoningResult, ReasoningStageLog
from . import stages
from .context import assemble_reasoning_context

MAX_GOVERNANCE_LOOPS = 2
_NO_KB_COVERAGE_MARKER = "No matching KnowledgeConcepts"


def run_pipeline(objective: str) -> ReasoningResult:
    reasoning_context = assemble_reasoning_context(objective)
    stage_log: list[ReasoningStageLog] = []
    governance_notes: list[str] = []

    domains = stages.select_domains(objective, reasoning_context)
    stage_log.append(ReasoningStageLog(stage="domain_selection", summary=", ".join(domains)))

    business_motivation = stages.business_analysis(objective, reasoning_context)
    stage_log.append(ReasoningStageLog(stage="business_analysis", summary=business_motivation))

    capability_summary = stages.capability_analysis(objective, business_motivation)
    stage_log.append(ReasoningStageLog(stage="capability_analysis", summary=capability_summary))

    nodes, relationships, risks, compliant, loop_count = [], [], [], False, 0
    while True:
        nodes = stages.architecture_thinking(objective, capability_summary, reasoning_context)
        stage_log.append(
            ReasoningStageLog(stage="architecture_thinking", summary=f"{len(nodes)} candidate node(s)")
        )

        relationships = stages.dependency_reasoning(objective, nodes)
        stage_log.append(
            ReasoningStageLog(
                stage="dependency_reasoning", summary=f"{len(relationships)} candidate relationship(s)"
            )
        )

        risks = stages.risk_reasoning(objective, nodes, relationships)
        stage_log.append(ReasoningStageLog(stage="risk_reasoning", summary=f"{len(risks)} candidate risk(s)"))

        compliant, violations = stages.governance_reasoning(objective, nodes, reasoning_context)
        stage_log.append(
            ReasoningStageLog(
                stage="governance_reasoning",
                summary="compliant" if compliant else f"non-compliant: {violations}",
            )
        )
        if compliant or loop_count >= MAX_GOVERNANCE_LOOPS:
            governance_notes.extend(violations)
            break
        governance_notes.append(
            f"Loop {loop_count + 1}: {violations} -- re-entering architecture thinking "
            "(Phase 4 section 3's iterative design)"
        )
        capability_summary = f"{capability_summary}\n\nA prior attempt violated: {violations}. Address these."
        loop_count += 1

    nodes = stages.technology_reasoning(objective, nodes)
    stage_log.append(ReasoningStageLog(stage="technology_reasoning", summary=f"annotated {len(nodes)} node(s)"))

    implementation_plan = stages.implementation_reasoning(objective, nodes)
    stage_log.append(ReasoningStageLog(stage="implementation_reasoning", summary=implementation_plan))

    confidence_tier, rationale = _score_confidence(reasoning_context, risks, compliant, loop_count)

    return ReasoningResult(
        objective=objective,
        domains=domains,
        stages=stage_log,
        proposed_nodes=nodes,
        proposed_relationships=relationships,
        proposed_risks=risks,
        confidence_tier=confidence_tier,
        confidence_rationale=rationale,
        requires_human_review=confidence_tier != "High",
        governance_notes=governance_notes,
    )


def _score_confidence(
    reasoning_context: str, risks: list[ProposedRisk], compliant: bool, loop_count: int
) -> Tuple[str, str]:
    """Phase 4 section 8: confidence is driven by Knowledge Base coverage, unresolved
    risk, and governance outcome -- computed here, not a number the model invents for
    itself. High still passes governance (section 8's own rule) but is the only tier
    without a mandatory blocking human review."""
    had_kb_coverage = _NO_KB_COVERAGE_MARKER not in reasoning_context
    high_severity_risk = any(r.initial_level in ("Critical", "High") for r in risks)

    if not compliant:
        return "Low", "Governance reasoning could not resolve a principle violation within the retry budget."
    if high_severity_risk:
        return "Low", "A Critical or High severity risk was identified and remains unresolved."
    if not had_kb_coverage:
        return "Medium", "No relevant Knowledge Base content was retrieved; reasoning drew on general knowledge only."
    if loop_count > 0:
        return "Medium", "Governance reasoning required a retry before reaching compliance."
    return "High", "Strong Knowledge Base coverage, no unresolved risk, compliant on first pass."
