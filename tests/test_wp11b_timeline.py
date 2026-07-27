"""WP11b (Timeline workspace) tests.

Resolves Phase 9 section 6's own flagged gap: temporal attributes (target_date,
duration_days) didn't exist on Node until this WP. Covers the model/tree-layer wiring,
live-DB persistence round-trip (the exact bug class WP9 caught for WP8 -- new Node fields
silently failing to persist because the Postgres repository's column lists weren't
updated), and the API surface. Frontend rendering (the actual Timeline board) has no
Python surface to test and was verified via node --check + live HTTP asset fetch instead,
same as WP11/WP11a.
"""

import uuid

import pytest
from fastapi.testclient import TestClient

from app import app
from backend import storage, tree
from backend.auth import AuthenticatedUser, require_auth

TEST_PREFIX = "__WP11B_TEST__"


# ---------- Unit tests: tree.rename_node ----------


@pytest.fixture
def test_project():
    project = storage.create_project(f"{TEST_PREFIX}project")
    try:
        yield project
    finally:
        storage.delete_project(project.id)


def test_rename_node_sets_target_date_and_duration(test_project):
    root_id = next(iter(test_project.nodes))
    tree.rename_node(test_project, root_id, None, None, target_date="2026-10-01", duration_days=5)
    node = test_project.nodes[root_id]
    assert node.target_date == "2026-10-01"
    assert node.duration_days == 5


def test_rename_node_leaves_schedule_untouched_when_not_provided(test_project):
    root_id = next(iter(test_project.nodes))
    tree.rename_node(test_project, root_id, None, None, target_date="2026-10-01", duration_days=5)
    tree.rename_node(test_project, root_id, "Renamed", None)
    node = test_project.nodes[root_id]
    assert node.label == "Renamed"
    assert node.target_date == "2026-10-01"
    assert node.duration_days == 5


def test_rename_node_rejects_edits_on_locked_node_for_schedule_too(test_project):
    root_id = next(iter(test_project.nodes))
    test_project.nodes[root_id].locked = True
    with pytest.raises(Exception):
        tree.rename_node(test_project, root_id, None, None, target_date="2026-10-01")


# ---------- Integration test: live-DB persistence round-trip ----------


def test_target_date_and_duration_persist_through_real_db(test_project):
    root_id = next(iter(test_project.nodes))
    child_id = str(uuid.uuid4())
    tree.add_node(test_project, root_id, "Scheduled child", child_id)
    tree.rename_node(test_project, child_id, None, None, target_date="2026-11-15", duration_days=10)
    storage.save_project(test_project)

    reloaded = storage.load_project(test_project.id)
    reloaded_child = reloaded.nodes[child_id]
    assert reloaded_child.target_date == "2026-11-15"
    assert reloaded_child.duration_days == 10


def test_schedule_defaults_to_none_for_unscheduled_nodes(test_project):
    root_id = next(iter(test_project.nodes))
    storage.save_project(test_project)
    reloaded = storage.load_project(test_project.id)
    assert reloaded.nodes[root_id].target_date is None
    assert reloaded.nodes[root_id].duration_days is None


# ---------- Integration tests: PUT /api/projects/{id}/nodes/{id} ----------


@pytest.fixture
def authed_client():
    app.dependency_overrides[require_auth] = lambda: AuthenticatedUser(
        id="wp11b-test-user", email="wp11b@example.com", role="EnterpriseArchitect"
    )
    try:
        yield TestClient(app)
    finally:
        app.dependency_overrides.clear()


def test_update_node_endpoint_sets_schedule(authed_client, test_project):
    root_id = next(iter(test_project.nodes))
    response = authed_client.put(
        f"/api/projects/{test_project.id}/nodes/{root_id}",
        json={"target_date": "2026-12-01", "duration_days": 7},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["target_date"] == "2026-12-01"
    assert body["duration_days"] == 7

    reloaded = storage.load_project(test_project.id)
    assert reloaded.nodes[root_id].target_date == "2026-12-01"
    assert reloaded.nodes[root_id].duration_days == 7


def test_update_node_endpoint_requires_auth(test_project):
    client = TestClient(app)
    root_id = next(iter(test_project.nodes))
    response = client.put(
        f"/api/projects/{test_project.id}/nodes/{root_id}", json={"target_date": "2026-12-01"}
    )
    assert response.status_code == 401
