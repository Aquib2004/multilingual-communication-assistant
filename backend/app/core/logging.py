"""Structured logging that does not leak message content.

What is logged: request id, operation, duration, provider, outcome.
What is never logged by default: message bodies, names, contact details.
"""

from __future__ import annotations

import logging
import sys
from collections.abc import MutableMapping
from typing import Any

import structlog

from app.core.config import Settings


def configure_logging(settings: Settings) -> None:
    """Configure structlog and stdlib logging.

    Args:
        settings: Runtime settings. ``log_message_content`` gates whether any
            helper is permitted to include text in a log record.
    """
    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=getattr(logging, settings.log_level.upper(), logging.INFO),
        force=True,
    )

    # Third-party loggers are noisy and can echo request bodies.
    for noisy in ("httpx", "httpcore", "urllib3", "asyncio", "sqlalchemy.engine"):
        logging.getLogger(noisy).setLevel(logging.WARNING)

    processors: list[Any] = [
        structlog.contextvars.merge_contextvars,
        structlog.stdlib.add_log_level,
        structlog.stdlib.add_logger_name,
        structlog.processors.TimeStamper(fmt="iso", utc=True),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.UnicodeDecoder(),
    ]

    if not settings.should_log_message_content:
        # A final safety net: even if a caller passes text, redact it.
        # Must sit *before* the renderer, which turns the event dict into a
        # string that _redact_text could no longer inspect.
        processors.append(_redact_text)

    renderer: Any = (
        structlog.dev.ConsoleRenderer(colors=False)
        if settings.app_env.lower() == "development"
        else structlog.processors.JSONRenderer()
    )
    processors.append(renderer)

    structlog.configure(
        processors=processors,
        wrapper_class=structlog.make_filtering_bound_logger(
            getattr(logging, settings.log_level.upper(), logging.INFO)
        ),
        # The stdlib factory is required because `add_logger_name` reads
        # `logger.name`. PrintLoggerFactory returns a PrintLogger without that
        # attribute, which makes the add_logger_name processor raise and would
        # break the exception handlers themselves.
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )


def _redact_text(
    _logger: Any, _method_name: str, event_dict: MutableMapping[str, Any]
) -> MutableMapping[str, Any]:
    """Replace obviously sensitive event-dict values before rendering."""
    sensitive = {"text", "message", "body", "content", "source", "translation"}
    for key in sensitive:
        if key in event_dict and isinstance(event_dict[key], str):
            event_dict[key] = f"<redacted {len(event_dict[key])} chars>"
    return event_dict


def get_logger(name: str) -> structlog.stdlib.BoundLogger:
    """Return a bound structlog logger for ``name``."""
    return structlog.get_logger(name)  # type: ignore[no-any-return]
