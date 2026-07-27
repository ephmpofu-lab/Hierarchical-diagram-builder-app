"""WP7 (Phase 12 Implementation Roadmap, Increment 3 -- Agent Orchestration) tests.

Covers the Agent taxonomy (Phase 7 section 2, 10) as inspectable data, and the
Orchestrator's attribution wrapping of the already-tested WP5 pipeline / WP6 workflow.
Per Phase 7's own continuity mapping, no new engine or governance mechanism exists here --
these tests verify attribution and dispatch, not reasoning or validation logic (already
covered by test_wp5_reasoning_pipeline.py / test_wp6_governance.py).
"""

import pytest
from fastapi.testclient import TestClient

from app import app
from backend.agents.agent import ALL_AGENTS, GOVERNANCE_AGENT, ORCHESTRATOR, VALIDATION_AGENT
from backend.agents.orchestrator import Orchestrator
from backend.auth import AuthenticatedUser, require_auth
from backend.intelligence.stages import ReasoningStageError
from backend.models import GovernanceFinding, GovernanceReview, ReasoningResult, ReasoningStageLog

# ---------- Unit tests: Agent taxonomy ----------


def test_all_agents_have_unique_names():
    names = [a.name for a in ALL_AGENTS]
    assert len(names) == len(set(names))


def test_all_agents_declare_a_governance_boundary():
    for agent in ALL_AGENTS:
        assert agent.can_propose.strip()
        assert agent.cannot_do.strip()


def test_orchestrator_is_the_only_orchestrator_category_agent():
    orchestrator_agents = [a for a in ALL_AGENTS if a.category == "orchestrator"]
    assert orchestrator_agents == [ORCHESTRATOR]


# ---------- Unit tests: Orchestrator.run_pipeline attribution ----------


def test_run_pipeline_attributes_known_stages_to_named_agents(monkeypatch):
    canned = ReasoningResult(
        objective="test",
        domains=["Business"],
        stages=[
            ReasoningStageLog(stage="business_analysis", summary="s1"),
            ReasoningStageLog(stage="architecture_thinking", summary="s2"),
            ReasoningStageLog(stage="risk_reasoning", summary="s3"),
        ],
        confidence_tier="High",
        requires_human_review=False,
    )
    monkeypatch.setattr("backend.agents.orchestrator._run_reasoning_pipeline", lambda objective: canned)
    result = Orchestrator().run_pipeline("test")
    attributed = {s.stage: s.agent for s in result.stages}
    assert attributed["business_analysis"] == "Business Architecture Agent"
    assert attributed["architecture_thinking"] == "Architecture Thinking Agent"
    assert attributed["risk_reasoning"] == GOVERNANCE_AGENT.name


def test_run_pipeline_falls_back_to_orchestrator_for_unmapped_stage(monkeypatch):
    canned = ReasoningResult(
        objective="test",
        domains=["Business"],
        stages=[ReasoningStageLog(stage="some_future_stage", summary="s1")],
        confidence_tier="High",
        requires_human_review=False,
    )
    monkeypatch.setattr("backend.agents.orchestrator._run_reasoning_pipeline", lambda objective: canned)
    result = Orchestrator().run_pipeline("test")
    assert result.stages[0].agent == ORCHESTRATOR.name


# ---------- Unit tests: Orchestrator.review_proposal attribution ----------


def test_review_proposal_attributes_structural_and_policy_findings(monkeypatch):
    canned = GovernanceReview(
        outcome="rejected",
        findings=[
            GovernanceFinding(category="structural", severity="Critical", message="dup label"),
            GovernanceFinding(category="policy", severity="Critical", message="violates X"),
        ],
        requires_human_review=False,
        requires_risk_acceptance=False,
        rationale="rejected",
    )
    monkeypatch.setattr("backend.agents.orchestrator.run_decision_workflow", lambda result: canned)
    result = ReasoningResult(objective="test", domains=["Business"], confidence_tier="High", requires_human_review=False)
    review = Orchestrator().review_proposal(result)
    attributed = {f.category: f.agent for f in review.findings}
    assert attributed["structural"] == VALIDATION_AGENT.name
    assert attributed["policy"] == GOVERNANCE_AGENT.name


# ---------- Integration tests: API endpoints ----------


@pytest.fixture
def authed_client():
    app.dependency_overrides[require_auth] = lambda: AuthenticatedUser(
        id="wp7-test-user", email="wp7@example.com", role="EnterpriseArchitect"
    )
    try:
        yield TestClient(app)
    finally:
        app.dependency_overrides.clear()


def test_agents_endpoint_returns_full_taxonomy(authed_client):
    response = authed_client.get("/api/agents")
    assert response.status_code == 200
    body = response.json()
    assert len(body) == len(ALL_AGENTS)
    assert {a["name"] for a in body} == {a.name for a in ALL_AGENTS}


def test_agents_endpoint_requires_auth():
    client = TestClient(app)
    response = client.get("/api/agents")
    assert response.status_code == 401


def test_reason_endpoint_returns_agent_attributed_stages(monkeypatch, authed_client):
    canned = ReasoningResult(
        objective="test",
        domains=["Business"],
        stages=[ReasoningStageLog(stage="dependency_reasoning", summary="s1")],
        confidence_tier="High",
        requires_human_review=False,
    )
    monkeypatch.setattr("backend.agents.orchestrator._run_reasoning_pipeline", lambda objective: canned)
    response = authed_client.post("/api/intelligence/reason", json={"objective": "test"})
    assert response.status_code == 200
    assert response.json()["stages"][0]["agent"] == "Dependency Agent"


def test_reason_endpoint_still_surfaces_stage_errors_as_502(monkeypatch, authed_client):
    def _raise(objective):
        raise ReasoningStageError("stage failed")

    monkeypatch.setattr("backend.agents.orchestrator._run_reasoning_pipeline", _raise)
    response = authed_client.post("/api/intelligence/reason", json={"objective": "test"})
    assert response.status_code == 502


def test_governance_review_endpoint_returns_agent_attributed_findings(authed_client):
    from backend.models import ProposedNode

    body = ReasoningResult(
        objective="test",
        domains=["Business"],
        proposed_nodes=[ProposedNode(label="A"), ProposedNode(label="A")],
        confidence_tier="High",
        requires_human_review=False,
    ).model_dump(by_alias=True)
    response = authed_client.post("/api/governance/review", json=body)
    assert response.status_code == 200
    findings = response.json()["findings"]
    assert any(f["category"] == "structural" and f["agent"] == VALIDATION_AGENT.name for f in findings)
