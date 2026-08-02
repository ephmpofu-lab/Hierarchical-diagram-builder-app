import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query, Response

from . import concept, storage, tree
from .agents.agent import ALL_AGENTS
from .agents.orchestrator import Orchestrator
from .tools import (
    ai_suitability,
    api_design,
    database_design,
    deployment_architecture,
    governance_assessment,
    requirement_analysis,
    risk_assessment,
    security_assessment,
    test_design,
    workflow_verification,
)
from .tools.tool import ALL_TOOLS
from .ai import service as ai_service
from .ai.provider import AIProviderError
from .auth import AuthenticatedUser, require_auth
from .architecture.service import build_architecture_view
from .change.impact import analyze_impact
from .cycles.service import run_decomposition_cycle, run_reasoning_cycle
from .db import postgres_cycle_repository as cycle_repo
from .db import postgres_discovery_repository as discovery_repo
from .blueprint.commit import commit_blueprint
from .decomposition.commit import commit_children
from .decompose.engine import propose_checklist, propose_tree, refine_tree, regroup_subtask
from .discovery.commit import commit_initiation_report
from .engineering.service import run_engineering_pipeline
from .intelligence.commit import commit_reasoning_proposal
from .intent.service import parse_intent
from .observability.metrics import summarize
from .intelligence.stages import ReasoningStageError
from .knowledge import lifecycle
from .knowledge.ingestion import parse_markdown
from .knowledge.qa import run_qa
from .knowledge.retrieval import retrieve as retrieve_knowledge
from .render.n8n_exporter import export_workflow
from .render.python_exporter import export_python_package
from .render.python_renderer import render_python
from .component import engine as component_engine
from .component import repository as component_repo
from .data_architecture import engine as data_architecture_engine
from .data_architecture import repository as data_architecture_repo
from .taxonomy import repository as taxonomy_repo
from .validator.service import validate_tree
from .models import (
    AddParentRequest,
    AISuitabilityAssessment,
    AISuitabilitySignals,
    APIDesignResult,
    APIDesignSignals,
    ArchitectureView,
    BlueprintResult,
    ChangeImpactRequest,
    ChangeImpactResult,
    Comment,
    Cycle,
    CommentCreate,
    ConceptObject,
    ConceptObjectCreate,
    ConceptObjectUpdate,
    ConvertToNodeRequest,
    DatabaseDesignResult,
    DatabaseDesignSignals,
    DecomposeRequest,
    DecompositionResult,
    DeploymentReadinessResult,
    DeploymentReadinessSignals,
    DiscoverySession,
    DiscoveryTurn,
    DiscoveryTurnRequest,
    DomainApproveRequest,
    DomainChecklist,
    ComponentTree,
    ComponentTreeApproveRequest,
    ComponentTreeDraftRequest,
    ComponentTreeDraftResult,
    DataArchitecture,
    DataArchitectureApproveRequest,
    DataArchitectureDraftRequest,
    DataArchitectureDraftResult,
    DomainDraftRequest,
    DomainDraftResult,
    DomainRenderRequest,
    DomainSummary,
    DomainTaskTree,
    GovernanceActionRequest,
    GovernanceAssessmentResult,
    GovernanceAssessmentSignals,
    GovernanceDecision,
    GovernanceDecisionCreate,
    GovernancePrinciple,
    GovernancePrincipleCreate,
    GovernanceReview,
    IntentRequest,
    IntentResult,
    KnowledgeConcept,
    KnowledgeIngestRequest,
    KnowledgeIngestResult,
    KnowledgeRelationship,
    KnowledgeRelationshipCreate,
    MoveSiblingRequest,
    N8nWorkflow,
    NodeCreate,
    NodePosition,
    NodeUpdate,
    NodeWithLevel,
    OutlineImport,
    PasteSubtreeRequest,
    PrincipleViolation,
    Project,
    ProjectCreate,
    ProjectInitiationReport,
    ProjectRename,
    ProjectSummary,
    QAReport,
    ReasoningRequest,
    ReasoningResult,
    Reference,
    ReferenceCreate,
    ReferenceUpdate,
    RefineTreeRequest,
    RegroundConfirmRequest,
    RegroundRequest,
    RenderedCodeBlock,
    ReparentRequest,
    RequirementQualityResult,
    RequirementQualitySignals,
    Risk,
    RiskAssessment,
    RiskAssessmentResult,
    RiskAssessmentSignals,
    SecurityAssessmentResult,
    SecurityAssessmentSignals,
    TaskTreeNode,
    Template,
    TemplateCreate,
    TemplateNode,
    TemplateSummary,
    TestDesignResult,
    TestDesignSignals,
    ValidationReport,
    ValidationResult,
    Variable,
    WorkflowVerificationResult,
    WorkflowVerificationSignals,
)

# Every route in this router requires a valid Supabase session -- "login required before
# accessing any project", the security requirement stated at the start of this project.
# Ownership enforcement (below) is scoped to the project-lifecycle boundary routes only
# (create/get/rename/delete/restore/clear/validation) for this pass, not every individual
# node/reference/comment sub-route -- a deliberate, stated WP2 scope line, not an oversight:
# with exactly one real user account today the residual gap is low-risk, and deep
# per-operation checks are straightforward to extend later following this same pattern.
router = APIRouter(prefix="/api", dependencies=[Depends(require_auth)])


def _project_with_levels(project: Project) -> dict:
    data = project.model_dump(by_alias=True)
    for node_id, node_data in data["nodes"].items():
        node_data["level"] = tree.compute_level(project, node_id)
    return data


def _ensure_owner(project: Project, user: AuthenticatedUser) -> None:
    # owner_id is None for legacy projects created before auth existed -- accessible to
    # any authenticated user until explicitly claimed, rather than locking them out.
    if project.owner_id is not None and project.owner_id != user.id:
        raise HTTPException(status_code=403, detail="You do not have access to this project")


def _ensure_session_owner(session: DiscoverySession, user: AuthenticatedUser) -> None:
    # Same posture as _ensure_owner above -- owner_id is nullable purely for testability
    # against the live auth.users FK (see DiscoverySession.owner_id's own docstring); a
    # null-owner session is accessible to any authenticated user, same as a legacy project.
    if session.owner_id is not None and session.owner_id != user.id:
        raise HTTPException(status_code=403, detail="You do not have access to this discovery session")


@router.get("/session")
def api_get_session(user: AuthenticatedUser = Depends(require_auth)):
    """A lightweight "who am I" check. This exists specifically so the frontend can verify
    a session is genuinely backend-valid before trusting it -- the Supabase client's own
    local getSession() only checks the token's client-side expiry, which can disagree with
    what this backend actually accepts (a real gap that produced a login/index redirect
    ping-pong: the login page trusted the local check, the app pages trusted the backend,
    and the two disagreed). Both pages now defer to this endpoint as the one source of truth."""
    return {"id": user.id, "email": user.email, "role": user.role}


@router.get("/ai/health")
def api_ai_health():
    """Verifies the AI Service abstraction end-to-end with one trivial completion call
    (WP4 / ADR-002) -- exercises the configured provider, not any specific vendor SDK."""
    try:
        result = ai_service.complete(
            system="You respond with exactly one word and nothing else.",
            prompt="Reply with the single word: OK",
            max_tokens=16,
        )
    except AIProviderError as exc:
        raise HTTPException(status_code=502, detail=f"AI provider error: {exc}") from exc
    return {
        "provider": ai_service.AI_PROVIDER,
        "model": result.model,
        "retries": result.retries,
        "response": result.text.strip(),
    }


@router.get("/observability/summary")
def api_observability_summary(hours: int = Query(24, ge=1, le=24 * 30)):
    """The technical substrate Phase 10 section 10's Governance Performance Monitoring
    reads from (Phase 11 section 13 / WP13b) -- AI service call metrics and agent
    invocation success/failure rates, aggregated over a recent rolling window. Building
    the monitoring dashboard itself remains out of scope (WP6's own scope line: "not
    requested") -- this only exposes the raw, already-recorded signals."""
    return summarize(hours=hours)


@router.get("/agents")
def api_list_agents():
    """The Agent taxonomy and governance boundary (Phase 7 sections 2, 10 / WP7) --
    inspectable data, not just documentation."""
    return [a.__dict__ for a in ALL_AGENTS]


@router.get("/tools")
def api_list_tools():
    """The Tool Registry (Tool Engineering Architecture, ADR-006 / WP16) -- inspectable
    data, honestly marked built/partial/not_built rather than assumed complete."""
    return [t.__dict__ for t in ALL_TOOLS]


@router.post("/tools/ai-suitability", response_model=AISuitabilityAssessment)
def api_assess_ai_suitability(signals: AISuitabilitySignals, explain: bool = Query(False)):
    """AI Suitability Assessment Tool (ADR-006, WP16a) -- a deterministic decision-tree
    classification, never an LLM call. `explain=true` additionally asks the AI Service to
    phrase the already-decided result in prose; it never changes the recommendation."""
    assessment = ai_suitability.assess(signals)
    if explain:
        assessment = assessment.model_copy(update={"explanation": ai_suitability.explain(assessment)})
    return assessment


@router.post("/tools/risk-assessment", response_model=RiskAssessmentResult)
def api_assess_risk(signals: RiskAssessmentSignals, explain: bool = Query(False)):
    """Risk Assessment Tool (ADR-006, WP16b) -- a deterministic ISO 31000-style
    likelihood x impact matrix, never an LLM call. `explain=true` additionally asks the
    AI Service to phrase the already-computed level in prose; it never changes it."""
    try:
        result = risk_assessment.assess(signals)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    if explain:
        result = result.model_copy(update={"explanation": risk_assessment.explain(result)})
    return result


