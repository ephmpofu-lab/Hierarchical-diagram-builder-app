"""Tests for committing an Implementation Blueprint proposal into real project data
(backend/blueprint/commit.py + POST /projects/{id}/nodes/{id}/commit-blueprint).

Journey 3's own gap-fix, mirroring Journey 2's own: api_generate_blueprint only
auto-commits an "approved" outcome; held_pending_human_review (the expected common case
-- a specific subtree's build plan rarely has High-confidence Knowledge Base coverage)
would otherwise have no way to ever be committed. commit_blueprint enriches
already-real Task nodes (milestone/schedule/planning_status) and creates real Dependency
References -- it never creates new nodes, unlike decomposition/reasoning's own commit
paths. Real throwaway __BLUEPRINT_COMMIT_TEST__-prefixed project against the live DB,
self-cleaning via try/finally, matching this project's established test convention.
"""

import uuid

import pytest
from fastapi.testclient import TestClient

from app import app
from backend import storage, tree
from backend.auth import AuthenticatedUser, require_auth
from backend.blueprint.commit import commit_blueprint
from backend.models import BlueprintResult, ProposedDependency, ProposedWorkPackage

TEST_PREFIX = "__BLUEPRINT_COMMIT_TEST__"


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


def _add_task(project, parent_id: str, label: str) -> str:
    node_id = str(uuid.uuid4())
    tree.add_node(project, parent_id, label, node_id)
    task = project.nodes[node_id]
    task.node_type = "Task"
    task.classification = "Technology"
    return node_id


# ---------- Unit tests: commit_blueprint (direct, live DB) ----------


def test_commit_sets_milestone_and_schedule_on_existing_task_nodes(throwaway_project):
    root_id = _root_id(throwaway_project)
    task_id = _add_task(throwaway_project, root_id, "Provision database")
    result = BlueprintResult(
        root_node_id=root_id,
        proposed_work_packages=[
            ProposedWorkPackage(
                node_id=task_id, milestone="Milestone 1", target_date="2026-08-15", duration_days=3
            )
        ],
    )
    committed_node_ids, _ = commit_blueprint(throwaway_project, result, actor="test@example.com")
    storage.save_project(throwaway_project)
    assert committed_node_ids == [task_id]

    reloaded = storage.load_project(throwaway_project.id)
    node = reloaded.nodes[task_id]
    assert node.milestone == "Milestone 1"
    assert node.target_date == "2026-08-15"
    assert node.duration_days == 3


def test_commit_creates_dependency_references_between_referenced_nodes(throwaway_project):
    root_id = _root_id(throwaway_project)
    a_id = _add_task(throwaway_project, root_id, "Provision database")
    b_id = _add_task(throwaway_project, root_id, "Run migrations")
    result = BlueprintResult(
        root_node_id=root_id,
        proposed_dependencies=[ProposedDependency(from_node_id=a_id, to_node_id=b_id, label="before")],
    )
    _, committed_dependency_ids = commit_blueprint(throwaway_project, result, actor="test@example.com")
    storage.save_project(throwaway_project)
    assert len(committed_dependency_ids) == 1

    reloaded = storage.load_project(throwaway_project.id)
    assert len(reloaded.references) == 1
    ref = reloaded.references[0]
    assert ref.from_ == a_id
    assert ref.to == b_id
    assert ref.reference_type == "Dependency"


def test_commit_skips_dependency_referencing_an_unknown_node_id(throwaway_project):
    root_id = _root_id(throwaway_project)
    a_id = _add_task(throwaway_project, root_id, "Provision database")
    result = BlueprintResult(
        root_node_id=root_id,
        proposed_dependencies=[ProposedDependency(from_node_id=a_id, to_node_id="does-not-exist")],
    )
    _, committed_dependency_ids = commit_blueprint(throwaway_project, result, actor="test@example.com")
    assert committed_dependency_ids == []
    assert throwaway_project.references == []


