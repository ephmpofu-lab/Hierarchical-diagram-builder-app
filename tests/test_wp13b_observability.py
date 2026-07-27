"""WP13b (Observability, Phase 11 section 13) tests.

Covers backend/observability/metrics.py (the metrics_events table + aggregation) and the
two chokepoints it's wired into -- backend/ai/service.py's complete() and
backend/agents/orchestrator.py's Orchestrator methods -- plus the read-only summary
endpoint. AI calls and Orchestrator internals are mocked throughout (never spend real
money on every test run, matching every prior WP's convention); metrics rows use a
throwaway __WP13B_TEST__ subject prefix, cleaned up via try/finally.
"""

import uuid

import pytest
from fastapi.testclient import TestClient

from app import app
from backend.auth import AuthenticatedUser, require_auth
from backend.db.connection import get_pool
from backend.observability import metrics
from backend.models import GovernanceFinding, GovernanceReview, ReasoningResult, ReasoningStageLog

TEST_PREFIX = "__WP13B_TEST__"


def _delete_test_events():
    with get_pool().connection() as conn:
        conn.execute("delete from metrics_events where subject like %s", (f"{TEST_PREFIX}%",))


@pytest.fixture
def cleanup_events():
    yield
    _delete_test_events()


# ---------- Unit tests: record_event / helpers / summarize ----------


def test_record_event_persists_and_is_queryable(cleanup_events):
    subject = f"{TEST_PREFIX}model"
    metrics.record_event("ai_call", subject, True, duration_ms=120, retries=1)
    with get_pool().connection() as conn:
        row = conn.execute(
            "select event_type, subject, success, duration_ms, retries from metrics_events where subject = %s",
            (subject,),
        ).fetchone()
    assert row == ("ai_call", subject, True, 120, 1)


def test_record_ai_call_and_record_agent_invocation_helpers(cleanup_events):
    model = f"{TEST_PREFIX}gpt"
    agent = f"{TEST_PREFIX}Agent"
    metrics.record_ai_call(model, True, 200, retries=2)
    metrics.record_agent_invocation(agent, False, error_type="ReasoningStageError")
    with get_pool().connection() as conn:
        ai_row = conn.execute(
            "select event_type, retries from metrics_events where subject = %s", (model,)
        ).fetchone()
        agent_row = conn.execute(
            "select event_type, success, error_type from metrics_events where subject = %s", (agent,)
        ).fetchone()
    assert ai_row == ("ai_call", 2)
    assert agent_row == ("agent_invocation", False, "ReasoningStageError")


def test_summarize_computes_success_rate_and_averages(cleanup_events):
    subject = f"{TEST_PREFIX}summarize_model"
    metrics.record_ai_call(subject, True, 100, retries=0)
    metrics.record_ai_call(subject, True, 300, retries=2)
    metrics.record_ai_call(subject, False, 200, retries=0, error_type="AITransientError")

    rows = metrics.summarize(hours=1)
    row = next(r for r in rows if r["subject"] == subject)
    assert row["event_type"] == "ai_call"
    assert row["total"] == 3
    assert row["successes"] == 2
    assert row["success_rate"] == pytest.approx(2 / 3, rel=1e-3)
    assert row["avg_duration_ms"] == pytest.approx(200.0)
    assert row["avg_retries"] == pytest.approx(0.67, abs=0.01)  # summarize() rounds to 2dp for API readability


def test_summarize_excludes_events_outside_the_window(cleanup_events):
    subject = f"{TEST_PREFIX}old_event"
    with get_pool().connection() as conn:
        conn.execute(
            "insert into metrics_events (id, event_type, subject, success, created_at) "
            "values (%s, 'ai_call', %s, true, now() - interval '48 hours')",
            (str(uuid.uuid4()), subject),
        )
    rows = metrics.summarize(hours=1)
    assert all(r["subject"] != subject for r in rows)


# ---------- Unit tests: backend.ai.service.complete() wiring ----------


def test_ai_service_complete_records_success_metric(monkeypatch, cleanup_events):
    from backend.ai import service as ai_service
    from backend.ai.provider import AICompletionResult

    monkeypatch.setattr(ai_service, "AI_MODEL", f"{TEST_PREFIX}model")
    fake_provider = type(
        "FakeProvider", (), {"complete": lambda self, **kw: AICompletionResult(text="ok", model="x", input_tokens=1, output_tokens=1, retries=3)}
    )()
    monkeypatch.setattr(ai_service, "_get_provider", lambda: fake_provider)

    ai_service.complete(system="s", prompt="p")

    with get_pool().connection() as conn:
        row = conn.execute(
            "select success, retries from metrics_events where subject = %s", (f"{TEST_PREFIX}model",)
        ).fetchone()
    assert row == (True, 3)


