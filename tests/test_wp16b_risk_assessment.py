"""WP16b (Risk Assessment Tool, ADR-006) tests.

Covers the deterministic ISO 31000-style likelihood x impact matrix
(backend/tools/risk_assessment.assess) with zero AI calls, the optional explain() step
mocked, invalid-signal handling, and the API endpoint's shape/auth/error mapping.
"""

import pytest
from fastapi.testclient import TestClient

from app import app
from backend.auth import AuthenticatedUser, require_auth
from backend.models import RiskAssessmentSignals
from backend.tools import risk_assessment

# ---------- Unit tests: deterministic matrix ----------


@pytest.mark.parametrize(
    "likelihood,impact,expected_level",
    [
        ("Almost Certain", "Severe", "Critical"),  # 5x5=25
        ("Likely", "Major", "Critical"),  # 4x4=16
        ("Possible", "Major", "High"),  # 3x4=12
        ("Likely", "Moderate", "High"),  # 4x3=12
        ("Possible", "Minor", "Medium"),  # 3x2=6
        ("Unlikely", "Negligible", "Low"),  # 2x1=2
        ("Rare", "Negligible", "Low"),  # 1x1=1
    ],
)
def test_matrix_bands_combined_score_into_expected_level(likelihood, impact, expected_level):
    result = risk_assessment.assess(RiskAssessmentSignals(likelihood=likelihood, impact=impact))
    assert result.level == expected_level


def test_boundary_score_of_exactly_15_is_critical():
    # Almost Certain (5) x Moderate (3) = 15 -- the >=15 boundary itself
    result = risk_assessment.assess(RiskAssessmentSignals(likelihood="Almost Certain", impact="Moderate"))
    assert result.level == "Critical"


def test_boundary_score_of_exactly_8_is_high():
    # Likely (4) x Minor (2) = 8 -- the >=8 boundary itself
    result = risk_assessment.assess(RiskAssessmentSignals(likelihood="Likely", impact="Minor"))
    assert result.level == "High"


def test_boundary_score_of_exactly_4_is_medium():
    # Unlikely (2) x Minor (2) = 4 -- the >=4 boundary itself
    result = risk_assessment.assess(RiskAssessmentSignals(likelihood="Unlikely", impact="Minor"))
    assert result.level == "Medium"


def test_result_carries_a_computed_rationale():
    result = risk_assessment.assess(RiskAssessmentSignals(likelihood="Rare", impact="Negligible"))
    assert "1/5" in result.rationale
    assert "1/25" in result.rationale


def test_result_has_no_explanation_unless_requested():
    result = risk_assessment.assess(RiskAssessmentSignals(likelihood="Rare", impact="Negligible"))
    assert result.explanation is None


def test_unknown_likelihood_raises_value_error():
    with pytest.raises(ValueError):
        risk_assessment.assess(RiskAssessmentSignals(likelihood="Certain-ish", impact="Minor"))


def test_unknown_impact_raises_value_error():
    with pytest.raises(ValueError):
        risk_assessment.assess(RiskAssessmentSignals(likelihood="Rare", impact="Catastrophic"))


# ---------- Unit tests: explain() never changes the decision ----------


def test_explain_only_phrases_never_recomputes(monkeypatch):
    class _FakeResult:
        text = "This is rated Low because both likelihood and impact are minimal."

    monkeypatch.setattr("backend.ai.service.complete", lambda **kwargs: _FakeResult())
    result = risk_assessment.assess(RiskAssessmentSignals(likelihood="Rare", impact="Negligible"))
    prose = risk_assessment.explain(result)
    assert prose == _FakeResult.text
    assert result.level == "Low"  # unchanged


# ---------- Integration tests: API endpoint ----------


@pytest.fixture
def authed_client():
    app.dependency_overrides[require_auth] = lambda: AuthenticatedUser(
        id="wp16b-test-user", email="wp16b@example.com", role="EnterpriseArchitect"
    )
    try:
        yield TestClient(app)
    finally:
        app.dependency_overrides.clear()


def test_endpoint_returns_deterministic_level_with_no_ai_call(authed_client):
    response = authed_client.post(
        "/api/tools/risk-assessment", json={"likelihood": "Almost Certain", "impact": "Severe"}
    )
    assert response.status_code == 200
    assert response.json()["level"] == "Critical"


def test_endpoint_rejects_unknown_signal_as_400(authed_client):
    response = authed_client.post(
        "/api/tools/risk-assessment", json={"likelihood": "Nonsense", "impact": "Minor"}
    )
    assert response.status_code == 400


def test_endpoint_with_explain_calls_ai_service(authed_client, monkeypatch):
    class _FakeResult:
        text = "This is Low risk because it is rare and negligible in impact."

    monkeypatch.setattr("backend.ai.service.complete", lambda **kwargs: _FakeResult())
    response = authed_client.post(
        "/api/tools/risk-assessment?explain=true",
        json={"likelihood": "Rare", "impact": "Negligible"},
    )
    assert response.status_code == 200
    assert response.json()["explanation"] == _FakeResult.text


def test_endpoint_requires_auth():
    client = TestClient(app)
    response = client.post("/api/tools/risk-assessment", json={})
    assert response.status_code == 401
