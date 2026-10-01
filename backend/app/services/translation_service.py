"""Translation service: placeholder-preserving translation of approved text.

The safety property of this stage is that a date, URL, or phone number is never
*asked* to be translated. Protected values are masked, the surrounding text is
translated, and the values are restored verbatim before anything is stored.
"""

from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.base import AIProvider, AIRequest, TranslationOutput
from app.ai.prompts.translation import TRANSLATION_SYSTEM, TRANSLATION_USER
from app.core.config import Settings
from app.core.errors import TooFewLanguagesError
from app.core.languages import Language, get_language
from app.core.logging import get_logger
from app.models.message import Message, MessageState
from app.models.protected_item import ProtectedItem
from app.models.translation import Translation
from app.services.message_service import MessageService
from app.verification.fact_extractor import (
    ExtractedItem,
    mask_placeholders,
    restore_placeholders,
)

logger = get_logger(__name__)


class TranslationService:
    """Translate an approved message into two or three target languages."""

    def __init__(self, provider: AIProvider, settings: Settings) -> None:
        """Bind the provider and settings.

        Args:
            provider: The configured :class:`AIProvider`.
            settings: Runtime settings, used for the language-count rules.
        """
        self._provider = provider
        self._settings = settings

    async def translate(
        self,
        session: AsyncSession,
        message: Message,
        *,
        target_languages: list[str],
        locale: str | None = None,
        tone: str | None = None,
        reading_level: str | None = None,
    ) -> list[Translation]:
        """Translate an approved message.

        Args:
            session: Active database session.
            message: The workspace. It must already be approved.
            target_languages: Two or three language codes.
            locale: BCP-47 tag used for date and time conventions.
            tone: Tone override for this run.
            reading_level: Reading-level target, e.g. ``grade 6``.

        Returns:
            The created :class:`Translation` rows, one per language.

        Raises:
            SourceNotApprovedError: If the message has not been approved.
            TooFewLanguagesError: If fewer than two languages were requested.
            UnsupportedLanguageError: If a requested language is not registered.
        """
        # The gate. Nothing downstream of this line is reachable without it.
        approved_text = await MessageService(self._provider).assert_approved(message)

        languages = self._resolve_languages(target_languages)
        active_locale = locale or message.locale
        active_tone = tone or message.tone

        source_items = self._items_from(message.protected_items)
        masked_text, mapping = mask_placeholders(approved_text, source_items)

        created: list[Translation] = []
        for language in languages:
            created.append(
                await self._translate_one(
                    session,
                    message,
                    language=language,
                    masked_text=masked_text,
                    mapping=mapping,
                    locale=active_locale,
                    tone=active_tone,
                    reading_level=reading_level or "grade 6-8",
                )
            )

        message.state = MessageState.TRANSLATED
        codes = [lang.code for lang in languages]
        if message.target_languages != codes:
            message.target_languages = codes
        await session.flush()

        logger.info(
            "translations created",
            message_id=message.id,
            languages=codes,
            provider=self._provider.name,
        )
        return created

    async def _translate_one(
        self,
        session: AsyncSession,
        message: Message,
        *,
        language: Language,
        masked_text: str,
        mapping: dict[str, str],
        locale: str,
        tone: str,
        reading_level: str,
    ) -> Translation:
        """Translate into one language and store the result."""
        request = AIRequest(
            task="translate",
            system_prompt=TRANSLATION_SYSTEM.format(
                source_language="English",
                target_language=language.name,
                audience=message.audience or "families and community members",
                purpose=message.purpose or "not stated",
                locale=locale,
                tone=tone,
                reading_level=reading_level,
            ),
            user_prompt=TRANSLATION_USER.format(
                text=masked_text,
                target_language=language.name,
            ),
            response_model=TranslationOutput,
            temperature=0.2,
            metadata={"target_language": language.code, "locale": locale, "tone": tone},
        )

        response = await self._provider.complete(request)
        output = TranslationOutput.model_validate(response.data)

        restored, missing = restore_placeholders(output.translated_message, mapping)

        uncertainties = list(output.uncertainties)
        if missing:
            # A dropped placeholder is a dropped fact. Never pass it through.
            uncertainties.append(
                "The translation omitted or altered these protected items, which "
                f"were restored from the source: {', '.join(missing)}."
            )

        translation = Translation(
            message_id=message.id,
            target_language=language.code,
            locale=locale,
            translated_message=restored,
            placeholders=mapping,
            protected_items=[item.to_dict() for item in self._items_from(message.protected_items)],
            uncertainties=sorted(set(uncertainties)),
            terminology_notes=output.terminology_notes,
            provider=response.provider,
            model=response.model,
        )
        session.add(translation)
        await session.flush()
        return translation

    def _resolve_languages(self, codes: list[str]) -> list[Language]:
        """Validate and de-duplicate the requested language codes.

        Args:
            codes: Requested language codes.

        Returns:
            The resolved :class:`Language` objects.

        Raises:
            TooFewLanguagesError: If fewer than the required number were given.
            UnsupportedLanguageError: If a code is not registered.
        """
        unique: list[Language] = []
        seen: set[str] = set()

        for code in codes:
            normalized = code.strip().lower()
            if not normalized or normalized in seen:
                continue
            # The source language is not a translation target.
            if normalized == "en":
                continue
            language = get_language(normalized)
            seen.add(normalized)
            unique.append(language)

        if len(unique) < self._settings.min_target_languages:
            raise TooFewLanguagesError(
                f"Select at least {self._settings.min_target_languages} target languages "
                "other than English, for example Spanish and Hindi."
            )
        if len(unique) > self._settings.max_target_languages:
            raise TooFewLanguagesError(
                f"Select at most {self._settings.max_target_languages} target languages."
            )
        return unique

    @staticmethod
    def _items_from(rows: list[ProtectedItem]) -> list[ExtractedItem]:
        """Convert stored protected items into extractor objects."""
        return [
            ExtractedItem(
                item_type=row.item_type.value,
                value=row.value,
                must_match_exactly=row.must_match_exactly,
                start_offset=row.start_offset,
                end_offset=row.end_offset,
                context_sentence=row.context_sentence,
                source=row.source,
                placeholder=row.placeholder,
            )
            for row in rows
        ]