@router.post("/tools/governance-assessment", response_model=GovernanceAssessmentResult)
def api_assess_governance(signals: GovernanceAssessmentSignals, explain: bool = Query(False)):
    """Governance Assessment Tool (ADR-006, WP16c) -- a deterministic ISO 38500
    six-principle assessment, never an LLM call. `explain=true` additionally asks the AI
    Service to phrase the already-computed verdict in prose; it never changes it."""
    result = governance_assessment.assess(signals)
    if explain:
        result = result.model_copy(update={"explanation": governance_assessment.explain(result)})
    return result


@router.post("/tools/requirement-analysis", response_model=RequirementQualityResult)
def api_analyze_requirement(signals: RequirementQualitySignals, explain: bool = Query(False)):
    """Requirement Analysis Tool (ADR-006, WP16d) -- deterministic INCOSE/IEEE 830
    weak-word and completeness checks, never an LLM call. `explain=true` additionally
    asks the AI Service to phrase the already-computed findings in prose; it never adds
    or removes a finding."""
    result = requirement_analysis.assess(signals)
    if explain:
        result = result.model_copy(update={"explanation": requirement_analysis.explain(result)})
    return result


@router.post("/tools/security-assessment", response_model=SecurityAssessmentResult)
def api_assess_security(signals: SecurityAssessmentSignals, explain: bool = Query(False)):
    """Security Architecture Tool (ADR-006, WP16e) -- a deterministic NIST CSF
    five-function checklist, never an LLM call. `explain=true` additionally asks the AI
    Service to phrase the already-computed verdict in prose; it never changes it."""
    result = security_assessment.assess(signals)
    if explain:
        result = result.model_copy(update={"explanation": security_assessment.explain(result)})
    return result


@router.post("/tools/database-design", response_model=DatabaseDesignResult)
def api_assess_database_design(signals: DatabaseDesignSignals, explain: bool = Query(False)):
    """Database Design Tool (ADR-006, WP16f) -- a deterministic Codd normal-form check
    (1NF/2NF/3NF), never an LLM call. `explain=true` additionally asks the AI Service to
    phrase the already-computed result in prose; it never changes it."""
    result = database_design.assess(signals)
    if explain:
        result = result.model_copy(update={"explanation": database_design.explain(result)})
    return result


@router.post("/tools/workflow-verification", response_model=WorkflowVerificationResult)
def api_verify_workflow(signals: WorkflowVerificationSignals, explain: bool = Query(False)):
    """Workflow Verification Tool (ADR-006, WP16g) -- deterministic BPMN structural
    well-formedness checks (reachability, cycle detection) over an explicit directed
    graph, never an LLM call. `explain=true` additionally asks the AI Service to phrase
    the already-computed verdict in prose; it never changes it."""
    result = workflow_verification.assess(signals)
    if explain:
        result = result.model_copy(update={"explanation": workflow_verification.explain(result)})
    return result


@router.post("/tools/api-design", response_model=APIDesignResult)
def api_assess_api_design(signals: APIDesignSignals, explain: bool = Query(False)):
    """API Design Tool (ADR-006, WP16h) -- deterministic REST convention checks
    (noun-resource naming, method/body semantics), never an LLM call. `explain=true`
    additionally asks the AI Service to phrase the already-computed findings in prose;
    it never adds, removes, or reweights a finding."""
    result = api_design.assess(signals)
    if explain:
        result = result.model_copy(update={"explanation": api_design.explain(result)})
    return result


@router.post("/tools/test-design", response_model=TestDesignResult)
def api_recommend_test_design(signals: TestDesignSignals, explain: bool = Query(False)):
    """Test Design Tool (ADR-006, WP16i) -- deterministic ISTQB test-level mapping,
    never an LLM call. `explain=true` additionally asks the AI Service to phrase the
    already-computed recommendation in prose; it never adds or removes a level."""
    result = test_design.assess(signals)
    if explain:
        result = result.model_copy(update={"explanation": test_design.explain(result)})
    return result


@router.post("/tools/deployment-architecture", response_model=DeploymentReadinessResult)
def api_assess_deployment_readiness(
    signals: DeploymentReadinessSignals, explain: bool = Query(False)
):
    """Deployment Architecture Tool (ADR-006, WP16j) -- a deterministic 12-Factor App
    checklist, never an LLM call. `explain=true` additionally asks the AI Service to
    phrase the already-computed verdict in prose; it never changes it."""
    result = deployment_architecture.assess(signals)
    if explain:
        result = result.model_copy(update={"explanation": deployment_architecture.explain(result)})
    return result


@router.post("/intelligence/reason", response_model=ReasoningResult)
def api_reason(body: ReasoningRequest):
    """Runs the 8-stage Enterprise Reasoning Pipeline (WP5 / Phase 4) via the Orchestrator
    (WP7 / Phase 7), which dispatches to and attributes each stage to its named agent.
    Synchronous, single-pass. Returns proposals only -- nothing here is committed to any
    project; that requires the governance checkpoint below."""
    if not body.objective.strip():
        raise HTTPException(status_code=400, detail="Objective cannot be empty")
    try:
        return Orchestrator().run_pipeline(body.objective.strip())
    except ReasoningStageError as exc:
        raise HTTPException(status_code=502, detail=f"Reasoning pipeline failed: {exc}") from exc


@router.post("/intelligence/reason-async", response_model=Cycle, status_code=202)
def api_reason_async(
    body: ReasoningRequest, background_tasks: BackgroundTasks, user: AuthenticatedUser = Depends(require_auth)
):
    """The event-driven counterpart to /intelligence/reason above (Phase 11 sections 5-6,
    WP10): accepts the request and returns a Cycle acknowledgment immediately instead of
    blocking on the full 8-stage pipeline. The same Orchestrator call runs in the
    background; poll GET /cycles/{cycle_id} for progress and the final result. Not
    project-scoped, matching the synchronous endpoint it wraps (WP5's reasoning pipeline
    never belonged to a project either)."""
    if not body.objective.strip():
        raise HTTPException(status_code=400, detail="Objective cannot be empty")
    cycle = cycle_repo.create_cycle(kind="reasoning", objective=body.objective.strip())
    background_tasks.add_task(run_reasoning_cycle, cycle.id, body.objective.strip())
    return cycle


@router.post("/projects/{project_id}/nodes/{parent_id}/commit-reasoning")
def api_commit_reasoning(
    project_id: str, parent_id: str, body: ReasoningResult, user: AuthenticatedUser = Depends(require_auth)
):
    """Commits an approved Reasoning Pipeline proposal into real project data (first UI
    phase for the reasoning/governance backend) -- the reasoning pipeline and governance
    review above only ever produce a proposal; nothing commits it without this step. Mirrors
    decomposition's own commit_children (WP8) for node creation, extended to also commit
    proposed_relationships as real References and proposed_risks as real Risks, since a
    reasoning proposal carries all three, not just nodes. No response_model, matching the
    plain-dict precedent GET /api/agents and GET /api/tools already established."""
    project = storage.load_project(project_id)
    _ensure_owner(project, user)
    tree.get_node_or_404(project, parent_id)
    committed_node_ids, committed_risk_ids = commit_reasoning_proposal(
        project, parent_id, body, user.email or user.id
    )
    tree.log_activity(
        project, f"Committed reasoning proposal for '{body.objective}' ({len(committed_node_ids)} node(s))"
    )
    storage.save_project(project)
    return {"committed_node_ids": committed_node_ids, "committed_risk_ids": committed_risk_ids}


@router.get("/cycles/{cycle_id}", response_model=Cycle)
def api_get_cycle(cycle_id: str, user: AuthenticatedUser = Depends(require_auth)):
    """Polls a Cycle's current status/events/result (Phase 11 section 6) -- this stack has
    no websocket/push infrastructure, so a client observes progress by polling this
    endpoint rather than receiving a true server push; the Cycle record itself is exactly
    what section 6's diagram calls "CycleUpdated"."""
    cycle = cycle_repo.get_cycle(cycle_id)
    if cycle is None:
        raise HTTPException(status_code=404, detail="Cycle not found")
    if cycle.project_id is not None:
        _ensure_owner(storage.load_project(cycle.project_id), user)
    return cycle


@router.get("/projects/{project_id}/cycles", response_model=list[Cycle])
def api_list_cycles(project_id: str, user: AuthenticatedUser = Depends(require_auth)):
    """Recent decomposition Cycles for this project (Phase 11 section 6), newest first."""
    project = storage.load_project(project_id)
    _ensure_owner(project, user)
    return cycle_repo.list_cycles(project_id)


@router.post("/governance/review", response_model=GovernanceReview)
def api_governance_review(result: ReasoningResult):
    """Runs the Decision & Approval Workflow (WP6 / Phase 10 section 3) via the
    Orchestrator, against a ReasoningResult the caller already has from
    /api/intelligence/reason. Stateless -- nothing here is persisted; recording an actual
    human decision is a separate call below, scoped to a real project."""
    return Orchestrator().review_proposal(result)


@router.post("/projects/{project_id}/governance-decisions", response_model=GovernanceDecision, status_code=201)
def api_record_governance_decision(
    project_id: str, body: GovernanceDecisionCreate, user: AuthenticatedUser = Depends(require_auth)
):
    """Records a human's approve/edit/reject decision (Phase 10 section 3/9) -- the first
    real persistence path for the GovernanceDecision model WP1 defined. `actor` is always
    the authenticated caller, never client-supplied, so the audit trail (section 9's "who
    approved, and why") can't be spoofed."""
    project = storage.load_project(project_id)
    decision = GovernanceDecision(
        id=str(uuid.uuid4()),
        timestamp=datetime.now(timezone.utc).isoformat(),
        actor=user.email or user.id,
        decision_type=body.decision_type,
        target_node_id=body.target_node_id,
        rationale=body.rationale,
    )
    project.governance_decisions.append(decision)
    # An Approve decision against a Held node clears it (Recommitted, Phase 10 section 8) --
    # a Reject leaves it Held, which needs no extra action since it's already flagged.
    if body.decision_type == "Approve" and body.target_node_id is not None:
        target = project.nodes.get(body.target_node_id)
        if target is not None and target.held_for_change:
            target.held_for_change = False
    tree.log_activity(project, f"Governance decision recorded: {body.decision_type} by {decision.actor}")
    storage.save_project(project)
    return decision


