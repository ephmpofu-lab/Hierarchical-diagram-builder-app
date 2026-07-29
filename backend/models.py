from typing import Dict, List, Optional
from pydantic import BaseModel, Field


class Comment(BaseModel):
    id: str
    text: str
    created_at: str


class Node(BaseModel):
    id: str
    label: str
    parent_id: Optional[str] = None
    children: List[str] = Field(default_factory=list)
    notes: str = ""
    canvas_x: float = 0
    canvas_y: float = 0
    collapsed: bool = False

    node_type: Optional[str] = None
    status: Optional[str] = None
    priority: Optional[str] = None
    complexity: Optional[str] = None
    risk_level: Optional[str] = None
    tags: List[str] = Field(default_factory=list)
    owner: Optional[str] = None
    comments: List[Comment] = Field(default_factory=list)
    shape: str = "rect"
    group_children: bool = False
    is_group: bool = False
    classification: Optional[str] = None
    custom_color: Optional[str] = None
    planning_status: Optional[str] = None
    locked: bool = False
    abstraction_level: Optional[str] = None  # Contextual | Conceptual | Logical | Physical
    # (TOGAF Building Block levels, Phase 3 section 3.6) -- Physical overrides strategy
    # selection to Technology regardless of classification (Phase 5 section 9, WP8)
    decomposition_terminal: Optional[bool] = None  # human override marking this node
    # terminal early (Phase 5 section 5, HITL point 4) -- None means "not overridden, use
    # the computed stopping rule"
    held_for_change: bool = False  # Phase 5 section 3's "Held" state, applied specifically
    # by Change Impact Analysis (Phase 10 section 8, WP9) -- cleared when a human Approves
    # a GovernanceDecision against this node (Recommitted); a Reject leaves it Held
    target_date: Optional[str] = None  # ISO date (YYYY-MM-DD) -- Phase 9 section 6's own
    # flagged gap ("temporal attributes... do not yet exist on DecompositionNode"), resolved
    # here for WP11b (Timeline workspace) rather than left deferred again
    duration_days: Optional[int] = None  # whole days; None means "no estimate yet"


class Reference(BaseModel):
    id: str
    from_: str = Field(alias="from")
    to: str
    label: Optional[str] = None
    reference_type: Optional[str] = None  # None | "Dependency" | "Warning" | "Broken" | "Data Flow" | "Optional"
    custom_color: Optional[str] = None
    thickness: Optional[str] = None  # "Thin" | "Normal" | "Thick"
    direction: Optional[str] = None  # "Forward" | "Backward" | "Both"
    animated: bool = False
    connector_hidden: bool = False
    line_style: Optional[str] = None  # "solid" | "dashed" | "dotted"
    opacity: Optional[float] = None  # 0-1, None means fully opaque
    show_arrowhead: bool = True
    curve_style: Optional[str] = None  # "curved" (default) | "straight"
    animation_speed: Optional[float] = None  # seconds per lap, None means the default speed

    model_config = {"populate_by_name": True}


class ReferenceCreate(BaseModel):
    from_: str = Field(alias="from")
    to: str
    label: Optional[str] = None
    reference_type: Optional[str] = None

    model_config = {"populate_by_name": True}


class ReferenceUpdate(BaseModel):
    from_: Optional[str] = Field(default=None, alias="from")
    to: Optional[str] = None
    label: Optional[str] = None
    reference_type: Optional[str] = None
    custom_color: Optional[str] = None
    thickness: Optional[str] = None
    direction: Optional[str] = None
    animated: Optional[bool] = None
    connector_hidden: Optional[bool] = None
    line_style: Optional[str] = None
    opacity: Optional[float] = None
    show_arrowhead: Optional[bool] = None
    curve_style: Optional[str] = None
    animation_speed: Optional[float] = None

    model_config = {"populate_by_name": True}


class ActivityEntry(BaseModel):
    id: str
    timestamp: str
    message: str


# ---------- Concept Mode: freeform planning objects ----------
# Deliberately a separate, additive model from Node — planning objects use free x/y
# positioning (dragged, resized, rotated) rather than the deterministic grid the
# architecture tree uses, so they cannot share Node's layout assumptions.

