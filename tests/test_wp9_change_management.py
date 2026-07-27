"""WP9 (Phase 12 Implementation Roadmap, Increment 4 -- Change Management) tests.

Covers Change Impact Analysis (Phase 10 section 8): reusing the existing structural
(parent/children) and traceability (TraceabilityLink) models with no new traversal
mechanism, flagging affected nodes Held, and re-governing them via the existing
GovernanceDecision persistence endpoint (WP6) -- an Approve clears the Held flag
(Recommitted), anything else leaves it Held. Pure structural logic, no AI involved, so
unit tests build an in-memory Project directly; API tests use a real throwaway
__WP9_TEST__-prefixed project against the live DB, self-cleaning via try/finally.
"""

import uuid
from datetime import datetime, timezone

import pytest
from fastapi.testclient import TestClient

from app import app
from backend import storage
from backend.auth import AuthenticatedUser, require_auth
from backend.change.impact import analyze_impact
from backend.models import Node, Project, TraceabilityLink

TEST_PREFIX = "__WP9_TEST__"


def _project(nodes, links=None) -> Project:
    now = datetime.now(timezone.utc).isoformat()
    return Project(
        id="p1",
        name="test",
        created_at=now,
        updated_at=now,
        nodes={n.id: n for n in nodes},
        traceability_links=links or [],
    )


# ---------- Unit tests: analyze_impact ----------


def test_analyze_impact_finds_structural_descendants():
    root = Node(id="root", label="Root", children=["a"])
    a = Node(id="a", label="A", parent_id="root", children=["b"])
    b = Node(id="b", label="B", parent_id="a")
    project = _project([root, a, b])

    findings = analyze_impact(project, "root")
    ids = {f.node_id for f in findings}
    assert ids == {"a", "b"}
    assert all("Structural descendant" in f.reason for f in findings)


def test_analyze_impact_finds_traceability_linked_nodes():
    root = Node(id="root", label="Root")
    other = Node(id="other", label="Other", parent_id="root")
    project = _project(
        [root, other],
        links=[
            TraceabilityLink(id="l1", requirement_id="req1", node_id="root"),
            TraceabilityLink(id="l2", requirement_id="req1", node_id="other"),
        ],
    )

    findings = analyze_impact(project, "root")
    assert len(findings) == 1
    assert findings[0].node_id == "other"
    assert "req1" in findings[0].reason


def test_analyze_impact_deduplicates_when_both_structural_and_traced():
    root = Node(id="root", label="Root", children=["a"])
    a = Node(id="a", label="A", parent_id="root")
    project = _project(
        [root, a],
        links=[
            TraceabilityLink(id="l1", requirement_id="req1", node_id="root"),
            TraceabilityLink(id="l2", requirement_id="req1", node_id="a"),
        ],
    )

    findings = analyze_impact(project, "root")
    assert len(findings) == 1
    assert findings[0].node_id == "a"


def test_analyze_impact_ignores_unrelated_requirements():
    root = Node(id="root", label="Root")
    unrelated = Node(id="unrelated", label="Unrelated", parent_id="root")
    project = _project(
        [root, unrelated],
        links=[
            TraceabilityLink(id="l1", requirement_id="req1", node_id="root"),
            TraceabilityLink(id="l2", requirement_id="req2", node_id="unrelated"),
        ],
    )

    findings = analyze_impact(project, "root")
    assert findings == []


def test_analyze_impact_empty_when_leaf_node_untraced():
    root = Node(id="root", label="Root", children=["a"])
    a = Node(id="a", label="A", parent_id="root")
    project = _project([root, a])

    assert analyze_impact(project, "a") == []


# ---------- Integration tests: propose-change, held-nodes, governance-decisions ----------


@pytest.fixture
def authed_client():
    app.dependency_overrides[require_auth] = lambda: AuthenticatedUser(
        id="wp9-test-user", email="wp9@example.com", role="EnterpriseArchitect"
    )
    try:
        yield TestClient(app)
    finally:
        app.dependency_overrides.clear()


