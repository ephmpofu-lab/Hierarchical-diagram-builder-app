"""WP16i (Test Design Tool, ADR-006) tests.

Covers the deterministic ISTQB test-level mapping (backend/tools/test_design.assess) with
zero AI calls, the optional explain() step mocked, and the API endpoint's shape/auth.
"""

import pytest
from fastapi.testclient import TestClient

from app import app
from backend.auth import AuthenticatedUser, require_auth
from backend.models import TestDesignSignals
from backend.tools import test_design

# ---------- Unit tests: deterministic level mapping ----------


def test_all_signals_recommend_all_four_levels():
    signals = TestDesignSignals(
        is_standalone_component=True,
        has_external_dependencies=True,
        represents_end_to_end_behavior=True,
        has_business_acceptance_criteria=True,
    )
    result = test_design.assess(signals)
    assert result.recommended_levels == [
        "Component Testing",
        "Integration Testing",
        "System Testing",
        "Acceptance Testing",
    ]


def test_no_signals_recommends_nothing():
    result = test_design.assess(TestDesignSignals())
    assert result.recommended_levels == []


def test_standalone_component_recommends_component_testing_only():
    result = test_design.assess(TestDesignSignals(is_standalone_component=True))
    assert result.recommended_levels == ["Component Testing"]


def test_external_dependencies_recommends_integration_testing_only():
    result = test_design.assess(TestDesignSignals(has_external_dependencies=True))
    assert result.recommended_levels == ["Integration Testing"]


def test_end_to_end_behavior_recommends_system_testing_only():
    result = test_design.assess(TestDesignSignals(represents_end_to_end_behavior=True))
    assert result.recommended_levels == ["System Testing"]


def test_acceptance_criteria_recommends_acceptance_testing_only():
    result = test_design.assess(TestDesignSignals(has_business_acceptance_criteria=True))
    assert result.recommended_levels == ["Acceptance Testing"]


def test_mixed_signals_preserve_istqb_level_order():
    signals = TestDesignSignals(is_standalone_component=True, has_business_acceptance_criteria=True)
    result = test_design.assess(signals)
    assert result.recommended_levels == ["Component Testing", "Acceptance Testing"]


def test_result_carries_a_nonempty_rationale():
    result = test_design.assess(TestDesignSignals())
    assert result.rationale.strip()


def test_result_has_no_explanation_unless_requested():
    result = test_design.assess(TestDesignSignals())
    assert result.explanation is None


# ---------- Unit tests: explain() never changes the recommendation ----------


def test_explain_only_phrases_never_changes_levels(monkeypatch):
    class _FakeResult:
        text = "Component testing is recommended because it's a standalone unit."

    monkeypatch.setattr("backend.ai.service.complete", lambda **kwargs: _FakeResult())
    result = test_design.assess(TestDesignSignals(is_standalone_component=True))
    prose = test_design.explain(result)
    assert prose == _FakeResult.text
    assert result.recommended_levels == ["Component Testing"]  # unchanged


# ---------- Integration tests: API endpoint ----------


@pytest.fixture
def authed_client():
    app.dependency_overrides[require_auth] = lambda: AuthenticatedUser(
        id="wp16i-test-user", email="wp16i@example.com", role="EnterpriseArchitect"
    )
    try:
        yield TestClient(app)
    finally:
        app.dependency_overrides.clear()


def test_endpoint_returns_deterministic_recommendation_with_no_ai_call(authed_client):
    response = authed_client.post(
        "/api/tools/test-design", json={"has_external_dependencies": True}
    )
    assert response.status_code == 200
    assert response.json()["recommended_levels"] == ["Integration Testing"]


def test_endpoint_with_explain_calls_ai_service(authed_client, monkeypatch):
    class _FakeResult:
        text = "Integration testing is recommended because it has external dependencies."

    monkeypatch.setattr("backend.ai.service.complete", lambda **kwargs: _FakeResult())
    response = authed_client.post(
        "/api/tools/test-design?explain=true", json={"has_external_dependencies": True}
    )
    assert response.status_code == 200
    assert response.json()["explanation"] == _FakeResult.text


def test_endpoint_requires_auth():
    client = TestClient(app)
    response = client.post("/api/tools/test-design", json={})
    assert response.status_code == 401