class ConceptObject(BaseModel):
    id: str
    type: str  # rectangle | rounded-rectangle | circle | diamond | sticky-note | arrow | divider | text | icon
    x: float
    y: float
    width: float = 160
    height: float = 90
    rotation: float = 0
    text: str = ""
    color: Optional[str] = None
    border_style: str = "solid"  # solid | dashed | none
    z_index: int = 0
    locked: bool = False
    group_id: Optional[str] = None


class ConceptObjectCreate(BaseModel):
    type: str
    x: float
    y: float
    width: Optional[float] = None
    height: Optional[float] = None
    text: str = ""
    color: Optional[str] = None


class ConceptObjectUpdate(BaseModel):
    x: Optional[float] = None
    y: Optional[float] = None
    width: Optional[float] = None
    height: Optional[float] = None
    rotation: Optional[float] = None
    text: Optional[str] = None
    color: Optional[str] = None
    border_style: Optional[str] = None
    z_index: Optional[int] = None
    locked: Optional[bool] = None
    group_id: Optional[str] = None


class ConvertToNodeRequest(BaseModel):
    parent_id: str


class Project(BaseModel):
    id: str
    name: str
    description: Optional[str] = None
    owner_id: Optional[str] = None  # Supabase auth.users id; None = legacy pre-auth project
    created_at: str
    updated_at: str
    nodes: Dict[str, Node] = Field(default_factory=dict)
    references: List[Reference] = Field(default_factory=list)
    activity_log: List[ActivityEntry] = Field(default_factory=list)
    concept_objects: List[ConceptObject] = Field(default_factory=list)
    requirements: List["Requirement"] = Field(default_factory=list)
    traceability_links: List["TraceabilityLink"] = Field(default_factory=list)
    risks: List["Risk"] = Field(default_factory=list)
    governance_decisions: List["GovernanceDecision"] = Field(default_factory=list)
    validation_findings: List["ValidationFinding"] = Field(default_factory=list)
    risk_assessments: List["RiskAssessment"] = Field(default_factory=list)


class ProjectSummary(BaseModel):
    id: str
    name: str
    updated_at: str
    node_count: int


class ProjectCreate(BaseModel):
    name: str


class ProjectRename(BaseModel):
    name: str


class NodeCreate(BaseModel):
    parent_id: str
    label: str = "New node"
    insert_after: Optional[str] = None
    insert_before: Optional[str] = None
    is_group: bool = False


class NodeUpdate(BaseModel):
    label: Optional[str] = None
    notes: Optional[str] = None
    collapsed: Optional[bool] = None
    node_type: Optional[str] = None
    status: Optional[str] = None
    priority: Optional[str] = None
    complexity: Optional[str] = None
    risk_level: Optional[str] = None
    tags: Optional[List[str]] = None
    owner: Optional[str] = None
    shape: Optional[str] = None
    group_children: Optional[bool] = None
    is_group: Optional[bool] = None
    classification: Optional[str] = None
    custom_color: Optional[str] = None
    planning_status: Optional[str] = None
    locked: Optional[bool] = None
    target_date: Optional[str] = None
    duration_days: Optional[int] = None


class MoveSiblingRequest(BaseModel):
    direction: str  # "up" or "down"


class ReparentRequest(BaseModel):
    new_parent_id: str


class NodePosition(BaseModel):
    canvas_x: float
    canvas_y: float


class NodeWithLevel(Node):
    level: int


class CommentCreate(BaseModel):
    text: str


class TemplateNode(BaseModel):
    label: str
    notes: str = ""
    children: List["TemplateNode"] = Field(default_factory=list)


TemplateNode.model_rebuild()


class Template(BaseModel):
    id: str
    name: str
    created_at: str
    root: TemplateNode


class TemplateSummary(BaseModel):
    id: str
    name: str
    created_at: str
    node_count: int


class TemplateCreate(BaseModel):
    name: str


class OutlineImport(BaseModel):
    text: str


class AddParentRequest(BaseModel):
    label: str = "New parent"


class PasteSubtreeRequest(BaseModel):
    root: TemplateNode


class ValidationIssue(BaseModel):
    id: str
    label: str


