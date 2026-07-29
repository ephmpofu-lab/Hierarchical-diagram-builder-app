"""WP16g (Workflow Verification Tool, ADR-006) tests.

Covers the deterministic BPMN reachability/cycle-detection graph algorithms
(backend/tools/workflow_verification.assess) with zero AI calls, the optional explain()
step mocked, and the API endpoint's shape/auth. Each graph is hand-traced (which nodes
are reachable, whether a cycle exists) before asserting, per the discipline established
after WP16b's arithmetic slip.
"""

import pytest
from fastapi.testclient import TestClient

from app import app
from backend.auth import AuthenticatedUser, require_auth
from backend.models import WorkflowVerificationSignals, WorkflowEdge
from backend.tools import workflow_verification

# ---------- Unit tests: deterministic graph checks ----------


def test_linear_workflow_with_start_and_end_is_sound():
    # A -> B -> C, start=A, end=C: every node reachable, no cycle.
    signals = WorkflowVerificationSignals(
        node_ids=["A", "B", "C"],
        start_ids=["A"],
        end_ids=["C"],
        edges=[WorkflowEdge(from_id="A", to_id="B"), WorkflowEdge(from_id="B", to_id="C")],
    )
    result = workflow_verification.assess(signals)
    assert result.verdict == "Sound"
    assert result.has_cycle is False
    assert result.unreachable_node_ids == []


def test_missing_start_is_unsound():
    signals = WorkflowVerificationSignals(
        node_ids=["A", "B"],
        start_ids=[],
        end_ids=["B"],
        edges=[WorkflowEdge(from_id="A", to_id="B")],
    )
    result = workflow_verification.assess(signals)
    assert result.verdict == "Unsound"
    assert any("No start node" in f for f in result.findings)


def test_missing_end_is_unsound():
    signals = WorkflowVerificationSignals(
        node_ids=["A", "B"],
        start_ids=["A"],
        end_ids=[],
        edges=[WorkflowEdge(from_id="A", to_id="B")],
    )
    result = workflow_verification.assess(signals)
    assert result.verdict == "Unsound"
    assert any("No end node" in f for f in result.findings)


def test_unreachable_node_is_unsound():
    # C has no incoming edges from the reachable set starting at A -> B only.
    signals = WorkflowVerificationSignals(
        node_ids=["A", "B", "C"],
        start_ids=["A"],
        end_ids=["B"],
        edges=[WorkflowEdge(from_id="A", to_id="B")],
    )
    result = workflow_verification.assess(signals)
    assert result.verdict == "Unsound"
    assert result.unreachable_node_ids == ["C"]


def test_cycle_is_reported_but_does_not_by_itself_make_it_unsound():
    # A -> B -> A: both reachable from A, has a cycle, but start/end present and
    # nothing is unreachable -- still Sound, cycle only informational.
    signals = WorkflowVerificationSignals(
        node_ids=["A", "B"],
        start_ids=["A"],
        end_ids=["B"],
        edges=[WorkflowEdge(from_id="A", to_id="B"), WorkflowEdge(from_id="B", to_id="A")],
    )
    result = workflow_verification.assess(signals)
    assert result.verdict == "Sound"
    assert result.has_cycle is True
    assert any("directed cycle" in f for f in result.findings)


def test_result_carries_a_nonempty_rationale():
    result = workflow_verification.assess(WorkflowVerificationSignals())
    assert result.rationale.strip()


def test_result_has_no_explanation_unless_requested():
    signals = WorkflowVerificationSignals(
        node_ids=["A"], start_ids=["A"], end_ids=["A"], edges=[]
    )
    result = workflow_verification.assess(signals)
    assert result.explanation is None


# ---------- Unit tests: explain() never changes the decision ----------


def test_explain_only_phrases_never_reclassifies(monkeypatch):
    class _FakeResult:
        text = "This workflow is sound because every activity is reachable."

    monkeypatch.setattr("backend.ai.service.complete", lambda **kwargs: _FakeResult())
    signals = WorkflowVerificationSignals(
        node_ids=["A", "B"],
        start_ids=["A"],
        end_ids=["B"],
        edges=[WorkflowEdge(from_id="A", to_id="B")],
    )
    result = workflow_verification.assess(signals)
    prose = workflow_verification.explain(result)
    assert prose == _FakeResult.text
    assert result.verdict == "Sound"  # unchanged


# ---------- Integration tests: API endpoint ----------


@pytest.fixture
def authed_client():
    app.dependency_overrides[require_auth] = lambda: AuthenticatedUser(
        id="wp16g-test-user", email="wp16g@example.com", role="EnterpriseArchitect"
    )
    try:
        yield TestClient(app)
    finally:
        app.dependency_overrides.clear()


def test_endpoint_returns_deterministic_verdict_with_no_ai_call(authed_client):
    response = authed_client.post(
        "/api/tools/workflow-verification",
        json={
            "node_ids": ["A", "B"],
            "start_ids": ["A"],
            "end_ids": ["B"],
            "edges": [{"from_id": "A", "to_id": "B"}],
        },
    )
    assert response.status_code == 200
    assert response.json()["verdict"] == "Sound"


def test_endpoint_with_explain_calls_ai_service(authed_client, monkeypatch):
    class _FakeResult:
        text = "This is sound because it has a clear start, end, and no dead activities."

    monkeypatch.setattr("backend.ai.service.complete", lambda **kwargs: _FakeResult())
    response = authed_client.post(
        "/api/tools/workflow-verification?explain=true",
        json={
            "node_ids": ["A", "B"],
            "start_ids": ["A"],
            "end_ids": ["B"],
            "edges": [{"from_id": "A", "to_id": "B"}],
        },
    )
    assert response.status_code == 200
    assert response.json()["explanation"] == _FakeResult.text


def test_endpoint_requires_auth():
    client = TestClient(app)
    response = client.post("/api/tools/workflow-verification", json={})
    assert response.status_code == 401
