"""Tests for committing an approved Reasoning Pipeline proposal into real project data
(backend/intelligence/commit.py + POST /projects/{id}/nodes/{id}/commit-reasoning).

This closes the gap found while designing the first UI for the reasoning/governance
backend: the reasoning pipeline and governance review only ever produce a proposal --
nothing previously committed it. Mirrors decomposition's own commit_children (WP8) for
node creation; extends the pattern to relationships and risks. Real throwaway
__REASONING_COMMIT_TEST__-prefixed project against the live DB, self-cleaning via
try/finally, matching this project's established test convention.
"""

import pytest
from fastapi.testclient import TestClient

from app import app
from backend import storage
from backend.auth import AuthenticatedUser, require_auth
from backend.intelligence.commit import commit_reasoning_proposal
from backend.models import ProposedNode, ProposedRelationship, ProposedRisk, ReasoningResult

TEST_PREFIX = "__REASONING_COMMIT_TEST__"


@pytest.fixture
def throwaway_project():
    project = storage.create_project(f"{TEST_PREFIX}project")
    try:
        yield project
    finally:
        try:
            storage.delete_project(project.id)
        except Exception:
            pass


def _root_id(project) -> str:
    return next(n.id for n in project.nodes.values() if n.parent_id is None)


# ---------- Unit tests: commit_reasoning_proposal (direct, live DB) ----------


def test_commit_creates_real_nodes_under_the_given_parent(throwaway_project):
    result = ReasoningResult(
        objective="Enable single sign-on",
        proposed_nodes=[
            ProposedNode(label="Identity Provider Integration", node_type="Capability", notes="n1"),
            ProposedNode(label="Session Management", node_type="Capability", notes="n2"),
        ],
    )
    node_ids, risk_ids = commit_reasoning_proposal(
        throwaway_project, _root_id(throwaway_project), result, actor="test@example.com"
    )
    storage.save_project(throwaway_project)
    assert len(node_ids) == 2
    assert risk_ids == []
    reloaded = storage.load_project(throwaway_project.id)
    labels = {reloaded.nodes[nid].label for nid in node_ids}
    assert labels == {"Identity Provider Integration", "Session Management"}
    for nid in node_ids:
        assert reloaded.nodes[nid].parent_id == _root_id(throwaway_project)


def test_commit_creates_references_resolving_labels_to_new_ids(throwaway_project):
    result = ReasoningResult(
        objective="Enable single sign-on",
        proposed_nodes=[
            ProposedNode(label="Identity Provider Integration"),
            ProposedNode(label="Session Management"),
        ],
        proposed_relationships=[
            ProposedRelationship(
                from_label="Session Management", to_label="Identity Provider Integration", label="depends on"
            )
        ],
    )
    node_ids, _ = commit_reasoning_proposal(
        throwaway_project, _root_id(throwaway_project), result, actor="test@example.com"
    )
    storage.save_project(throwaway_project)
    reloaded = storage.load_project(throwaway_project.id)
    assert len(reloaded.references) == 1
    ref = reloaded.references[0]
    session_id = next(nid for nid in node_ids if reloaded.nodes[nid].label == "Session Management")
    idp_id = next(nid for nid in node_ids if reloaded.nodes[nid].label == "Identity Provider Integration")
    assert ref.from_ == session_id
    assert ref.to == idp_id


def test_relationship_referencing_an_unknown_label_is_skipped_not_errored(throwaway_project):
    result = ReasoningResult(
        objective="Enable single sign-on",
        proposed_nodes=[ProposedNode(label="Identity Provider Integration")],
        proposed_relationships=[
            ProposedRelationship(from_label="Identity Provider Integration", to_label="Nonexistent Thing")
        ],
    )
    commit_reasoning_proposal(throwaway_project, _root_id(throwaway_project), result, actor="test@example.com")
    reloaded = storage.load_project(throwaway_project.id)
    assert reloaded.references == []


def test_commit_creates_real_risks_from_proposed_risks(throwaway_project):
    result = ReasoningResult(
        objective="Enable single sign-on",
        proposed_risks=[
            ProposedRisk(description="Token replay risk", classification="Security", initial_level="High")
        ],
    )
    _, risk_ids = commit_reasoning_proposal(
        throwaway_project, _root_id(throwaway_project), result, actor="test@example.com"
    )
    storage.save_project(throwaway_project)
    assert len(risk_ids) == 1
    reloaded = storage.load_project(throwaway_project.id)
    risk = next(r for r in reloaded.risks if r.id == risk_ids[0])
    assert risk.description == "Token replay risk"
    assert risk.initial_level == "High"
    assert risk.status == "Identified"


def test_commit_appends_one_governance_decision_per_node(throwaway_project):
    result = ReasoningResult(
        objective="Enable single sign-on",
        proposed_nodes=[ProposedNode(label="Identity Provider Integration"), ProposedNode(label="Session Management")],
    )
    node_ids, _ = commit_reasoning_proposal(
        throwaway_project, _root_id(throwaway_project), result, actor="test@example.com"
    )
    storage.save_project(throwaway_project)
    reloaded = storage.load_project(throwaway_project.id)
    decisions = [d for d in reloaded.governance_decisions if d.target_node_id in node_ids]
    assert len(decisions) == 2
    for d in decisions:
        assert d.decision_type == "Approve"
        assert "Enable single sign-on" in d.rationale


# ---------- Integration tests: API endpoint ----------


@pytest.fixture
def authed_client():
    app.dependency_overrides[require_auth] = lambda: AuthenticatedUser(
        id="reasoning-commit-test-user", email="reasoning-commit@example.com", role="EnterpriseArchitect"
    )
    try:
        yield TestClient(app)
    finally:
        app.dependency_overrides.clear()


def test_endpoint_commits_and_returns_ids(authed_client, throwaway_project):
    root_id = _root_id(throwaway_project)
    body = ReasoningResult(
        objective="Enable single sign-on",
        proposed_nodes=[ProposedNode(label="Identity Provider Integration")],
        proposed_risks=[ProposedRisk(description="Token replay risk", initial_level="High")],
    ).model_dump()
    response = authed_client.post(
        f"/api/projects/{throwaway_project.id}/nodes/{root_id}/commit-reasoning", json=body
    )
    assert response.status_code == 200
    payload = response.json()
    assert len(payload["committed_node_ids"]) == 1
    assert len(payload["committed_risk_ids"]) == 1


def test_endpoint_404s_for_unknown_parent(authed_client, throwaway_project):
    body = ReasoningResult(objective="x").model_dump()
    response = authed_client.post(
        f"/api/projects/{throwaway_project.id}/nodes/does-not-exist/commit-reasoning", json=body
    )
    assert response.status_code == 404


def test_endpoint_requires_auth(throwaway_project):
    root_id = _root_id(throwaway_project)
    client = TestClient(app)
    body = ReasoningResult(objective="x").model_dump()
    response = client.post(f"/api/projects/{throwaway_project.id}/nodes/{root_id}/commit-reasoning", json=body)
    assert response.status_code == 401
