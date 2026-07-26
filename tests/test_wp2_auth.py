"""WP2 (Phase 12 Implementation Roadmap, Increment 1 -- Foundation) tests.

JWT verification is tested against a *locally generated* EC key pair, never the real
Supabase signing key -- that's the whole point of asymmetric verification: only Supabase's
private key can mint a token our code will actually accept, and that's exactly what these
tests confirm (a token signed by the wrong key, or missing/expired, is correctly rejected).

Ownership enforcement is tested as an integration test against the live database, via a
throwaway project, self-cleaning in a `finally` block.
"""

import uuid
from datetime import datetime, timedelta, timezone

import jwt
import pytest
from cryptography.hazmat.primitives.asymmetric import ec
from fastapi import HTTPException

from backend import auth as auth_module
from backend import storage

TEST_PREFIX = "__WP2_TEST__"


class _FakeSigningKey:
    def __init__(self, key):
        self.key = key


class _FakeJWKClient:
    """Stands in for auth._get_jwks_client() -- returns our own test key instead of
    fetching Supabase's real JWKS, so these tests never touch the network or the real
    signing key."""

    def __init__(self, public_key):
        self._public_key = public_key

    def get_signing_key_from_jwt(self, token):
        return _FakeSigningKey(self._public_key)


@pytest.fixture
def keypair():
    private_key = ec.generate_private_key(ec.SECP256R1())
    return private_key, private_key.public_key()


def _make_token(private_key, *, sub="user-123", email="architect@example.com", app_metadata=None, **overrides):
    now = datetime.now(timezone.utc)
    claims = {
        "sub": sub,
        "email": email,
        "app_metadata": app_metadata or {},
        "aud": "authenticated",
        "iss": f"{auth_module.SUPABASE_URL}/auth/v1",
        "iat": now,
        "exp": now + timedelta(hours=1),
        **overrides,
    }
    return jwt.encode(claims, private_key, algorithm="ES256")


def test_valid_token_is_accepted_and_claims_extracted(monkeypatch, keypair):
    private_key, public_key = keypair
    monkeypatch.setattr(auth_module, "_get_jwks_client", lambda: _FakeJWKClient(public_key))

    token = _make_token(private_key, sub="user-abc", app_metadata={"role": "EnterpriseArchitect"})
    user = auth_module._verify_token(token)

    assert user.id == "user-abc"
    assert user.email == "architect@example.com"
    assert user.role == "EnterpriseArchitect"


def test_missing_role_defaults_to_enterprise_architect(monkeypatch, keypair):
    private_key, public_key = keypair
    monkeypatch.setattr(auth_module, "_get_jwks_client", lambda: _FakeJWKClient(public_key))

    token = _make_token(private_key)  # no app_metadata.role
    user = auth_module._verify_token(token)

    assert user.role == auth_module.DEFAULT_ROLE


def test_token_signed_by_wrong_key_is_rejected(monkeypatch, keypair):
    _private_key, public_key = keypair
    other_private_key = ec.generate_private_key(ec.SECP256R1())  # a different key entirely
    monkeypatch.setattr(auth_module, "_get_jwks_client", lambda: _FakeJWKClient(public_key))

    forged_token = _make_token(other_private_key)
    with pytest.raises(HTTPException) as exc_info:
        auth_module._verify_token(forged_token)
    assert exc_info.value.status_code == 401


def test_expired_token_is_rejected(monkeypatch, keypair):
    private_key, public_key = keypair
    monkeypatch.setattr(auth_module, "_get_jwks_client", lambda: _FakeJWKClient(public_key))

    now = datetime.now(timezone.utc)
    expired_token = _make_token(
        private_key, iat=now - timedelta(hours=2), exp=now - timedelta(hours=1)
    )
    with pytest.raises(HTTPException) as exc_info:
        auth_module._verify_token(expired_token)
    assert exc_info.value.status_code == 401


def test_wrong_audience_is_rejected(monkeypatch, keypair):
    private_key, public_key = keypair
    monkeypatch.setattr(auth_module, "_get_jwks_client", lambda: _FakeJWKClient(public_key))

    token = _make_token(private_key, aud="some-other-service")
    with pytest.raises(HTTPException) as exc_info:
        auth_module._verify_token(token)
    assert exc_info.value.status_code == 401


def test_require_auth_rejects_missing_or_malformed_header():
    with pytest.raises(HTTPException) as exc_info:
        auth_module.require_auth(authorization=None)
    assert exc_info.value.status_code == 401

    with pytest.raises(HTTPException) as exc_info:
        auth_module.require_auth(authorization="not-a-bearer-token")
    assert exc_info.value.status_code == 401


# ---------- Ownership enforcement (integration, live DB) ----------


def test_owner_id_column_is_fk_constrained_to_real_supabase_users():
    # owner_id references auth.users(id) -- a random UUID that isn't a real Supabase user
    # is correctly rejected. This is the actual, live constraint doing its job; it also
    # means the "two different real owners see different projects" scenario can only be
    # tested once a real account exists (see test_owner_id_set_on_create_and_enforced_on_list
    # skip below), since fabricating a fake auth.users row would mean writing directly into
    # Supabase's own managed auth schema from test code -- deliberately avoided.
    with pytest.raises(Exception):
        storage.create_project(f"{TEST_PREFIX}should-fail", str(uuid.uuid4()))


@pytest.mark.skip(
    reason="Requires a real Supabase auth.users row (owner_id has a live FK to it). "
    "Un-skip once a real account exists, using its real user id in place of a random UUID."
)
def test_owner_id_set_on_create_and_enforced_on_list():
    owner_a = str(uuid.uuid4())  # replace with a real auth.users id once one exists
    owner_b = str(uuid.uuid4())
    project_a = storage.create_project(f"{TEST_PREFIX}project-a", owner_a)
    try:
        assert project_a.owner_id == owner_a

        visible_to_a = {p.id for p in storage.list_projects(owner_a)}
        visible_to_b = {p.id for p in storage.list_projects(owner_b)}
        assert project_a.id in visible_to_a
        assert project_a.id not in visible_to_b  # b doesn't own it and it isn't legacy/null
    finally:
        storage.delete_project(project_a.id)


def test_legacy_null_owner_project_is_visible_to_any_user():
    legacy_project = storage.create_project(f"{TEST_PREFIX}legacy-project")  # owner_id=None
    try:
        assert legacy_project.owner_id is None
        visible_to_anyone = {p.id for p in storage.list_projects(str(uuid.uuid4()))}
        assert legacy_project.id in visible_to_anyone
    finally:
        storage.delete_project(legacy_project.id)
