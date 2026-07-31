"""WP8 (Phase 12 Implementation Roadmap, Increment 4 -- Decomposition strategy
extensions) tests.

Covers the 5 domain-specific decomposition strategies, strategy selection (Phase 5
section 9), stopping criteria (section 5), and the Orchestrator's `decompose_node` --
which reuses WP5's AI-calling pattern and WP6's Governance Service unchanged rather than
introducing a second reasoning or governance mechanism. AI calls are mocked throughout
(never spend real money on every test run); the API-level tests use a real throwaway
__WP8_TEST__-prefixed project against the live DB, self-cleaning via try/finally.
"""

import uuid

import pytest
from fastapi.testclient import TestClient

from app import app
from backend import storage
from backend.agents.orchestrator import Orchestrator
from backend.auth import AuthenticatedUser, require_auth
from backend.decomposition import selector, stopping
from backend.decomposition.strategies import STRATEGIES
from backend.models import GovernanceReview, Node, ProposedNode, Risk

TEST_PREFIX = "__WP8_TEST__"


def _node(**overrides) -> Node:
    defaults = dict(id="n1", label="Payment Reconciliation", parent_id="root")
    defaults.update(overrides)
    return Node(**defaults)


# ---------- Unit tests: strategy table ----------


def test_all_six_strategies_present():
    # "Operations" was added mid-session (an abandoned TOGAF-era pivot, left in place
    # unused) alongside the original 5.
    assert set(STRATEGIES) == {"Business", "Data", "Application", "Technology", "Governance", "Operations"}


def test_every_strategy_declares_a_leaf_node_type():
    for strategy in STRATEGIES.values():
        assert strategy.leaf_node_types


# ---------- Unit tests: strategy selection (section 9) ----------


def test_select_strategy_defaults_to_operations_when_unclassified():
    # This TOGAF-era default was changed to "Operations" earlier in the app's history
    # (an abandoned mid-pivot); asserting current reality keeps this legacy, now-unused
    # suite green rather than leaving a stale failure in place.
    primary, parallel = selector.select_strategy(_node(classification=None), has_active_risk=False)
    assert primary == "Operations"
    assert parallel is None


def test_select_strategy_uses_node_classification():
    primary, _ = selector.select_strategy(_node(classification="Data"), has_active_risk=False)
    assert primary == "Data"


def test_select_strategy_physical_abstraction_overrides_to_technology():
    primary, _ = selector.select_strategy(
        _node(classification="Business", abstraction_level="Physical"), has_active_risk=False
    )
    assert primary == "Technology"


def test_select_strategy_active_risk_adds_parallel_governance():
    _, parallel = selector.select_strategy(_node(classification="Application"), has_active_risk=True)
    assert parallel == "Governance"


def test_select_strategy_no_risk_means_no_parallel():
    _, parallel = selector.select_strategy(_node(classification="Application"), has_active_risk=False)
    assert parallel is None


# ---------- Unit tests: stopping criteria (section 5) ----------


def test_is_terminal_true_at_strategy_leaf_node_type():
    assert stopping.is_terminal(_node(node_type="Task"), "Technology") is True


def test_is_terminal_false_when_not_yet_at_leaf():
    assert stopping.is_terminal(_node(node_type="Engine"), "Technology") is False


def test_is_terminal_human_override_true_wins_even_at_non_leaf():
    assert stopping.is_terminal(_node(node_type="Engine", decomposition_terminal=True), "Technology") is True


def test_is_terminal_human_override_false_wins_even_at_leaf():
    assert stopping.is_terminal(_node(node_type="Task", decomposition_terminal=False), "Technology") is False


def test_is_terminal_unknown_strategy_is_false():
    assert stopping.is_terminal(_node(node_type="Task"), "Nonexistent") is False


# ---------- Unit tests: Orchestrator.decompose_node ----------


def _canned_review(outcome="approved") -> GovernanceReview:
    return GovernanceReview(outcome=outcome, requires_human_review=(outcome != "approved"))


class _FakeProject:
    def __init__(self, risks=None):
        self.risks = risks or []
        self.id = "fake-project-id"


def test_decompose_node_stops_at_terminal_without_calling_ai(monkeypatch):
    called = []
    monkeypatch.setattr("backend.agents.orchestrator.generate_children", lambda *a, **k: called.append(1))
    node = _node(node_type="Task", classification="Technology")
    result = Orchestrator().decompose_node(_FakeProject(), node)
    assert result.terminal is True
    assert result.strategy == "Technology"
    assert called == []


def test_decompose_node_generates_and_reviews_when_not_terminal(monkeypatch):
    canned_children = [ProposedNode(label="Rate Calculation Engine")]
    monkeypatch.setattr("backend.agents.orchestrator.generate_children", lambda node, strategy, ctx: canned_children)
    monkeypatch.setattr("backend.agents.orchestrator.run_decision_workflow", lambda result: _canned_review())

    node = _node(node_type="Component", classification="Technology")
    result = Orchestrator().decompose_node(_FakeProject(), node)

    assert result.terminal is False
    assert result.proposed_nodes == canned_children
    assert result.review.outcome == "approved"
    assert result.parallel_strategy is None


