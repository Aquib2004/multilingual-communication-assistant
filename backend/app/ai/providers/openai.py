"""OpenAI provider, using the chat completions API over plain HTTP.

Written against ``httpx`` rather than a vendor SDK so the dependency surface
stays small and the local provider can reuse the same client code.
"""

from __future__ import annotations

import json
from typing import Any

import httpx

from app.ai.base import AIProvider, AIRequest, AIResponse
from app.core.config import Settings
from app.core.errors import (
    AIProviderAuthError,
    AIProviderError,
    AIProviderRateLimitError,
    AIProviderTimeoutError,
)
from app.core.logging import get_logger

logger = get_logger(__name__)


class OpenAIProvider(AIProvider):
    """Chat-completions provider for OpenAI and compatible endpoints.

    Every native error is translated into the application's own error hierarchy
    here, so no service ever imports or catches a vendor exception.
    """

    name = "openai"

    def __init__(self, settings: Settings) -> None:
        """Build the provider from settings.

        Args:
            settings: Runtime settings. ``openai_api_key`` must be set.

        Raises:
            AIProviderAuthError: If no API key is configured.
        """
        if not settings.openai_api_key:
            msg = "OPENAI_API_KEY is not configured."
            raise AIProviderAuthError(msg)

        self._api_key = settings.openai_api_key
        self._base_url = settings.openai_base_url.rstrip("/")
        self._timeout = settings.openai_timeout_seconds
        self._max_retries = settings.openai_max_retries
        self.model = settings.openai_model
        self._client = httpx.AsyncClient(
            base_url=self._base_url,
            timeout=self._timeout,
            headers={
                "Authorization": f"Bearer {self._api_key}",
                "Content-Type": "application/json",
            },
        )

    async def complete(self, request: AIRequest) -> AIResponse:
        """Call the chat completions endpoint and validate the reply.

        Args:
            request: The task, prompts, and expected schema.

        Returns:
            A validated :class:`AIResponse`.

        Raises:
            AIProviderAuthError: The key was rejected.
            AIProviderRateLimitError: The upstream is rate limiting.
            AIProviderTimeoutError: The request took too long.
            AIProviderError: Any other upstream failure.
        """
        payload = {
            "model": self.model,
            "temperature": request.temperature,
            "max_tokens": request.max_tokens,
            "response_format": {"type": "json_object"},
            "messages": [
                {"role": "system", "content": request.system_prompt},
                {"role": "user", "content": request.user_prompt},
            ],
        }

        data = await self._post(payload)
        raw_text = self._extract_text(data)

        try:
            parsed = json.loads(raw_text)
        except json.JSONDecodeError as exc:
            # Log the raw text for diagnosis; never return it to the user.
            logger.error("provider returned non-JSON", task=request.task, raw=raw_text[:500])
            msg = "The model did not return a usable JSON response."
            raise AIProviderError(msg) from exc

        return AIResponse(
            data=parsed,
            provider=self.name,
            model=self.model,
            response_model=request.response_model,
            raw_text=raw_text,
        )

    async def _post(self, payload: dict[str, Any]) -> dict[str, Any]:
        """POST to the endpoint, mapping every transport failure to our errors."""
        url = f"{self._base_url}/chat/completions"
        last_error: Exception | None = None

        for attempt in range(self._max_retries + 1):
            try:
                response = await self._client.post(url, json=payload)
            except httpx.TimeoutException as exc:
                last_error = exc
                logger.warning("provider timeout", attempt=attempt)
                continue
            except httpx.HTTPError as exc:
                last_error = exc
                logger.warning("provider transport error", attempt=attempt, type=type(exc).__name__)
                continue

            if response.status_code == 401:
                msg = "The configured API key was rejected."
                raise AIProviderAuthError(msg)

            if response.status_code == 429:
                msg = "The AI provider is rate limiting requests. Please retry shortly."
                raise AIProviderRateLimitError(msg)

            if response.status_code >= 400:
                logger.error(
                    "provider error", status=response.status_code, body=response.text[:300]
                )
                msg = f"The AI provider returned an error (HTTP {response.status_code})."
                raise AIProviderError(msg)

            return response.json()  # type: ignore[no-any-return]

        msg = "The AI provider did not respond. Please retry."
        raise AIProviderTimeoutError(msg) from last_error

    @staticmethod
    def _extract_text(data: dict[str, Any]) -> str:
        """Pull the assistant message out of a chat-completions response."""
        try:
            return str(data["choices"][0]["message"]["content"])
        except (KeyError, IndexError, TypeError) as exc:
            msg = "The AI provider returned an unexpected response shape."
            raise AIProviderError(msg) from exc

    async def health(self) -> bool:
        """True when a key is configured. Does not call the API."""
        return bool(self._api_key)

    async def aclose(self) -> None:
        """Close the underlying HTTP connection pool."""
        await self._client.aclose()