class ValidationReport(BaseModel):
    score: int
    rating: str
    duplicate_labels: List[ValidationIssue]
    circular_references: List[List[str]]
    large_modules: List[ValidationIssue]
    single_child_nodes: List[ValidationIssue]
    missing_notes: List[ValidationIssue]
    missing_owners: List[ValidationIssue]
    orphan_nodes: List[ValidationIssue]
    broken_references: List[str]
    avg_depth: float
    max_depth: int
    risk_distribution: Dict[str, int]


# ============================================================================
# Enterprise Architecture Meta Model (Phase 3) -- additive entities, per the
# Phase 12 Implementation Roadmap's WP1 ("Repository domain extension").
# Project-scoped: Requirement, TraceabilityLink, Risk, GovernanceDecision,
# ValidationFinding, RiskAssessment (nested on Project, same whole-project
# load/save semantics as references/concept_objects).
# Project-independent (Knowledge Domain + Standards Library, Phase 8 §2):
# KnowledgeConcept, KnowledgeRelationship, GovernancePrinciple.
# ============================================================================


class Requirement(BaseModel):
    id: str
    description: str
    parent_id: Optional[str] = None  # self-referential -- Requirements form their own
    # parallel tree, cross-linked to the architecture tree via TraceabilityLink rather
    # than merged into it (Phase 5 §6).
    origin_node_id: Optional[str] = None
    status: str = "Draft"  # Draft | Active | Satisfied | Withdrawn


class RequirementCreate(BaseModel):
    description: str
    parent_id: Optional[str] = None
    origin_node_id: Optional[str] = None


class RequirementUpdate(BaseModel):
    description: Optional[str] = None
    status: Optional[str] = None


class TraceabilityLink(BaseModel):
    id: str
    requirement_id: str
    node_id: str
    link_type: str = "satisfies"


class TraceabilityLinkCreate(BaseModel):
    requirement_id: str
    node_id: str
    link_type: str = "satisfies"


class Risk(BaseModel):
    id: str
    description: str
    classification: Optional[str] = None
    initial_level: Optional[str] = None
    residual_level: Optional[str] = None
    status: str = "Identified"  # Identified | Classified | Mitigated | Monitored | Accepted
    target_node_id: Optional[str] = None


class RiskCreate(BaseModel):
    description: str
    classification: Optional[str] = None
    target_node_id: Optional[str] = None


class RiskUpdate(BaseModel):
    description: Optional[str] = None
    classification: Optional[str] = None
    initial_level: Optional[str] = None
    residual_level: Optional[str] = None
    status: Optional[str] = None


class GovernanceDecision(BaseModel):
    id: str
    timestamp: str
    actor: str
    decision_type: str  # Approve | Edit | Reject
    target_node_id: Optional[str] = None
    rationale: Optional[str] = None


class GovernanceDecisionCreate(BaseModel):
    actor: str
    decision_type: str
    target_node_id: Optional[str] = None
    rationale: Optional[str] = None


class ValidationFinding(BaseModel):
    id: str
    timestamp: str
    category: str
    severity: str  # Critical | Warning | Suggestion
    target_node_id: Optional[str] = None


class RiskAssessment(BaseModel):
    id: str
    timestamp: str
    risk_id: str
    assessment_type: str  # Initial | Residual
    level: str


class KnowledgeConcept(BaseModel):
    id: str
    concept_id: str  # the Knowledge Base's own stable id, e.g. "ARC-0002"
    name: str
    category: str
    chapter_source: Optional[int] = None
    section_source: Optional[str] = None
    definition: str
    purpose: Optional[str] = None
    characteristics: List[str] = Field(default_factory=list)
    rules: List[str] = Field(default_factory=list)
    validation_criteria: List[str] = Field(default_factory=list)
    related: List[str] = Field(default_factory=list)
    extended: Dict[str, object] = Field(default_factory=dict)  # non-core YAML keys (e.g.
    # domains:, lifecycle:) retained rather than discarded -- the schema is a common core
    # plus an open extension (Phase 6 §3), not a rigid fixed shape.
    supersedes: Optional[str] = None  # concept_id this one revises, if any -- informational
    # lineage only (Phase 6 §9). The superseded concept keeps its own distinct concept_id and
    # is independently transitioned to status="Superseded"; this is not an atomic version swap
    # under one shared identity (which would require rewriting a live FK'd primary key), and
    # true byte-for-byte historical content diffing is out of scope for this pass -- same kind
    # of explicitly-named gap as the architecture's other repeatedly-flagged open items.
    status: str = "Proposed"  # Proposed | UnderReview | Active | Rejected | Superseded |
    # Deprecated | Archived (Phase 6 §9) -- new concepts always start Proposed; only WP1's
    # original direct-write test data relied on the old "Active" default.


