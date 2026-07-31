"""WP20 (Journey 4: Discovery Session -> Project Initiation Report -> Project Creation)
tests.

Covers backend/discovery/service.py's per-turn topic-coverage/turn-cap behavior and report
generation, backend/discovery/commit.py's node/classification/Requirement/
TraceabilityLink creation (the first real writer of both models), and the five Discovery
Session endpoints end-to-end. AI calls are mocked throughout via
backend.discovery.service._ask_json (never spend real money on every test run); commit
tests use a real throwaway __WP20_TEST__-prefixed project against the live DB, self-
cleaning via try/finally.
"""

import uuid

import pytest
from fastapi.testclient import TestClient

from app import app
from backend import storage
from backend.auth import AuthenticatedUser, require_auth
from backend.db import postgres_discovery_repository as discovery_repo
from backend.discovery import service as discovery_service
from backend.discovery.commit import commit_initiation_report
from backend.models import (
    DiscoverySession,
    DiscoveryTurn,
    GovernanceReview,
    ProjectInitiationReport,
    ProposedInitiationNode,
    ProposedInitiationRequirement,
)

TEST_PREFIX = "__WP20_TEST__"


def _root_id(project) -> str:
    return next(n.id for n in project.nodes.values() if n.parent_id is None)


def _canned_review(outcome="held_pending_human_review") -> GovernanceReview:
    return GovernanceReview(outcome=outcome, requires_human_review=True)


def _sequenced_ask_json(responses):
    state = {"n": 0}

    def _mock(system, prompt, max_tokens=800):
        i = min(state["n"], len(responses) - 1)
        state["n"] += 1
        return responses[i]

    return _mock


# ---------- Unit tests: discovery.service.advance_turn ----------


def test_advance_turn_tracks_topic_coverage(monkeypatch):
    session = DiscoverySession(id="s1", owner_id="user-1")
    monkeypatch.setattr(
        discovery_service,
        "_ask_json",
        lambda system, prompt, max_tokens=800: {
            "message": "What business objectives are driving this?",
            "topic_coverage": {"business_objectives": "Partial"},
            "ready_for_report": False,
        },
    )
    turn = discovery_service.advance_turn(session, "We need to cut manual review time.")
    assert turn.topic_coverage == {"business_objectives": "Partial"}
    assert turn.ready_for_report is False


def test_advance_turn_forces_ready_at_turn_cap(monkeypatch):
    session = DiscoverySession(id="s1", owner_id="user-1", turn_count=discovery_service.MAX_DISCOVERY_TURNS - 1)
    monkeypatch.setattr(
        discovery_service,
        "_ask_json",
        lambda system, prompt, max_tokens=800: {
            "message": "One more thing...",
            "topic_coverage": {"business_objectives": "Partial"},
            "ready_for_report": False,
        },
    )
    turn = discovery_service.advance_turn(session, "Still explaining.")
    assert turn.ready_for_report is True  # forced by the turn cap, not the model's own signal


# ---------- Unit tests: discovery.service.generate_report ----------


def test_generate_report_parses_full_shape(monkeypatch):
    session = DiscoverySession(
        id="s1",
        owner_id="user-1",
        turns=[DiscoveryTurn(id="t1", timestamp="2026-01-01T00:00:00", role="architect", message="Hi")],
    )
    monkeypatch.setattr(
        discovery_service,
        "_ask_json",
        lambda system, prompt, max_tokens=3000: {
            "business_problem": "Manual invoice review is too slow.",
            "business_objectives": ["Reduce review time by 50%"],
            "engineering_scope": "Invoice intake through approval.",
            "stakeholders": ["Finance team"],
            "recommended_solution_type": "Workflow Automation",
            "recommended_engineering_approach": "Rules engine with human review",
            "recommended_architecture_patterns": ["Human-in-the-loop approval"],
            "estimated_complexity": "Medium",
            "recommended_initial_workspaces": ["Invoice Intake"],
            "proposed_operations_model": [
                {
                    "label": "Invoice Intake",
                    "parent_label": None,
                    "node_type": "Workspace",
                    "classification": "Business",
                    "notes": "",
                },
                {
                    "label": "Validate Invoice",
                    "parent_label": "Invoice Intake",
                    "node_type": "Task",
                    "classification": "Business",
                    "notes": "",
                },
            ],
            "recommended_engineering_activities": ["Define validation rules"],
            "known_risks": ["Vendor data may be inconsistent"],
            "knowledge_gaps": ["No sample invoices reviewed yet"],
            "recommended_next_steps": ["Collect 20 sample invoices"],
            "suggested_knowledge_sources": ["Existing SOP document"],
            "suggested_evidence_collection": ["Interview AP clerks"],
            "proposed_requirements": [
                {
                    "description": "System must flag invoices over $10k",
                    "parent_label": None,
                    "origin_node_label": "Invoice Intake",
                }
            ],
        },
    )
    report = discovery_service.generate_report(session)
    assert report.business_problem == "Manual invoice review is too slow."
    assert len(report.proposed_operations_model) == 2
    assert report.proposed_operations_model[1].parent_label == "Invoice Intake"
    assert len(report.proposed_requirements) == 1


