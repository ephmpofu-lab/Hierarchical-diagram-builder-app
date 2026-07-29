"""WP16c (Governance Assessment Tool, ADR-006) tests.

Covers the deterministic ISO 38500 six-principle assessment
(backend/tools/governance_assessment.assess) with zero AI calls, the optional explain()
step mocked, the Conformance hard-gate precedence, and the API endpoint's shape/auth.
"""

import pytest
from fastapi.testclient import TestClient

from app import app
from backend.auth import AuthenticatedUser, require_auth
from backend.models import GovernanceAssessmentSignals
from backend.tools import governance_assessment

# ---------- Unit tests: deterministic assessment ----------


def test_all_principles_satisfied_is_fully_conformant():
    signals = GovernanceAssessmentSignals(
        has_assigned_owner=True,
        aligns_with_documented_strategy=True,
        acquisition_is_justified=True,
        has_performance_monitoring=True,
        has_no_unresolved_critical_findings=True,
        considers_human_impact=True,
    )
    result = governance_assessment.assess(signals)
    assert result.verdict == "Fully Conformant"
    assert set(result.principles_satisfied) == {
        "Conformance",
        "Responsibility",
        "Strategy",
        "Acquisition",
        "Performance",
        "Human Behaviour",
    }
    assert result.principles_unmet == []


def test_three_of_five_other_principles_is_substantially_conformant():
    signals = GovernanceAssessmentSignals(
        has_assigned_owner=True,
        aligns_with_documented_strategy=True,
        acquisition_is_justified=True,
        has_performance_monitoring=False,
        has_no_unresolved_critical_findings=True,
        considers_human_impact=False,
    )
    result = governance_assessment.assess(signals)
    assert result.verdict == "Substantially Conformant"


def test_two_of_five_other_principles_is_partially_conformant():
    signals = GovernanceAssessmentSignals(
        has_assigned_owner=True,
        aligns_with_documented_strategy=True,
        acquisition_is_justified=False,
        has_performance_monitoring=False,
        has_no_unresolved_critical_findings=True,
        considers_human_impact=False,
    )
    result = governance_assessment.assess(signals)
    assert result.verdict == "Partially Conformant"


def test_no_other_principles_defaults_to_partially_conformant_not_worse():
    signals = GovernanceAssessmentSignals(has_no_unresolved_critical_findings=True)
    result = governance_assessment.assess(signals)
    assert result.verdict == "Partially Conformant"


def test_unresolved_critical_findings_is_a_hard_gate_regardless_of_others():
    signals = GovernanceAssessmentSignals(
        has_assigned_owner=True,
        aligns_with_documented_strategy=True,
        acquisition_is_justified=True,
        has_performance_monitoring=True,
        has_no_unresolved_critical_findings=False,
        considers_human_impact=True,
    )
    result = governance_assessment.assess(signals)
    assert result.verdict == "Non-Conformant"


def test_non_conformant_still_reports_individually_satisfied_principles():
    signals = GovernanceAssessmentSignals(
        has_assigned_owner=True,
        has_no_unresolved_critical_findings=False,
    )
    result = governance_assessment.assess(signals)
    assert result.verdict == "Non-Conformant"
    assert "Responsibility" in result.principles_satisfied
    assert "Conformance" in result.principles_unmet


def test_result_carries_a_nonempty_rationale():
    result = governance_assessment.assess(GovernanceAssessmentSignals())
    assert result.rationale.strip()


def test_result_has_no_explanation_unless_requested():
    result = governance_assessment.assess(GovernanceAssessmentSignals())
    assert result.explanation is None


# ---------- Unit tests: explain() never changes the decision ----------


def test_explain_only_phrases_never_reclassifies(monkeypatch):
    class _FakeResult:
        text = "This is Fully Conformant because every principle is satisfied."

    monkeypatch.setattr("backend.ai.service.complete", lambda **kwargs: _FakeResult())
    signals = GovernanceAssessmentSignals(
        has_assigned_owner=True,
        aligns_with_documented_strategy=True,
        acquisition_is_justified=True,
        has_performance_monitoring=True,
        has_no_unresolved_critical_findings=True,
        considers_human_impact=True,
    )
    result = governance_assessment.assess(signals)
    prose = governance_assessment.explain(result)
    assert prose == _FakeResult.text
    assert result.verdict == "Fully Conformant"  # unchanged


# ---------- Integration tests: API endpoint ----------


@pytest.fixture
def authed_client():
    app.dependency_overrides[require_auth] = lambda: AuthenticatedUser(
        id="wp16c-test-user", email="wp16c@example.com", role="EnterpriseArchitect"
    )
    try:
        yield TestClient(app)
    finally:
        app.dependency_overrides.clear()


def test_endpoint_returns_deterministic_verdict_with_no_ai_call(authed_client):
    response = authed_client.post(
        "/api/tools/governance-assessment", json={"has_no_unresolved_critical_findings": False}
    )
    assert response.status_code == 200
    assert response.json()["verdict"] == "Non-Conformant"


def test_endpoint_with_explain_calls_ai_service(authed_client, monkeypatch):
    class _FakeResult:
        text = "No owner is assigned yet, among other gaps."

    monkeypatch.setattr("backend.ai.service.complete", lambda **kwargs: _FakeResult())
    response = authed_client.post(
        "/api/tools/governance-assessment?explain=true",
        json={"has_no_unresolved_critical_findings": True},
    )
    assert response.status_code == 200
    assert response.json()["explanation"] == _FakeResult.text


def test_endpoint_requires_auth():
    client = TestClient(app)
    response = client.post("/api/tools/governance-assessment", json={})
    assert response.status_code == 401