@router.post("/projects/{project_id}/nodes/{node_id}/propose-change", response_model=ChangeImpactResult)
def api_propose_change(
    project_id: str, node_id: str, body: ChangeImpactRequest, user: AuthenticatedUser = Depends(require_auth)
):
    """Change Impact Analysis (Phase 10 section 8 / WP9). Computes what a proposed change
    to this committed node ripples into -- structural descendants plus anything traced to
    the same Requirement(s) -- and flags each affected node Held (Phase 5 section 3's
    state). Held nodes are individually re-governed via the governance-decisions endpoint
    above: an Approve decision against a Held node clears it (Recommitted); anything else
    leaves it Held. This does not intercept or gate the node's own edit -- that still goes
    through the existing, already-live edit endpoints unchanged; this only manages the
    downstream fallout, per section 8's own diagram."""
    project = storage.load_project(project_id)
    _ensure_owner(project, user)
    node = tree.get_node_or_404(project, node_id)
    findings = analyze_impact(project, node_id)
    for finding in findings:
        project.nodes[finding.node_id].held_for_change = True
    if findings:
        activity = f"Change proposed to '{node.label}' held {len(findings)} affected node(s) for re-governance"
        if body.reason:
            activity = f"{activity}: {body.reason}"
        tree.log_activity(project, activity)
        storage.save_project(project)
    return ChangeImpactResult(trigger_node_id=node_id, findings=findings, held_count=len(findings))


@router.get("/projects/{project_id}/held-nodes", response_model=List[NodeWithLevel])
def api_list_held_nodes(project_id: str, user: AuthenticatedUser = Depends(require_auth)):
    """Nodes currently Held pending re-governance after a change (Phase 10 section 8)."""
    project = storage.load_project(project_id)
    _ensure_owner(project, user)
    return [
        NodeWithLevel(**n.model_dump(), level=tree.compute_level(project, n.id))
        for n in project.nodes.values()
        if n.held_for_change
    ]


@router.post("/projects/{project_id}/risks/{risk_id}/accept", response_model=Risk)
def api_accept_risk(
    project_id: str, risk_id: str, body: GovernanceActionRequest = GovernanceActionRequest(),
    user: AuthenticatedUser = Depends(require_auth),
):
    """Risk acceptance (Phase 10 section 6) -- a Risk is only 'managed' once formally
    accepted, and that is always a human act, never automatic (ARC-0021)."""
    project = storage.load_project(project_id)
    risk = next((r for r in project.risks if r.id == risk_id), None)
    if risk is None:
        raise HTTPException(status_code=404, detail="Risk not found")
    risk.status = "Accepted"
    project.risk_assessments.append(
        RiskAssessment(
            id=str(uuid.uuid4()),
            timestamp=datetime.now(timezone.utc).isoformat(),
            risk_id=risk_id,
            assessment_type="Residual",
            level=risk.residual_level or risk.initial_level or "Unknown",
        )
    )
    tree.log_activity(project, f"Risk accepted by {user.email or user.id}: {risk.description[:60]}")
    storage.save_project(project)
    return risk


@router.get("/projects", response_model=list[ProjectSummary])
def api_list_projects(user: AuthenticatedUser = Depends(require_auth)):
    return storage.list_projects(user.id)


@router.post("/projects", response_model=Project, status_code=201)
def api_create_project(body: ProjectCreate, user: AuthenticatedUser = Depends(require_auth)):
    if not body.name.strip():
        raise HTTPException(status_code=400, detail="Name cannot be empty")
    return storage.create_project(body.name.strip(), user.id)


@router.post("/projects/from-outline", response_model=Project, status_code=201)
def api_create_project_from_outline(
    body: OutlineImport, name: Optional[str] = Query(None), user: AuthenticatedUser = Depends(require_auth)
):
    root_template = tree.parse_outline_text(body.text)
    project_name = name.strip() if name and name.strip() else root_template.label
    project = storage.create_project(project_name, user.id)
    root_id = next(iter(project.nodes))
    project.nodes[root_id].label = root_template.label
    project.nodes[root_id].notes = root_template.notes
    for child_template in root_template.children:
        tree.apply_template(project, root_id, child_template)
    tree.log_activity(project, f"Created project from imported outline ({len(project.nodes)} nodes)")
    storage.save_project(project)
    return project


@router.get("/projects/{project_id}")
def api_get_project(project_id: str, user: AuthenticatedUser = Depends(require_auth)):
    project = storage.load_project(project_id)
    _ensure_owner(project, user)
    return _project_with_levels(project)


@router.get("/projects/{project_id}/raw", response_model=Project)
def api_get_project_raw(project_id: str, user: AuthenticatedUser = Depends(require_auth)):
    """Exact on-disk file format, no computed fields — used for JSON export."""
    project = storage.load_project(project_id)
    _ensure_owner(project, user)
    return project


@router.get("/projects/{project_id}/validation", response_model=ValidationReport)
def api_get_validation(project_id: str, user: AuthenticatedUser = Depends(require_auth)):
    project = storage.load_project(project_id)
    _ensure_owner(project, user)
    return tree.build_validation_report(project)


@router.put("/projects/{project_id}", response_model=Project)
def api_rename_project(project_id: str, body: ProjectRename, user: AuthenticatedUser = Depends(require_auth)):
    if not body.name.strip():
        raise HTTPException(status_code=400, detail="Name cannot be empty")
    _ensure_owner(storage.load_project(project_id), user)
    return storage.rename_project(project_id, body.name.strip())


@router.delete("/projects/{project_id}", status_code=204)
def api_delete_project(project_id: str, user: AuthenticatedUser = Depends(require_auth)):
    _ensure_owner(storage.load_project(project_id), user)
    storage.delete_project(project_id)


@router.post("/projects/{project_id}/clear", response_model=Project)
def api_clear_project(project_id: str, user: AuthenticatedUser = Depends(require_auth)):
    """Resets the project back to just its root node - deletes every other node, every
    reference, and every free object. Gated client-side behind a type-to-confirm modal
    since this is destructive and undo history doesn't survive a page reload."""
    project = storage.load_project(project_id)
    _ensure_owner(project, user)
    tree.clear_project(project)
    tree.log_activity(project, "Cleared the canvas back to just the root")
    storage.save_project(project)
    return project


@router.put("/projects/{project_id}/restore", response_model=Project)
def api_restore_project(project_id: str, body: Project, user: AuthenticatedUser = Depends(require_auth)):
    """Overwrites the whole project with a client-supplied snapshot. Used by the editor's
    Undo/Redo, which keeps prior project states in memory and replays them wholesale
    rather than trying to compute a structural inverse for every possible edit."""
    existing = storage.load_project(project_id)  # 404s if the project doesn't exist
    _ensure_owner(existing, user)
    body.id = project_id
    body.owner_id = existing.owner_id  # never let a client-supplied snapshot reassign ownership
    storage.save_project(body)
    return body


@router.post("/projects/{project_id}/nodes", response_model=NodeWithLevel, status_code=201)
def api_add_node(project_id: str, body: NodeCreate):
    project = storage.load_project(project_id)
    node_id = str(uuid.uuid4())
    tree.add_node(project, body.parent_id, body.label, node_id, body.insert_after, body.is_group, body.insert_before)
    tree.log_activity(project, f"Added {'group' if body.is_group else 'node'} '{body.label}'")
    storage.save_project(project)
    node = project.nodes[node_id]
    return NodeWithLevel(**node.model_dump(), level=tree.compute_level(project, node_id))


@router.post("/projects/{project_id}/nodes/{node_id}/decompose", response_model=DecompositionResult)
def api_decompose_node(
    project_id: str, node_id: str, body: DecomposeRequest, user: AuthenticatedUser = Depends(require_auth)
):
    """Recursive Decomposition Framework (Phase 5 / WP8) applied to one already-committed
    node: selects a domain strategy (section 9), generates its next level of children via
    the Orchestrator (attributed to that domain's named agent -- Business/Data/
    Application/Technology/Governance, giving those agents their first real callable
    capability per WP7's own noted gap), and runs the same Governance Service review
    WP6/WP7 already established. An approved batch commits immediately as real child
    nodes (section 2 step 5); anything held or rejected is returned for review but nothing
    is committed -- re-running decompose after conditions change (e.g. a blocking risk is
    accepted) is this MVP's retry path, not a persisted pending-proposal queue."""
    project = storage.load_project(project_id)
    _ensure_owner(project, user)
    node = tree.get_node_or_404(project, node_id)
    try:
        result = Orchestrator().decompose_node(project, node, body.strategy_override)
    except ReasoningStageError as exc:
        raise HTTPException(status_code=502, detail=f"Decomposition failed: {exc}") from exc

    actor = user.email or user.id
    committed_any = False
    if result.review is not None and result.review.outcome == "approved":
        result.committed_node_ids = commit_children(project, node, result.proposed_nodes, result.strategy, actor)
        committed_any = True
    if result.parallel_review is not None and result.parallel_review.outcome == "approved":
        result.parallel_committed_node_ids = commit_children(
            project, node, result.parallel_proposed_nodes, result.parallel_strategy, actor
        )
        committed_any = True
    if committed_any:
        total = len(result.committed_node_ids) + len(result.parallel_committed_node_ids)
        tree.log_activity(project, f"Decomposed '{node.label}' ({total} child(ren) committed)")
        storage.save_project(project)
    return result