# ---------- Unit tests: discovery.commit.commit_initiation_report ----------


@pytest.fixture
def test_project():
    project = storage.create_project(f"{TEST_PREFIX}project")
    try:
        yield project
    finally:
        try:
            storage.delete_project(project.id)
        except Exception:
            pass


def _sample_report() -> ProjectInitiationReport:
    return ProjectInitiationReport(
        business_problem="Manual invoice review is too slow.",
        proposed_operations_model=[
            ProposedInitiationNode(label="Invoice Intake", parent_label=None, node_type="Workspace", classification="Business"),
            ProposedInitiationNode(label="Validate Invoice", parent_label="Invoice Intake", node_type="Task", classification="Business"),
            ProposedInitiationNode(label="Orphaned Activity", parent_label="Nonexistent Workspace", node_type="Task"),
        ],
        recommended_engineering_activities=["Define validation rules"],
        known_risks=["Vendor data may be inconsistent"],
        knowledge_gaps=["No sample invoices reviewed yet"],
        proposed_requirements=[
            ProposedInitiationRequirement(description="Flag invoices over $10k", origin_node_label="Invoice Intake"),
            ProposedInitiationRequirement(description="Orphaned requirement", origin_node_label="Nonexistent Workspace"),
        ],
    )


def test_commit_creates_nodes_with_classification(test_project):
    report = _sample_report()
    result = commit_initiation_report(test_project, report, "test-actor")
    assert len(result["committed_node_ids"]) == 2  # the orphaned activity's parent never resolves -> dropped

    labels = {n.label: n for n in test_project.nodes.values()}
    assert labels["Invoice Intake"].classification == "Business"
    assert labels["Validate Invoice"].parent_id == labels["Invoice Intake"].id
    assert "Orphaned Activity" not in labels


def test_commit_creates_requirements_and_traceability_links(test_project):
    report = _sample_report()
    result = commit_initiation_report(test_project, report, "test-actor")
    # Both requirements are committed -- an unresolvable origin_node_label drops only the
    # traceability link, not the requirement itself (a requirement can meaningfully exist
    # before being traced to anything; a node cannot meaningfully exist without a parent).
    assert len(result["committed_requirement_ids"]) == 2
    assert len(test_project.requirements) == 2
    assert len(test_project.traceability_links) == 1
    link = test_project.traceability_links[0]
    assert link.requirement_id in result["committed_requirement_ids"]
    assert link.link_type == "satisfies"


def test_commit_writes_prose_to_root_notes(test_project):
    report = _sample_report()
    commit_initiation_report(test_project, report, "test-actor")
    root = test_project.nodes[_root_id(test_project)]
    assert "Vendor data may be inconsistent" in root.notes
    assert "No sample invoices reviewed yet" in root.notes


def test_commit_logs_engineering_activities(test_project):
    report = _sample_report()
    commit_initiation_report(test_project, report, "test-actor")
    messages = [e.message for e in test_project.activity_log]
    assert "Define validation rules" in messages


# ---------- Integration tests: the five Discovery Session endpoints ----------


@pytest.fixture
def authed_client():
    app.dependency_overrides[require_auth] = lambda: AuthenticatedUser(
        id="wp20-test-user", email="wp20@example.com", role="EnterpriseArchitect"
    )
    try:
        yield TestClient(app)
    finally:
        app.dependency_overrides.clear()


