"""WP5 (Phase 12 Implementation Roadmap, Increment 3 -- Reasoning Pipeline synchronous MVP)
tests. Covers the 8-stage Enterprise Reasoning Pipeline (Phase 4 sections 2-3). Like WP4,
every AI call here is billed against a real vendor, so stage-level and pipeline-level tests
mock `ai_service.complete` / the stage functions rather than spending real money on every
run. Context-assembly tests hit the live DB with throwaway __WP5_TEST__-prefixed data,
matching this project's established convention (no separate test database).
"""

import json
import uuid

import pytest
from fastapi.testclient import TestClient

from app import app
from backend import storage
from backend.ai.provider import AIAuthenticationError, AICompletionResult
from backend.auth import AuthenticatedUser, require_auth
from backend.intelligence import context as context_module
from backend.intelligence import pipeline as pipeline_module
from backend.intelligence import stages
from backend.intelligence.stages import ReasoningStageError
from backend.models import (
    GovernancePrincipleCreate,
    KnowledgeConceptCreate,
    ProposedNode,
    ProposedRelationship,
    ProposedRisk,
)

TEST_PREFIX = "__WP5_TEST__"


def _completion(text: str) -> AICompletionResult:
    return AICompletionResult(text=text, model="gpt-5.5", input_tokens=10, output_tokens=5)


# ---------- Unit tests: individual stages ----------


def test_select_domains_parses_primary_and_influenced(monkeypatch):
    monkeypatch.setattr(
        "backend.intelligence.stages.ai_service.complete",
        lambda **kwargs: _completion(json.dumps({"primary": "Business", "influenced": ["Data", "Technology"]})),
    )
    domains = stages.select_domains("Improve customer onboarding", "some context")
    assert domains == ["Business", "Data", "Technology"]


def test_select_domains_rejects_unrecognized_primary(monkeypatch):
    monkeypatch.setattr(
        "backend.intelligence.stages.ai_service.complete",
        lambda **kwargs: _completion(json.dumps({"primary": "Not A Domain", "influenced": []})),
    )
    with pytest.raises(ReasoningStageError):
        stages.select_domains("objective", "context")


def test_ask_text_wraps_provider_error(monkeypatch):
    def _raise(**kwargs):
        raise AIAuthenticationError("bad key")

    monkeypatch.setattr("backend.intelligence.stages.ai_service.complete", _raise)
    with pytest.raises(ReasoningStageError):
        stages.business_analysis("objective", "context")


def test_ask_json_rejects_non_json_output(monkeypatch):
    monkeypatch.setattr(
        "backend.intelligence.stages.ai_service.complete", lambda **kwargs: _completion("not json at all")
    )
    with pytest.raises(ReasoningStageError):
        stages.select_domains("objective", "context")


def test_architecture_thinking_builds_proposed_nodes(monkeypatch):
    monkeypatch.setattr(
        "backend.intelligence.stages.ai_service.complete",
        lambda **kwargs: _completion(
            json.dumps({"nodes": [{"label": "Onboarding Service", "node_type": "Application", "notes": ""}]})
        ),
    )
    nodes = stages.architecture_thinking("objective", "capability summary", "context")
    assert nodes == [ProposedNode(label="Onboarding Service", node_type="Application", notes="")]


def test_architecture_thinking_malformed_node_raises_stage_error(monkeypatch):
    # Missing the required "label" field
    monkeypatch.setattr(
        "backend.intelligence.stages.ai_service.complete",
        lambda **kwargs: _completion(json.dumps({"nodes": [{"node_type": "Application"}]})),
    )
    with pytest.raises(ReasoningStageError):
        stages.architecture_thinking("objective", "capability", "context")


def test_dependency_reasoning_drops_relationships_with_unknown_labels(monkeypatch):
    nodes = [ProposedNode(label="A"), ProposedNode(label="B")]
    monkeypatch.setattr(
        "backend.intelligence.stages.ai_service.complete",
        lambda **kwargs: _completion(
            json.dumps(
                {
                    "relationships": [
                        {"from_label": "A", "to_label": "B", "label": None, "reference_type": None},
                        {"from_label": "A", "to_label": "Nonexistent", "label": None, "reference_type": None},
                    ]
                }
            )
        ),
    )
    relationships = stages.dependency_reasoning("objective", nodes)
    assert relationships == [ProposedRelationship(from_label="A", to_label="B")]


