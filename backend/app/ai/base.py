"""The provider interface and the request/response contracts around it.

Two rules shape this module:

1. The service layer never imports a vendor SDK. Providers translate their own
   native errors into the :class:`AIProviderError` hierarchy first.
2. Structured output is never trusted. A model response is validated against a
   Pydantic model, and malformed output fails closed.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Literal

from pydantic import BaseModel, Field, ValidationError

from app.core.errors import AIInvalidOutputError

#: The kinds of structured request this application makes.
TaskType = Literal["rewrite", "translate", "back_translate", "verify", "tone", "extract"]


@dataclass(slots=True)
class AIRequest:
    """One structured request to a provider.

    Attributes:
        task: Which pipeline stage this is for.
        system_prompt: Instructions for the model.
        user_prompt: The rendered user content.
        response_model: The Pydantic model the reply must satisfy.
        temperature: Sampling temperature. Low for verification, higher for
            rewriting.
        max_tokens: Upper bound on the reply length.
        metadata: Free-form context, never sent to the provider.
    """

    task: TaskType
    system_prompt: str
    user_prompt: str
    response_model: type[BaseModel]
    temperature: float = 0.2
    max_tokens: int = 2000
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class AIResponse:
    """A validated structured response."""

    data: dict[str, Any]
    provider: str
    model: str
    response_model: type[BaseModel]
    raw_text: str = ""
    duration_ms: int = 0

    def as_model(self) -> BaseModel:
        """Re-validate the payload into its Pydantic model.

        Returns:
            The validated model instance.

        Raises:
            AIInvalidOutputError: If the payload does not satisfy the schema.
        """
        return validate_structured(self.data, self.response_model)


def validate_structured(data: Any, model: type[BaseModel]) -> BaseModel:
    """Validate ``data`` against ``model``, failing closed.

    Args:
        data: The decoded provider payload.
        model: The schema it must satisfy.

    Returns:
        The validated model instance.

    Raises:
        AIInvalidOutputError: If validation fails. The provider's raw text is
            logged server-side but never returned to the user.
    """
    try:
        return model.model_validate(data)
    except ValidationError as exc:
        raise AIInvalidOutputError(
            "The language assistant returned a response that could not be read. Please retry.",
            details={"errors": exc.error_count()},
        ) from exc


class AIProvider(ABC):
    """Interface every provider implements.

    Attributes:
        name: Stable identifier, e.g. ``openai``.
        model: The specific model in use.
    """

    name: str = "base"
    model: str = "unknown"

    @abstractmethod
    async def complete(self, request: AIRequest) -> AIResponse:
        """Run one structured request and return a validated response.

        Args:
            request: The task, prompts, and expected schema.

        Returns:
            An :class:`AIResponse` whose ``data`` satisfies the schema.

        Raises:
            AIProviderError: On any upstream failure, including malformed output.
        """

    async def health(self) -> bool:
        """True when the provider is usable.

        The default reports usable without a network call, which is correct for
        the offline mock provider.
        """
        return True

    def describe(self) -> dict[str, str]:
        """Provider identity, for the health endpoint and stored records."""
        return {"provider": self.name, "model": self.model}


# --- Shared structured response schemas ------------------------------------


class RewriteChanges(BaseModel):
    """One 'what changed and why' entry."""

    original: str = Field(description="The wording before the change.")
    revised: str = Field(description="The wording after the change.")
    reason: str = Field(description="Why this improves clarity without changing the meaning.")


class RewriteOutput(BaseModel):
    """The plain-language engine's structured response."""

    rewritten_message: str = Field(description="The revised message.")
    changes: list[RewriteChanges] = Field(
        default_factory=list, description="Every change, with its reason."
    )
    open_questions: list[str] = Field(
        default_factory=list,
        description="Ambiguities that must be answered by a human, not guessed at.",
    )
    reading_level: dict[str, Any] = Field(default_factory=dict)
    protected_items_preserved: bool = Field(
        default=True,
        description="False if the model believes it altered a protected item.",
    )


class TranslationOutput(BaseModel):
    """The translation engine's structured response."""

    translated_message: str = Field(
        description="The translated text, with every placeholder still present."
    )
    uncertainties: list[str] = Field(
        default_factory=list, description="Anything the model was unsure about."
    )
    terminology_notes: list[str] = Field(
        default_factory=list, description="Recurring terms whose sense may be wrong locally."
    )
    tone_assessment: str = Field(
        default="unknown", description="welcoming, neutral, mechanical, patronising, alarming."
    )
    reading_level_note: str = Field(default="")


class BackTranslationOutput(BaseModel):
    """A back-translation of critical lines into English."""

    back_translated: str = Field(description="The English rendering.")
    meaning_preserved: bool = Field(
        description="True only if the meaning, action, and deadline are unchanged."
    )
    issues: list[str] = Field(default_factory=list, description="Any divergence from the source.")


class ToneOutput(BaseModel):
    """A pragmatic and terminological review."""

    tone: str = Field(description="welcoming, neutral, mechanical, patronising, or alarming.")
    mechanical_phrases: list[str] = Field(default_factory=list)
    cultural_awkwardness: list[str] = Field(default_factory=list)
    terminology_notes: list[str] = Field(default_factory=list)
    requires_human_review: bool = True