@router.post("/projects/{project_id}/nodes/{node_id}/decompose-async", response_model=Cycle, status_code=202)
def api_decompose_node_async(
    project_id: str,
    node_id: str,
    body: DecomposeRequest,
    background_tasks: BackgroundTasks,
    user: AuthenticatedUser = Depends(require_auth),
):
    """The event-driven counterpart to the decompose endpoint above (Phase 11 sections
    5-6, WP10): accepts the request and returns a Cycle acknowledgment immediately instead
    of blocking on the AI call + governance review + commit. The exact same Orchestrator
    call and commit_children helper run in the background; poll GET /cycles/{cycle_id}
    for progress and the final DecompositionResult (as Cycle.result)."""
    project = storage.load_project(project_id)
    _ensure_owner(project, user)
    tree.get_node_or_404(project, node_id)  # 404s early, before acknowledging a bad request
    cycle = cycle_repo.create_cycle(kind="decomposition", project_id=project_id, node_id=node_id)
    background_tasks.add_task(
        run_decomposition_cycle, cycle.id, project_id, node_id, body.strategy_override, user.email or user.id
    )
    return cycle


@router.post("/projects/{project_id}/nodes/{node_id}/commit-decomposition")
def api_commit_decomposition(
    project_id: str, node_id: str, body: DecompositionResult, user: AuthenticatedUser = Depends(require_auth)
):
    """Journey 2's human-override commit point: a decompose result held at
    held_pending_human_review (the common case -- most nodes have no matching Knowledge
    Base coverage) is never auto-committed by api_decompose_node above. This lets a human
    override that hold and commit anyway, exactly mirroring how WP17's Approve button
    overrides a held reasoning proposal. Accepts the whole DecompositionResult the
    original decompose call returned (only .proposed_nodes and .strategy are used) rather
    than a narrower purpose-built shape, same precedent as commit-reasoning accepting the
    whole ReasoningResult back. Reuses commit_children directly -- no new commit logic,
    since a decomposition proposal has no relationships or risks to handle, unlike
    reasoning's. No response_model, matching the plain-dict precedent GET /api/agents,
    GET /api/tools, and commit-reasoning already established."""
    project = storage.load_project(project_id)
    _ensure_owner(project, user)
    node = tree.get_node_or_404(project, node_id)
    committed_node_ids = commit_children(project, node, body.proposed_nodes, body.strategy, user.email or user.id)
    tree.log_activity(project, f"Committed decomposition of '{node.label}' ({len(committed_node_ids)} child(ren))")
    storage.save_project(project)
    return {"committed_node_ids": committed_node_ids}


@router.post("/projects/{project_id}/nodes/{node_id}/blueprint", response_model=BlueprintResult)
def api_generate_blueprint(project_id: str, node_id: str, user: AuthenticatedUser = Depends(require_auth)):
    """Journey 3 (Decomposition -> Implementation Blueprint, WP19): turns an already-
    decomposed subtree's leaf Task nodes into a real work plan -- milestone grouping,
    schedule, build-order dependencies -- via the Orchestrator (attributed to the
    Execution Planning Agent), then the same Governance Service review WP6/WP7 already
    established. An approved proposal commits immediately, exactly mirroring
    api_decompose_node above; anything held or rejected is returned for review but
    nothing is committed -- override a hold via commit-blueprint below."""
    project = storage.load_project(project_id)
    _ensure_owner(project, user)
    node = tree.get_node_or_404(project, node_id)
    try:
        result = Orchestrator().generate_blueprint(project, node)
    except ReasoningStageError as exc:
        raise HTTPException(status_code=502, detail=f"Blueprint generation failed: {exc}") from exc

    if result.review is not None and result.review.outcome == "approved":
        committed_wp_ids, committed_dep_ids = commit_blueprint(project, result, user.email or user.id)
        result.committed_work_package_node_ids = committed_wp_ids
        result.committed_dependency_ids = committed_dep_ids
        tree.log_activity(
            project, f"Blueprint committed for '{node.label}' ({len(committed_wp_ids)} work package(s))"
        )
        storage.save_project(project)
    return result


@router.post("/projects/{project_id}/nodes/{node_id}/commit-blueprint")
def api_commit_blueprint(
    project_id: str, node_id: str, body: BlueprintResult, user: AuthenticatedUser = Depends(require_auth)
):
    """Journey 3's human-override commit point, mirroring commit-decomposition/commit-
    reasoning exactly: a Blueprint held at held_pending_human_review (the expected common
    case -- a specific subtree's build plan rarely has High-confidence Knowledge Base
    coverage) is never auto-committed by api_generate_blueprint above. Accepts the whole
    BlueprintResult the original /blueprint call returned rather than a narrower
    purpose-built shape, same reuse precedent. No response_model, matching the plain-dict
    precedent already established by commit-reasoning/commit-decomposition."""
    project = storage.load_project(project_id)
    _ensure_owner(project, user)
    node = tree.get_node_or_404(project, node_id)
    committed_wp_ids, committed_dep_ids = commit_blueprint(project, body, user.email or user.id)
    tree.log_activity(
        project, f"Committed Implementation Blueprint for '{node.label}' ({len(committed_wp_ids)} work package(s))"
    )
    storage.save_project(project)
    return {"committed_work_package_node_ids": committed_wp_ids, "committed_dependency_ids": committed_dep_ids}


# ---------- Discovery Session (Journey 4, WP20) ----------
# Replaces "pick a template" with "describe the business problem": an adaptive, multi-turn
# interview conducted by the Architect Agent, concluding in a Project Initiation Report the
# human must explicitly approve before anything is created -- see backend/discovery/ for
# the underlying service/commit logic and Orchestrator.advance_discovery/
# generate_initiation_report for the agent-attributed calls into it.


@router.post("/discovery-sessions", response_model=DiscoverySession, status_code=201)
def api_start_discovery_session(user: AuthenticatedUser = Depends(require_auth)):
    """Creates the session, then immediately runs one opening Architect Agent turn (an
    empty transcript prompts a broad opening question) so the conversation always starts
    with the agent speaking first, not a blank screen."""
    session = discovery_repo.create_session(user.id)
    try:
        turn = Orchestrator().advance_discovery(session, "")
    except ReasoningStageError as exc:
        raise HTTPException(status_code=502, detail=f"Discovery Session failed to start: {exc}") from exc

    architect_turn = DiscoveryTurn(
        id=str(uuid.uuid4()),
        timestamp=datetime.now(timezone.utc).isoformat(),
        role="architect",
        message=turn.message,
    )
    discovery_repo.append_turn(session.id, architect_turn)
    discovery_repo.update_coverage(
        session.id, turn.topic_coverage, 1, "ReadyForReport" if turn.ready_for_report else "InProgress"
    )
    return discovery_repo.get_session(session.id)


