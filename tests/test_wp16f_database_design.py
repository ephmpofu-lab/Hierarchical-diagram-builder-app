"""WP16f (Database Design Tool, ADR-006) tests.

Covers the deterministic Codd normal-form check (backend/tools/database_design.assess)
with zero AI calls, the optional explain() step mocked, and the API endpoint's
shape/auth. Each case is hand-verified against the nested 1NF/2NF/3NF logic before
asserting, per the discipline established after WP16b's arithmetic slip.
"""

import pytest
from fastapi.testclient import TestClient

from app import app
from backend.auth import AuthenticatedUser, require_auth
from backend.models import DatabaseDesignSignals
from backend.tools import database_design

# ---------- Unit tests: deterministic normal-form checks ----------


def test_clean_entity_with_simple_key_is_3nf():
    signals = DatabaseDesignSignals(has_primary_key=True)
    result = database_design.assess(signals)
    assert result.normal_form == "3NF"
    assert result.findings == []


def test_missing_primary_key_is_not_1nf():
    signals = DatabaseDesignSignals(has_primary_key=False)
    result = database_design.assess(signals)
    assert result.normal_form == "Not 1NF"
    assert any("primary key" in f for f in result.findings)


def test_repeating_groups_is_not_1nf_even_with_a_primary_key():
    signals = DatabaseDesignSignals(has_primary_key=True, has_repeating_groups=True)
    result = database_design.assess(signals)
    assert result.normal_form == "Not 1NF"
    assert any("Repeating groups" in f for f in result.findings)


def test_composite_key_with_partial_dependency_is_1nf_only():
    signals = DatabaseDesignSignals(
        has_primary_key=True, has_composite_key=True, has_partial_key_dependency=True
    )
    result = database_design.assess(signals)
    assert result.normal_form == "1NF"
    assert any("part of the composite primary key" in f for f in result.findings)


def test_composite_key_without_partial_dependency_can_still_reach_3nf():
    signals = DatabaseDesignSignals(
        has_primary_key=True, has_composite_key=True, has_partial_key_dependency=False
    )
    result = database_design.assess(signals)
    assert result.normal_form == "3NF"


def test_transitive_dependency_is_2nf_only():
    signals = DatabaseDesignSignals(has_primary_key=True, has_transitive_dependency=True)
    result = database_design.assess(signals)
    assert result.normal_form == "2NF"
    assert any("transitive dependency" in f.lower() for f in result.findings)


def test_result_carries_a_nonempty_rationale():
    result = database_design.assess(DatabaseDesignSignals(has_primary_key=True))
    assert result.rationale.strip()


def test_result_has_no_explanation_unless_requested():
    result = database_design.assess(DatabaseDesignSignals(has_primary_key=True))
    assert result.explanation is None


# ---------- Unit tests: explain() never changes the decision ----------


def test_explain_only_phrases_never_reclassifies(monkeypatch):
    class _FakeResult:
        text = "This entity is in 3NF because it has a clean key and no dependency issues."

    monkeypatch.setattr("backend.ai.service.complete", lambda **kwargs: _FakeResult())
    result = database_design.assess(DatabaseDesignSignals(has_primary_key=True))
    prose = database_design.explain(result)
    assert prose == _FakeResult.text
    assert result.normal_form == "3NF"  # unchanged


# ---------- Integration tests: API endpoint ----------


@pytest.fixture
def authed_client():
    app.dependency_overrides[require_auth] = lambda: AuthenticatedUser(
        id="wp16f-test-user", email="wp16f@example.com", role="EnterpriseArchitect"
    )
    try:
        yield TestClient(app)
    finally:
        app.dependency_overrides.clear()


def test_endpoint_returns_deterministic_result_with_no_ai_call(authed_client):
    response = authed_client.post("/api/tools/database-design", json={"has_primary_key": True})
    assert response.status_code == 200
    assert response.json()["normal_form"] == "3NF"


def test_endpoint_with_explain_calls_ai_service(authed_client, monkeypatch):
    class _FakeResult:
        text = "This is 3NF because the key structure and dependencies are all clean."

    monkeypatch.setattr("backend.ai.service.complete", lambda **kwargs: _FakeResult())
    response = authed_client.post(
        "/api/tools/database-design?explain=true", json={"has_primary_key": True}
    )
    assert response.status_code == 200
    assert response.json()["explanation"] == _FakeResult.text


def test_endpoint_requires_auth():
    client = TestClient(app)
    response = client.post("/api/tools/database-design", json={})
    assert response.status_code == 401
