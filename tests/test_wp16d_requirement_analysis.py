"""WP16d (Requirement Analysis Tool, ADR-006) tests.

Covers the deterministic INCOSE/IEEE 830 weak-word and completeness checks
(backend/tools/requirement_analysis.assess) with zero AI calls, the optional explain()
step mocked, and the API endpoint's shape/auth. Each test isolates one finding category by
keeping every other signal clean, rather than asserting exact finding counts, so the
assertions stay robust if another check is added later.
"""

import pytest
from fastapi.testclient import TestClient

from app import app
from backend.auth import AuthenticatedUser, require_auth
from backend.models import RequirementQualitySignals
from backend.tools import requirement_analysis

_CLEAN = "The system shall authenticate users via OAuth2 within 500 milliseconds."

# ---------- Unit tests: deterministic checks ----------


def test_clean_requirement_with_criteria_and_owner_is_well_formed():
    signals = RequirementQualitySignals(
        description=_CLEAN, has_acceptance_criteria=True, has_assigned_owner=True
    )
    result = requirement_analysis.assess(signals)
    assert result.verdict == "Well-Formed"
    assert result.findings == []


def test_weak_ambiguous_words_are_flagged():
    signals = RequirementQualitySignals(
        description="The system should provide a user-friendly and efficient interface, etc.",
        has_acceptance_criteria=True,
        has_assigned_owner=True,
    )
    result = requirement_analysis.assess(signals)
    assert result.verdict == "Needs Revision"
    assert any("Ambiguous language" in f for f in result.findings)


def test_vague_quantifier_is_flagged():
    signals = RequirementQualitySignals(
        description="The system shall support several concurrent users.",
        has_acceptance_criteria=True,
        has_assigned_owner=True,
    )
    result = requirement_analysis.assess(signals)
    assert any("Vague quantifier" in f for f in result.findings)


def test_compound_requirement_is_flagged():
    signals = RequirementQualitySignals(
        description="The system shall log in users and validate passwords and send notifications.",
        has_acceptance_criteria=True,
        has_assigned_owner=True,
    )
    result = requirement_analysis.assess(signals)
    assert any("compound requirement" in f for f in result.findings)


def test_missing_obligation_modal_is_flagged():
    signals = RequirementQualitySignals(
        description="The system provides real-time notifications to users.",
        has_acceptance_criteria=True,
        has_assigned_owner=True,
    )
    result = requirement_analysis.assess(signals)
    assert any("obligation modal" in f for f in result.findings)


def test_missing_acceptance_criteria_is_flagged():
    signals = RequirementQualitySignals(
        description=_CLEAN, has_acceptance_criteria=False, has_assigned_owner=True
    )
    result = requirement_analysis.assess(signals)
    assert any("acceptance criteria" in f for f in result.findings)


def test_missing_owner_is_flagged():
    signals = RequirementQualitySignals(
        description=_CLEAN, has_acceptance_criteria=True, has_assigned_owner=False
    )
    result = requirement_analysis.assess(signals)
    assert any("owner" in f for f in result.findings)


def test_result_has_no_explanation_unless_requested():
    signals = RequirementQualitySignals(
        description=_CLEAN, has_acceptance_criteria=True, has_assigned_owner=True
    )
    result = requirement_analysis.assess(signals)
    assert result.explanation is None


# ---------- Unit tests: explain() never changes the findings ----------


def test_explain_only_phrases_never_changes_findings(monkeypatch):
    class _FakeResult:
        text = "This requirement is well-formed and needs no changes."

    monkeypatch.setattr("backend.ai.service.complete", lambda **kwargs: _FakeResult())
    signals = RequirementQualitySignals(
        description=_CLEAN, has_acceptance_criteria=True, has_assigned_owner=True
    )
    result = requirement_analysis.assess(signals)
    prose = requirement_analysis.explain(result)
    assert prose == _FakeResult.text
    assert result.verdict == "Well-Formed"  # unchanged
    assert result.findings == []  # unchanged


# ---------- Integration tests: API endpoint ----------


@pytest.fixture
def authed_client():
    app.dependency_overrides[require_auth] = lambda: AuthenticatedUser(
        id="wp16d-test-user", email="wp16d@example.com", role="EnterpriseArchitect"
    )
    try:
        yield TestClient(app)
    finally:
        app.dependency_overrides.clear()


def test_endpoint_returns_deterministic_verdict_with_no_ai_call(authed_client):
    response = authed_client.post(
        "/api/tools/requirement-analysis",
        json={
            "description": _CLEAN,
            "has_acceptance_criteria": True,
            "has_assigned_owner": True,
        },
    )
    assert response.status_code == 200
    assert response.json()["verdict"] == "Well-Formed"


def test_endpoint_with_explain_calls_ai_service(authed_client, monkeypatch):
    class _FakeResult:
        text = "This is well-formed because it has a clear obligation and no ambiguity."

    monkeypatch.setattr("backend.ai.service.complete", lambda **kwargs: _FakeResult())
    response = authed_client.post(
        "/api/tools/requirement-analysis?explain=true",
        json={
            "description": _CLEAN,
            "has_acceptance_criteria": True,
            "has_assigned_owner": True,
        },
    )
    assert response.status_code == 200
    assert response.json()["explanation"] == _FakeResult.text


def test_endpoint_requires_auth():
    client = TestClient(app)
    response = client.post("/api/tools/requirement-analysis", json={"description": "x"})
    assert response.status_code == 401