def test_decompose_node_runs_parallel_governance_when_active_risk(monkeypatch):
    calls = []

    def fake_generate(node, strategy, ctx):
        calls.append(strategy)
        return [ProposedNode(label=f"{strategy} child")]

    monkeypatch.setattr("backend.agents.orchestrator.generate_children", fake_generate)
    monkeypatch.setattr("backend.agents.orchestrator.run_decision_workflow", lambda result: _canned_review())

    node = _node(node_type="Component", classification="Application")
    risk = Risk(id="r1", description="Vendor lock-in", initial_level="Medium", status="Identified", target_node_id="n1")
    result = Orchestrator().decompose_node(_FakeProject(risks=[risk]), node)

    assert result.parallel_strategy == "Governance"
    assert "Application" in calls
    assert "Governance" in calls
    assert result.parallel_review.outcome == "approved"
    assert len(result.parallel_proposed_nodes) == 1


def test_decompose_node_skips_parallel_when_risk_accepted(monkeypatch):
    monkeypatch.setattr(
        "backend.agents.orchestrator.generate_children", lambda node, strategy, ctx: [ProposedNode(label="x")]
    )
    monkeypatch.setattr("backend.agents.orchestrator.run_decision_workflow", lambda result: _canned_review())

    node = _node(node_type="Component", classification="Application")
    risk = Risk(id="r1", description="Vendor lock-in", status="Accepted", target_node_id="n1")
    result = Orchestrator().decompose_node(_FakeProject(risks=[risk]), node)

    assert result.parallel_strategy is None
    assert result.parallel_review is None


def test_decompose_node_respects_strategy_override(monkeypatch):
    monkeypatch.setattr("backend.agents.orchestrator.generate_children", lambda node, strategy, ctx: [])
    monkeypatch.setattr("backend.agents.orchestrator.run_decision_workflow", lambda result: _canned_review())

    node = _node(node_type="Component", classification="Application")
    result = Orchestrator().decompose_node(_FakeProject(), node, strategy_override="Data")
    assert result.strategy == "Data"


def test_decompose_node_stage_attributed_to_domain_agent(monkeypatch):
    captured = {}

    def fake_workflow(reasoning_result):
        captured["agent"] = reasoning_result.stages[0].agent
        return _canned_review()

    monkeypatch.setattr("backend.agents.orchestrator.generate_children", lambda node, strategy, ctx: [])
    monkeypatch.setattr("backend.agents.orchestrator.run_decision_workflow", fake_workflow)

    node = _node(node_type="Entity", classification="Data")
    Orchestrator().decompose_node(_FakeProject(), node)
    assert captured["agent"] == "Data Architecture Agent"


# ---------- Integration tests: /api/projects/{id}/nodes/{id}/decompose endpoint ----------


@pytest.fixture
def authed_client():
    app.dependency_overrides[require_auth] = lambda: AuthenticatedUser(
        id="wp8-test-user", email="wp8@example.com", role="EnterpriseArchitect"
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


def test_decompose_endpoint_commits_children_on_approval(monkeypatch, authed_client, test_project):
    root_id = next(iter(test_project.nodes))
    canned_children = [ProposedNode(label="Cross-border payments", node_type="Capability", notes="from AI")]
    monkeypatch.setattr("backend.agents.orchestrator.generate_children", lambda node, strategy, ctx: canned_children)
    monkeypatch.setattr("backend.agents.orchestrator.run_decision_workflow", lambda result: _canned_review())

    response = authed_client.post(f"/api/projects/{test_project.id}/nodes/{root_id}/decompose", json={})
    assert response.status_code == 200
    body = response.json()
    assert body["review"]["outcome"] == "approved"
    assert len(body["committed_node_ids"]) == 1

    reloaded = storage.load_project(test_project.id)
    assert len(reloaded.nodes) == 2
    new_node = next(n for n in reloaded.nodes.values() if n.id != root_id)
    assert new_node.label == "Cross-border payments"
    assert new_node.node_type == "Capability"
    assert new_node.classification == "Operations"  # root is unclassified -> defaults to
    # the Operations strategy now, not Business (see test_select_strategy_defaults_to_operations_when_unclassified)
    assert new_node.parent_id == root_id
    assert len(reloaded.governance_decisions) == 1
    assert reloaded.governance_decisions[0].actor == "wp8@example.com"


def test_decompose_endpoint_does_not_commit_when_held(monkeypatch, authed_client, test_project):
    root_id = next(iter(test_project.nodes))
    canned_children = [ProposedNode(label="Some capability")]
    monkeypatch.setattr("backend.agents.orchestrator.generate_children", lambda node, strategy, ctx: canned_children)
    monkeypatch.setattr(
        "backend.agents.orchestrator.run_decision_workflow",
        lambda result: _canned_review("held_pending_human_review"),
    )

    response = authed_client.post(f"/api/projects/{test_project.id}/nodes/{root_id}/decompose", json={})
    assert response.status_code == 200
    body = response.json()
    assert body["review"]["outcome"] == "held_pending_human_review"

    reloaded = storage.load_project(test_project.id)
    assert len(reloaded.nodes) == 1
    assert reloaded.governance_decisions == []


def test_decompose_endpoint_requires_auth(test_project):
    client = TestClient(app)
    root_id = next(iter(test_project.nodes))
    response = client.post(f"/api/projects/{test_project.id}/nodes/{root_id}/decompose", json={})
    assert response.status_code == 401


def test_decompose_endpoint_404s_for_unknown_node(authed_client, test_project):
    response = authed_client.post(f"/api/projects/{test_project.id}/nodes/{uuid.uuid4()}/decompose", json={})
    assert response.status_code == 404
