"""WP19 (Journey 3: Decomposition -> Implementation Blueprint) tests.

Covers subtree readiness checking (backend/blueprint/readiness.py), blueprint proposal
generation's own id-filtering (backend/blueprint/service.py), and Orchestrator.
generate_blueprint's governance integration -- mirroring decompose_node's own precedent
of reusing a throwaway ReasoningResult for structural checking, plus the Workflow
Verification Tool's deterministic cycle-detection for the proposed dependency graph
(dependencies reference already-real nodes, so the label-based validate_structure check
doesn't fit them). AI calls are mocked throughout (never spend real money on every test
run); tests that need real subtree structure use a real throwaway __WP19_TEST__-prefixed
project against the live DB, self-cleaning via try/finally.
"""

import uuid

import pytest
from fastapi.testclient import TestClient

from app import app
from backend import storage, tree
from backend.agents.orchestrator import Orchestrator
from backend.auth import AuthenticatedUser, require_auth
from backend.blueprint import readiness
from backend.blueprint import service as blueprint_service
from backend.models import BlueprintResult, GovernanceReview, Node, ProposedDependency, ProposedWorkPackage

TEST_PREFIX = "__WP19_TEST__"


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


def _add_task(project, parent_id, label, node_type="Task", classification="Technology"):
    node_id = str(uuid.uuid4())
    tree.add_node(project, parent_id, label, node_id)
    node = project.nodes[node_id]
    node.node_type = node_type
    node.classification = classification
    return node_id


# ---------- Unit tests: readiness ----------


def test_readiness_flags_non_terminal_leaves_without_blocking(test_project):
    root_id = _root_id(test_project)
    _add_task(test_project, root_id, "Provision database", node_type="Task")
    _add_task(test_project, root_id, "Half-decomposed capability", node_type="Component")
    ready, non_terminal = readiness.check_readiness(test_project, root_id)
    assert ready is False
    assert non_terminal == ["Half-decomposed capability"]


def test_readiness_true_when_every_leaf_is_a_task(test_project):
    root_id = _root_id(test_project)
    _add_task(test_project, root_id, "Provision database")
    _add_task(test_project, root_id, "Run migrations")
    ready, non_terminal = readiness.check_readiness(test_project, root_id)
    assert ready is True
    assert non_terminal == []


def test_collect_leaf_nodes_finds_only_childless_nodes(test_project):
    root_id = _root_id(test_project)
    child_id = _add_task(test_project, root_id, "Middle layer", node_type="Component")
    grandchild_id = _add_task(test_project, child_id, "Provision database")
    leaves = readiness.collect_leaf_nodes(test_project, root_id)
    assert [leaf.id for leaf in leaves] == [grandchild_id]


# ---------- Unit tests: blueprint.service.generate_blueprint's own id-filtering ----------


def test_generate_blueprint_drops_ids_outside_the_leaf_set(monkeypatch):
    leaf = Node(id="real-leaf", label="Provision database", parent_id="root", node_type="Task")
    monkeypatch.setattr(
        "backend.blueprint.service._ask_json",
        lambda system, prompt, max_tokens=3000: {
            "work_packages": [
                {"node_id": "real-leaf", "milestone": "Milestone 1"},
                {"node_id": "hallucinated-id", "milestone": "Milestone 1"},
            ],
            "dependencies": [{"from_node_id": "real-leaf", "to_node_id": "hallucinated-id"}],
            "testing_strategy": "Unit test everything.",
            "ci_cd_strategy": "Deploy via pipeline.",
        },
    )
    root = Node(id="root", label="Root", parent_id=None)
    result = blueprint_service.generate_blueprint(root, [leaf], "no context")
    assert [wp.node_id for wp in result.proposed_work_packages] == ["real-leaf"]
    assert result.proposed_dependencies == []  # the only dependency referenced a dropped id
    assert result.testing_strategy == "Unit test everything."
    assert result.ci_cd_strategy == "Deploy via pipeline."


# ---------- Unit tests: Orchestrator.generate_blueprint ----------


def _canned_review(outcome="approved") -> GovernanceReview:
    return GovernanceReview(outcome=outcome, requires_human_review=(outcome != "approved"))


def test_generate_blueprint_sets_readiness_fields(monkeypatch, test_project):
    root_id = _root_id(test_project)
    _add_task(test_project, root_id, "Provision database", node_type="Task")
    _add_task(test_project, root_id, "Half-decomposed capability", node_type="Component")

    monkeypatch.setattr(
        "backend.agents.orchestrator.blueprint_service.generate_blueprint",
        lambda root, leaves, ctx: BlueprintResult(root_node_id=root.id),
    )
    monkeypatch.setattr("backend.agents.orchestrator.run_decision_workflow", lambda result: _canned_review())

    result = Orchestrator().generate_blueprint(test_project, test_project.nodes[root_id])
    assert result.ready is False
    assert result.non_terminal_leaf_labels == ["Half-decomposed capability"]


