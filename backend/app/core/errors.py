"""Domain error types.

Every error carries a stable machine-readable ``code``, an HTTP ``status``, and
a **user-safe** message. Internal detail belongs in the log, never in the
response body.
"""

from __future__ import annotations

from typing import Any


class AppError(Exception):
    """Base class for all expected, user-visible application errors."""

    code: str = "INTERNAL_ERROR"
    status_code: int = 500
    default_message: str = "An unexpected error occurred."

    def __init__(
        self,
        message: str | None = None,
        *,
        code: str | None = None,
        status_code: int | None = None,
        details: dict[str, Any] | None = None,
    ) -> None:
        self.message = message or self.default_message
        if code is not None:
            self.code = code
        if status_code is not None:
            self.status_code = status_code
        self.details = details or {}
        super().__init__(self.message)

    def to_payload(self) -> dict[str, Any]:
        """The user-safe representation of this error."""
        payload: dict[str, Any] = {"code": self.code, "message": self.message}
        if self.details:
            payload["details"] = self.details
        return payload


# --- Domain errors -----------------------------------------------------------


class NotFoundError(AppError):
    """A requested resource does not exist."""

    code = "NOT_FOUND"
    status_code = 404
    default_message = "The requested resource was not found."


class MessageNotFoundError(NotFoundError):
    code = "MESSAGE_NOT_FOUND"
    default_message = "Message not found."


class TranslationNotFoundError(NotFoundError):
    code = "TRANSLATION_NOT_FOUND"
    default_message = "Translation not found."


class VerificationNotFoundError(NotFoundError):
    code = "VERIFICATION_NOT_FOUND"
    default_message = "Verification report not found."


class InvalidStateTransitionError(AppError):
    """The operation is not allowed in the message's current state."""

    code = "INVALID_STATE_TRANSITION"
    status_code = 409
    default_message = "That action is not allowed at the current stage."


class SourceNotApprovedError(AppError):
    """The approval gate refused the request.

    Raised whenever a translation is requested for a source that a human has
    not yet approved. This is the single most important guard in the product.
    """

    code = "SOURCE_NOT_APPROVED"
    status_code = 409
    default_message = (
        "The source message must be reviewed and approved before it can be translated."
    )


class ValidationError(AppError):
    """Domain-level validation failure (not schema validation)."""

    code = "VALIDATION_ERROR"
    status_code = 422
    default_message = "The request could not be processed as submitted."


class UnsupportedLanguageError(AppError):
    """A requested target language or locale is not registered."""

    code = "UNSUPPORTED_LANGUAGE"
    status_code = 400
    default_message = "That language is not supported."


class TooFewLanguagesError(AppError):
    """Fewer target languages were requested than the workflow requires."""

    code = "MINIMUM_TWO_LANGUAGES"
    status_code = 400
    default_message = "Select at least two target languages."


class DatabaseError(AppError):
    """The database was unreachable or rejected the operation."""

    code = "DATABASE_ERROR"
    status_code = 503
    default_message = "The service is temporarily unable to store your work. Please retry."


# --- AI provider errors ------------------------------------------------------


class AIProviderError(AppError):
    """Base class for AI provider failures.

    The service layer never sees a vendor-specific exception; providers map
    their native errors onto these before re-raising.
    """

    code = "AI_PROVIDER_ERROR"
    status_code = 502
    default_message = (
        "The language assistant is temporarily unavailable. Your work is saved - please retry."
    )


class AIProviderAuthError(AIProviderError):
    code = "AI_PROVIDER_AUTH_ERROR"
    status_code = 502
    default_message = "The language assistant is not configured correctly. Contact the administrator."


class AIProviderRateLimitError(AIProviderError):
    code = "AI_PROVIDER_RATE_LIMIT"
    status_code = 429
    default_message = "The language assistant is busy right now. Please retry in a moment."


class AIProviderTimeoutError(AIProviderError):
    code = "AI_PROVIDER_TIMEOUT"
    status_code = 504
    default_message = "The language assistant took too long to respond. Please retry."


class AIInvalidOutputError(AIProviderError):
    """The model returned output that failed schema validation.

    Failing closed here is deliberate: a malformed response is never partially
    trusted.
    """

    code = "AI_INVALID_OUTPUT"
    status_code = 502
    default_message = (
        "The language assistant returned an unusable response. Please retry, or switch provider."
    )
