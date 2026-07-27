"""Agent Orchestration (Phase 7 sections 4-5) -- WP7. Hub-and-spoke: agents never
communicate peer-to-peer; the Orchestrator is the one and only thing that dispatches to
them. This wraps the Reasoning Pipeline (WP5) and the Governance Service (WP6) -- both
already built and live-verified -- with per-stage/per-finding agent attribution and
sequencing. It does not reimplement any reasoning or validation logic: "No new engine,
pipeline, or governance mechanism was introduced in this phase" (Phase 7's own continuity
mapping). Recovery from a failed stage is already just re-invocation against the same
stateless AI Service call (WP4/WP5) -- nothing new needed for Phase 7 section 11 either."""

from ..decomposition import selector as decomposition_selector
from ..decomposition import stopping as decomposition_stopping
from ..decomposition.service import generate_children
from ..decomposition.strategies import STRATEGIES
from ..governance.workflow import run_decision_workflow
from ..intelligence.context import assemble_reasoning_context
from ..intelligence.pipeline import _score_confidence
from ..intelligence.pipeline import run_pipeline as _run_reasoning_pipeline
from ..intelligence.stages import ReasoningStageError
from ..models import DecompositionResult, GovernanceReview, Node, Project, ReasoningResult, ReasoningStageLog
from ..observability.metrics import record_agent_invocation
from .agent import (
    APPLICATION_ARCHITECTURE_AGENT,
    ARCHITECTURE_THINKING_AGENT,
    BUSINESS_ARCHITECTURE_AGENT,
    DATA_ARCHITECTURE_AGENT,
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

# Maps a decomposition strategy (Phase 5 section 4) to the agent that owns it -- WP8 is
# where the Data/Application/Technology Architecture Agents get their first real callable
# capability, closing the gap WP7 flagged (named in the taxonomy but nothing to do yet).
_STRATEGY_TO_AGENT = {
    "Business": BUSINESS_ARCHITECTURE_AGENT.name,
    "Data": DATA_ARCHITECTURE_AGENT.name,
    "Application": APPLICATION_ARCHITECTURE_AGENT.name,
    "Technology": TECHNOLOGY_ARCHITECTURE_AGENT.name,
    "Governance": GOVERNANCE_AGENT.name,
}


def _safe_record_agent_invocation(agent_name: str, success: bool, project_id=None, error_type=None) -> None:
    # Observability (Phase 11 section 13, WP13b) is deliberately best-effort here too --
    # same reasoning as backend/ai/service.py's AI call metrics: a metrics write failure
    # must never become a second, unrelated failure on top of (or instead of) a real result.
    try:
        record_agent_invocation(agent_name, success, project_id=project_id, error_type=error_type)
    except Exception:  # noqa: BLE001
        pass


class Orchestrator:
    def run_pipeline(self, objective: str) -> ReasoningResult:
        """Dispatches the Reasoning Pipeline (WP5), attributing each stage to its named
        agent -- the audit-trail extension Phase 7 section 10 calls for."""
        try:
            result = _run_reasoning_pipeline(objective)
        except ReasoningStageError as exc:
            # Which specific stage failed isn't known here without instrumenting
            # intelligence/pipeline.py itself (deliberately not touched, per this
            # increment's whole "no new engine" discipline) -- attributed to the
            # Orchestrator as the dispatcher, an honest, coarser signal rather than a
            # fabricated precise one.
            _safe_record_agent_invocation(ORCHESTRATOR.name, False, error_type=type(exc).__name__)
            raise
        for stage_log in result.stages:
            stage_log.agent = _STAGE_TO_AGENT.get(stage_log.stage, ORCHESTRATOR.name)
            _safe_record_agent_invocation(stage_log.agent, True)
        return result

    def review_proposal(self, result: ReasoningResult) -> GovernanceReview:
        """Dispatches the Governance Service (WP6), attributing each finding to its
        named agent."""
        review = run_decision_workflow(result)
        seen_agents = set()
        for finding in review.findings:
            finding.agent = _FINDING_CATEGORY_TO_AGENT.get(finding.category, ORCHESTRATOR.name)
            if finding.agent not in seen_agents:
                seen_agents.add(finding.agent)
                _safe_record_agent_invocation(finding.agent, True)
        return review

    def decompose_node(self, project: Project, node: Node, strategy_override=None) -> DecompositionResult:
        """Recursive Decomposition Framework (Phase 5) for one already-committed node.
        Selects a strategy (section 9), stops if the node already matches its strategy's
        leaf type (section 5), otherwise generates its next level of candidate children
        and runs the same Governance Service review WP6 already established -- no second
        governance mechanism, per this whole increment's continuity discipline. Governance
        runs as a second, independent pass alongside the primary strategy whenever the node
        has an active Risk against it (section 9's "parallel, not instead of" rule)."""
        has_active_risk = any(
            r.target_node_id == node.id and r.status not in ("Accepted", "Mitigated") for r in project.risks
        )
        primary, parallel_name = decomposition_selector.select_strategy(node, has_active_risk)
        strategy_name = strategy_override if strategy_override in STRATEGIES else primary
        terminal = decomposition_stopping.is_terminal(node, strategy_name)

        result = DecompositionResult(strategy=strategy_name, parallel_strategy=parallel_name, terminal=terminal)
        if not terminal:
            result.proposed_nodes, result.review = self._run_strategy(node, strategy_name, project.id)
        if parallel_name and not decomposition_stopping.is_terminal(node, parallel_name):
            result.parallel_proposed_nodes, result.parallel_review = self._run_strategy(
                node, parallel_name, project.id
            )
        return result

    def _run_strategy(self, node: Node, strategy_name: str, project_id: str):
        agent_name = _STRATEGY_TO_AGENT.get(strategy_name, ORCHESTRATOR.name)
        reasoning_context = assemble_reasoning_context(f"{node.label}. {node.notes}".strip())
        try:
            children = generate_children(node, strategy_name, reasoning_context)
        except ReasoningStageError as exc:
            _safe_record_agent_invocation(agent_name, False, project_id=project_id, error_type=type(exc).__name__)
            raise
        _safe_record_agent_invocation(agent_name, True, project_id=project_id)
        confidence_tier, rationale = _score_confidence(reasoning_context, [], True, 0)
        reasoning_result = ReasoningResult(
            objective=node.label,
            domains=[strategy_name],
            stages=[
                ReasoningStageLog(
                    stage=f"decompose:{strategy_name}",
                    summary=f"{len(children)} candidate child(ren)",
                    agent=agent_name,
                )
            ],
            proposed_nodes=children,
            confidence_tier=confidence_tier,
            confidence_rationale=rationale,
            requires_human_review=confidence_tier != "High",
        )
        review = run_decision_workflow(reasoning_result)
        seen_agents = set()
        for finding in review.findings:
            finding.agent = _FINDING_CATEGORY_TO_AGENT.get(finding.category, ORCHESTRATOR.name)
            if finding.agent not in seen_agents:
                seen_agents.add(finding.agent)
                _safe_record_agent_invocation(finding.agent, True, project_id=project_id)
        return children, review