def test_ai_service_complete_records_failure_metric_and_reraises(monkeypatch, cleanup_events):
    from backend.ai import service as ai_service
    from backend.ai.provider import AITransientError

    monkeypatch.setattr(ai_service, "AI_MODEL", f"{TEST_PREFIX}failmodel")

    def _raise(**kw):
        raise AITransientError("boom")

    fake_provider = type("FakeProvider", (), {"complete": lambda self, **kw: _raise(**kw)})()
    monkeypatch.setattr(ai_service, "_get_provider", lambda: fake_provider)

    with pytest.raises(AITransientError):
        ai_service.complete(system="s", prompt="p")

    with get_pool().connection() as conn:
        row = conn.execute(
            "select success, error_type from metrics_events where subject = %s", (f"{TEST_PREFIX}failmodel",)
        ).fetchone()
    assert row == (False, "AITransientError")


# ---------- Unit tests: Orchestrator wiring ----------


def test_run_pipeline_records_one_invocation_per_stage(monkeypatch, cleanup_events):
    from backend.agents.orchestrator import Orchestrator

    canned = ReasoningResult(
        objective="test",
        domains=["Business"],
        stages=[ReasoningStageLog(stage="business_analysis", summary="s1")],
        confidence_tier="High",
        requires_human_review=False,
    )
    monkeypatch.setattr("backend.agents.orchestrator._run_reasoning_pipeline", lambda objective: canned)
    monkeypatch.setattr(
        "backend.agents.orchestrator.record_agent_invocation",
        lambda agent_name, success, **kw: metrics.record_agent_invocation(f"{TEST_PREFIX}{agent_name}", success, **kw),
    )

    Orchestrator().run_pipeline("test")

    with get_pool().connection() as conn:
        row = conn.execute(
            "select success from metrics_events where subject = %s",
            (f"{TEST_PREFIX}Business Architecture Agent",),
        ).fetchone()
    assert row == (True,)


def test_run_pipeline_records_failure_on_exception(monkeypatch, cleanup_events):
    from backend.agents.orchestrator import Orchestrator
    from backend.intelligence.stages import ReasoningStageError

    def _raise(objective):
        raise ReasoningStageError("boom")

    monkeypatch.setattr("backend.agents.orchestrator._run_reasoning_pipeline", _raise)
    monkeypatch.setattr(
        "backend.agents.orchestrator.record_agent_invocation",
        lambda agent_name, success, **kw: metrics.record_agent_invocation(f"{TEST_PREFIX}{agent_name}", success, **kw),
    )

    with pytest.raises(ReasoningStageError):
        Orchestrator().run_pipeline("test")

    with get_pool().connection() as conn:
        row = conn.execute(
            "select success, error_type from metrics_events where subject = %s",
            (f"{TEST_PREFIX}Orchestrator",),
        ).fetchone()
    assert row == (False, "ReasoningStageError")


def test_review_proposal_records_one_invocation_per_distinct_agent(monkeypatch, cleanup_events):
    from backend.agents.orchestrator import Orchestrator

    canned_review = GovernanceReview(
        outcome="rejected",
        findings=[
            GovernanceFinding(category="structural", severity="Critical", message="dup"),
            GovernanceFinding(category="policy", severity="Critical", message="violation"),
        ],
    )
    monkeypatch.setattr("backend.agents.orchestrator.run_decision_workflow", lambda result: canned_review)
    monkeypatch.setattr(
        "backend.agents.orchestrator.record_agent_invocation",
        lambda agent_name, success, **kw: metrics.record_agent_invocation(f"{TEST_PREFIX}{agent_name}", success, **kw),
    )

    result = ReasoningResult(objective="test", domains=["Business"], confidence_tier="High", requires_human_review=False)
    Orchestrator().review_proposal(result)

    with get_pool().connection() as conn:
        rows = conn.execute(
            "select subject from metrics_events where subject like %s", (f"{TEST_PREFIX}%",)
        ).fetchall()
    subjects = {r[0] for r in rows}
    assert f"{TEST_PREFIX}Validation Agent" in subjects
    assert f"{TEST_PREFIX}Governance Agent" in subjects


# ---------- Integration tests: GET /api/observability/summary ----------


@pytest.fixture
def authed_client():
    app.dependency_overrides[require_auth] = lambda: AuthenticatedUser(
        id="wp13b-test-user", email="wp13b@example.com", role="EnterpriseArchitect"
    )
    try:
        yield TestClient(app)
    finally:
        app.dependency_overrides.clear()


def test_observability_summary_endpoint_returns_recorded_events(authed_client, cleanup_events):
    subject = f"{TEST_PREFIX}endpoint_model"
    metrics.record_ai_call(subject, True, 150, retries=0)

    response = authed_client.get("/api/observability/summary")
    assert response.status_code == 200
    body = response.json()
    row = next((r for r in body if r["subject"] == subject), None)
    assert row is not None
    assert row["total"] == 1
    assert row["success_rate"] == 1.0


def test_observability_summary_endpoint_requires_auth():
    client = TestClient(app)
    response = client.get("/api/observability/summary")
    assert response.status_code == 401
