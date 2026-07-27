"""The one entry point the rest of the application is allowed to call for AI completions
(ADR-002). Reasoning pipelines (WP5), governance services, and agent orchestration depend
on `complete()` here, never on `backend.ai.openai_provider` or the `openai` package
directly -- swapping providers later means writing one new class satisfying the
`AIProvider` Protocol and pointing `AI_PROVIDER` at it, not touching any caller.

Which concrete provider is active is a config read, not a code change -- the same
configuration-over-code-change pattern `backend/db/connection.py`/`backend/auth.py`
already use for SUPABASE_URL/DATABASE_URL."""

import os
import time

from dotenv import load_dotenv

from ..observability.metrics import record_ai_call
from .provider import AICompletionResult, AIProvider, AIProviderError

load_dotenv()

AI_PROVIDER = os.environ.get("AI_PROVIDER", "openai")
AI_MODEL = os.environ.get("AI_MODEL", "gpt-5.5")

_provider: AIProvider | None = None


def _build_provider() -> AIProvider:
    if AI_PROVIDER == "openai":
        from .openai_provider import OpenAIProvider

        api_key = os.environ.get("OPENAI_API_KEY")
        if not api_key:
            raise RuntimeError(
                "OPENAI_API_KEY is not set. Add it to a local .env file "
                "(OPENAI_API_KEY=sk-...) -- see the OpenAI dashboard > API keys."
            )
        return OpenAIProvider(api_key=api_key, model=AI_MODEL)
    raise RuntimeError(f"Unknown AI_PROVIDER '{AI_PROVIDER}'. Supported: openai.")


def _get_provider() -> AIProvider:
    global _provider
    if _provider is None:
        _provider = _build_provider()
    return _provider


def complete(
    system: str, prompt: str, max_tokens: int = 4096, effort: str = "none", json_mode: bool = False
) -> AICompletionResult:
    """The sole AI entry point (ADR-002) -- also the sole chokepoint for AI call metrics
    (Phase 11 section 13, WP13b), so every provider/every caller is instrumented for free.
    Metrics recording is deliberately best-effort: a metrics write failure is logged and
    swallowed, never allowed to turn an otherwise-successful (or already-failed) AI call
    into a second, unrelated failure."""
    started = time.monotonic()
    try:
        result = _get_provider().complete(
            system=system, prompt=prompt, max_tokens=max_tokens, effort=effort, json_mode=json_mode
        )
    except AIProviderError as exc:
        _safe_record_ai_call(AI_MODEL, False, started, error_type=type(exc).__name__)
        raise
    _safe_record_ai_call(AI_MODEL, True, started, result=result)
    return result


def _safe_record_ai_call(model: str, success: bool, started: float, result=None, error_type=None) -> None:
    # Reading `result.retries` happens INSIDE this already-guarded function, not in
    # complete()'s own body -- a provider (real or a test double) that returns something
    # without a `.retries` attribute must never turn an otherwise-successful call into a
    # failure just because the metrics side-path choked on it.
    try:
        retries = getattr(result, "retries", 0) or 0
        duration_ms = int((time.monotonic() - started) * 1000)
        record_ai_call(model, success, duration_ms, retries=retries, error_type=error_type)
    except Exception:  # noqa: BLE001 -- observability must never become a new failure mode
        pass