@router.post("/discovery-sessions/{session_id}/turns", response_model=DiscoverySession)
def api_advance_discovery_session(
    session_id: str, body: DiscoveryTurnRequest, user: AuthenticatedUser = Depends(require_auth)
):
    if not body.message.strip():
        raise HTTPException(status_code=400, detail="Message cannot be empty")
    session = discovery_repo.get_session(session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Discovery session not found")
    _ensure_session_owner(session, user)

    user_turn = DiscoveryTurn(
        id=str(uuid.uuid4()),
        timestamp=datetime.now(timezone.utc).isoformat(),
        role="user",
        message=body.message.strip(),
    )
    discovery_repo.append_turn(session_id, user_turn)

    try:
        turn = Orchestrator().advance_discovery(session, body.message.strip())
    except ReasoningStageError as exc:
        raise HTTPException(status_code=502, detail=f"Discovery Session turn failed: {exc}") from exc

    architect_turn = DiscoveryTurn(
        id=str(uuid.uuid4()),
        timestamp=datetime.now(timezone.utc).isoformat(),
        role="architect",
        message=turn.message,
    )
    discovery_repo.append_turn(session_id, architect_turn)
    discovery_repo.update_coverage(
        session_id,
        turn.topic_coverage,
        session.turn_count + 1,
        "ReadyForReport" if turn.ready_for_report else "InProgress",
    )
    return discovery_repo.get_session(session_id)


@router.post("/discovery-sessions/{session_id}/generate-report", response_model=ProjectInitiationReport)
def api_generate_discovery_report(session_id: str, user: AuthenticatedUser = Depends(require_auth)):
    """Callable once the Architect Agent signals readiness, or as an explicit early-
    generate override -- never blocks, same "warn, don't block" posture as Blueprint's own
    readiness check."""
    session = discovery_repo.get_session(session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Discovery session not found")
    _ensure_session_owner(session, user)

    try:
        report = Orchestrator().generate_initiation_report(session)
    except ReasoningStageError as exc:
        raise HTTPException(status_code=502, detail=f"Project Initiation Report generation failed: {exc}") from exc

    discovery_repo.set_report(session_id, report.model_dump(), "ReportGenerated")
    return report


@router.get("/discovery-sessions/{session_id}", response_model=DiscoverySession)
def api_get_discovery_session(session_id: str, user: AuthenticatedUser = Depends(require_auth)):
    session = discovery_repo.get_session(session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Discovery session not found")
    _ensure_session_owner(session, user)
    return session


@router.post("/discovery-sessions/{session_id}/approve", response_model=Project, status_code=201)
def api_approve_discovery_session(
    session_id: str,
    body: ProjectInitiationReport,
    project_name: Optional[str] = Query(None),
    user: AuthenticatedUser = Depends(require_auth),
):
    """Explicit human approval, never automatic: unlike Blueprint/Decompose, which
    auto-commit inline the moment governance returns approved, Discovery Session's entire
    premise is "the user reviews and approves" -- nothing commits until this call. Accepts
    the whole ProjectInitiationReport back in the body, same "accept the result back,
    possibly human-edited" precedent as commit-blueprint/commit-reasoning."""
    session = discovery_repo.get_session(session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Discovery session not found")
    _ensure_session_owner(session, user)

    name = project_name.strip() if project_name and project_name.strip() else body.business_problem[:80]
    project = storage.create_project(name, user.id)
    commit_initiation_report(project, body, user.email or user.id)
    tree.log_activity(project, "Created from an approved Project Initiation Report (Discovery Session)")
    storage.save_project(project)

    discovery_repo.set_status(session_id, "Approved", created_project_id=project.id)
    return project


# ---------- TOGAF Architecture Generation (Journey 5, WP21) ----------
# The only architecture framework Architeq generates -- a pure, deterministic grouping of
# a project's already-real nodes into the four TOGAF domains (see
# backend/architecture/service.py), plus the chained background pipeline that gets a
# project's nodes to that point (see backend/engineering/service.py). No AI call in either
# endpoint below -- generation itself is the deterministic view; engineering is the
# existing, already-governed decompose_node loop, just chained.


@router.get("/projects/{project_id}/architecture", response_model=ArchitectureView)
def api_get_architecture(project_id: str, user: AuthenticatedUser = Depends(require_auth)):
    project = storage.load_project(project_id)
    _ensure_owner(project, user)
    return build_architecture_view(project)


@router.post("/projects/{project_id}/nodes/{root_id}/engineer-architecture", response_model=Cycle, status_code=202)
def api_engineer_architecture(
    project_id: str,
    root_id: str,
    background_tasks: BackgroundTasks,
    user: AuthenticatedUser = Depends(require_auth),
):
    """Kicks off the chained Engineering Cycle for root_id's subtree -- the background
    pipeline that recursively decomposes every non-terminal leaf until Business/Data/
    Application/Technology architecture has emerged (or the safety cap is hit). Returns
    immediately; poll GET /cycles/{cycle_id} for progress and GET .../architecture for the
    progressively-populated result, same convention as decompose-async."""
    project = storage.load_project(project_id)
    _ensure_owner(project, user)
    tree.get_node_or_404(project, root_id)
    cycle = cycle_repo.create_cycle(kind="engineering", project_id=project_id, node_id=root_id)
    background_tasks.add_task(run_engineering_pipeline, cycle.id, project_id, root_id, user.email or user.id)
    return cycle


@router.put("/projects/{project_id}/nodes/{node_id}", response_model=NodeWithLevel)
def api_update_node(project_id: str, node_id: str, body: NodeUpdate):
    project = storage.load_project(project_id)
    old_label = project.nodes[node_id].label
    tree.rename_node(
        project,
        node_id,
        body.label,
        body.notes,
        body.collapsed,
        body.node_type,
        body.status,
        body.priority,
        body.complexity,
        body.risk_level,
        body.tags,
        body.owner,
        body.shape,
        body.group_children,
        body.is_group,
        body.classification,
        body.custom_color,
        body.planning_status,
        body.locked,
        body.target_date,
        body.duration_days,
    )
    if body.label is not None and body.label != old_label:
        tree.log_activity(project, f"Renamed '{old_label}' to '{body.label}'")
    storage.save_project(project)
    node = project.nodes[node_id]
    return NodeWithLevel(**node.model_dump(), level=tree.compute_level(project, node_id))


@router.post("/projects/{project_id}/nodes/{node_id}/move-sibling", response_model=NodeWithLevel)
def api_move_sibling(project_id: str, node_id: str, body: MoveSiblingRequest):
    project = storage.load_project(project_id)
    tree.move_sibling(project, node_id, body.direction)
    storage.save_project(project)
    node = project.nodes[node_id]
    return NodeWithLevel(**node.model_dump(), level=tree.compute_level(project, node_id))


@router.delete("/projects/{project_id}/nodes/{node_id}", status_code=204)
def api_delete_node(project_id: str, node_id: str, promote_children: bool = Query(False)):
    project = storage.load_project(project_id)
    label = project.nodes[node_id].label
    tree.delete_node(project, node_id, promote_children)
    tree.log_activity(project, f"Deleted node '{label}'")
    storage.save_project(project)


@router.put("/projects/{project_id}/nodes/{node_id}/position", response_model=NodeWithLevel)
def api_move_node(project_id: str, node_id: str, body: NodePosition):
    project = storage.load_project(project_id)
    tree.move_node_position(project, node_id, body.canvas_x, body.canvas_y)
    storage.save_project(project)
    node = project.nodes[node_id]
    return NodeWithLevel(**node.model_dump(), level=tree.compute_level(project, node_id))


@router.post("/projects/{project_id}/nodes/{node_id}/indent", response_model=NodeWithLevel)
def api_indent_node(project_id: str, node_id: str):
    project = storage.load_project(project_id)
    tree.indent_node(project, node_id)
    tree.log_activity(project, f"Indented '{project.nodes[node_id].label}'")
    storage.save_project(project)
    node = project.nodes[node_id]
    return NodeWithLevel(**node.model_dump(), level=tree.compute_level(project, node_id))


@router.post("/projects/{project_id}/nodes/{node_id}/arrange-children", response_model=NodeWithLevel)
def api_arrange_children(project_id: str, node_id: str):
    project = storage.load_project(project_id)
    tree.arrange_children(project, node_id)
    storage.save_project(project)
    node = project.nodes[node_id]
    return NodeWithLevel(**node.model_dump(), level=tree.compute_level(project, node_id))


@router.post("/projects/{project_id}/nodes/{node_id}/reparent", response_model=NodeWithLevel)
def api_reparent_node(project_id: str, node_id: str, body: ReparentRequest):
    project = storage.load_project(project_id)
    old_parent_label = project.nodes[project.nodes[node_id].parent_id].label if project.nodes[node_id].parent_id else "?"
    tree.reparent_node(project, node_id, body.new_parent_id)
    new_parent_label = project.nodes[body.new_parent_id].label
    tree.log_activity(
        project, f"Moved '{project.nodes[node_id].label}' from '{old_parent_label}' to '{new_parent_label}'"
    )
    storage.save_project(project)
    node = project.nodes[node_id]
    return NodeWithLevel(**node.model_dump(), level=tree.compute_level(project, node_id))


@router.post("/projects/{project_id}/nodes/{node_id}/promote-to-root", response_model=NodeWithLevel)
def api_promote_to_root(project_id: str, node_id: str):
    project = storage.load_project(project_id)
    label = project.nodes[node_id].label
    tree.promote_to_root(project, node_id)
    tree.log_activity(project, f"Promoted '{label}' to be the new root")
    storage.save_project(project)
    node = project.nodes[node_id]
    return NodeWithLevel(**node.model_dump(), level=tree.compute_level(project, node_id))


@router.post("/projects/{project_id}/nodes/{node_id}/duplicate", response_model=NodeWithLevel, status_code=201)
def api_duplicate_node(project_id: str, node_id: str):
    project = storage.load_project(project_id)
    label = project.nodes[node_id].label
    new_id = tree.duplicate_node(project, node_id)
    tree.log_activity(project, f"Duplicated '{label}'")
    storage.save_project(project)
    node = project.nodes[new_id]
    return NodeWithLevel(**node.model_dump(), level=tree.compute_level(project, new_id))


@router.post("/projects/{project_id}/nodes/{node_id}/add-parent", response_model=NodeWithLevel, status_code=201)
def api_add_parent(project_id: str, node_id: str, body: AddParentRequest):
    project = storage.load_project(project_id)
    child_label = project.nodes[node_id].label
    new_id = tree.add_parent_above(project, node_id, body.label)
    tree.log_activity(project, f"Inserted '{body.label}' as new parent of '{child_label}'")
    storage.save_project(project)
    node = project.nodes[new_id]
    return NodeWithLevel(**node.model_dump(), level=tree.compute_level(project, new_id))


@router.get("/projects/{project_id}/nodes/{node_id}/subtree", response_model=TemplateNode)
def api_get_subtree(project_id: str, node_id: str):
    """Serializes a node's subtree structure — used for both Copy (client holds it for a
    later Paste) and Export Subtree (client downloads it as JSON)."""
    project = storage.load_project(project_id)
    return tree.capture_template(project, node_id)


@router.post("/projects/{project_id}/nodes/{node_id}/paste-subtree", response_model=NodeWithLevel, status_code=201)
def api_paste_subtree(project_id: str, node_id: str, body: PasteSubtreeRequest):
    project = storage.load_project(project_id)
    new_id = tree.apply_template(project, node_id, body.root)
    tree.log_activity(project, f"Pasted '{body.root.label}' under '{project.nodes[node_id].label}'")
    storage.save_project(project)
    node = project.nodes[new_id]
    return NodeWithLevel(**node.model_dump(), level=tree.compute_level(project, new_id))


@router.post("/projects/{project_id}/nodes/{node_id}/outdent", response_model=NodeWithLevel)
def api_outdent_node(project_id: str, node_id: str):
    project = storage.load_project(project_id)
    tree.outdent_node(project, node_id)
    tree.log_activity(project, f"Outdented '{project.nodes[node_id].label}'")
    storage.save_project(project)
    node = project.nodes[node_id]
    return NodeWithLevel(**node.model_dump(), level=tree.compute_level(project, node_id))


# ---------- References ----------


@router.post("/projects/{project_id}/references", response_model=Reference, status_code=201)
def api_add_reference(project_id: str, body: ReferenceCreate):
    project = storage.load_project(project_id)
    ref = tree.add_reference(project, body.from_, body.to, body.label, body.reference_type)
    tree.log_activity(
        project,
        f"Linked '{tree.canvas_object_label(project, body.from_)}' -> '{tree.canvas_object_label(project, body.to)}'",
    )
    storage.save_project(project)
    return ref


@router.put("/projects/{project_id}/references/{reference_id}", response_model=Reference)
def api_update_reference(project_id: str, reference_id: str, body: ReferenceUpdate):
    project = storage.load_project(project_id)
    ref = tree.update_reference(
        project,
        reference_id,
        body.from_,
        body.to,
        body.label,
        body.reference_type,
        body.custom_color,
        body.thickness,
        body.direction,
        body.animated,
        body.connector_hidden,
        body.line_style,
        body.opacity,
        body.show_arrowhead,
        body.curve_style,
        body.animation_speed,
    )
    tree.log_activity(
        project,
        f"Relinked reference to '{tree.canvas_object_label(project, ref.from_)}' -> '{tree.canvas_object_label(project, ref.to)}'",
    )
    storage.save_project(project)
    return ref


@router.delete("/projects/{project_id}/references/{reference_id}", status_code=204)
def api_delete_reference(project_id: str, reference_id: str):
    project = storage.load_project(project_id)
    tree.delete_reference(project, reference_id)
    storage.save_project(project)


# ---------- Comments ----------


@router.post("/projects/{project_id}/nodes/{node_id}/comments", response_model=Comment, status_code=201)
def api_add_comment(project_id: str, node_id: str, body: CommentCreate):
    project = storage.load_project(project_id)
    if not body.text.strip():
        raise HTTPException(status_code=400, detail="Comment text cannot be empty")
    comment = tree.add_comment(project, node_id, body.text.strip())
    storage.save_project(project)
    return comment


@router.delete("/projects/{project_id}/nodes/{node_id}/comments/{comment_id}", status_code=204)
def api_delete_comment(project_id: str, node_id: str, comment_id: str):
    project = storage.load_project(project_id)
    tree.delete_comment(project, node_id, comment_id)
    storage.save_project(project)


# ---------- Templates ----------


@router.get("/templates", response_model=list[TemplateSummary])
def api_list_templates():
    return storage.list_templates()


@router.post("/projects/{project_id}/nodes/{node_id}/save-as-template", response_model=Template, status_code=201)
def api_save_as_template(project_id: str, node_id: str, body: TemplateCreate):
    project = storage.load_project(project_id)
    root = tree.capture_template(project, node_id)
    if not body.name.strip():
        raise HTTPException(status_code=400, detail="Name cannot be empty")
    return storage.save_new_template(body.name.strip(), root)


@router.delete("/templates/{template_id}", status_code=204)
def api_delete_template(template_id: str):
    storage.delete_template(template_id)


@router.post("/projects/{project_id}/nodes/{node_id}/apply-template/{template_id}", response_model=NodeWithLevel, status_code=201)
def api_apply_template(project_id: str, node_id: str, template_id: str):
    project = storage.load_project(project_id)
    template = storage.load_template(template_id)
    new_id = tree.apply_template(project, node_id, template.root)
    tree.log_activity(project, f"Applied template '{template.name}' under '{project.nodes[node_id].label}'")
    storage.save_project(project)
    node = project.nodes[new_id]
    return NodeWithLevel(**node.model_dump(), level=tree.compute_level(project, new_id))


# ---------- Outline import ----------


@router.post("/projects/{project_id}/nodes/{node_id}/import-outline", response_model=NodeWithLevel, status_code=201)
def api_import_outline_under_node(project_id: str, node_id: str, body: OutlineImport):
    project = storage.load_project(project_id)
    root_template = tree.parse_outline_text(body.text)
    new_id = tree.apply_template(project, node_id, root_template)
    tree.log_activity(project, f"Imported outline under '{project.nodes[node_id].label}'")
    storage.save_project(project)
    node = project.nodes[new_id]
    return NodeWithLevel(**node.model_dump(), level=tree.compute_level(project, new_id))


# ---------- Engineering Decomposition & Solution Generation Pipeline ----------
# The app's new core model (see plan doc): a user's engineering goal is recursively
# decomposed into a frozen, versioned per-domain task tree (backend/taxonomy/), validated
# against P1-P7 + a domain checklist (backend/validator/), then rendered as Python or an
# n8n workflow (backend/render/). Stateless per request -- only the frozen taxonomy is a
# durable artifact, matching this journey's own "no unnecessary chatter" minimalism.


@router.post("/decompose/intent", response_model=IntentResult)
def api_parse_intent(body: IntentRequest, user: AuthenticatedUser = Depends(require_auth)):
    if not body.text.strip():
        raise HTTPException(status_code=400, detail="Text cannot be empty")
    return parse_intent(body.text.strip())


@router.get("/decompose/domains", response_model=List[DomainSummary])
def api_list_domains(user: AuthenticatedUser = Depends(require_auth)):
    return taxonomy_repo.list_domain_summaries()


@router.get("/decompose/domains/{domain}/tree", response_model=DomainTaskTree)
def api_get_domain_tree(domain: str, user: AuthenticatedUser = Depends(require_auth)):
    domain_tree = taxonomy_repo.load_tree(domain)
    if domain_tree is None:
        raise HTTPException(status_code=404, detail=f"No frozen task tree for domain '{domain}' yet")
    return domain_tree


@router.post("/decompose/domains/{domain}/draft", response_model=DomainDraftResult)
def api_draft_domain(domain: str, body: DomainDraftRequest, user: AuthenticatedUser = Depends(require_auth)):
    """One-time, per-domain authoring step (doc section 4.2/4.4) -- never runs again for
    this domain once approved. If a checklist doesn't exist yet, drafts one too (app
    drafts, user approves); an existing checklist (e.g. RAG's, hand-authored) is reused
    as-is. Nothing is frozen here -- /approve does that."""
    checklist = taxonomy_repo.load_checklist(domain)
    if checklist is None:
        checklist = propose_checklist(domain, body.reasoning_context)
    domain_tree = propose_tree(domain, body.reasoning_context, checklist)
    validation = validate_tree(domain_tree, checklist)
    return DomainDraftResult(domain=domain, checklist=checklist, tree=domain_tree, validation=validation)


@router.post("/decompose/domains/{domain}/approve", response_model=DomainDraftResult, status_code=201)
def api_approve_domain(domain: str, body: DomainApproveRequest, user: AuthenticatedUser = Depends(require_auth)):
    """Explicit human approval, never automatic -- mirrors Discovery Session's own
    generate-report/approve shape. Freezes the (possibly human-edited) checklist and tree;
    every subsequent request in this domain loads this exact frozen pair, never
    regenerating it."""
    validation = validate_tree(body.tree, body.checklist)
    if not validation.passed:
        raise HTTPException(
            status_code=422,
            detail=[v.model_dump() for v in validation.violations],
        )
    taxonomy_repo.save_checklist(body.checklist)
    taxonomy_repo.save_tree(body.tree)
    return DomainDraftResult(domain=domain, checklist=body.checklist, tree=body.tree, validation=validation)


@router.post("/decompose/domains/{domain}/component-tree/draft", response_model=ComponentTreeDraftResult)
def api_draft_component_tree(domain: str, body: ComponentTreeDraftRequest, user: AuthenticatedUser = Depends(require_auth)):
    """Sub-plan 11l -- Stages -3 through 0, mirroring api_draft_domain's shape. Requires
    the domain's Workflow Tree to already be frozen (CD6's Reconciliation Rule needs a real
    tree to check attributes against) -- 404 if not, rather than reconciling against
    nothing."""
    workflow_tree = taxonomy_repo.load_tree(domain)
    if workflow_tree is None:
        raise HTTPException(
            status_code=404,
            detail=f"No frozen Workflow Tree for domain '{domain}' yet -- Component Tree reconciliation (CD6) needs one to check against",
        )
    tree, validation = component_engine.propose_component_tree(domain, body.prd_text, body.reasoning_context, workflow_tree)
    return ComponentTreeDraftResult(domain=domain, tree=tree, validation=validation)


@router.post("/decompose/domains/{domain}/component-tree/approve", response_model=ComponentTreeDraftResult, status_code=201)
def api_approve_component_tree(domain: str, body: ComponentTreeApproveRequest, user: AuthenticatedUser = Depends(require_auth)):
    """Explicit human approval, never automatic -- mirrors api_approve_domain's own
    re-validate-before-save posture exactly, including the full Output Documentation Gate
    (CD10) this time, since `documentation` only genuinely exists once a human supplies it
    before freezing."""
    workflow_tree = taxonomy_repo.load_tree(domain)
    if workflow_tree is None:
        raise HTTPException(status_code=404, detail=f"No frozen Workflow Tree for domain '{domain}' yet")
    validation = component_engine.validate_component_tree(body.tree, workflow_tree, include_documentation_gate=True)
    if not validation.passed:
        raise HTTPException(status_code=422, detail=[v.model_dump() for v in validation.violations])
    component_repo.save_component_tree(body.tree)
    return ComponentTreeDraftResult(domain=domain, tree=body.tree, validation=validation)


@router.get("/decompose/domains/{domain}/component-tree", response_model=ComponentTree)
def api_get_component_tree(domain: str, user: AuthenticatedUser = Depends(require_auth)):
    tree = component_repo.load_component_tree(domain)
    if tree is None:
        raise HTTPException(status_code=404, detail=f"No frozen Component Tree for domain '{domain}' yet")
    return tree


@router.post("/decompose/domains/{domain}/data-architecture/draft", response_model=DataArchitectureDraftResult)
def api_draft_data_architecture(domain: str, body: DataArchitectureDraftRequest, user: AuthenticatedUser = Depends(require_auth)):
    """Sub-plan 13e -- Stage 5/6, mirroring api_draft_component_tree's shape. Requires the
    domain's Workflow Tree to already be frozen (R41: always derived, never authored
    independently)."""
    workflow_tree = taxonomy_repo.load_tree(domain)
    if workflow_tree is None:
        raise HTTPException(status_code=404, detail=f"No frozen Workflow Tree for domain '{domain}' yet")
    architecture, validation = data_architecture_engine.propose_data_architecture(domain, workflow_tree, body.reasoning_context)
    return DataArchitectureDraftResult(domain=domain, architecture=architecture, validation=validation)


@router.post("/decompose/domains/{domain}/data-architecture/approve", response_model=DataArchitectureDraftResult, status_code=201)
def api_approve_data_architecture(domain: str, body: DataArchitectureApproveRequest, user: AuthenticatedUser = Depends(require_auth)):
    """Explicit human approval, never automatic -- mirrors api_approve_component_tree's
    own re-validate-before-save posture exactly."""
    workflow_tree = taxonomy_repo.load_tree(domain)
    if workflow_tree is None:
        raise HTTPException(status_code=404, detail=f"No frozen Workflow Tree for domain '{domain}' yet")
    validation = data_architecture_engine.validate_data_architecture(body.architecture, workflow_tree)
    if not validation.passed:
        raise HTTPException(status_code=422, detail=[v.model_dump() for v in validation.violations])
    data_architecture_repo.save_data_architecture(body.architecture)
    return DataArchitectureDraftResult(domain=domain, architecture=body.architecture, validation=validation)


@router.get("/decompose/domains/{domain}/data-architecture", response_model=DataArchitecture)
def api_get_data_architecture(domain: str, user: AuthenticatedUser = Depends(require_auth)):
    architecture = data_architecture_repo.load_data_architecture(domain)
    if architecture is None:
        raise HTTPException(status_code=404, detail=f"No frozen Data Architecture for domain '{domain}' yet")
    return architecture


@router.post("/decompose/render/python", response_model=List[RenderedCodeBlock])
def api_render_python(body: DomainRenderRequest, user: AuthenticatedUser = Depends(require_auth)):
    domain_tree = taxonomy_repo.load_tree(body.domain)
    if domain_tree is None:
        raise HTTPException(status_code=404, detail=f"No frozen task tree for domain '{body.domain}' yet")
    return render_python(domain_tree)


@router.post("/decompose/render/python/export")
def api_export_python_package(body: DomainRenderRequest, user: AuthenticatedUser = Depends(require_auth)):
    domain_tree = taxonomy_repo.load_tree(body.domain)
    if domain_tree is None:
        raise HTTPException(status_code=404, detail=f"No frozen task tree for domain '{body.domain}' yet")
    zip_bytes = export_python_package(body.domain, domain_tree)
    return Response(
        content=zip_bytes,
        media_type="application/zip",
        headers={"Content-Disposition": f'attachment; filename="{body.domain}_python.zip"'},
    )


@router.post("/decompose/render/n8n", response_model=N8nWorkflow)
def api_render_n8n(body: DomainRenderRequest, user: AuthenticatedUser = Depends(require_auth)):
    domain_tree = taxonomy_repo.load_tree(body.domain)
    if domain_tree is None:
        raise HTTPException(status_code=404, detail=f"No frozen task tree for domain '{body.domain}' yet")
    return export_workflow(domain_tree)


@router.post("/decompose/domains/{domain}/refine", response_model=DomainDraftResult)
def api_refine_domain(domain: str, body: RefineTreeRequest, user: AuthenticatedUser = Depends(require_auth)):
    """The persistent Command/Refine Input's backend (AMENDMENT 4 item 6) -- a targeted
    mutation to an already-frozen tree, not a fresh draft. Auto-freezes on pass (unlike
    /draft, which always needs an explicit /approve) since this is already an
    authenticated user's direct, specific instruction against a domain they're actively
    looking at -- never partially accepted; a failing refinement is returned for display
    but never written to disk, leaving the previously-frozen tree untouched."""
    if not body.instruction.strip():
        raise HTTPException(status_code=400, detail="Instruction cannot be empty")
    checklist = taxonomy_repo.load_checklist(domain)
    current_tree = taxonomy_repo.load_tree(domain)
    if checklist is None or current_tree is None:
        raise HTTPException(status_code=404, detail=f"No frozen domain '{domain}' to refine")

    try:
        refined_tree = refine_tree(current_tree, body.instruction.strip())
    except ReasoningStageError as exc:
        raise HTTPException(status_code=502, detail=f"Refine failed: {exc}") from exc

    validation = validate_tree(refined_tree, checklist)
    if validation.passed:
        taxonomy_repo.save_tree(refined_tree)
    return DomainDraftResult(domain=domain, checklist=checklist, tree=refined_tree, validation=validation)


def _entry_for_subtask(domain: str, sub_task_id: str):
    """Shared lookup for both regroup endpoints: resolves a sub-task id (from the still-
    frozen tree) back to its owning Layer's checklist entry + its own label -- the same
    Layer/Input-Output-Contract context Stage 2/2.5 originally grounded it in."""
    tree = taxonomy_repo.load_tree(domain)
    checklist = taxonomy_repo.load_checklist(domain)
    if tree is None or checklist is None:
        raise HTTPException(status_code=404, detail=f"No frozen domain '{domain}'")
    sub_node = tree.nodes.get(sub_task_id)
    if sub_node is None or sub_node.level != "Sub-task":
        raise HTTPException(status_code=404, detail=f"No sub-task '{sub_task_id}' in domain '{domain}'")
    layer_node = tree.nodes.get(sub_node.parent_id) if sub_node.parent_id else None
    entry = next((e for e in checklist.mandatory_layers if layer_node and e.layer == layer_node.label), None)
    if entry is None:
        raise HTTPException(status_code=404, detail="No matching checklist entry for this sub-task's layer")
    return entry, sub_node.label


@router.post("/decompose/domains/{domain}/subtasks/{sub_task_id}/regroup", response_model=Dict[str, List[str]])
def api_regroup_subtask(
    domain: str, sub_task_id: str, body: RegroundRequest, user: AuthenticatedUser = Depends(require_auth)
):
    """Manually-triggered re-grounding for ONE already-frozen sub-task (spec addendum
    Section 2a) -- never automatic. Returns the new candidate version for review; nothing
    is saved until /regroup/confirm is called explicitly with the reviewed result."""
    entry, sub_task_label = _entry_for_subtask(domain, sub_task_id)
    try:
        return regroup_subtask(entry, sub_task_label, body.reasoning_context)
    except ReasoningStageError as exc:
        raise HTTPException(status_code=502, detail=f"Regroup failed: {exc}") from exc


@router.post("/decompose/domains/{domain}/subtasks/{sub_task_id}/regroup/confirm", response_model=Dict[str, Any])
def api_confirm_regroup(
    domain: str, sub_task_id: str, body: RegroundConfirmRequest, user: AuthenticatedUser = Depends(require_auth)
):
    """Explicit confirmation step -- appends the reviewed version to this sub-task's
    versions[] in the grounding cache. Never touches the frozen tree.json and never
    regenerates atomic steps (deliberately out of scope, see regroup_subtask's docstring)."""
    # Confirms this sub-task genuinely exists in the frozen tree before writing anything.
    _entry_for_subtask(domain, sub_task_id)

    grounding = taxonomy_repo.load_grounding(domain) or {"domain": domain, "sub_tasks": {}}
    sub_tasks = grounding.setdefault("sub_tasks", {})
    entry = sub_tasks.setdefault(sub_task_id, {"sub_task_label": "", "versions": []})
    next_version = len(entry["versions"]) + 1
    entry["versions"].append({
        "grounding_version": next_version,
        "operator_trace": body.operator_trace,
        "builder_trace": body.builder_trace,
        "merged_trace": body.merged_trace,
    })
    taxonomy_repo.save_grounding(domain, grounding)
    return entry


# ---------- Settings (hidden Screen 3, AMENDMENT 4 item 7) ----------
# Not linked from any nav element -- reached only by navigating to settings.html directly.
# Raw JSON in/out throughout, matching backend/taxonomy/repository.py's own "reached
# deliberately" posture for this surface (no schema enforcement on save).


@router.get("/decompose/settings/principles", response_model=Dict[str, Any])
def api_get_principles(user: AuthenticatedUser = Depends(require_auth)):
    return taxonomy_repo.load_principles_raw()


@router.put("/decompose/settings/principles", response_model=Dict[str, Any])
def api_save_principles(body: Dict[str, Any], user: AuthenticatedUser = Depends(require_auth)):
    taxonomy_repo.save_principles_raw(body)
    return body


@router.get("/decompose/settings/reference-architectures", response_model=List[str])
def api_list_reference_architectures(user: AuthenticatedUser = Depends(require_auth)):
    return taxonomy_repo.list_reference_architectures()


@router.get("/decompose/settings/reference-architectures/{name}", response_model=Dict[str, Any])
def api_get_reference_architecture(name: str, user: AuthenticatedUser = Depends(require_auth)):
    data = taxonomy_repo.load_reference_architecture_raw(name)
    if data is None:
        raise HTTPException(status_code=404, detail=f"No reference architecture named '{name}'")
    return data


@router.put("/decompose/settings/reference-architectures/{name}", response_model=Dict[str, Any])
def api_save_reference_architecture(name: str, body: Dict[str, Any], user: AuthenticatedUser = Depends(require_auth)):
    taxonomy_repo.save_reference_architecture_raw(name, body)
    return body


@router.get("/decompose/settings/checklists", response_model=List[str])
def api_list_settings_checklists(user: AuthenticatedUser = Depends(require_auth)):
    return taxonomy_repo.list_checklist_domains()


@router.get("/decompose/settings/checklists/{domain}", response_model=Dict[str, Any])
def api_get_settings_checklist(domain: str, user: AuthenticatedUser = Depends(require_auth)):
    data = taxonomy_repo.load_checklist_raw(domain)
    if data is None:
        raise HTTPException(status_code=404, detail=f"No checklist for domain '{domain}'")
    return data


@router.put("/decompose/settings/checklists/{domain}", response_model=Dict[str, Any])
def api_save_settings_checklist(domain: str, body: Dict[str, Any], user: AuthenticatedUser = Depends(require_auth)):
    taxonomy_repo.save_checklist_raw(domain, body)
    return body


# ---------- Concept Mode: freeform planning objects ----------


@router.post("/projects/{project_id}/concept-objects", response_model=ConceptObject, status_code=201)
def api_add_concept_object(project_id: str, body: ConceptObjectCreate):
    project = storage.load_project(project_id)
    obj = concept.add_object(project, body.type, body.x, body.y, body.width, body.height, body.text, body.color)
    storage.save_project(project)
    return obj


@router.put("/projects/{project_id}/concept-objects/{object_id}", response_model=ConceptObject)
def api_update_concept_object(project_id: str, object_id: str, body: ConceptObjectUpdate):
    project = storage.load_project(project_id)
    obj = concept.update_object(
        project,
        object_id,
        body.x,
        body.y,
        body.width,
        body.height,
        body.rotation,
        body.text,
        body.color,
        body.border_style,
        body.z_index,
        body.locked,
        body.group_id,
    )
    storage.save_project(project)
    return obj


@router.delete("/projects/{project_id}/concept-objects/{object_id}", status_code=204)
def api_delete_concept_object(project_id: str, object_id: str):
    project = storage.load_project(project_id)
    concept.delete_object(project, object_id)
    storage.save_project(project)


@router.post("/projects/{project_id}/concept-objects/{object_id}/duplicate", response_model=ConceptObject, status_code=201)
def api_duplicate_concept_object(project_id: str, object_id: str):
    project = storage.load_project(project_id)
    obj = concept.duplicate_object(project, object_id)
    storage.save_project(project)
    return obj


@router.post("/projects/{project_id}/concept-objects/{object_id}/bring-to-front", response_model=ConceptObject)
def api_bring_concept_object_to_front(project_id: str, object_id: str):
    project = storage.load_project(project_id)
    obj = concept.bring_to_front(project, object_id)
    storage.save_project(project)
    return obj


@router.post("/projects/{project_id}/concept-objects/{object_id}/send-to-back", response_model=ConceptObject)
def api_send_concept_object_to_back(project_id: str, object_id: str):
    project = storage.load_project(project_id)
    obj = concept.send_to_back(project, object_id)
    storage.save_project(project)
    return obj


@router.post("/projects/{project_id}/concept-objects/{object_id}/convert-to-node", response_model=NodeWithLevel, status_code=201)
def api_convert_object_to_node(project_id: str, object_id: str, body: ConvertToNodeRequest):
    project = storage.load_project(project_id)
    node = concept.convert_object_to_node(project, object_id, body.parent_id)
    tree.log_activity(project, f"Converted planning object '{node.label}' into an architecture component")
    storage.save_project(project)
    return NodeWithLevel(**node.model_dump(), level=tree.compute_level(project, node.id))


@router.post("/projects/{project_id}/nodes/{node_id}/convert-to-object", response_model=ConceptObject, status_code=201)
def api_convert_node_to_object(project_id: str, node_id: str):
    project = storage.load_project(project_id)
    obj = concept.convert_node_to_object(project, node_id)
    tree.log_activity(project, f"Converted '{project.nodes[node_id].label}' into a planning object")
    storage.save_project(project)
    return obj


# ---------- Knowledge Layer (Phase 6 / WP3) ----------
# Project-independent -- the Knowledge Domain + Standards Library, not nested under any
# project. Acquisition -> Parser -> Classifier -> QA -> Repository -> Versioning ->
# Retrieval, per the approved Knowledge & Reasoning Framework.


def _require_transition(current_status: str, target_status: str) -> None:
    try:
        lifecycle.require_transition(current_status, target_status)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/knowledge/ingest", response_model=KnowledgeIngestResult, status_code=201)
def api_ingest_knowledge(body: KnowledgeIngestRequest):
    """Parses one or more ```yaml blocks out of a curated Markdown document into Proposed
    KnowledgeConcepts (Phase 6 §3). A malformed block is reported as an error string rather
    than aborting the whole batch."""
    candidates, errors = parse_markdown(body.markdown)
    created = [storage.save_knowledge_concept(candidate) for candidate in candidates]
    return KnowledgeIngestResult(created=created, errors=errors)


@router.get("/knowledge/concepts", response_model=list[KnowledgeConcept])
def api_list_knowledge_concepts(status: Optional[str] = Query(None), category: Optional[str] = Query(None)):
    return storage.list_knowledge_concepts(status, category)


@router.get("/knowledge/concepts/{concept_id}", response_model=KnowledgeConcept)
def api_get_knowledge_concept(concept_id: str):
    return storage.load_knowledge_concept(concept_id)


@router.delete("/knowledge/concepts/{concept_id}", status_code=204)
def api_delete_knowledge_concept(concept_id: str):
    storage.delete_knowledge_concept(concept_id)


@router.post("/knowledge/concepts/{concept_id}/submit-for-qa", response_model=QAReport)
def api_submit_knowledge_concept_for_qa(concept_id: str):
    """Proposed -> UnderReview, then runs the automated half of QA (§6). A Critical finding
    auto-rejects (fails QA / conflicts, per the state diagram); Warnings never block --
    the concept stays UnderReview, pending a human Knowledge Governance decision."""
    current = storage.load_knowledge_concept(concept_id)
    _require_transition(current.status, "UnderReview")
    storage.set_knowledge_concept_status(concept_id, "UnderReview")
    others = [c for c in storage.list_knowledge_concepts() if c.concept_id != concept_id]
    updated = storage.load_knowledge_concept(concept_id)
    report = run_qa(updated, others)
    if not report.passed:
        storage.set_knowledge_concept_status(concept_id, "Rejected")
    return report


@router.post("/knowledge/concepts/{concept_id}/approve", response_model=KnowledgeConcept)
def api_approve_knowledge_concept(concept_id: str, body: GovernanceActionRequest = GovernanceActionRequest()):
    """UnderReview -> Active: Knowledge Governance sign-off (§10), distinct from Architecture
    Governance. If this concept declares `supersedes`, the concept it replaces is moved
    Active -> Superseded in the same call, matching §9's versioning model."""
    current = storage.load_knowledge_concept(concept_id)
    _require_transition(current.status, "Active")
    approved = storage.set_knowledge_concept_status(concept_id, "Active")
    if approved.supersedes:
        try:
            superseded = storage.load_knowledge_concept(approved.supersedes)
        except HTTPException:
            superseded = None
        if superseded and lifecycle.can_transition(superseded.status, "Superseded"):
            storage.set_knowledge_concept_status(superseded.concept_id, "Superseded")
    return approved


@router.post("/knowledge/concepts/{concept_id}/reject", response_model=KnowledgeConcept)
def api_reject_knowledge_concept(concept_id: str, body: GovernanceActionRequest = GovernanceActionRequest()):
    current = storage.load_knowledge_concept(concept_id)
    _require_transition(current.status, "Rejected")
    return storage.set_knowledge_concept_status(concept_id, "Rejected")


@router.post("/knowledge/concepts/{concept_id}/deprecate", response_model=KnowledgeConcept)
def api_deprecate_knowledge_concept(concept_id: str, body: GovernanceActionRequest = GovernanceActionRequest()):
    current = storage.load_knowledge_concept(concept_id)
    _require_transition(current.status, "Deprecated")
    return storage.set_knowledge_concept_status(concept_id, "Deprecated")


@router.post("/knowledge/concepts/{concept_id}/archive", response_model=KnowledgeConcept)
def api_archive_knowledge_concept(concept_id: str, body: GovernanceActionRequest = GovernanceActionRequest()):
    """Deprecated -> Archived is a manual action here. §9 describes this happening
    automatically "after a retention window" -- no scheduler/background-job infrastructure
    exists in this project yet, so that sweep is left as a named future operational concern
    rather than invented for this pass."""
    current = storage.load_knowledge_concept(concept_id)
    _require_transition(current.status, "Archived")
    return storage.set_knowledge_concept_status(concept_id, "Archived")


@router.get("/knowledge/retrieve", response_model=list[KnowledgeConcept])
def api_retrieve_knowledge(
    objective: str = Query(...),
    stage: Optional[str] = Query(None),
    domain: Optional[str] = Query(None),
):
    """The retrieve(objective, stage, domain hints) contract (Phase 4 §4 / Phase 6 §5) --
    knowledge-side context assembly only. Only Active concepts are ever served here."""
    active_concepts = storage.list_knowledge_concepts(status=lifecycle.RETRIEVABLE_STATUS)
    relationships = storage.list_all_knowledge_relationships()
    return retrieve_knowledge(objective, active_concepts, relationships, stage, domain)


@router.post("/knowledge/relationships", response_model=KnowledgeRelationship, status_code=201)
def api_add_knowledge_relationship(body: KnowledgeRelationshipCreate):
    storage.load_knowledge_concept(body.from_concept_id)  # 404s if either side doesn't exist
    storage.load_knowledge_concept(body.to_concept_id)
    return storage.save_knowledge_relationship(body)


@router.get("/knowledge/concepts/{concept_id}/relationships", response_model=list[KnowledgeRelationship])
def api_list_knowledge_relationships(concept_id: str):
    return storage.list_knowledge_relationships(concept_id)


@router.post("/knowledge/principles", response_model=GovernancePrinciple, status_code=201)
def api_add_governance_principle(body: GovernancePrincipleCreate):
    """A GovernancePrinciple is a deliberate human derivation from a KnowledgeConcept's
    rules (§7/§10) -- this endpoint records that derivation, it never runs automatically."""
    if body.source_concept_id:
        storage.load_knowledge_concept(body.source_concept_id)  # 404s if it doesn't exist
    return storage.save_governance_principle(body)


@router.get("/knowledge/principles", response_model=list[GovernancePrinciple])
def api_list_governance_principles():
    return storage.list_governance_principles()


@router.delete("/knowledge/principles/{principle_id}", status_code=204)
def api_delete_governance_principle(principle_id: str):
    storage.delete_governance_principle(principle_id)