def test_discovery_session_full_flow(monkeypatch, authed_client):
    # The authed_client fixture's user id ("wp20-test-user") is a fake, non-UUID string --
    # owner_id has a real, live FK to auth.users(id) (same as Project.owner_id), so no test
    # user id can ever be inserted for real without a genuine Supabase account (see WP2's
    # own test_owner_id_column_is_fk_constrained_to_real_supabase_users). No existing test
    # in this repo exercises real project creation through an authenticated fake user for
    # exactly this reason; Discovery Session's endpoints are the first to need it, since
    # project creation is their entire point. Coercing owner_id to None here is a test-only
    # accommodation -- the real endpoints always pass a real user.id in actual use.
    real_create_session = discovery_repo.create_session
    real_create_project = storage.create_project
    monkeypatch.setattr("backend.api.discovery_repo.create_session", lambda owner_id=None: real_create_session(None))
    monkeypatch.setattr("backend.api.storage.create_project", lambda name, owner_id=None: real_create_project(name, None))

    responses = [
        {
            "message": "Tell me about the business problem you're trying to solve.",
            "topic_coverage": {t: "Unexplored" for t in discovery_service.DISCOVERY_TOPICS},
            "ready_for_report": False,
        },
        {
            "message": "Got it -- who are the key stakeholders?",
            "topic_coverage": {t: "Covered" for t in discovery_service.DISCOVERY_TOPICS},
            "ready_for_report": True,
        },
    ]
    monkeypatch.setattr(discovery_service, "_ask_json", _sequenced_ask_json(responses))
    monkeypatch.setattr("backend.agents.orchestrator.run_decision_workflow", lambda result: _canned_review())

    start = authed_client.post("/api/discovery-sessions")
    assert start.status_code == 201
    start_body = start.json()
    session_id = start_body["id"]
    assert start_body["status"] == "InProgress"
    assert len(start_body["turns"]) == 1
    assert start_body["turns"][0]["role"] == "architect"

    turn_resp = authed_client.post(
        f"/api/discovery-sessions/{session_id}/turns", json={"message": "We need to cut manual review time."}
    )
    assert turn_resp.status_code == 200
    turn_body = turn_resp.json()
    assert turn_body["status"] == "ReadyForReport"
    assert len(turn_body["turns"]) == 3  # architect, user, architect

    report_data = {
        "business_problem": "Manual invoice review is too slow.",
        "proposed_operations_model": [
            {
                "label": "Invoice Intake",
                "parent_label": None,
                "node_type": "Workspace",
                "classification": "Business",
                "notes": "",
            }
        ],
        "known_risks": ["Vendor data may be inconsistent"],
        "knowledge_gaps": ["No sample invoices reviewed yet"],
        "proposed_requirements": [],
    }
    monkeypatch.setattr(discovery_service, "generate_report", lambda session: ProjectInitiationReport(**report_data))

    report_resp = authed_client.post(f"/api/discovery-sessions/{session_id}/generate-report")
    assert report_resp.status_code == 200
    report_body = report_resp.json()
    assert report_body["review"]["outcome"] == "held_pending_human_review"

    get_resp = authed_client.get(f"/api/discovery-sessions/{session_id}")
    assert get_resp.json()["status"] == "ReportGenerated"

    approve_resp = authed_client.post(f"/api/discovery-sessions/{session_id}/approve", json=report_body)
    assert approve_resp.status_code == 201
    project_body = approve_resp.json()
    project_id = project_body["id"]

    try:
        reloaded = storage.load_project(project_id)
        labels = {n.label for n in reloaded.nodes.values()}
        assert "Invoice Intake" in labels

        final = authed_client.get(f"/api/discovery-sessions/{session_id}")
        assert final.json()["status"] == "Approved"
        assert final.json()["created_project_id"] == project_id
    finally:
        try:
            storage.delete_project(project_id)
        except Exception:
            pass


def test_discovery_session_requires_auth():
    client = TestClient(app)
    response = client.post("/api/discovery-sessions")
    assert response.status_code == 401


def test_discovery_session_404s_for_unknown_id(authed_client):
    response = authed_client.get(f"/api/discovery-sessions/{uuid.uuid4()}")
    assert response.status_code == 404
