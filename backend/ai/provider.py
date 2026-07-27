"""The AI Service abstraction (Phase 12 Implementation Roadmap, WP4; ADR-002). A
stateless LLM invocation layer, consistent with Phase 7 section 3/7's design (agents hold
no memory across calls -- all state lives in the Reasoning Context and Enterprise
Repository, never in the provider). Every call must be safely retryable (Phase 7 section 11)
since agents are stateless by design -- a failed call has no state to recover, only to redo.

Per ADR-002: business logic, reasoning pipelines, governance services, and agent
orchestration depend only on the `AIProvider` Protocol (or the `backend/ai/service.py`
facade over it) -- never on a vendor SDK directly. Concrete providers live in sibling
modules (e.g. `openai_provider.py`); adding a new vendor means writing one new class that
satisfies this Protocol, not touching any caller."""

import time
from dataclasses import dataclass
from typing import Callable, Protocol, TypeVar

T = TypeVar("T")


@dataclass
class AICompletionResult:
    text: str
    model: str
    input_tokens: int | None = None
    output_tokens: int | None = None
    retries: int = 0


class AIProviderError(Exception):
    """Base for all AI provider errors -- normalized across vendors so callers never
    need to know which concrete provider (or which vendor's exception hierarchy) is active."""


class AIAuthenticationError(AIProviderError):
    """Invalid or missing credentials. Not retryable."""


class AIRateLimitError(AIProviderError):
    """Rate limited, and retries were exhausted."""


class AITransientError(AIProviderError):
    """A transient failure (timeout, connection, server error) survived retries."""


class AIInvalidRequestError(AIProviderError):
    """The request itself was malformed. Not retryable."""


class AIProvider(Protocol):
    def complete(
        self,
        *,
        system: str,
        prompt: str,
        max_tokens: int = 4096,
        effort: str = "none",
        json_mode: bool = False,
    ) -> AICompletionResult: ...
    # `json_mode` asks the provider to guarantee syntactically valid JSON output (OpenAI:
    # response_format={"type": "json_object"}) -- used by the Reasoning Pipeline (WP5) for
    # stages that need structured extraction (candidate nodes/relationships/risks). It
    # guarantees valid JSON *syntax*, not a specific schema -- callers still validate shape
    # with Pydantic and treat a mismatch as a stage failure, not a crash.
    # `effort` is a provider-agnostic reasoning-depth knob (OpenAI: reasoning_effort --
    # confirmed live against gpt-5.5 to accept none/low/medium/high/xhigh, not the
    # "minimal" value some other GPT-5 variants document; Anthropic: effort
    # low/medium/high/xhigh/max) -- each provider maps it to its own vendor-specific
    # parameter. Defaults to the lowest setting: a reasoning-capable model can otherwise
    # spend its entire max_tokens budget on hidden reasoning and return empty visible
    # text with no error (confirmed live during WP4 verification -- 16 max_tokens, 16
    # output_tokens billed, empty response, because the unset default is "medium").


def retry_with_backoff(
    fn: Callable[[], T],
    *,
    is_retryable: Callable[[Exception], bool],
    max_retries: int = 3,
    base_delay: float = 1.0,
) -> tuple[T, int]:
    """Calls fn(), retrying with exponential backoff on exceptions `is_retryable` accepts.
    Returns (result, retries_used) so callers can report retry counts (Phase 11 section 13's
    AI service call metrics: latency, retry counts)."""
    attempt = 0
    while True:
        try:
            return fn(), attempt
        except Exception as exc:
            if attempt >= max_retries or not is_retryable(exc):
                raise
            time.sleep(base_delay * (2**attempt))
            attempt += 1
