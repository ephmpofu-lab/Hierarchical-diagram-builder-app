"""Supabase Auth verification (Phase 12 WP2). This project's Supabase instance signs
session JWTs asymmetrically (ES256, confirmed via its public JWKS endpoint) -- no shared
secret is needed or stored here; tokens are verified against Supabase's own public signing
keys, fetched and cached via PyJWT's PyJWKClient.

Every request to backend/api.py's router requires a valid session (see api.py's router
dependency) -- "login required before accessing any project", the security requirement
stated at the very start of this project.
"""

import os
from dataclasses import dataclass
from typing import Optional

import jwt
from dotenv import load_dotenv
from fastapi import Header, HTTPException

load_dotenv()  # explicit here too -- this module must not depend on import order relative
# to backend/db/connection.py (which also calls this) to see .env's values.

SUPABASE_URL = os.environ.get("SUPABASE_URL")

# The one role a solo user implicitly holds until real multi-user role assignment exists
# (Phase 9 §4 / Phase 10 §12 name five roles; enforcing distinctions between them has no
# meaning with a single account). A future admin can raise/lower this per-user via
# Supabase's `app_metadata` (trusted, not user-editable) once more accounts exist --
# reading it here already, just with a same-default fallback today.
DEFAULT_ROLE = "EnterpriseArchitect"

_jwks_client: Optional[jwt.PyJWKClient] = None


def _get_jwks_client() -> jwt.PyJWKClient:
    global _jwks_client
    if _jwks_client is None:
        if not SUPABASE_URL:
            raise RuntimeError(
                "SUPABASE_URL is not set. Add it to a local .env file "
                "(SUPABASE_URL=https://<project-ref>.supabase.co) — see Supabase dashboard > Settings > API."
            )
        _jwks_client = jwt.PyJWKClient(f"{SUPABASE_URL}/auth/v1/.well-known/jwks.json")
    return _jwks_client


@dataclass
class AuthenticatedUser:
    id: str
    email: Optional[str]
    role: str


def _verify_token(token: str) -> AuthenticatedUser:
    try:
        signing_key = _get_jwks_client().get_signing_key_from_jwt(token)
        claims = jwt.decode(
            token,
            signing_key.key,
            algorithms=["ES256"],
            audience="authenticated",
            issuer=f"{SUPABASE_URL}/auth/v1",
            # Tolerates ordinary clock skew between this machine and Supabase's auth
            # server (a dev machine's clock is never perfectly NTP-synced) -- without
            # this, a token's `iat`/`exp` can appear invalid by a few tens of seconds
            # even though the token itself is genuinely fresh.
            leeway=120,
        )
    except jwt.PyJWTError as exc:
        raise HTTPException(status_code=401, detail=f"Invalid or expired session: {exc}") from exc

    app_metadata = claims.get("app_metadata") or {}
    return AuthenticatedUser(
        id=claims["sub"],
        email=claims.get("email"),
        role=app_metadata.get("role", DEFAULT_ROLE),
    )


def require_auth(authorization: Optional[str] = Header(default=None)) -> AuthenticatedUser:
    """FastAPI dependency -- raises 401 if there is no valid Supabase session. Applied at the
    router level in api.py so every route requires login, not opted into per-route."""
    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(status_code=401, detail="Missing bearer token")
    token = authorization.split(" ", 1)[1].strip()
    return _verify_token(token)
