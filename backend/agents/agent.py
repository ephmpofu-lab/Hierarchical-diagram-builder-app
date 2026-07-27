"""Agent taxonomy and per-agent governance boundary (Phase 7 sections 2, 10) -- WP7. Per
Phase 7's own continuity mapping: "No new engine, pipeline, or governance mechanism was
introduced in this phase. What's new here is only the naming, the collaboration pattern,
and the agent-level governance boundary." These 11 agents are the named workers behind the
8-stage Reasoning Pipeline (WP5) and the Governance Service (WP6) -- not a new system.

Several agents (Data/Application Architecture, Documentation, Progress Intelligence) are
named here as the complete taxonomy the architecture calls for, but have no callable
capability yet -- their underlying work (domain-specific decomposition strategies, the
Documentation workspace, progress-intelligence insight surfacing) belongs to later work
packages (WP8, WP11+). Recorded honestly rather than stubbed with fake behavior."""

from dataclasses import dataclass


@dataclass(frozen=True)
class Agent:
    name: str
    category: str  # domain | cross-cutting | orchestrator
    can_propose: str
    cannot_do: str


ORCHESTRATOR = Agent(
    name="Orchestrator",
    category="orchestrator",
    can_propose="Dispatch, sequencing, escalation",
    cannot_do="Generate architecture content or approve anything itself",
)

ARCHITECTURE_THINKING_AGENT = Agent(
    name="Architecture Thinking Agent",
    category="cross-cutting",
    can_propose="A draft architecture skeleton's overall structure",
    cannot_do="Author Business/Data/Application/Technology domain content itself -- it "
    "delegates that to the matching domain agent",
)
BUSINESS_ARCHITECTURE_AGENT = Agent(
    name="Business Architecture Agent",
    category="domain",
    can_propose="Candidate Objectives / Capabilities / Processes within Business",
    cannot_do="Approve its own proposal; directly touch another domain's already-committed nodes",
)
DATA_ARCHITECTURE_AGENT = Agent(
    name="Data Architecture Agent",
    category="domain",
    can_propose="Candidate Data Entities / Attributes",
    cannot_do="Approve its own proposal; directly touch another domain's already-committed nodes",
)
APPLICATION_ARCHITECTURE_AGENT = Agent(
    name="Application Architecture Agent",
    category="domain",
    can_propose="Candidate Applications / Modules / Services",
    cannot_do="Approve its own proposal; directly touch another domain's already-committed nodes",
)
TECHNOLOGY_ARCHITECTURE_AGENT = Agent(
    name="Technology Architecture Agent",
    category="domain",
    can_propose="Candidate Engines / Components / Functions (Solution Building Blocks)",
    cannot_do="Approve its own proposal; directly touch another domain's already-committed nodes",
)
GOVERNANCE_AGENT = Agent(
    name="Governance Agent",
    category="cross-cutting",
    can_propose="Compliance annotations, flagged violations, draft GovernanceDecisions",
    cannot_do="Generate architecture content itself",
)
DEPENDENCY_AGENT = Agent(
    name="Dependency Agent",
    category="cross-cutting",
    can_propose="Candidate Relationships",
    cannot_do="Generate the nodes it relates -- only the relationships between them",
)
VALIDATION_AGENT = Agent(
    name="Validation Agent",
    category="cross-cutting",
    can_propose="ValidationFindings",
    cannot_do="Approve or reject -- findings inform the decision, they aren't the decision",
)
DOCUMENTATION_AGENT = Agent(
    name="Documentation Agent",
    category="cross-cutting",
    can_propose="Draft documentation, Knowledge Base gap reports",
    cannot_do="Approve Knowledge Base changes -- Knowledge Governance is human-only (Phase 6 section 10)",
)
EXECUTION_PLANNING_AGENT = Agent(
    name="Execution Planning Agent",
    category="cross-cutting",
    can_propose="Decomposition plans, candidate Tasks",
    cannot_do="Commit without a governance pass",
)
PROGRESS_INTELLIGENCE_AGENT = Agent(
    name="Progress Intelligence Agent",
    category="cross-cutting",
    can_propose="Read-only progress insights (e.g. stalled-branch flags)",
    cannot_do="Mutate anything -- read-only by design",
)

ALL_AGENTS = [
    ORCHESTRATOR,
    ARCHITECTURE_THINKING_AGENT,
    BUSINESS_ARCHITECTURE_AGENT,
    DATA_ARCHITECTURE_AGENT,
    APPLICATION_ARCHITECTURE_AGENT,
    TECHNOLOGY_ARCHITECTURE_AGENT,
    GOVERNANCE_AGENT,
    DEPENDENCY_AGENT,
    VALIDATION_AGENT,
    DOCUMENTATION_AGENT,
    EXECUTION_PLANNING_AGENT,
    PROGRESS_INTELLIGENCE_AGENT,
]