class KnowledgeConceptCreate(BaseModel):
    concept_id: str
    name: str
    category: str
    chapter_source: Optional[int] = None
    section_source: Optional[str] = None
    definition: str
    purpose: Optional[str] = None
    characteristics: List[str] = Field(default_factory=list)
    rules: List[str] = Field(default_factory=list)
    validation_criteria: List[str] = Field(default_factory=list)
    related: List[str] = Field(default_factory=list)
    extended: Dict[str, object] = Field(default_factory=dict)
    supersedes: Optional[str] = None


class KnowledgeIngestRequest(BaseModel):
    markdown: str


class KnowledgeIngestResult(BaseModel):
    created: List[KnowledgeConcept]
    errors: List[str]  # parse-level failures (malformed YAML, missing required keys) --
    # one bad block never aborts the rest of the batch (Phase 6 §3 stage 3).


class QAFinding(BaseModel):
    severity: str  # Critical | Warning
    message: str


class QAReport(BaseModel):
    concept_id: str
    passed: bool  # no Critical findings
    findings: List[QAFinding]


class GovernanceActionRequest(BaseModel):
    rationale: Optional[str] = None


class KnowledgeRelationship(BaseModel):
    id: str
    from_concept_id: str
    to_concept_id: str
    relation_type: str


class KnowledgeRelationshipCreate(BaseModel):
    from_concept_id: str
    to_concept_id: str
    relation_type: str


class GovernancePrinciple(BaseModel):
    id: str
    statement: str
    applies_to_domain: Optional[str] = None
    source_concept_id: Optional[str] = None  # the KnowledgeConcept.concept_id this
    # principle was derived from, if any (Phase 6 §7's rule-to-principle derivation)


class GovernancePrincipleCreate(BaseModel):
    statement: str
    applies_to_domain: Optional[str] = None
    source_concept_id: Optional[str] = None


# ============================================================================
# Enterprise Reasoning Pipeline (Phase 4) -- WP5, Increment 3's synchronous MVP
# of the 8-stage pipeline. A pure-reasoning result: proposals only, never
# auto-committed to a Project -- Phase 4 section 2's lifecycle only commits
# after a governance checkpoint, which this WP does not implement (WP6).
# ============================================================================


class ReasoningRequest(BaseModel):
    objective: str


class ProposedNode(BaseModel):
    label: str
    node_type: Optional[str] = None
    parent_hint: Optional[str] = None  # label of the intended parent, if any --
    # resolved by a human or a later decomposition step (Phase 5), not this WP
    notes: str = ""


class ProposedRelationship(BaseModel):
    from_label: str
    to_label: str
    label: Optional[str] = None
    reference_type: Optional[str] = None


class ProposedRisk(BaseModel):
    description: str
    classification: Optional[str] = None
    initial_level: Optional[str] = None  # Critical | High | Medium | Low


class ReasoningStageLog(BaseModel):
    stage: str
    summary: str
    agent: str = ""  # which named agent performed this stage (Phase 7 WP7) -- blank
    # when produced directly by intelligence.pipeline.run_pipeline without going through
    # the Orchestrator, so older callers/tests are unaffected


class ReasoningResult(BaseModel):
    objective: str
    domains: List[str] = Field(default_factory=list)
    stages: List[ReasoningStageLog] = Field(default_factory=list)
    proposed_nodes: List[ProposedNode] = Field(default_factory=list)
    proposed_relationships: List[ProposedRelationship] = Field(default_factory=list)
    proposed_risks: List[ProposedRisk] = Field(default_factory=list)
    confidence_tier: str = "Low"  # High | Medium | Low (Phase 4 section 8)
    confidence_rationale: str = ""
    requires_human_review: bool = True  # Medium/Low always True; High still passes
    # governance but without a MANDATORY blocking review (Phase 4 section 8's own rule)
    governance_notes: List[str] = Field(default_factory=list)


