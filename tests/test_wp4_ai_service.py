"""WP4 (Phase 12 Implementation Roadmap, Increment 3 -- AI Service foundation) tests.

Per ADR-002, this is a provider-agnostic AI Service abstraction with OpenAI as the first
concrete provider. Tests mock the OpenAI client rather than calling the real API -- unlike
the free-tier Supabase integration tests elsewhere in this project, every call here is a
billed request against a real vendor, so the automated suite must not spend real money on
every run. A one-off live smoke check (not part of this suite) is how the real key gets
verified end-to-end.
"""

from types import SimpleNamespace
from unittest.mock import Mock

import httpx
import pytest
from fastapi.testclient import TestClient
from openai import (
    APIConnectionError,
    APITimeoutError,
    AuthenticationError,
    BadRequestError,
    InternalServerError,
    RateLimitError,
)

from app import app
from backend.ai import service as ai_service
from backend.ai.openai_provider import OpenAIProvider
from backend.ai.provider import (
    AIAuthenticationError,
    AIInvalidRequestError,
    AIProviderError,
    AIRateLimitError,
    AITransientError,
    retry_with_backoff,
)
from backend.auth import AuthenticatedUser, require_auth


def _http_response(status_code: int) -> httpx.Response:
    request = httpx.Request("POST", "https://api.openai.com/v1/chat/completions")
    return httpx.Response(status_code=status_code, request=request)


def _fake_response(text: str, model: str = "gpt-5.5", input_tokens=12, output_tokens=3):
    return SimpleNamespace(
        choices=[SimpleNamespace(message=SimpleNamespace(content=text))],
        model=model,
        usage=SimpleNamespace(prompt_tokens=input_tokens, completion_tokens=output_tokens),
    )


# ---------- Unit tests: retry_with_backoff ----------


def test_retry_succeeds_first_try_with_zero_retries():
    result, retries = retry_with_backoff(lambda: "ok", is_retryable=lambda exc: True)
    assert result == "ok"
    assert retries == 0


def test_retry_recovers_after_transient_failures(monkeypatch):
    monkeypatch.setattr("backend.ai.provider.time.sleep", lambda _: None)
    calls = {"count": 0}

    def flaky():
        calls["count"] += 1
        if calls["count"] < 3:
            raise ValueError("transient")
        return "recovered"

    result, retries = retry_with_backoff(flaky, is_retryable=lambda exc: True, max_retries=5)
    assert result == "recovered"
    assert retries == 2


def test_retry_does_not_retry_non_retryable_errors(monkeypatch):
    monkeypatch.setattr("backend.ai.provider.time.sleep", lambda _: None)
    calls = {"count": 0}

    def always_fails():
        calls["count"] += 1
        raise ValueError("not retryable")

    with pytest.raises(ValueError):
        retry_with_backoff(always_fails, is_retryable=lambda exc: False, max_retries=5)
    assert calls["count"] == 1


def test_retry_raises_after_exhausting_max_retries(monkeypatch):
    monkeypatch.setattr("backend.ai.provider.time.sleep", lambda _: None)
    calls = {"count": 0}

    def always_fails():
        calls["count"] += 1
        raise ValueError("still failing")

    with pytest.raises(ValueError):
        retry_with_backoff(always_fails, is_retryable=lambda exc: True, max_retries=2)
    assert calls["count"] == 3  # initial attempt + 2 retries


# ---------- Unit tests: OpenAIProvider ----------


@pytest.fixture
def provider(monkeypatch):
    monkeypatch.setattr("backend.ai.provider.time.sleep", lambda _: None)
    return OpenAIProvider(api_key="test-key", model="gpt-5.5")


def test_complete_returns_normalized_result(provider):
    provider._client.chat.completions.create = Mock(return_value=_fake_response("OK"))
    result = provider.complete(system="be terse", prompt="say ok")
    assert result.text == "OK"
    assert result.model == "gpt-5.5"
    assert result.input_tokens == 12
    assert result.output_tokens == 3
    assert result.retries == 0


def test_complete_uses_max_completion_tokens_not_max_tokens(provider):
    mock_create = Mock(return_value=_fake_response("OK"))
    provider._client.chat.completions.create = mock_create
    provider.complete(system="s", prompt="p", max_tokens=99)
    _, kwargs = mock_create.call_args
    assert kwargs["max_completion_tokens"] == 99
    assert "max_tokens" not in kwargs


def test_complete_defaults_reasoning_effort_to_lowest_setting(provider):
    # A reasoning-capable model defaults reasoning_effort to "medium" server-side when
    # omitted, which can consume the whole max_tokens budget on hidden reasoning and
    # return empty visible text with no error -- confirmed live during WP4 verification.
    # gpt-5.5 accepts none/low/medium/high/xhigh (not "minimal", which some other GPT-5
    # variants document but this model rejects with a 400 -- also confirmed live).
    mock_create = Mock(return_value=_fake_response("OK"))
    provider._client.chat.completions.create = mock_create
    provider.complete(system="s", prompt="p")
    _, kwargs = mock_create.call_args
    assert kwargs["reasoning_effort"] == "none"


