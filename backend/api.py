import uuid
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query

from . import concept, storage, tree
from .agents.agent import ALL_AGENTS
from .agents.orchestrator import Orchestrator
from .ai import service as ai_service
from .ai.provider import AIProviderError
from .auth import AuthenticatedUser, require_auth
from .intelligence.stages import ReasoningStageError
from .knowledge import lifecycle
from .knowledge.ingestion import parse_markdown
from .knowledge.qa import run_qa
from .knowledge.retrieval import retrieve as retrieve_knowledge
from .models import (
    AddParentRequest,
    Comment,
    CommentCreate,
    ConceptObject,
    ConceptObjectCreate,
    ConceptObjectUpdate,
    ConvertToNodeRequest,
    DecomposeRequest,
    DecompositionResult,
    GovernanceActionRequest,
    GovernanceDecision,
    GovernanceDecisionCreate,
    GovernancePrinciple,
    GovernancePrincipleCreate,
    GovernanceReview,
    KnowledgeConcept,
    KnowledgeIngestRequest,
    KnowledgeIngestResult,
    KnowledgeRelationship,
    KnowledgeRelationshipCreate,
    MoveSiblingRequest,
    NodeCreate,
    NodePosition,
    NodeUpdate,
    NodeWithLevel,
    OutlineImport,
    PasteSubtreeRequest,
    Project,
    ProjectCreate,
    ProjectRename,
    ProjectSummary,
    QAReport,
    ReasoningRequest,
    ReasoningResult,
    Reference,
    ReferenceCreate,
    ReferenceUpdate,
    ReparentRequest,
    Risk,
    RiskAssessment,
    Template,
    TemplateCreate,
    TemplateNode,
    TemplateSummary,
    ValidationReport,
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


@router.get("/agents")
def api_list_agents():
    """The Agent taxonomy and governance boundary (Phase 7 sections 2, 10 / WP7) --
    inspectable data, not just documentation."""
    return [a.__dict__ for a in ALL_AGENTS]


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
    tree.log_activity(project, f"Governance decision recorded: {body.decision_type} by {decision.actor}")
    storage.save_project(project)
    return decision


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

    def _commit(children, strategy_name: str) -> list:
        committed_ids = []
        for child in children:
            child_id = str(uuid.uuid4())
            tree.add_node(project, node_id, child.label, child_id)
            committed = project.nodes[child_id]
            committed.classification = strategy_name
            committed.node_type = child.node_type
            committed.notes = child.notes
            committed_ids.append(child_id)
            project.governance_decisions.append(
                GovernanceDecision(
                    id=str(uuid.uuid4()),
                    timestamp=datetime.now(timezone.utc).isoformat(),
                    actor=user.email or user.id,
                    decision_type="Approve",
                    target_node_id=child_id,
                    rationale=f"Auto-approved {strategy_name} decomposition of '{node.label}'",
                )
            )
        return committed_ids

    committed_any = False
    if result.review is not None and result.review.outcome == "approved":
        result.committed_node_ids = _commit(result.proposed_nodes, result.strategy)
        committed_any = True
    if result.parallel_review is not None and result.parallel_review.outcome == "approved":
        result.parallel_committed_node_ids = _commit(result.parallel_proposed_nodes, result.parallel_strategy)
        committed_any = True
    if committed_any:
        total = len(result.committed_node_ids) + len(result.parallel_committed_node_ids)
        tree.log_activity(project, f"Decomposed '{node.label}' ({total} child(ren) committed)")
        storage.save_project(project)
    return result


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
