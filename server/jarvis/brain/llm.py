"""LLM backend abstraction and the Claude API implementation (streaming)."""

from __future__ import annotations

from collections.abc import AsyncIterator
from dataclasses import dataclass, field
from typing import Any, Protocol

import anthropic

from jarvis.config import ModelConfig


@dataclass
class StreamResult:
    """Filled in by the backend once the stream is exhausted."""

    text: str = ""
    stop_reason: str | None = None
    model: str = ""
    usage: dict[str, int] = field(default_factory=dict)


class LLMError(RuntimeError):
    """A failure the orchestrator can report to the user in plain words."""

    def __init__(self, user_message: str, *, retryable: bool = False) -> None:
        super().__init__(user_message)
        self.user_message = user_message
        self.retryable = retryable


class LLMBackend(Protocol):
    def stream(
        self,
        model: ModelConfig,
        system: list[dict[str, Any]],
        messages: list[dict[str, Any]],
        result: StreamResult,
    ) -> AsyncIterator[str]: ...


def build_request(
    model: ModelConfig, system: list[dict[str, Any]], messages: list[dict[str, Any]]
) -> dict[str, Any]:
    params: dict[str, Any] = {
        "model": model.model,
        "max_tokens": model.max_tokens,
        "system": system,
        "messages": messages,
    }
    if model.thinking:
        params["thinking"] = {"type": "adaptive"}
    if model.effort:
        params["output_config"] = {"effort": model.effort}
    return params


class AnthropicBackend:
    def __init__(self, api_key: str | None, timeout_s: float = 60) -> None:
        self._client = anthropic.AsyncAnthropic(api_key=api_key, timeout=timeout_s)

    async def stream(
        self,
        model: ModelConfig,
        system: list[dict[str, Any]],
        messages: list[dict[str, Any]],
        result: StreamResult,
    ) -> AsyncIterator[str]:
        params = build_request(model, system, messages)
        try:
            async with self._client.messages.stream(**params) as stream:
                async for text in stream.text_stream:
                    result.text += text
                    yield text
                final = await stream.get_final_message()
        except anthropic.AuthenticationError as exc:
            raise LLMError("La chiave Claude API non è valida o manca.") from exc
        except anthropic.PermissionDeniedError as exc:
            raise LLMError("La chiave Claude API non ha accesso a questo modello.") from exc
        except anthropic.NotFoundError as exc:
            raise LLMError(f"Il modello {model.model} non risulta disponibile.") from exc
        except anthropic.RateLimitError as exc:
            raise LLMError(
                "Ho raggiunto il limite di richieste, riprovi tra poco.", retryable=True
            ) from exc
        except anthropic.APIStatusError as exc:
            raise LLMError(
                "Il servizio Claude ha restituito un errore.", retryable=exc.status_code >= 500
            ) from exc
        except anthropic.APIConnectionError as exc:
            raise LLMError(
                "Non riesco a raggiungere il servizio Claude: la rete sembra assente.",
                retryable=True,
            ) from exc
        result.stop_reason = final.stop_reason
        result.model = final.model
        result.usage = {
            "input_tokens": final.usage.input_tokens,
            "output_tokens": final.usage.output_tokens,
            "cache_read_input_tokens": final.usage.cache_read_input_tokens or 0,
        }
