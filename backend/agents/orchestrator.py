"""Agent Orchestration (Phase 7 sections 4-5) -- WP7. Hub-and-spoke: agents never
communicate peer-to-peer; the Orchestrator is the one and only thing that dispatches to
them. This wraps the Reasoning Pipeline (WP5) and the Governance Service (WP6) -- both
already built and live-verified -- with per-stage/per-finding agent attribution and
sequencing. It does not reimplement any reasoning or validation logic: "No new engine,
pipeline, or governance mechanism was introduced in this phase" (Phase 7's own continuity
mapping). Recovery from a failed stage is already just re-invocation against the same
stateless AI Service call (WP4/WP5) -- nothing new needed for Phase 7 section 11 either."""

from ..governance.workflow import run_decision_workflow
from ..intelligence.pipeline import run_pipeline as _run_reasoning_pipeline
from ..models import GovernanceReview, ReasoningResult
from .agent import (
    ARCHITECTURE_THINKING_AGENT,
    BUSINESS_ARCHITECTURE_AGENT,
    DEPENDENCY_AGENT,
    EXECUTION_PLANNING_AGENT,
    GOVERNANCE_AGENT,
    ORCHESTRATOR,
    TECHNOLOGY_ARCHITECTURE_AGENT,
    VALIDATION_AGENT,
)

# Maps WP5's stage names to the agent that owns them (Phase 7 section 2's table). Risk
# reasoning (stage 5) is not explicitly assigned to a named agent in the approved
# architecture -- the closest fit is the Governance Agent, since Phase 10 later treats
# risk and governance as adjacent compliance concerns. Domain selection isn't assigned to
# an agent either; it's sequencing, which is the Orchestrator's own stated role.
_STAGE_TO_AGENT = {
    "domain_selection": ORCHESTRATOR.name,
    "business_analysis": BUSINESS_ARCHITECTURE_AGENT.name,
    "capability_analysis": BUSINESS_ARCHITECTURE_AGENT.name,
    "architecture_thinking": ARCHITECTURE_THINKING_AGENT.name,
    "dependency_reasoning": DEPENDENCY_AGENT.name,
    "risk_reasoning": GOVERNANCE_AGENT.name,
    "governance_reasoning": GOVERNANCE_AGENT.name,
    "technology_reasoning": TECHNOLOGY_ARCHITECTURE_AGENT.name,
    "implementation_reasoning": EXECUTION_PLANNING_AGENT.name,
}

_FINDING_CATEGORY_TO_AGENT = {
    "structural": VALIDATION_AGENT.name,
    "policy": GOVERNANCE_AGENT.name,
}


class Orchestrator:
    def run_pipeline(self, objective: str) -> ReasoningResult:
        """Dispatches the Reasoning Pipeline (WP5), attributing each stage to its named
        agent -- the audit-trail extension Phase 7 section 10 calls for."""
        result = _run_reasoning_pipeline(objective)
        for stage_log in result.stages:
            stage_log.agent = _STAGE_TO_AGENT.get(stage_log.stage, ORCHESTRATOR.name)
        return result

    def review_proposal(self, result: ReasoningResult) -> GovernanceReview:
        """Dispatches the Governance Service (WP6), attributing each finding to its
        named agent."""
        review = run_decision_workflow(result)
        for finding in review.findings:
            finding.agent = _FINDING_CATEGORY_TO_AGENT.get(finding.category, ORCHESTRATOR.name)
        return review
