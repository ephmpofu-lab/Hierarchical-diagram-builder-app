"""WP10 (Phase 12 Implementation Roadmap, Increment 5 -- Event-driven layer) tests.

Covers Cycle persistence (its own narrow table, Phase 11 sections 5-6) and background
execution (backend/cycles/service.py), which wraps the already-tested Orchestrator calls
from WP5/WP7/WP8 unchanged -- these tests verify sequencing/persistence/commit, not
reasoning or governance logic (covered by earlier WPs' own test files). AI calls are
mocked throughout; cycle rows and throwaway projects are real, against the live DB,
self-cleaning via try/finally.
"""

import uuid

import pytest
from fastapi.testclient import TestClient

from app import app
from backend import storage
from backend.auth import AuthenticatedUser, require_auth
from backend.cycles import service as cycles_service
from backend.db import postgres_cycle_repository as cycle_repo
from backend.db.connection import get_pool
from backend.models import GovernanceReview, ProposedNode, ReasoningResult, ReasoningStageLog

TEST_PREFIX = "__WP10_TEST__"


def _delete_cycle(cycle_id: str) -> None:
    with get_pool().connection() as conn:
        conn.execute("delete from cycles where id = %s", (cycle_id,))


# ---------- Unit tests: cycle repository (live DB) ----------


def test_create_and_get_cycle_roundtrips():
    cycle = cycle_repo.create_cycle(kind="reasoning", objective="Test objective")
    try:
        reloaded = cycle_repo.get_cycle(cycle.id)
        assert reloaded is not None
        assert reloaded.kind == "reasoning"
        assert reloaded.status == "Running"
        assert reloaded.objective == "Test objective"
        assert reloaded.project_id is None
        assert reloaded.events == []
    finally:
        _delete_cycle(cycle.id)


def test_get_cycle_returns_none_for_unknown_id():
    assert cycle_repo.get_cycle(str(uuid.uuid4())) is None


def test_append_event_accumulates_in_order():
    cycle = cycle_repo.create_cycle(kind="reasoning", objective="x")
    try:
        cycle_repo.append_event(cycle.id, cycles_service._event("CycleStarted", "a"))
        cycle_repo.append_event(cycle.id, cycles_service._event("StageCompleted", "b"))
        reloaded = cycle_repo.get_cycle(cycle.id)
        assert [e.event_type for e in reloaded.events] == ["CycleStarted", "StageCompleted"]
        assert [e.detail for e in reloaded.events] == ["a", "b"]
    finally:
        _delete_cycle(cycle.id)


def test_complete_cycle_sets_status_and_result():
    cycle = cycle_repo.create_cycle(kind="reasoning", objective="x")
    try:
        cycle_repo.complete_cycle(cycle.id, {"foo": "bar"})
        reloaded = cycle_repo.get_cycle(cycle.id)
        assert reloaded.status == "Completed"
        assert reloaded.result == {"foo": "bar"}
    finally:
        _delete_cycle(cycle.id)


def test_fail_cycle_sets_status_and_error():
    cycle = cycle_repo.create_cycle(kind="reasoning", objective="x")
    try:
        cycle_repo.fail_cycle(cycle.id, "boom")
        reloaded = cycle_repo.get_cycle(cycle.id)
        assert reloaded.status == "Failed"
        assert reloaded.error == "boom"
    finally:
        _delete_cycle(cycle.id)


# ---------- Unit tests: background execution (mocked Orchestrator, real cycle DB rows) ----------


