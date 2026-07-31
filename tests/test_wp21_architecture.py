"""WP21 (Journey 5: TOGAF Architecture Generation) tests.

Covers backend/architecture/service.py's deterministic grouping (zero AI, pure grouping of
already-real nodes by their own classification), backend/engineering/service.py's chained
Engineering Cycle (the one genuinely new piece of infrastructure this journey needs -- every
other Cycle in this app wraps exactly one bounded call), and the two new endpoints end to
end. AI calls are mocked throughout via the same monkeypatch points test_wp8_decomposition.py
already established (`backend.agents.orchestrator.generate_children` /
`backend.agents.orchestrator.run_decision_workflow`) -- decompose_node itself is never
duplicated or reimplemented, only chained. Endpoint tests use a real throwaway
__WP21_TEST__-prefixed project against the live DB, self-cleaning via try/finally.
"""

import uuid

import pytest
from fastapi.testclient import TestClient

from app import app
from backend import storage
from backend.architecture.service import build_architecture_view
from backend.auth import AuthenticatedUser, require_auth
from backend.engineering.service import MAX_ENGINEERING_ITERATIONS, run_engineering_pipeline
from backend.models import GovernanceReview, Node, Project, ProposedNode

TEST_PREFIX = "__WP21_TEST__"


def _canned_review(outcome="approved") -> GovernanceReview:
    return GovernanceReview(outcome=outcome, requires_human_review=(outcome != "approved"))


# ---------- Unit tests: architecture.service.build_architecture_view ----------


def _project_with_nodes(nodes: dict) -> Project:
    return Project(
        id="p1", name="test", created_at="2026-01-01T00:00:00", updated_at="2026-01-01T00:00:00", nodes=nodes
    )


def test_build_architecture_view_groups_by_classification():
    nodes = {
        "root": Node(id="root", label="Root", parent_id=None),
        "b1": Node(id="b1", label="Onboard Customer", parent_id="root", classification="Business"),
        "d1": Node(id="d1", label="Customer Entity", parent_id="root", classification="Data"),
        "a1": Node(id="a1", label="Onboarding Service", parent_id="root", classification="Application"),
        "t1": Node(id="t1", label="Provision Database", parent_id="root", classification="Technology"),
        "g1": Node(id="g1", label="KYC Control", parent_id="root", classification="Governance"),
        "u1": Node(id="u1", label="Not Yet Classified", parent_id="root", classification=None),
    }
    view = build_architecture_view(_project_with_nodes(nodes))
    assert view.business == ["b1"]
    assert view.data == ["d1"]
    assert view.application == ["a1"]
    assert view.technology == ["t1"]
    assert view.governance_node_ids == ["g1"]
    assert view.unclassified_node_ids == ["root", "u1"]


def test_build_architecture_view_empty_project_has_empty_buckets():
    view = build_architecture_view(_project_with_nodes({}))
    assert view.business == []
    assert view.data == []
    assert view.application == []
    assert view.technology == []
    assert view.governance_node_ids == []
    assert view.unclassified_node_ids == []


# ---------- Unit tests: engineering.service.run_engineering_pipeline ----------


@pytest.fixture
def test_project():
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


def test_run_engineering_pipeline_commits_children_until_terminal(monkeypatch, test_project):
    root_id = _root_id(test_project)
    test_project.nodes[root_id].classification = "Technology"
    storage.save_project(test_project)

    # First decompose_node call (on the root) proposes one Task-typed child -- terminal for
    # Technology, per strategies.py's own TECHNOLOGY.leaf_node_types. The second outer pass
    # finds only that terminal child as a leaf and stops, having made no more progress.
    monkeypatch.setattr(
        "backend.agents.orchestrator.generate_children",
        lambda node, strategy, ctx: [ProposedNode(label="Provision database", node_type="Task")],
    )
    monkeypatch.setattr("backend.agents.orchestrator.run_decision_workflow", lambda result: _canned_review())

    from backend.db import postgres_cycle_repository as cycle_repo

    created_cycle = cycle_repo.create_cycle(kind="engineering", project_id=test_project.id, node_id=root_id)
    run_engineering_pipeline(created_cycle.id, test_project.id, root_id, "test-actor")

    reloaded = storage.load_project(test_project.id)
    labels = {n.label for n in reloaded.nodes.values()}
    assert "Provision database" in labels

    final_cycle = cycle_repo.get_cycle(created_cycle.id)
    assert final_cycle.status == "Completed"
    assert any(e.event_type == "DomainProgress" for e in final_cycle.events)


