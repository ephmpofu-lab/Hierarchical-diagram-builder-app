"""Tests for the human-override decomposition commit endpoint
(POST /projects/{id}/nodes/{id}/commit-decomposition).

Journey 2's own gap-fix: api_decompose_node only auto-commits an "approved" outcome;
held_pending_human_review (the common case for decompose -- most nodes have no matching
Knowledge Base coverage) previously had no way to ever be committed. This endpoint is a
thin wrapper around the already-existing commit_children (backend/decomposition/commit.py),
reused unchanged -- no new commit logic. Real throwaway
__DECOMPOSITION_COMMIT_TEST__-prefixed project against the live DB, self-cleaning via
try/finally, matching this project's established test convention.
"""

import pytest
from fastapi.testclient import TestClient

from app import app
from backend import storage
from backend.auth import AuthenticatedUser, require_auth
from backend.models import DecompositionResult, ProposedNode

TEST_PREFIX = "__DECOMPOSITION_COMMIT_TEST__"


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


@pytest.fixture
def authed_client():
    app.dependency_overrides[require_auth] = lambda: AuthenticatedUser(
        id="decomp-commit-test-user", email="decomp-commit@example.com", role="EnterpriseArchitect"
    )
    try:
        yield TestClient(app)
    finally:
        app.dependency_overrides.clear()


# ---------- Integration tests: API endpoint ----------


def test_endpoint_commits_a_held_decomposition_result(authed_client, throwaway_project):
    root_id = _root_id(throwaway_project)
    body = DecompositionResult(
        strategy="Business",
        terminal=False,
        proposed_nodes=[
            ProposedNode(label="Source Candidates", node_type="Sub-process"),
            ProposedNode(label="Screen Candidates", node_type="Sub-process"),
        ],
    ).model_dump()
    response = authed_client.post(
        f"/api/projects/{throwaway_project.id}/nodes/{root_id}/commit-decomposition", json=body
    )
    assert response.status_code == 200
    committed_ids = response.json()["committed_node_ids"]
    assert len(committed_ids) == 2

    reloaded = storage.load_project(throwaway_project.id)
    labels = {reloaded.nodes[nid].label for nid in committed_ids}
    assert labels == {"Source Candidates", "Screen Candidates"}
    for nid in committed_ids:
        assert reloaded.nodes[nid].parent_id == root_id
        assert reloaded.nodes[nid].classification == "Business"


def test_endpoint_appends_one_governance_decision_per_committed_node(authed_client, throwaway_project):
    root_id = _root_id(throwaway_project)
    body = DecompositionResult(
        strategy="Data", terminal=False, proposed_nodes=[ProposedNode(label="Customer Entity")]
    ).model_dump()
    response = authed_client.post(
        f"/api/projects/{throwaway_project.id}/nodes/{root_id}/commit-decomposition", json=body
    )
    committed_ids = response.json()["committed_node_ids"]
    reloaded = storage.load_project(throwaway_project.id)
    decisions = [d for d in reloaded.governance_decisions if d.target_node_id in committed_ids]
    assert len(decisions) == 1
    assert decisions[0].decision_type == "Approve"
    assert "Data" in decisions[0].rationale


def test_endpoint_404s_for_unknown_node(authed_client, throwaway_project):
    body = DecompositionResult(strategy="Business", terminal=False).model_dump()
    response = authed_client.post(
        f"/api/projects/{throwaway_project.id}/nodes/does-not-exist/commit-decomposition", json=body
    )
    assert response.status_code == 404


def test_endpoint_requires_auth(throwaway_project):
    root_id = _root_id(throwaway_project)
    client = TestClient(app)
    body = DecompositionResult(strategy="Business", terminal=False).model_dump()
    response = client.post(
        f"/api/projects/{throwaway_project.id}/nodes/{root_id}/commit-decomposition", json=body
    )
    assert response.status_code == 401