def test_commit_defaults_planning_status_to_not_started_only_when_unset(throwaway_project):
    root_id = _root_id(throwaway_project)
    fresh_id = _add_task(throwaway_project, root_id, "Provision database")
    in_progress_id = _add_task(throwaway_project, root_id, "Run migrations")
    throwaway_project.nodes[in_progress_id].planning_status = "In Progress"

    result = BlueprintResult(
        root_node_id=root_id,
        proposed_work_packages=[
            ProposedWorkPackage(node_id=fresh_id, milestone="Milestone 1"),
            ProposedWorkPackage(node_id=in_progress_id, milestone="Milestone 1"),
        ],
    )
    commit_blueprint(throwaway_project, result, actor="test@example.com")
    assert throwaway_project.nodes[fresh_id].planning_status == "Not Started"
    assert throwaway_project.nodes[in_progress_id].planning_status == "In Progress"


def test_commit_appends_one_governance_decision_per_work_package(throwaway_project):
    root_id = _root_id(throwaway_project)
    a_id = _add_task(throwaway_project, root_id, "Provision database")
    b_id = _add_task(throwaway_project, root_id, "Run migrations")
    result = BlueprintResult(
        root_node_id=root_id,
        proposed_work_packages=[
            ProposedWorkPackage(node_id=a_id, milestone="Milestone 1"),
            ProposedWorkPackage(node_id=b_id, milestone="Milestone 1"),
        ],
    )
    committed_node_ids, _ = commit_blueprint(throwaway_project, result, actor="test@example.com")
    storage.save_project(throwaway_project)
    reloaded = storage.load_project(throwaway_project.id)
    decisions = [d for d in reloaded.governance_decisions if d.target_node_id in committed_node_ids]
    assert len(decisions) == 2
    for d in decisions:
        assert d.decision_type == "Approve"
        assert "Milestone 1" in d.rationale


def test_milestone_field_round_trips_through_postgres_repository(throwaway_project):
    """The specific regression this codebase has hit twice before (WP8/9, WP11b): a new
    Node field silently fails to persist unless models.py, the migration, and the
    repository's load()/save() column lists all land together. Only a real reload from
    storage catches it."""
    root_id = _root_id(throwaway_project)
    task_id = _add_task(throwaway_project, root_id, "Provision database")
    throwaway_project.nodes[task_id].milestone = "Milestone 1"
    storage.save_project(throwaway_project)
    reloaded = storage.load_project(throwaway_project.id)
    assert reloaded.nodes[task_id].milestone == "Milestone 1"


# ---------- Integration tests: API endpoint ----------


@pytest.fixture
def authed_client():
    app.dependency_overrides[require_auth] = lambda: AuthenticatedUser(
        id="blueprint-commit-test-user", email="blueprint-commit@example.com", role="EnterpriseArchitect"
    )
    try:
        yield TestClient(app)
    finally:
        app.dependency_overrides.clear()


def test_endpoint_commits_and_returns_ids(authed_client, throwaway_project):
    root_id = _root_id(throwaway_project)
    task_id = _add_task(throwaway_project, root_id, "Provision database")
    storage.save_project(throwaway_project)
    body = BlueprintResult(
        root_node_id=root_id,
        proposed_work_packages=[ProposedWorkPackage(node_id=task_id, milestone="Milestone 1")],
    ).model_dump()
    response = authed_client.post(f"/api/projects/{throwaway_project.id}/nodes/{root_id}/commit-blueprint", json=body)
    assert response.status_code == 200
    payload = response.json()
    assert payload["committed_work_package_node_ids"] == [task_id]


def test_endpoint_404s_for_unknown_node(authed_client, throwaway_project):
    body = BlueprintResult(root_node_id="does-not-exist").model_dump()
    response = authed_client.post(
        f"/api/projects/{throwaway_project.id}/nodes/does-not-exist/commit-blueprint", json=body
    )
    assert response.status_code == 404


def test_endpoint_requires_auth(throwaway_project):
    root_id = _root_id(throwaway_project)
    client = TestClient(app)
    body = BlueprintResult(root_node_id=root_id).model_dump()
    response = client.post(f"/api/projects/{throwaway_project.id}/nodes/{root_id}/commit-blueprint", json=body)
    assert response.status_code == 401