def test_complete_effort_is_overridable(provider):
    mock_create = Mock(return_value=_fake_response("OK"))
    provider._client.chat.completions.create = mock_create
    provider.complete(system="s", prompt="p", effort="high")
    _, kwargs = mock_create.call_args
    assert kwargs["reasoning_effort"] == "high"


def test_complete_recovers_from_transient_error_then_succeeds(provider):
    mock_create = Mock(
        side_effect=[
            APIConnectionError(request=httpx.Request("POST", "https://api.openai.com/v1/chat/completions")),
            _fake_response("OK"),
        ]
    )
    provider._client.chat.completions.create = mock_create
    result = provider.complete(system="s", prompt="p")
    assert result.text == "OK"
    assert result.retries == 1


def test_complete_rate_limit_exhausted_raises_normalized_error(provider):
    provider._client.chat.completions.create = Mock(
        side_effect=RateLimitError("rate limited", response=_http_response(429), body=None)
    )
    with pytest.raises(AIRateLimitError):
        provider.complete(system="s", prompt="p")


def test_complete_authentication_error_is_not_retried(provider):
    mock_create = Mock(
        side_effect=AuthenticationError("bad key", response=_http_response(401), body=None)
    )
    provider._client.chat.completions.create = mock_create
    with pytest.raises(AIAuthenticationError):
        provider.complete(system="s", prompt="p")
    assert mock_create.call_count == 1  # not retryable -- fails on first attempt


def test_complete_bad_request_raises_invalid_request_error(provider):
    provider._client.chat.completions.create = Mock(
        side_effect=BadRequestError("malformed", response=_http_response(400), body=None)
    )
    with pytest.raises(AIInvalidRequestError):
        provider.complete(system="s", prompt="p")


def test_complete_timeout_exhausted_raises_transient_error(provider):
    provider._client.chat.completions.create = Mock(
        side_effect=APITimeoutError(request=httpx.Request("POST", "https://api.openai.com/v1/chat/completions"))
    )
    with pytest.raises(AITransientError):
        provider.complete(system="s", prompt="p")


def test_complete_internal_server_error_exhausted_raises_transient_error(provider):
    provider._client.chat.completions.create = Mock(
        side_effect=InternalServerError("boom", response=_http_response(500), body=None)
    )
    with pytest.raises(AITransientError):
        provider.complete(system="s", prompt="p")


# ---------- Unit tests: service facade (config-driven provider selection) ----------


@pytest.fixture(autouse=True)
def _reset_service_singleton():
    ai_service._provider = None
    yield
    ai_service._provider = None


def test_service_defaults_to_openai_provider(monkeypatch):
    monkeypatch.setattr(ai_service, "AI_PROVIDER", "openai")
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    provider = ai_service._get_provider()
    assert isinstance(provider, OpenAIProvider)


def test_service_missing_api_key_raises_clear_error(monkeypatch):
    monkeypatch.setattr(ai_service, "AI_PROVIDER", "openai")
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    with pytest.raises(RuntimeError, match="OPENAI_API_KEY"):
        ai_service._get_provider()


def test_service_unknown_provider_raises_clear_error(monkeypatch):
    monkeypatch.setattr(ai_service, "AI_PROVIDER", "not-a-real-provider")
    with pytest.raises(RuntimeError, match="Unknown AI_PROVIDER"):
        ai_service._get_provider()


def test_service_complete_delegates_to_configured_provider(monkeypatch):
    fake_provider = Mock()
    fake_provider.complete.return_value = "sentinel-result"
    ai_service._provider = fake_provider
    result = ai_service.complete("sys", "prompt", max_tokens=50)
    assert result == "sentinel-result"
    fake_provider.complete.assert_called_once_with(
        system="sys", prompt="prompt", max_tokens=50, effort="none", json_mode=False
    )


# ---------- Integration test: /api/ai/health endpoint ----------


@pytest.fixture
def authed_client():
    app.dependency_overrides[require_auth] = lambda: AuthenticatedUser(
        id="wp4-test-user", email="wp4@example.com", role="EnterpriseArchitect"
    )
    try:
        yield TestClient(app)
    finally:
        app.dependency_overrides.clear()


def test_ai_health_endpoint_success(monkeypatch, authed_client):
    from backend.ai.provider import AICompletionResult

    monkeypatch.setattr(
        "backend.api.ai_service.complete",
        lambda **kwargs: AICompletionResult(text="OK", model="gpt-5.5", retries=0),
    )
    response = authed_client.get("/api/ai/health")
    assert response.status_code == 200
    body = response.json()
    assert body["model"] == "gpt-5.5"
    assert body["response"] == "OK"


def test_ai_health_endpoint_surfaces_provider_error(monkeypatch, authed_client):
    def _raise(**kwargs):
        raise AIProviderError("provider is down")

    monkeypatch.setattr("backend.api.ai_service.complete", _raise)
    response = authed_client.get("/api/ai/health")
    assert response.status_code == 502
    assert "provider is down" in response.json()["detail"]


def test_ai_health_endpoint_requires_auth():
    client = TestClient(app)
    response = client.get("/api/ai/health")
    assert response.status_code == 401