@pytest.fixture
def test_project():
    project = storage.create_project(f"{TEST_PREFIX}project")
    try:
        yield project
    finally:
        storage.delete_project(project.id)


def _add_child(authed_client, project_id, parent_id, label="Child"):
    response = authed_client.post(f"/api/projects/{project_id}/nodes", json={"parent_id": parent_id, "label": label})
    assert response.status_code == 201
    return response.json()["id"]


def test_propose_change_holds_descendants_and_lists_them(authed_client, test_project):
    root_id = next(iter(test_project.nodes))
    child_id = _add_child(authed_client, test_project.id, root_id)
    grandchild_id = _add_child(authed_client, test_project.id, child_id, label="Grandchild")

    response = authed_client.post(f"/api/projects/{test_project.id}/nodes/{root_id}/propose-change", json={})
    assert response.status_code == 200
    body = response.json()
    assert body["held_count"] == 2
    assert {f["node_id"] for f in body["findings"]} == {child_id, grandchild_id}

    held_response = authed_client.get(f"/api/projects/{test_project.id}/held-nodes")
    assert held_response.status_code == 200
    held_ids = {n["id"] for n in held_response.json()}
    assert held_ids == {child_id, grandchild_id}


def test_propose_change_with_no_descendants_holds_nothing(authed_client, test_project):
    root_id = next(iter(test_project.nodes))
    response = authed_client.post(f"/api/projects/{test_project.id}/nodes/{root_id}/propose-change", json={})
    assert response.status_code == 200
    assert response.json()["held_count"] == 0


def test_approving_held_node_clears_the_flag(authed_client, test_project):
    root_id = next(iter(test_project.nodes))
    child_id = _add_child(authed_client, test_project.id, root_id)
    authed_client.post(f"/api/projects/{test_project.id}/nodes/{root_id}/propose-change", json={})

    reloaded = storage.load_project(test_project.id)
    assert reloaded.nodes[child_id].held_for_change is True

    response = authed_client.post(
        f"/api/projects/{test_project.id}/governance-decisions",
        json={"actor": "ignored", "decision_type": "Approve", "target_node_id": child_id},
    )
    assert response.status_code == 201

    reloaded = storage.load_project(test_project.id)
    assert reloaded.nodes[child_id].held_for_change is False


def test_rejecting_held_node_leaves_it_held(authed_client, test_project):
    root_id = next(iter(test_project.nodes))
    child_id = _add_child(authed_client, test_project.id, root_id)
    authed_client.post(f"/api/projects/{test_project.id}/nodes/{root_id}/propose-change", json={})

    response = authed_client.post(
        f"/api/projects/{test_project.id}/governance-decisions",
        json={"actor": "ignored", "decision_type": "Reject", "target_node_id": child_id},
    )
    assert response.status_code == 201

    reloaded = storage.load_project(test_project.id)
    assert reloaded.nodes[child_id].held_for_change is True


def test_approving_non_held_node_is_a_harmless_no_op(authed_client, test_project):
    root_id = next(iter(test_project.nodes))
    response = authed_client.post(
        f"/api/projects/{test_project.id}/governance-decisions",
        json={"actor": "ignored", "decision_type": "Approve", "target_node_id": root_id},
    )
    assert response.status_code == 201
    reloaded = storage.load_project(test_project.id)
    assert reloaded.nodes[root_id].held_for_change is False


def test_propose_change_requires_auth(test_project):
    client = TestClient(app)
    root_id = next(iter(test_project.nodes))
    response = client.post(f"/api/projects/{test_project.id}/nodes/{root_id}/propose-change", json={})
    assert response.status_code == 401


def test_propose_change_404s_for_unknown_node(authed_client, test_project):
    response = authed_client.post(
        f"/api/projects/{test_project.id}/nodes/{uuid.uuid4()}/propose-change", json={}
    )
    assert response.status_code == 404