def test_generate_blueprint_stage_attributed_to_execution_planning_agent(monkeypatch, test_project):
    root_id = _root_id(test_project)
    _add_task(test_project, root_id, "Provision database")
    monkeypatch.setattr(
        "backend.agents.orchestrator.blueprint_service.generate_blueprint",
        lambda root, leaves, ctx: BlueprintResult(root_node_id=root.id),
    )
    monkeypatch.setattr("backend.agents.orchestrator.run_decision_workflow", lambda result: _canned_review())

    calls = []
    monkeypatch.setattr(
        "backend.agents.orchestrator._safe_record_agent_invocation",
        lambda agent_name, success, **kwargs: calls.append(agent_name),
    )
    Orchestrator().generate_blueprint(test_project, test_project.nodes[root_id])
    assert "Execution Planning Agent" in calls


def test_generate_blueprint_flags_a_cyclic_dependency_graph_as_a_warning(monkeypatch, test_project):
    root_id = _root_id(test_project)
    a_id = _add_task(test_project, root_id, "Task A")
    b_id = _add_task(test_project, root_id, "Task B")

    monkeypatch.setattr(
        "backend.agents.orchestrator.blueprint_service.generate_blueprint",
        lambda root, leaves, ctx: BlueprintResult(
            root_node_id=root.id,
            proposed_dependencies=[
                ProposedDependency(from_node_id=a_id, to_node_id=b_id),
                ProposedDependency(from_node_id=b_id, to_node_id=a_id),
            ],
        ),
    )
    monkeypatch.setattr("backend.agents.orchestrator.run_decision_workflow", lambda result: _canned_review())

    result = Orchestrator().generate_blueprint(test_project, test_project.nodes[root_id])
    cycle_findings = [f for f in result.review.findings if "cycle" in f.message.lower()]
    assert len(cycle_findings) == 1
    assert cycle_findings[0].severity == "Warning"  # informational, never blocking (WP16g's own stance)


# ---------- Integration tests: /api/projects/{id}/nodes/{id}/blueprint endpoint ----------


@pytest.fixture
def authed_client():
    app.dependency_overrides[require_auth] = lambda: AuthenticatedUser(
        id="wp19-test-user", email="wp19@example.com", role="EnterpriseArchitect"
    )
    try:
        yield TestClient(app)
    finally:
        app.dependency_overrides.clear()


def test_blueprint_endpoint_commits_on_approval(monkeypatch, authed_client, test_project):
    root_id = _root_id(test_project)
    task_id = _add_task(test_project, root_id, "Provision database")
    storage.save_project(test_project)

    monkeypatch.setattr(
        "backend.agents.orchestrator.blueprint_service.generate_blueprint",
        lambda root, leaves, ctx: BlueprintResult(
            root_node_id=root.id,
            proposed_work_packages=[ProposedWorkPackage(node_id=task_id, milestone="Milestone 1")],
        ),
    )
    monkeypatch.setattr("backend.agents.orchestrator.run_decision_workflow", lambda result: _canned_review())

    response = authed_client.post(f"/api/projects/{test_project.id}/nodes/{root_id}/blueprint", json={})
    assert response.status_code == 200
    body = response.json()
    assert body["review"]["outcome"] == "approved"
    assert body["committed_work_package_node_ids"] == [task_id]

    reloaded = storage.load_project(test_project.id)
    assert reloaded.nodes[task_id].milestone == "Milestone 1"


def test_blueprint_endpoint_does_not_commit_when_held(monkeypatch, authed_client, test_project):
    root_id = _root_id(test_project)
    task_id = _add_task(test_project, root_id, "Provision database")
    storage.save_project(test_project)

    monkeypatch.setattr(
        "backend.agents.orchestrator.blueprint_service.generate_blueprint",
        lambda root, leaves, ctx: BlueprintResult(
            root_node_id=root.id,
            proposed_work_packages=[ProposedWorkPackage(node_id=task_id, milestone="Milestone 1")],
        ),
    )
    monkeypatch.setattr(
        "backend.agents.orchestrator.run_decision_workflow",
        lambda result: _canned_review("held_pending_human_review"),
    )

    response = authed_client.post(f"/api/projects/{test_project.id}/nodes/{root_id}/blueprint", json={})
    assert response.status_code == 200
    body = response.json()
    assert body["review"]["outcome"] == "held_pending_human_review"

    reloaded = storage.load_project(test_project.id)
    assert reloaded.nodes[task_id].milestone is None


def test_blueprint_endpoint_requires_auth(test_project):
    client = TestClient(app)
    root_id = _root_id(test_project)
    response = client.post(f"/api/projects/{test_project.id}/nodes/{root_id}/blueprint", json={})
    assert response.status_code == 401


def test_blueprint_endpoint_404s_for_unknown_node(authed_client, test_project):
    response = authed_client.post(f"/api/projects/{test_project.id}/nodes/{uuid.uuid4()}/blueprint", json={})
    assert response.status_code == 404