def test_risk_reasoning_builds_proposed_risks(monkeypatch):
    monkeypatch.setattr(
        "backend.intelligence.stages.ai_service.complete",
        lambda **kwargs: _completion(
            json.dumps({"risks": [{"description": "Vendor lock-in", "classification": "Strategic", "initial_level": "Medium"}]})
        ),
    )
    risks = stages.risk_reasoning("objective", [ProposedNode(label="A")], [])
    assert risks == [ProposedRisk(description="Vendor lock-in", classification="Strategic", initial_level="Medium")]


def test_governance_reasoning_parses_compliance_and_violations(monkeypatch):
    monkeypatch.setattr(
        "backend.intelligence.stages.ai_service.complete",
        lambda **kwargs: _completion(json.dumps({"compliant": False, "violations": ["duplicate capability"]})),
    )
    compliant, violations = stages.governance_reasoning("objective", [ProposedNode(label="A")], "context")
    assert compliant is False
    assert violations == ["duplicate capability"]


def test_technology_reasoning_annotates_matching_nodes_only(monkeypatch):
    nodes = [ProposedNode(label="A", notes="original"), ProposedNode(label="B", notes="")]
    monkeypatch.setattr(
        "backend.intelligence.stages.ai_service.complete",
        lambda **kwargs: _completion(
            json.dumps({"annotations": [{"label": "A", "technology_notes": "use managed Postgres"}]})
        ),
    )
    annotated = stages.technology_reasoning("objective", nodes)
    assert annotated[0].notes == "original use managed Postgres"
    assert annotated[1].notes == ""


# ---------- Unit tests: pipeline orchestration (stages mocked) ----------


@pytest.fixture
def _no_kb_context(monkeypatch):
    monkeypatch.setattr(pipeline_module, "assemble_reasoning_context", lambda objective: "some retrieved context")


@pytest.fixture
def _stub_stages(monkeypatch):
    """Stubs every stage function to a deterministic, compliant, low-risk happy path.
    Individual tests override specific stages to exercise other branches."""
    nodes = [ProposedNode(label="Onboarding Service")]
    relationships = [ProposedRelationship(from_label="Onboarding Service", to_label="Onboarding Service")]
    risks = [ProposedRisk(description="minor risk", initial_level="Low")]

    monkeypatch.setattr(stages, "select_domains", lambda objective, ctx: ["Business"])
    monkeypatch.setattr(stages, "business_analysis", lambda objective, ctx: "motivation")
    monkeypatch.setattr(stages, "capability_analysis", lambda objective, motivation: "capability")
    monkeypatch.setattr(stages, "architecture_thinking", lambda objective, cap, ctx: list(nodes))
    monkeypatch.setattr(stages, "dependency_reasoning", lambda objective, n: list(relationships))
    monkeypatch.setattr(stages, "risk_reasoning", lambda objective, n, r: list(risks))
    monkeypatch.setattr(stages, "governance_reasoning", lambda objective, n, ctx: (True, []))
    monkeypatch.setattr(stages, "technology_reasoning", lambda objective, n: n)
    monkeypatch.setattr(stages, "implementation_reasoning", lambda objective, n: "ready for decomposition")
    return {"nodes": nodes, "relationships": relationships, "risks": risks}


def test_pipeline_happy_path_yields_high_confidence(_no_kb_context, _stub_stages):
    result = pipeline_module.run_pipeline("Improve customer onboarding")
    assert result.confidence_tier == "High"
    assert result.requires_human_review is False
    assert result.domains == ["Business"]
    assert len(result.proposed_nodes) == 1
    assert result.governance_notes == []


def test_pipeline_without_kb_coverage_yields_medium_confidence(monkeypatch, _stub_stages):
    monkeypatch.setattr(
        pipeline_module,
        "assemble_reasoning_context",
        lambda objective: "No matching KnowledgeConcepts or GovernancePrinciples were retrieved...",
    )
    result = pipeline_module.run_pipeline("Some objective")
    assert result.confidence_tier == "Medium"
    assert result.requires_human_review is True


def test_pipeline_high_severity_risk_forces_low_confidence(monkeypatch, _no_kb_context, _stub_stages):
    monkeypatch.setattr(
        stages, "risk_reasoning", lambda objective, n, r: [ProposedRisk(description="bad", initial_level="Critical")]
    )
    result = pipeline_module.run_pipeline("objective")
    assert result.confidence_tier == "Low"
    assert result.requires_human_review is True


