"""Covers the /api/session endpoint added while fixing the login/index redirect loop --
it's what both login.html and index.html now defer to as the one source of truth for
whether a session is genuinely backend-valid, instead of trusting the Supabase client's
own local (expiry-only) session cache, which is what let the two pages disagree in the
first place.

Uses FastAPI's dependency override rather than a real or synthetic token -- require_auth's
own JWT verification is already covered directly in test_wp2_auth.py; this test is only
about the route's own behavior once a caller is authenticated.
"""

from fastapi.testclient import TestClient

from app import app
from backend.auth import AuthenticatedUser, require_auth


def test_session_endpoint_returns_authenticated_user_fields():
    app.dependency_overrides[require_auth] = lambda: AuthenticatedUser(
        id="user-123", email="architect@example.com", role="EnterpriseArchitect"
    )
    try:
        client = TestClient(app)
        response = client.get("/api/session")
        assert response.status_code == 200
        assert response.json() == {
            "id": "user-123",
            "email": "architect@example.com",
            "role": "EnterpriseArchitect",
        }
    finally:
        app.dependency_overrides.clear()


def test_session_endpoint_requires_auth():
    client = TestClient(app)
    response = client.get("/api/session")
    assert response.status_code == 401