# ============================================================================
# Governance Service (Phase 10) -- WP6. The Decision & Approval Workflow (section 3)
# and the Validation Framework's structural + policy checks (section 4), formalizing
# what WP5's reasoning pipeline already produces into an enforcement decision, plus
# real persistence for the WP1-era GovernanceDecision/Risk-acceptance actions, which
# have had a model since WP1 but no API surface until this WP.
# ============================================================================


class GovernanceFinding(BaseModel):
    category: str  # structural | policy
    severity: str  # Critical | Warning
    message: str
    agent: str = ""  # which named agent produced this finding (Phase 7 WP7) -- Validation
    # Agent for structural, Governance Agent for policy; blank when produced directly by
    # governance.workflow.run_decision_workflow without going through the Orchestrator


class GovernanceReview(BaseModel):
    outcome: str  # approved | rejected | held_pending_human_review | held_pending_risk_acceptance
    findings: List[GovernanceFinding] = Field(default_factory=list)
    requires_human_review: bool = False
    requires_risk_acceptance: bool = False
    rationale: str = ""


class DecomposeRequest(BaseModel):
    strategy_override: Optional[str] = None  # a human re-selecting the strategy (Phase 5
    # section 10, HITL points 1 & 5) instead of the computed default


class DecompositionResult(BaseModel):
    strategy: str
    parallel_strategy: Optional[str] = None  # set only when an active Risk against this
    # node triggers the Governance strategy to run alongside the primary one (section 9)
    terminal: bool
    proposed_nodes: List[ProposedNode] = Field(default_factory=list)
    review: Optional[GovernanceReview] = None
    committed_node_ids: List[str] = Field(default_factory=list)
    parallel_proposed_nodes: List[ProposedNode] = Field(default_factory=list)
    parallel_review: Optional[GovernanceReview] = None
    parallel_committed_node_ids: List[str] = Field(default_factory=list)


class ChangeImpactRequest(BaseModel):
    reason: str = ""  # optional human rationale for the change about to be made -- this
    # endpoint computes and flags impact only; the actual edit still goes through the
    # existing node-edit endpoints unchanged (Phase 10 section 8, WP9)


class ChangeImpactFinding(BaseModel):
    node_id: str
    label: str
    reason: str  # "Structural descendant..." | "Traced to the same Requirement (...) ..."


class ChangeImpactResult(BaseModel):
    trigger_node_id: str
    findings: List[ChangeImpactFinding] = Field(default_factory=list)
    held_count: int = 0


class CycleEvent(BaseModel):
    id: str
    timestamp: str
    event_type: str  # CycleStarted | StageCompleted | Compliant | Violation | Committed | CycleFailed
    detail: str = ""


class Cycle(BaseModel):
    id: str
    project_id: Optional[str] = None  # None for a "reasoning" cycle -- the existing
    # /api/intelligence/reason it wraps was never project-scoped either (WP5)
    kind: str  # "reasoning" | "decomposition" (Phase 11 section 5's "AI-driven, inherently
    # long-running operations" -- everything else stays on the existing synchronous REST API)
    status: str = "Running"  # Running | Completed | Failed
    objective: Optional[str] = None  # reasoning cycles
    node_id: Optional[str] = None  # decomposition cycles
    events: List[CycleEvent] = Field(default_factory=list)
    result: Optional[dict] = None  # the completed ReasoningResult/DecompositionResult, as a
    # plain dict -- deliberately untyped here since a Cycle can wrap either shape
    error: Optional[str] = None


class AISuitabilitySignals(BaseModel):
    """Structured inputs to the AI Suitability Assessment Tool (ADR-006, WP16a) --
    deliberately explicit booleans, not raw text, so the classifier stays deterministic
    (see backend/tools/ai_suitability.py's own module docstring for why)."""

    requires_external_knowledge_retrieval: bool = False
    requires_multi_step_autonomous_tool_use: bool = False
    requires_pattern_prediction_from_historical_data: bool = False
    process_is_fully_deterministic: bool = False
    requires_natural_language_understanding_or_generation: bool = False