def test_pipeline_retries_on_governance_violation_then_succeeds(monkeypatch, _no_kb_context, _stub_stages):
    calls = {"count": 0}

    def _governance(objective, nodes, ctx):
        calls["count"] += 1
        if calls["count"] == 1:
            return False, ["violates principle X"]
        return True, []

    monkeypatch.setattr(stages, "governance_reasoning", _governance)
    result = pipeline_module.run_pipeline("objective")
    assert calls["count"] == 2
    assert result.confidence_tier == "Medium"  # loop occurred, even though it eventually complied
    assert any("re-entering architecture thinking" in note for note in result.governance_notes)


def test_pipeline_exhausts_governance_retries_and_proceeds_with_low_confidence(monkeypatch, _no_kb_context, _stub_stages):
    monkeypatch.setattr(stages, "governance_reasoning", lambda objective, n, ctx: (False, ["still violates"]))
    result = pipeline_module.run_pipeline("objective")
    assert result.confidence_tier == "Low"
    assert "still violates" in result.governance_notes


def test_pipeline_stage_error_propagates(monkeypatch, _no_kb_context, _stub_stages):
    def _raise(objective, ctx):
        raise ReasoningStageError("boom")

    monkeypatch.setattr(stages, "select_domains", _raise)
    with pytest.raises(ReasoningStageError):
        pipeline_module.run_pipeline("objective")


# ---------- Integration test: context assembly against the live DB ----------


@pytest.fixture
def seeded_concept_and_principle():
    concept = storage.save_knowledge_concept(
        KnowledgeConceptCreate(
            concept_id=f"{TEST_PREFIX}{uuid.uuid4().hex[:8]}",
            name="Zzyzxonboarding",  # deliberately unusual token so keyword matching is unambiguous
            category="Core Concept",
            definition="Zzyzxonboarding is the process of introducing a new customer.",
        )
    )
    storage.set_knowledge_concept_status(concept.concept_id, "Active")
    principle = storage.save_governance_principle(
        GovernancePrincipleCreate(statement="Zzyzxonboarding must always be automated.", applies_to_domain="Business")
    )
    try:
        yield concept, principle
    finally:
        storage.delete_governance_principle(principle.id)
        storage.delete_knowledge_concept(concept.concept_id)


def test_assemble_reasoning_context_includes_matching_concepts_and_principles(seeded_concept_and_principle):
    concept, principle = seeded_concept_and_principle
    result = context_module.assemble_reasoning_context("How should we handle Zzyzxonboarding for new customers?")
    assert concept.concept_id in result
    assert "Zzyzxonboarding must always be automated." in result


def test_assemble_reasoning_context_falls_back_when_nothing_matches():
    result = context_module.assemble_reasoning_context("Xqfltnobyzquux completely unrelated gibberish")
    assert "No matching KnowledgeConcepts" in result


# ---------- Integration test: /api/intelligence/reason endpoint ----------


@pytest.fixture
def authed_client():
    app.dependency_overrides[require_auth] = lambda: AuthenticatedUser(
        id="wp5-test-user", email="wp5@example.com", role="EnterpriseArchitect"
    )
    try:
        yield TestClient(app)
    finally:
        app.dependency_overrides.clear()


def test_reason_endpoint_returns_pipeline_result(monkeypatch, authed_client):
    from backend.models import ReasoningResult

    canned = ReasoningResult(objective="test", domains=["Business"], confidence_tier="High", requires_human_review=False)
    monkeypatch.setattr("backend.agents.orchestrator.Orchestrator.run_pipeline", lambda self, objective: canned)
    response = authed_client.post("/api/intelligence/reason", json={"objective": "test"})
    assert response.status_code == 200
    assert response.json()["confidence_tier"] == "High"


def test_reason_endpoint_rejects_empty_objective(authed_client):
    response = authed_client.post("/api/intelligence/reason", json={"objective": "   "})
    assert response.status_code == 400


def test_reason_endpoint_surfaces_stage_errors_as_502(monkeypatch, authed_client):
    def _raise(self, objective):
        raise ReasoningStageError("stage failed")

    monkeypatch.setattr("backend.agents.orchestrator.Orchestrator.run_pipeline", _raise)
    response = authed_client.post("/api/intelligence/reason", json={"objective": "test"})
    assert response.status_code == 502


def test_reason_endpoint_requires_auth():
    client = TestClient(app)
    response = client.post("/api/intelligence/reason", json={"objective": "test"})
    assert response.status_code == 401