def test_run_reasoning_cycle_completes_and_records_stage_events(monkeypatch):
    canned = ReasoningResult(
        objective="test",
        domains=["Business"],
        stages=[ReasoningStageLog(stage="business_analysis", summary="s1", agent="Business Architecture Agent")],
        confidence_tier="High",
        requires_human_review=False,
    )
    canned_review = GovernanceReview(outcome="approved", rationale="looks good")
    monkeypatch.setattr("backend.cycles.service.Orchestrator.run_pipeline", lambda self, objective: canned)
    monkeypatch.setattr("backend.cycles.service.Orchestrator.review_proposal", lambda self, result: canned_review)

    cycle = cycle_repo.create_cycle(kind="reasoning", objective="test")
    try:
        cycles_service.run_reasoning_cycle(cycle.id, "test")
        reloaded = cycle_repo.get_cycle(cycle.id)
        assert reloaded.status == "Completed"
        event_types = [e.event_type for e in reloaded.events]
        assert event_types == ["CycleStarted", "StageCompleted", "Compliant"]
        assert reloaded.result["review"]["outcome"] == "approved"
    finally:
        _delete_cycle(cycle.id)


def test_run_reasoning_cycle_records_failure_on_exception(monkeypatch):
    def _raise(self, objective):
        raise RuntimeError("pipeline exploded")

    monkeypatch.setattr("backend.cycles.service.Orchestrator.run_pipeline", _raise)

    cycle = cycle_repo.create_cycle(kind="reasoning", objective="test")
    try:
        cycles_service.run_reasoning_cycle(cycle.id, "test")
        reloaded = cycle_repo.get_cycle(cycle.id)
        assert reloaded.status == "Failed"
        assert "pipeline exploded" in reloaded.error
        assert reloaded.events[-1].event_type == "CycleFailed"
    finally:
        _delete_cycle(cycle.id)


@pytest.fixture
def test_project():
    project = storage.create_project(f"{TEST_PREFIX}project")
    try:
        yield project
    finally:
        storage.delete_project(project.id)


def test_run_decomposition_cycle_commits_on_approval(monkeypatch, test_project):
    from backend.models import DecompositionResult

    root_id = next(iter(test_project.nodes))
    canned = DecompositionResult(
        strategy="Business",
        terminal=False,
        proposed_nodes=[ProposedNode(label="Capability A", node_type="Capability")],
        review=GovernanceReview(outcome="approved", rationale="fine"),
    )
    monkeypatch.setattr("backend.cycles.service.Orchestrator.decompose_node", lambda self, project, node, override: canned)

    cycle = cycle_repo.create_cycle(kind="decomposition", project_id=test_project.id, node_id=root_id)
    try:
        cycles_service.run_decomposition_cycle(cycle.id, test_project.id, root_id, None, "wp10@example.com")
        reloaded = cycle_repo.get_cycle(cycle.id)
        assert reloaded.status == "Completed"
        assert "Committed" in [e.event_type for e in reloaded.events]
        assert len(reloaded.result["committed_node_ids"]) == 1

        reloaded_project = storage.load_project(test_project.id)
        assert len(reloaded_project.nodes) == 2
        new_node = next(n for n in reloaded_project.nodes.values() if n.id != root_id)
        assert new_node.label == "Capability A"
        assert new_node.classification == "Business"
        assert len(reloaded_project.governance_decisions) == 1
        assert reloaded_project.governance_decisions[0].actor == "wp10@example.com"
    finally:
        _delete_cycle(cycle.id)


def test_run_decomposition_cycle_does_not_commit_when_held(monkeypatch, test_project):
    from backend.models import DecompositionResult

    root_id = next(iter(test_project.nodes))
    canned = DecompositionResult(
        strategy="Business",
        terminal=False,
        proposed_nodes=[ProposedNode(label="Capability A")],
        review=GovernanceReview(outcome="held_pending_human_review", requires_human_review=True),
    )
    monkeypatch.setattr("backend.cycles.service.Orchestrator.decompose_node", lambda self, project, node, override: canned)

    cycle = cycle_repo.create_cycle(kind="decomposition", project_id=test_project.id, node_id=root_id)
    try:
        cycles_service.run_decomposition_cycle(cycle.id, test_project.id, root_id, None, "wp10@example.com")
        reloaded = cycle_repo.get_cycle(cycle.id)
        assert reloaded.status == "Completed"
        assert "Committed" not in [e.event_type for e in reloaded.events]

        reloaded_project = storage.load_project(test_project.id)
        assert len(reloaded_project.nodes) == 1
    finally:
        _delete_cycle(cycle.id)