class AISuitabilityAssessment(BaseModel):
    recommended_pattern: str  # Rules Engine | Workflow Automation | Agentic AI | RAG |
    # Predictive AI | Generic LLM
    rationale: str  # which rule fired and why -- always deterministic, never AI-authored
    signals: AISuitabilitySignals
    explanation: Optional[str] = None  # populated only when explain=true is requested;
    # phrasing only, never re-decides recommended_pattern


class RiskAssessmentSignals(BaseModel):
    """Structured inputs to the Risk Assessment Tool (ADR-006, WP16b) -- ISO 31000-style
    5-point likelihood/impact scales, assessed separately rather than guessed as one
    combined level (see backend/tools/risk_assessment.py's own module docstring)."""

    likelihood: str  # Rare | Unlikely | Possible | Likely | Almost Certain
    impact: str  # Negligible | Minor | Moderate | Major | Severe


class RiskAssessmentResult(BaseModel):
    level: str  # Critical | High | Medium | Low -- computed, never AI-authored
    rationale: str  # the matrix computation that produced level
    likelihood: str
    impact: str
    explanation: Optional[str] = None  # populated only when explain=true is requested


class GovernanceAssessmentSignals(BaseModel):
    """Structured inputs to the Governance Assessment Tool (ADR-006, WP16c) -- one
    boolean per ISO 38500 principle, assessed separately rather than a single holistic
    governance judgment (see backend/tools/governance_assessment.py's own docstring)."""

    has_assigned_owner: bool = False  # ISO 38500 Responsibility
    aligns_with_documented_strategy: bool = False  # ISO 38500 Strategy
    acquisition_is_justified: bool = False  # ISO 38500 Acquisition
    has_performance_monitoring: bool = False  # ISO 38500 Performance
    has_no_unresolved_critical_findings: bool = True  # ISO 38500 Conformance -- hard gate
    considers_human_impact: bool = False  # ISO 38500 Human Behaviour


class GovernanceAssessmentResult(BaseModel):
    verdict: str  # Non-Conformant | Partially Conformant | Substantially Conformant | Fully Conformant
    rationale: str  # computed, never AI-authored
    principles_satisfied: List[str] = Field(default_factory=list)
    principles_unmet: List[str] = Field(default_factory=list)
    signals: GovernanceAssessmentSignals
    explanation: Optional[str] = None  # populated only when explain=true is requested


class RequirementQualitySignals(BaseModel):
    """Structured inputs to the Requirement Analysis Tool (ADR-006, WP16d) -- the raw
    requirement text plus two structural facts the tool can't infer from text alone (see
    backend/tools/requirement_analysis.py's own docstring)."""

    description: str
    has_acceptance_criteria: bool = False
    has_assigned_owner: bool = False


class RequirementQualityResult(BaseModel):
    verdict: str  # Well-Formed | Needs Revision -- computed, never AI-authored
    findings: List[str] = Field(default_factory=list)
    signals: RequirementQualitySignals
    explanation: Optional[str] = None  # populated only when explain=true is requested


class SecurityAssessmentSignals(BaseModel):
    """Structured inputs to the Security Architecture Tool (ADR-006, WP16e) -- one
    boolean per NIST CSF control area, assessed separately rather than a single holistic
    security judgment (see backend/tools/security_assessment.py's own docstring)."""

    has_asset_inventory: bool = False  # Identify
    has_authentication_and_authorization: bool = False  # Protect (Zero Trust: verify explicitly)
    has_encryption_at_rest_and_in_transit: bool = False  # Protect
    has_input_validation: bool = False  # Protect (OWASP)
    has_monitoring_and_logging: bool = False  # Detect
    has_incident_response_plan: bool = False  # Respond
    has_backup_and_recovery_plan: bool = False  # Recover


class SecurityAssessmentResult(BaseModel):
    verdict: str  # Non-Compliant | Partially Compliant | Substantially Compliant | Fully Compliant
    rationale: str  # computed, never AI-authored
    functions_satisfied: List[str] = Field(default_factory=list)  # NIST CSF functions covered
    functions_unmet: List[str] = Field(default_factory=list)
    signals: SecurityAssessmentSignals
    explanation: Optional[str] = None  # populated only when explain=true is requested


Project.model_rebuild()
