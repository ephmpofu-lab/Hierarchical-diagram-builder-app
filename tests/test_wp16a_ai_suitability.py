"""WP16a (AI Suitability Assessment Tool, ADR-006) tests.

Covers the deterministic decision tree (backend/tools/ai_suitability.assess) with zero AI
calls, the optional explain() step mocked (never live -- matches every other WP's
AI-mocking convention), and the API endpoint's shape/auth.
"""

import pytest
from fastapi.testclient import TestClient

from app import app
from backend.auth import AuthenticatedUser, require_auth
from backend.models import AISuitabilityAssessment, AISuitabilitySignals
from backend.tools import ai_suitability

# ---------- Unit tests: deterministic classification ----------


def test_fully_deterministic_process_recommends_rules_engine():
    signals = AISuitabilitySignals(process_is_fully_deterministic=True)
    result = ai_suitability.assess(signals)
    assert result.recommended_pattern == "Rules Engine"


def test_deterministic_but_needs_nlu_does_not_short_circuit_to_rules_engine():
    signals = AISuitabilitySignals(
        process_is_fully_deterministic=True,
        requires_natural_language_understanding_or_generation=True,
    )
    result = ai_suitability.assess(signals)
    assert result.recommended_pattern == "Generic LLM"


def test_autonomous_tool_use_recommends_agentic_even_with_other_signals():
    signals = AISuitabilitySignals(
        requires_multi_step_autonomous_tool_use=True,
        requires_external_knowledge_retrieval=True,
    )
    result = ai_suitability.assess(signals)
    assert result.recommended_pattern == "Agentic AI"


def test_external_knowledge_retrieval_recommends_rag():
    signals = AISuitabilitySignals(requires_external_knowledge_retrieval=True)
    result = ai_suitability.assess(signals)
    assert result.recommended_pattern == "RAG"


def test_historical_pattern_prediction_recommends_predictive_ai():
    signals = AISuitabilitySignals(requires_pattern_prediction_from_historical_data=True)
    result = ai_suitability.assess(signals)
    assert result.recommended_pattern == "Predictive AI"


def test_nlu_only_recommends_generic_llm():
    signals = AISuitabilitySignals(requires_natural_language_understanding_or_generation=True)
    result = ai_suitability.assess(signals)
    assert result.recommended_pattern == "Generic LLM"


def test_no_signals_defaults_to_workflow_automation():
    signals = AISuitabilitySignals()
    result = ai_suitability.assess(signals)
    assert result.recommended_pattern == "Workflow Automation"


def test_assessment_always_carries_a_nonempty_rationale():
    result = ai_suitability.assess(AISuitabilitySignals())
    assert result.rationale.strip()


def test_assessment_has_no_explanation_unless_requested():
    result = ai_suitability.assess(AISuitabilitySignals())
    assert result.explanation is None


# ---------- Unit tests: explain() never changes the decision ----------


def test_explain_only_phrases_never_reclassifies(monkeypatch):
    class _FakeResult:
        text = "Because it needs no AI at all, workflow automation is simplest."

    monkeypatch.setattr(
        "backend.ai.service.complete", lambda **kwargs: _FakeResult()
    )
    assessment = ai_suitability.assess(AISuitabilitySignals())
    prose = ai_suitability.explain(assessment)
    assert prose == _FakeResult.text
    assert assessment.recommended_pattern == "Workflow Automation"  # unchanged


# ---------- Integration tests: API endpoint ----------


@pytest.fixture
def authed_client():
    app.dependency_overrides[require_auth] = lambda: AuthenticatedUser(
        id="wp16a-test-user", email="wp16a@example.com", role="EnterpriseArchitect"
    )
    try:
        yield TestClient(app)
    finally:
        app.dependency_overrides.clear()


def test_endpoint_returns_deterministic_assessment_with_no_ai_call(authed_client):
    response = authed_client.post(
        "/api/tools/ai-suitability", json={"requires_external_knowledge_retrieval": True}
    )
    assert response.status_code == 200
    body = response.json()
    assert body["recommended_pattern"] == "RAG"


def test_endpoint_with_explain_calls_ai_service(authed_client, monkeypatch):
    class _FakeResult:
        text = "RAG fits because the task needs external knowledge."

    monkeypatch.setattr("backend.ai.service.complete", lambda **kwargs: _FakeResult())
    response = authed_client.post(
        "/api/tools/ai-suitability?explain=true",
        json={"requires_external_knowledge_retrieval": True},
    )
    assert response.status_code == 200
    body = response.json()
    explanation = body.get("explanation")
    assert explanation == _FakeResult.text


def test_endpoint_requires_auth():
    client = TestClient(app)
    response = client.post("/api/tools/ai-suitability", json={})
    assert response.status_code == 401