def test_run_engineering_pipeline_held_branch_does_not_block_sibling(monkeypatch, test_project):
    root_id = _root_id(test_project)
    test_project.nodes[root_id].classification = "Technology"
    # Two children: one will be held by governance, one will be approved and committed.
    import backend.tree as tree

    held_id = str(uuid.uuid4())
    approved_id = str(uuid.uuid4())
    tree.add_node(test_project, root_id, "Held branch", held_id)
    tree.add_node(test_project, root_id, "Approved branch", approved_id)
    test_project.nodes[held_id].classification = "Technology"
    test_project.nodes[approved_id].classification = "Technology"
    storage.save_project(test_project)

    def fake_generate(node, strategy, ctx):
        return [ProposedNode(label=f"{node.label} child", node_type="Task")]

    def fake_review(result):
        # generate_children is called once per pending leaf per pass; use the node count
        # already in the (in-memory) result's proposed_nodes to key behavior deterministically
        # isn't reliable here, so key off proposed label instead.
        if result.proposed_nodes and result.proposed_nodes[0].label.startswith("Held branch"):
            return _canned_review("held_pending_human_review")
        return _canned_review("approved")

    monkeypatch.setattr("backend.agents.orchestrator.generate_children", fake_generate)
    monkeypatch.setattr("backend.agents.orchestrator.run_decision_workflow", fake_review)

    from backend.db import postgres_cycle_repository as cycle_repo

    created_cycle = cycle_repo.create_cycle(kind="engineering", project_id=test_project.id, node_id=root_id)
    run_engineering_pipeline(created_cycle.id, test_project.id, root_id, "test-actor")

    reloaded = storage.load_project(test_project.id)
    labels = {n.label for n in reloaded.nodes.values()}
    assert "Approved branch child" in labels
    assert "Held branch child" not in labels  # held -- never committed

    final_cycle = cycle_repo.get_cycle(created_cycle.id)
    assert any(e.event_type == "BranchHeld" for e in final_cycle.events)


def test_max_engineering_iterations_is_a_small_fixed_constant():
    assert 1 < MAX_ENGINEERING_ITERATIONS <= 100


# ---------- Integration tests: the two new endpoints ----------


@pytest.fixture
def authed_client():
    app.dependency_overrides[require_auth] = lambda: AuthenticatedUser(
        id="wp21-test-user", email="wp21@example.com", role="EnterpriseArchitect"
    )
    try:
        yield TestClient(app)
    finally:
        app.dependency_overrides.clear()


def test_architecture_endpoint_requires_auth(test_project):
    client = TestClient(app)
    response = client.get(f"/api/projects/{test_project.id}/architecture")
    assert response.status_code == 401


def test_architecture_endpoint_404s_for_unknown_project(authed_client):
    response = authed_client.get(f"/api/projects/{uuid.uuid4()}/architecture")
    assert response.status_code == 404


def test_architecture_endpoint_returns_correct_bucketing(authed_client, test_project):
    root_id = _root_id(test_project)
    test_project.nodes[root_id].classification = "Business"
    storage.save_project(test_project)

    response = authed_client.get(f"/api/projects/{test_project.id}/architecture")
    assert response.status_code == 200
    body = response.json()
    assert body["business"] == [root_id]
    assert body["data"] == []
    assert body["technology"] == []


def test_engineer_architecture_endpoint_starts_a_cycle(monkeypatch, authed_client, test_project):
    root_id = _root_id(test_project)
    test_project.nodes[root_id].classification = "Technology"
    storage.save_project(test_project)

    monkeypatch.setattr("backend.agents.orchestrator.generate_children", lambda node, strategy, ctx: [])
    monkeypatch.setattr("backend.agents.orchestrator.run_decision_workflow", lambda result: _canned_review())

    response = authed_client.post(f"/api/projects/{test_project.id}/nodes/{root_id}/engineer-architecture")
    assert response.status_code == 202
    cycle = response.json()
    assert cycle["kind"] == "engineering"

    poll = authed_client.get(f"/api/cycles/{cycle['id']}")
    assert poll.status_code == 200


def test_engineer_architecture_endpoint_404s_for_unknown_node(authed_client, test_project):
    response = authed_client.post(f"/api/projects/{test_project.id}/nodes/{uuid.uuid4()}/engineer-architecture")
    assert response.status_code == 404
