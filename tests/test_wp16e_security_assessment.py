"""WP16e (Security Architecture Tool, ADR-006) tests.

Covers the deterministic NIST CSF five-function checklist
(backend/tools/security_assessment.assess) with zero AI calls, the optional explain()
step mocked, the all-three-required Protect sub-check, and the API endpoint's
shape/auth. Each case is hand-verified against the actual satisfied-function count
before asserting a verdict tier, per the lesson from WP16b's arithmetic slip.
"""

import pytest
from fastapi.testclient import TestClient

from app import app
from backend.auth import AuthenticatedUser, require_auth
from backend.models import SecurityAssessmentSignals
from backend.tools import security_assessment

# ---------- Unit tests: deterministic checklist ----------


def test_all_five_functions_satisfied_is_fully_compliant():
    signals = SecurityAssessmentSignals(
        has_asset_inventory=True,
        has_authentication_and_authorization=True,
        has_encryption_at_rest_and_in_transit=True,
        has_input_validation=True,
        has_monitoring_and_logging=True,
        has_incident_response_plan=True,
        has_backup_and_recovery_plan=True,
    )
    result = security_assessment.assess(signals)
    assert result.verdict == "Fully Compliant"
    assert set(result.functions_satisfied) == {"Identify", "Protect", "Detect", "Respond", "Recover"}
    assert result.functions_unmet == []


def test_no_signals_is_non_compliant():
    result = security_assessment.assess(SecurityAssessmentSignals())
    assert result.verdict == "Non-Compliant"
    assert result.functions_satisfied == []


def test_three_single_signal_functions_is_substantially_compliant():
    # Identify + Detect + Respond satisfied (3 functions); Protect's 3 sub-signals all
    # False so Protect is unmet; Recover False too -- 3/5 total.
    signals = SecurityAssessmentSignals(
        has_asset_inventory=True,
        has_monitoring_and_logging=True,
        has_incident_response_plan=True,
    )
    result = security_assessment.assess(signals)
    assert result.verdict == "Substantially Compliant"
    assert set(result.functions_satisfied) == {"Identify", "Detect", "Respond"}


def test_single_function_is_partially_compliant():
    signals = SecurityAssessmentSignals(has_asset_inventory=True)
    result = security_assessment.assess(signals)
    assert result.verdict == "Partially Compliant"
    assert result.functions_satisfied == ["Identify"]


def test_protect_requires_all_three_sub_signals_not_just_one():
    # Two of Protect's three sub-signals true is NOT enough -- Protect must not appear
    # satisfied, and with nothing else true the overall count is 0.
    signals = SecurityAssessmentSignals(
        has_authentication_and_authorization=True,
        has_encryption_at_rest_and_in_transit=True,
        has_input_validation=False,
    )
    result = security_assessment.assess(signals)
    assert "Protect" not in result.functions_satisfied
    assert result.verdict == "Non-Compliant"


def test_result_carries_a_nonempty_rationale():
    result = security_assessment.assess(SecurityAssessmentSignals())
    assert result.rationale.strip()


def test_result_has_no_explanation_unless_requested():
    result = security_assessment.assess(SecurityAssessmentSignals())
    assert result.explanation is None


# ---------- Unit tests: explain() never changes the decision ----------


def test_explain_only_phrases_never_reclassifies(monkeypatch):
    class _FakeResult:
        text = "This is Non-Compliant because no NIST CSF functions are covered."

    monkeypatch.setattr("backend.ai.service.complete", lambda **kwargs: _FakeResult())
    result = security_assessment.assess(SecurityAssessmentSignals())
    prose = security_assessment.explain(result)
    assert prose == _FakeResult.text
    assert result.verdict == "Non-Compliant"  # unchanged


# ---------- Integration tests: API endpoint ----------


@pytest.fixture
def authed_client():
    app.dependency_overrides[require_auth] = lambda: AuthenticatedUser(
        id="wp16e-test-user", email="wp16e@example.com", role="EnterpriseArchitect"
    )
    try:
        yield TestClient(app)
    finally:
        app.dependency_overrides.clear()


def test_endpoint_returns_deterministic_verdict_with_no_ai_call(authed_client):
    response = authed_client.post("/api/tools/security-assessment", json={"has_asset_inventory": True})
    assert response.status_code == 200
    assert response.json()["verdict"] == "Partially Compliant"


def test_endpoint_with_explain_calls_ai_service(authed_client, monkeypatch):
    class _FakeResult:
        text = "This is Partially Compliant because only asset inventory is in place."

    monkeypatch.setattr("backend.ai.service.complete", lambda **kwargs: _FakeResult())
    response = authed_client.post(
        "/api/tools/security-assessment?explain=true", json={"has_asset_inventory": True}
    )
    assert response.status_code == 200
    assert response.json()["explanation"] == _FakeResult.text


def test_endpoint_requires_auth():
    client = TestClient(app)
    response = client.post("/api/tools/security-assessment", json={})
    assert response.status_code == 401
