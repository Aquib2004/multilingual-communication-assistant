"""Provider for any OpenAI-compatible local server.

Works with Ollama, llama.cpp's server, vLLM, LM Studio, and text-generation-
webui. This is how a contributor runs the whole pipeline on an open-source
model with no paid API.
"""

from __future__ import annotations

from app.ai.providers.openai import OpenAIProvider
from app.core.config import Settings
from app.core.logging import get_logger

logger = get_logger(__name__)


class LocalProvider(OpenAIProvider):
    """OpenAI-compatible provider pointed at a local endpoint.

    Reuses the OpenAI request and error-mapping code and only overrides
    identity and configuration, which is the point of the abstraction.
    """

    name = "local"

    def __init__(self, settings: Settings) -> None:
        """Build the provider against the configured local base URL.

        Args:
            settings: Runtime settings. No API key is required, though some
                servers expect a placeholder value, so one is sent.
        """
        local_settings = settings.model_copy(
            update={
                "openai_api_key": settings.local_api_key or "not-needed",
                "openai_base_url": settings.local_base_url,
                "openai_model": settings.local_model,
                "openai_timeout_seconds": settings.local_timeout_seconds,
            }
        )
        super().__init__(local_settings)
        logger.info(
            "local provider configured",
            base_url=settings.local_base_url,
            model=settings.local_model,
        )