# ---------- Integration tests: API endpoints ----------


@pytest.fixture
def authed_client():
    app.dependency_overrides[require_auth] = lambda: AuthenticatedUser(
        id="wp10-test-user", email="wp10@example.com", role="EnterpriseArchitect"
    )
    try:
        yield TestClient(app)
    finally:
        app.dependency_overrides.clear()


def test_reason_async_endpoint_returns_running_cycle_then_completes(monkeypatch, authed_client):
    canned = ReasoningResult(objective="test", domains=["Business"], confidence_tier="High", requires_human_review=False)
    monkeypatch.setattr("backend.agents.orchestrator.Orchestrator.run_pipeline", lambda self, objective: canned)
    monkeypatch.setattr(
        "backend.agents.orchestrator.Orchestrator.review_proposal",
        lambda self, result: GovernanceReview(outcome="approved"),
    )

    response = authed_client.post("/api/intelligence/reason-async", json={"objective": "test"})
    assert response.status_code == 202
    cycle_id = response.json()["id"]
    try:
        status_response = authed_client.get(f"/api/cycles/{cycle_id}")
        assert status_response.status_code == 200
        assert status_response.json()["status"] == "Completed"
    finally:
        _delete_cycle(cycle_id)


def test_reason_async_rejects_empty_objective(authed_client):
    response = authed_client.post("/api/intelligence/reason-async", json={"objective": "   "})
    assert response.status_code == 400


def test_reason_async_requires_auth():
    client = TestClient(app)
    response = client.post("/api/intelligence/reason-async", json={"objective": "test"})
    assert response.status_code == 401


def test_decompose_async_endpoint_commits_on_approval(monkeypatch, authed_client, test_project):
    from backend.models import DecompositionResult

    root_id = next(iter(test_project.nodes))
    canned = DecompositionResult(
        strategy="Business",
        terminal=False,
        proposed_nodes=[ProposedNode(label="Capability A")],
        review=GovernanceReview(outcome="approved"),
    )
    monkeypatch.setattr(
        "backend.agents.orchestrator.Orchestrator.decompose_node", lambda self, project, node, override: canned
    )

    response = authed_client.post(f"/api/projects/{test_project.id}/nodes/{root_id}/decompose-async", json={})
    assert response.status_code == 202
    cycle_id = response.json()["id"]
    try:
        status_response = authed_client.get(f"/api/cycles/{cycle_id}")
        assert status_response.status_code == 200
        body = status_response.json()
        assert body["status"] == "Completed"
        assert len(body["result"]["committed_node_ids"]) == 1

        reloaded = storage.load_project(test_project.id)
        assert len(reloaded.nodes) == 2
    finally:
        _delete_cycle(cycle_id)


def test_decompose_async_404s_for_unknown_node(authed_client, test_project):
    response = authed_client.post(
        f"/api/projects/{test_project.id}/nodes/{uuid.uuid4()}/decompose-async", json={}
    )
    assert response.status_code == 404


def test_get_cycle_404s_for_unknown_id(authed_client):
    response = authed_client.get(f"/api/cycles/{uuid.uuid4()}")
    assert response.status_code == 404


def test_get_cycle_requires_auth():
    client = TestClient(app)
    response = client.get(f"/api/cycles/{uuid.uuid4()}")
    assert response.status_code == 401


def test_list_cycles_returns_project_scoped_cycles(authed_client, test_project):
    root_id = next(iter(test_project.nodes))
    cycle = cycle_repo.create_cycle(kind="decomposition", project_id=test_project.id, node_id=root_id)
    try:
        response = authed_client.get(f"/api/projects/{test_project.id}/cycles")
        assert response.status_code == 200
        ids = {c["id"] for c in response.json()}
        assert cycle.id in ids
    finally:
        _delete_cycle(cycle.id)
