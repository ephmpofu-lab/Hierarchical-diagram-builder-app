"""WP16j (Deployment Architecture Tool, ADR-006) tests.

Covers the deterministic 12-Factor App checklist
(backend/tools/deployment_architecture.assess) with zero AI calls, the optional
explain() step mocked, and the API endpoint's shape/auth.
"""

import pytest
from fastapi.testclient import TestClient

from app import app
from backend.auth import AuthenticatedUser, require_auth
from backend.models import DeploymentReadinessSignals
from backend.tools import deployment_architecture

# ---------- Unit tests: deterministic checklist ----------


def test_all_five_factors_satisfied_is_fully_ready():
    signals = DeploymentReadinessSignals(
        has_externalized_config=True,
        has_pinned_dependencies=True,
        is_stateless=True,
        has_separate_build_release_run=True,
        logs_to_stdout=True,
    )
    result = deployment_architecture.assess(signals)
    assert result.verdict == "Fully Ready"
    assert set(result.factors_satisfied) == {
        "Config", "Dependencies", "Processes", "Build, release, run", "Logs",
    }
    assert result.factors_unmet == []


def test_no_signals_is_not_ready():
    result = deployment_architecture.assess(DeploymentReadinessSignals())
    assert result.verdict == "Not Ready"
    assert result.factors_satisfied == []


def test_three_of_five_is_substantially_ready():
    signals = DeploymentReadinessSignals(
        has_externalized_config=True,
        has_pinned_dependencies=True,
        is_stateless=True,
    )
    result = deployment_architecture.assess(signals)
    assert result.verdict == "Substantially Ready"


def test_one_of_five_is_partially_ready():
    signals = DeploymentReadinessSignals(has_externalized_config=True)
    result = deployment_architecture.assess(signals)
    assert result.verdict == "Partially Ready"
    assert result.factors_satisfied == ["Config"]


def test_result_carries_a_nonempty_rationale():
    result = deployment_architecture.assess(DeploymentReadinessSignals())
    assert result.rationale.strip()


def test_result_has_no_explanation_unless_requested():
    result = deployment_architecture.assess(DeploymentReadinessSignals())
    assert result.explanation is None


# ---------- Unit tests: explain() never changes the decision ----------


def test_explain_only_phrases_never_reclassifies(monkeypatch):
    class _FakeResult:
        text = "This is Not Ready because none of the 12-Factor criteria are satisfied."

    monkeypatch.setattr("backend.ai.service.complete", lambda **kwargs: _FakeResult())
    result = deployment_architecture.assess(DeploymentReadinessSignals())
    prose = deployment_architecture.explain(result)
    assert prose == _FakeResult.text
    assert result.verdict == "Not Ready"  # unchanged


# ---------- Integration tests: API endpoint ----------


@pytest.fixture
def authed_client():
    app.dependency_overrides[require_auth] = lambda: AuthenticatedUser(
        id="wp16j-test-user", email="wp16j@example.com", role="EnterpriseArchitect"
    )
    try:
        yield TestClient(app)
    finally:
        app.dependency_overrides.clear()


def test_endpoint_returns_deterministic_verdict_with_no_ai_call(authed_client):
    response = authed_client.post(
        "/api/tools/deployment-architecture", json={"has_externalized_config": True}
    )
    assert response.status_code == 200
    assert response.json()["verdict"] == "Partially Ready"


def test_endpoint_with_explain_calls_ai_service(authed_client, monkeypatch):
    class _FakeResult:
        text = "This is Partially Ready because only config is externalized."

    monkeypatch.setattr("backend.ai.service.complete", lambda **kwargs: _FakeResult())
    response = authed_client.post(
        "/api/tools/deployment-architecture?explain=true",
        json={"has_externalized_config": True},
    )
    assert response.status_code == 200
    assert response.json()["explanation"] == _FakeResult.text


def test_endpoint_requires_auth():
    client = TestClient(app)
    response = client.post("/api/tools/deployment-architecture", json={})
    assert response.status_code == 401
