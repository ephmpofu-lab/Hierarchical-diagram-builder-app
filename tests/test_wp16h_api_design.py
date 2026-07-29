"""WP16h (API Design Tool, ADR-006) tests.

Covers the deterministic REST convention checks (backend/tools/api_design.assess) with
zero AI calls, the optional explain() step mocked, and the API endpoint's shape/auth.
The path-segment-splitting regex was verified empirically against real examples before
these tests were written (see the commit message), continuing the post-WP16b discipline
of confirming mechanics before asserting on them.
"""

import pytest
from fastapi.testclient import TestClient

from app import app
from backend.auth import AuthenticatedUser, require_auth
from backend.models import APIDesignSignals
from backend.tools import api_design

# ---------- Unit tests: deterministic REST convention checks ----------


def test_clean_versioned_noun_resource_path_follows_conventions():
    signals = APIDesignSignals(
        method="GET",
        path="/api/v1/projects/{id}/nodes",
        has_request_body=False,
        has_version_segment=True,
    )
    result = api_design.assess(signals)
    assert result.verdict == "Follows REST Conventions"
    assert result.findings == []


def test_verb_in_path_is_flagged_and_needs_revision():
    signals = APIDesignSignals(
        method="GET", path="/api/getUsers", has_request_body=False, has_version_segment=True
    )
    result = api_design.assess(signals)
    assert result.verdict == "Needs Revision"
    assert any("verb-like segment" in f for f in result.findings)


def test_get_with_request_body_is_flagged_and_needs_revision():
    signals = APIDesignSignals(
        method="GET", path="/api/v1/projects", has_request_body=True, has_version_segment=True
    )
    result = api_design.assess(signals)
    assert result.verdict == "Needs Revision"
    assert any("conventionally carry no request body" in f for f in result.findings)


def test_delete_with_request_body_is_also_flagged():
    signals = APIDesignSignals(
        method="DELETE", path="/api/v1/projects/{id}", has_request_body=True, has_version_segment=True
    )
    result = api_design.assess(signals)
    assert result.verdict == "Needs Revision"
    assert any("conventionally carry no request body" in f for f in result.findings)


def test_post_with_request_body_is_not_flagged_for_body():
    signals = APIDesignSignals(
        method="POST", path="/api/v1/projects", has_request_body=True, has_version_segment=True
    )
    result = api_design.assess(signals)
    assert result.verdict == "Follows REST Conventions"


def test_missing_version_segment_is_informational_only_not_blocking():
    signals = APIDesignSignals(
        method="POST", path="/api/projects", has_request_body=True, has_version_segment=False
    )
    result = api_design.assess(signals)
    # A finding is recorded, but it does not make the verdict Needs Revision on its own.
    assert any("version segment" in f for f in result.findings)
    assert result.verdict == "Follows REST Conventions"


def test_result_carries_a_nonempty_rationale():
    result = api_design.assess(APIDesignSignals(method="GET", path="/api/v1/projects"))
    assert result.rationale.strip()


def test_result_has_no_explanation_unless_requested():
    result = api_design.assess(APIDesignSignals(method="GET", path="/api/v1/projects"))
    assert result.explanation is None


# ---------- Unit tests: explain() never changes the findings ----------


def test_explain_only_phrases_never_changes_findings(monkeypatch):
    class _FakeResult:
        text = "This follows REST conventions with no issues found."

    monkeypatch.setattr("backend.ai.service.complete", lambda **kwargs: _FakeResult())
    signals = APIDesignSignals(
        method="GET",
        path="/api/v1/projects/{id}/nodes",
        has_request_body=False,
        has_version_segment=True,
    )
    result = api_design.assess(signals)
    prose = api_design.explain(result)
    assert prose == _FakeResult.text
    assert result.verdict == "Follows REST Conventions"  # unchanged
    assert result.findings == []  # unchanged


# ---------- Integration tests: API endpoint ----------


@pytest.fixture
def authed_client():
    app.dependency_overrides[require_auth] = lambda: AuthenticatedUser(
        id="wp16h-test-user", email="wp16h@example.com", role="EnterpriseArchitect"
    )
    try:
        yield TestClient(app)
    finally:
        app.dependency_overrides.clear()


def test_endpoint_returns_deterministic_verdict_with_no_ai_call(authed_client):
    response = authed_client.post(
        "/api/tools/api-design",
        json={"method": "GET", "path": "/api/getUsers", "has_version_segment": True},
    )
    assert response.status_code == 200
    assert response.json()["verdict"] == "Needs Revision"


def test_endpoint_with_explain_calls_ai_service(authed_client, monkeypatch):
    class _FakeResult:
        text = "This needs revision because the path uses a verb instead of a noun."

    monkeypatch.setattr("backend.ai.service.complete", lambda **kwargs: _FakeResult())
    response = authed_client.post(
        "/api/tools/api-design?explain=true",
        json={"method": "GET", "path": "/api/getUsers", "has_version_segment": True},
    )
    assert response.status_code == 200
    assert response.json()["explanation"] == _FakeResult.text


def test_endpoint_requires_auth():
    client = TestClient(app)
    response = client.post("/api/tools/api-design", json={"method": "GET", "path": "/x"})
    assert response.status_code == 401
