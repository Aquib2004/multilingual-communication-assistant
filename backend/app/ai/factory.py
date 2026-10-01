"""Provider selection by configuration.

The only thing that decides which provider runs is the ``AI_PROVIDER``
environment variable. No service code changes when the provider changes.
"""

from __future__ import annotations

from functools import lru_cache

from app.ai.base import AIProvider
from app.ai.providers.local import LocalProvider
from app.ai.providers.mock import MockProvider
from app.ai.providers.openai import OpenAIProvider
from app.core.config import Settings, get_settings
from app.core.errors import AIProviderAuthError
from app.core.logging import get_logger

logger = get_logger(__name__)

#: Registry of available providers, keyed by the ``AI_PROVIDER`` value.
PROVIDERS: dict[str, type[AIProvider]] = {
    "mock": MockProvider,
    "openai": OpenAIProvider,
    "local": LocalProvider,
}


def build_provider(settings: Settings) -> AIProvider:
    """Instantiate the configured provider.

    Args:
        settings: Runtime settings.

    Returns:
        A ready-to-use :class:`AIProvider`.

    Raises:
        AIProviderAuthError: If a provider that needs a key was selected
            without one. Failing at startup is better than failing per request.
    """
    name = settings.ai_provider
    provider_class = PROVIDERS.get(name)

    if provider_class is None:
        raise AIProviderAuthError(
            f"Unknown AI provider {name!r}. Choose one of: {sorted(PROVIDERS)}."
        )

    if name == "openai" and not settings.openai_api_key:
        raise AIProviderAuthError(
            "AI_PROVIDER=openai requires OPENAI_API_KEY. "
            "Set it, or use AI_PROVIDER=mock to run without a key."
        )

    provider = provider_class(settings)
    logger.info("ai provider selected", provider=provider.name, model=provider.model)
    return provider


@lru_cache(maxsize=1)
def get_provider() -> AIProvider:
    """Return the process-wide provider, creating it on first use."""
    return build_provider(get_settings())


def reset_provider_cache() -> None:
    """Clear the cached provider. Used by tests that change configuration."""
    get_provider.cache_clear()
