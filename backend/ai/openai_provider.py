"""OpenAI-backed AIProvider (ADR-002's initial concrete provider). Never imported outside
`backend/ai/service.py` -- everything else depends on the AIProvider Protocol, never this
module or the `openai` package directly, so a future provider swap (Anthropic, Azure OpenAI,
local/Ollama) touches this file's sibling, not any caller.

Uses `max_completion_tokens`, not the older `max_tokens` -- OpenAI deprecated `max_tokens`
in favor of `max_completion_tokens` starting with the o1 reasoning-model generation (it
conflated visible output tokens with the hidden reasoning tokens those models also spend),
and the configured model (gpt-5.5) is itself a reasoning-capable model in that same lineage."""

from openai import (
    APIConnectionError,
    APITimeoutError,
    AuthenticationError,
    BadRequestError,
    InternalServerError,
    OpenAI,
    RateLimitError,
)

from .provider import (
    AIAuthenticationError,
    AICompletionResult,
    AIInvalidRequestError,
    AIProviderError,
    AIRateLimitError,
    AITransientError,
    retry_with_backoff,
)

_RETRYABLE = (APIConnectionError, APITimeoutError, InternalServerError, RateLimitError)


class OpenAIProvider:
    def __init__(self, api_key: str, model: str):
        self._client = OpenAI(api_key=api_key)
        self._model = model

    def complete(
        self, *, system: str, prompt: str, max_tokens: int = 4096, effort: str = "none"
    ) -> AICompletionResult:
        def _call():
            return self._client.chat.completions.create(
                model=self._model,
                max_completion_tokens=max_tokens,
                reasoning_effort=effort,
                messages=[
                    {"role": "system", "content": system},
                    {"role": "user", "content": prompt},
                ],
            )

        try:
            response, retries = retry_with_backoff(_call, is_retryable=lambda exc: isinstance(exc, _RETRYABLE))
        except RateLimitError as exc:
            raise AIRateLimitError(str(exc)) from exc
        except AuthenticationError as exc:
            raise AIAuthenticationError(str(exc)) from exc
        except BadRequestError as exc:
            raise AIInvalidRequestError(str(exc)) from exc
        except (APIConnectionError, APITimeoutError, InternalServerError) as exc:
            raise AITransientError(str(exc)) from exc
        except Exception as exc:
            raise AIProviderError(str(exc)) from exc

        choice = response.choices[0]
        usage = response.usage
        return AICompletionResult(
            text=choice.message.content or "",
            model=response.model,
            input_tokens=usage.prompt_tokens if usage else None,
            output_tokens=usage.completion_tokens if usage else None,
            retries=retries,
        )
