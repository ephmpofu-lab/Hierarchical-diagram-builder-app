"""WP16 (Tool Registry framework, ADR-006 -- Tool Engineering Architecture) tests.

Per ADR-006, agents orchestrate and tools carry specialised domain logic; this WP is the
registry/framework only, mirroring how WP7's test_wp7_agents.py covers the Agent taxonomy
as inspectable data. No tool's actual logic is exercised here since most entries are
honestly `not_built` -- see the initial Tool Registry for what remains.
"""

import pytest
from fastapi.testclient import TestClient

from app import app
from backend.auth import AuthenticatedUser, require_auth
from backend.tools.tool import ALL_TOOLS

# ---------- Unit tests: Tool Registry ----------


def test_all_tools_have_unique_names():
    names = [t.name for t in ALL_TOOLS]
    assert len(names) == len(set(names))


def test_every_tool_declares_a_status():
    for tool in ALL_TOOLS:
        assert tool.status in {"built", "partial", "not_built"}


def test_built_and_partial_tools_cite_a_real_implementation():
    for tool in ALL_TOOLS:
        if tool.status in {"built", "partial"}:
            assert tool.implementation.strip()


def test_not_built_tools_cite_no_implementation():
    for tool in ALL_TOOLS:
        if tool.status == "not_built":
            assert tool.implementation == ""


def test_every_tool_declares_an_evidence_base():
    for tool in ALL_TOOLS:
        assert tool.evidence_base.strip()


def test_every_tool_declares_needs_tool_value():
    for tool in ALL_TOOLS:
        assert tool.needs_tool in {"No", "Partial", "Yes"}


# ---------- Integration tests: API endpoint ----------


@pytest.fixture
def authed_client():
    app.dependency_overrides[require_auth] = lambda: AuthenticatedUser(
        id="wp16-test-user", email="wp16@example.com", role="EnterpriseArchitect"
    )
    try:
        yield TestClient(app)
    finally:
        app.dependency_overrides.clear()


def test_tools_endpoint_returns_full_registry(authed_client):
    response = authed_client.get("/api/tools")
    assert response.status_code == 200
    body = response.json()
    assert len(body) == len(ALL_TOOLS)
    assert {t["name"] for t in body} == {t.name for t in ALL_TOOLS}


def test_tools_endpoint_requires_auth():
    client = TestClient(app)
    response = client.get("/api/tools")
    assert response.status_code == 401
