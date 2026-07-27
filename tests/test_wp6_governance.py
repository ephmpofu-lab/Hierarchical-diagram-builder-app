"""WP6 (Phase 12 Implementation Roadmap, Increment 3 -- Governance Service MVP) tests.

Covers structural + policy validation and the Decision & Approval Workflow (Phase 10
sections 3-4), plus real persistence for GovernanceDecision and Risk acceptance -- both
WP1-era models that had no API surface until this WP. Live-DB integration tests use
throwaway __WP6_TEST__-prefixed projects, self-cleaning via try/finally, matching this
project's established convention.
"""

import uuid

import pytest
from fastapi.testclient import TestClient

from app import app
from backend import storage
from backend.auth import AuthenticatedUser, require_auth
from backend.governance.validation import validate_policy, validate_structure
from backend.governance.workflow import run_decision_workflow
from backend.models import ProposedNode, ProposedRelationship, ProposedRisk, ReasoningResult, Risk

TEST_PREFIX = "__WP6_TEST__"


def _clean_result(**overrides) -> ReasoningResult:
    defaults = dict(
        objective="Test objective",
        domains=["Business"],
        proposed_nodes=[ProposedNode(label="A"), ProposedNode(label="B")],
        proposed_relationships=[ProposedRelationship(from_label="A", to_label="B")],
        proposed_risks=[],
        confidence_tier="High",
        requires_human_review=False,
        governance_notes=[],
    )
    defaults.update(overrides)
    return ReasoningResult(**defaults)


# ---------- Unit tests: structural validation ----------


def test_validate_structure_passes_clean_proposal():
    assert validate_structure(_clean_result()) == []


def test_validate_structure_flags_duplicate_labels():
    result = _clean_result(proposed_nodes=[ProposedNode(label="A"), ProposedNode(label="A")])
    findings = validate_structure(result)
    assert any(f.category == "structural" and f.severity == "Critical" for f in findings)


def test_validate_structure_flags_dangling_relationship():
    result = _clean_result(
        proposed_nodes=[ProposedNode(label="A")],
        proposed_relationships=[ProposedRelationship(from_label="A", to_label="Nonexistent")],
    )
    findings = validate_structure(result)
    assert any("Nonexistent" in f.message for f in findings)


# ---------- Unit tests: policy validation ----------


def test_validate_policy_passes_when_no_governance_notes():
    assert validate_policy(_clean_result(governance_notes=[])) == []


def test_validate_policy_formalizes_governance_notes_as_critical_findings():
    result = _clean_result(governance_notes=["violates principle X"])
    findings = validate_policy(result)
    assert len(findings) == 1
    assert findings[0].category == "policy"
    assert findings[0].severity == "Critical"
    assert "violates principle X" in findings[0].message


# ---------- Unit tests: decision workflow ----------


def test_workflow_rejects_on_structural_critical():
    result = _clean_result(proposed_nodes=[ProposedNode(label="A"), ProposedNode(label="A")])
    review = run_decision_workflow(result)
    assert review.outcome == "rejected"


def test_workflow_rejects_on_policy_critical():
    result = _clean_result(governance_notes=["violates principle X"])
    review = run_decision_workflow(result)
    assert review.outcome == "rejected"


def test_workflow_holds_for_human_review_when_confidence_requires_it():
    result = _clean_result(requires_human_review=True, confidence_tier="Medium")
    review = run_decision_workflow(result)
    assert review.outcome == "held_pending_human_review"
    assert review.requires_human_review is True


def test_workflow_holds_for_risk_acceptance_when_high_confidence_but_risk_present():
    result = _clean_result(
        requires_human_review=False,
        proposed_risks=[ProposedRisk(description="some risk", initial_level="Low")],
    )
    review = run_decision_workflow(result)
    assert review.outcome == "held_pending_risk_acceptance"
    assert review.requires_risk_acceptance is True


def test_workflow_approves_clean_high_confidence_no_risk_proposal():
    review = run_decision_workflow(_clean_result())
    assert review.outcome == "approved"
    assert review.requires_human_review is False
    assert review.requires_risk_acceptance is False


def test_workflow_structural_rejection_takes_priority_over_everything_else():
    result = _clean_result(
        proposed_nodes=[ProposedNode(label="A"), ProposedNode(label="A")],
        governance_notes=["also violates something"],
        requires_human_review=True,
        proposed_risks=[ProposedRisk(description="risk", initial_level="Critical")],
    )
    review = run_decision_workflow(result)
    assert review.outcome == "rejected"


# ---------- Integration test: /api/governance/review endpoint ----------


@pytest.fixture
def authed_client():
    app.dependency_overrides[require_auth] = lambda: AuthenticatedUser(
        id="wp6-test-user", email="wp6@example.com", role="EnterpriseArchitect"
    )
    try:
        yield TestClient(app)
    finally:
        app.dependency_overrides.clear()


def test_governance_review_endpoint_returns_workflow_outcome(authed_client):
    body = _clean_result().model_dump(by_alias=True)
    response = authed_client.post("/api/governance/review", json=body)
    assert response.status_code == 200
    assert response.json()["outcome"] == "approved"


def test_governance_review_endpoint_requires_auth():
    client = TestClient(app)
    body = _clean_result().model_dump(by_alias=True)
    response = client.post("/api/governance/review", json=body)
    assert response.status_code == 401


# ---------- Integration tests: governance decisions + risk acceptance (live DB) ----------


@pytest.fixture
def test_project():
    project = storage.create_project(f"{TEST_PREFIX}project")
    try:
        yield project
    finally:
        storage.delete_project(project.id)


def test_record_governance_decision_persists_and_overrides_actor(authed_client, test_project):
    response = authed_client.post(
        f"/api/projects/{test_project.id}/governance-decisions",
        json={"actor": "someone-else-entirely", "decision_type": "Approve", "rationale": "Looks good"},
    )
    assert response.status_code == 201
    body = response.json()
    # actor is always the authenticated caller, never the client-supplied value -- the
    # audit trail (Phase 10 section 9) can't be spoofed
    assert body["actor"] == "wp6@example.com"
    assert body["decision_type"] == "Approve"

    reloaded = storage.load_project(test_project.id)
    assert len(reloaded.governance_decisions) == 1
    assert reloaded.governance_decisions[0].actor == "wp6@example.com"


def test_accept_risk_transitions_status_and_appends_assessment(authed_client, test_project):
    risk = Risk(id=str(uuid.uuid4()), description="Vendor lock-in", initial_level="Medium", status="Classified")
    test_project.risks = [risk]
    storage.save_project(test_project)

    response = authed_client.post(f"/api/projects/{test_project.id}/risks/{risk.id}/accept")
    assert response.status_code == 200
    assert response.json()["status"] == "Accepted"

    reloaded = storage.load_project(test_project.id)
    accepted_risk = next(r for r in reloaded.risks if r.id == risk.id)
    assert accepted_risk.status == "Accepted"
    assert len(reloaded.risk_assessments) == 1
    assert reloaded.risk_assessments[0].assessment_type == "Residual"
    assert reloaded.risk_assessments[0].risk_id == risk.id


def test_accept_risk_404s_for_unknown_risk(authed_client, test_project):
    response = authed_client.post(f"/api/projects/{test_project.id}/risks/{uuid.uuid4()}/accept")
    assert response.status_code == 404
