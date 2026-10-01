"""Message lifecycle: the workspace, the rewrite, and the approval gate.

This module owns the state machine that makes human approval non-skippable. It
is the reason a translation can never be produced from an unapproved source.
"""

from __future__ import annotations

from typing import Any
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.base import AIProvider, AIRequest, RewriteOutput
from app.ai.prompts.plain_language import PLAIN_LANGUAGE_SYSTEM, PLAIN_LANGUAGE_USER
from app.core.errors import (
    InvalidStateTransitionError,
    MessageNotFoundError,
    SourceNotApprovedError,
    ValidationError,
)
from app.core.languages import get_locale
from app.core.logging import get_logger
from app.core.security import PRIVACY_WARNING, PIIFinding, screen_for_pii
from app.models.message import Message, MessageState, RiskLevel
from app.models.protected_item import ProtectedItem, ProtectedItemType
from app.schemas.message import ProtectedItemInput
from app.verification.fact_extractor import ExtractedItem, extract_protected_items

logger = get_logger(__name__)


class MessageService:
    """Create, revise, approve, and inspect communication workspaces."""

    def __init__(self, provider: AIProvider) -> None:
        """Bind the AI provider used for the rewrite stage.

        Args:
            provider: The configured :class:`AIProvider`.
        """
        self._provider = provider

    # --- Reads --------------------------------------------------------------

    async def get(self, session: AsyncSession, message_id: str | UUID) -> Message:
        """Fetch one workspace or raise.

        Args:
            session: Active database session.
            message_id: The workspace identifier.

        Returns:
            The :class:`Message`.

        Raises:
            MessageNotFoundError: If no such workspace exists.
        """
        message = await session.get(Message, str(message_id))
        if message is None:
            raise MessageNotFoundError
        return message

    async def list_recent(
        self,
        session: AsyncSession,
        *,
        limit: int = 20,
        offset: int = 0,
        state: MessageState | None = None,
        risk_level: RiskLevel | None = None,
    ) -> tuple[list[Message], int]:
        """List workspaces newest first.

        Args:
            session: Active database session.
            limit: Page size, 1-100.
            offset: Page offset.
            state: Optional state filter.
            risk_level: Optional risk filter.

        Returns:
            The page of messages and the total matching count.
        """
        query = select(Message)
        if state is not None:
            query = query.where(Message.state == state)
        if risk_level is not None:
            query = query.where(Message.risk_level == risk_level)

        total = await session.scalar(select(func.count()).select_from(query.subquery()))
        result = await session.execute(
            query.order_by(Message.created_at.desc()).limit(limit).offset(offset)
        )
        return list(result.scalars().all()), int(total or 0)

    # --- Approval gate ------------------------------------------------------

    async def approve(
        self,
        session: AsyncSession,
        message: Message,
        *,
        reviewer: str | None = None,
        notes: str | None = None,
    ) -> Message:
        """Approve the revision. This is the gate that translation depends on.

        The exact approved text is frozen onto the message, and translation
        always reads that frozen text rather than the original source.

        Args:
            session: Active database session.
            message: The workspace to approve.
            reviewer: Initials or name of the approver.
            notes: Optional approval note.

        Returns:
            The updated :class:`Message` in state ``APPROVED``.

        Raises:
            InvalidStateTransitionError: If there is no revision to approve, or
                the message is already approved.
        """
        if message.state is MessageState.APPROVED:
            msg = "This message has already been approved."
            raise InvalidStateTransitionError(msg)

        if not message.revised_message:
            msg = "Rewrite the message before approving it."
            raise InvalidStateTransitionError(msg)

        from app.db.base import utc_now

        message.approved_message = message.revised_message
        message.approved_at = utc_now()
        message.approved_by = reviewer
        message.approval_notes = notes
        message.state = MessageState.APPROVED

        await self.refresh_protected_items(session, message)
        await session.flush()

        logger.info("message approved", message_id=message.id, reviewer=reviewer or "anonymous")
        return message

    async def reject(self, session: AsyncSession, message: Message, *, notes: str) -> Message:
        """Send a revision back with feedback.

        Args:
            session: Active database session.
            message: The workspace to revise again.
            notes: What the reviewer wants changed.

        Returns:
            The updated :class:`Message` in state ``DRAFT``.

        Raises:
            InvalidStateTransitionError: If the message is already approved.
        """
        if message.state is MessageState.APPROVED:
            msg = "This message is already approved. Create a new one to revise it."
            raise InvalidStateTransitionError(msg)

        message.state = MessageState.DRAFT
        message.reviewer_feedback = notes
        message.revised_message = None
        message.approved_message = None
        await session.flush()
        return message

    async def assert_approved(self, message: Message) -> str:
        """Return the approved text, or refuse.

        This is the single guard that makes the approval gate real.

        Args:
            message: The workspace to check.

        Returns:
            The frozen approved text.

        Raises:
            SourceNotApprovedError: If the message has not been approved.
        """
        if message.state is not MessageState.APPROVED or not message.approved_message:
            raise SourceNotApprovedError
        return message.approved_message

    async def create(
        self,
        session: AsyncSession,
        *,
        source_message: str,
        audience: str = "",
        purpose: str = "",
        action: str = "",
        deadline: str = "",
        contact_path: str = "",
        tone: str = "warm, respectful, direct",
        risk_level: RiskLevel = RiskLevel.ROUTINE,
        target_languages: list[str] | None = None,
        locale: str = "en-US",
        protected_items: list[ProtectedItemInput] | None = None,
    ) -> Message:
        """Create a workspace from a source message.

        PII screening happens here so the warning is stored with the workspace
        and shown on every later view.

        Args:
            session: Active database session.
            source_message: The original message.
            audience: Who the message is for.
            purpose: Why the message is being sent.
            action: What the reader is asked to do.
            deadline: When a response is expected.
            contact_path: How to ask a question.
            tone: Desired tone.
            risk_level: The user's own risk assessment.
            target_languages: Requested target language codes.
            locale: BCP-47 locale hint.
            protected_items: Items the user declared must not change.

        Returns:
            The created :class:`Message` in state ``DRAFT``.

        Raises:
            ValidationError: If the source is empty.
        """
        text = source_message.strip()
        if not text:
            msg = "A source message is required."
            raise ValidationError(msg)

        findings = screen_for_pii(text)
        message = Message(
            source_message=text,
            audience=audience,
            purpose=purpose,
            action=action,
            deadline=deadline,
            contact_path=contact_path,
            tone=tone,
            risk_level=risk_level,
            target_languages=target_languages or [],
            locale=locale,
            state=MessageState.DRAFT,
            pii_warnings=[self._finding_to_dict(f) for f in findings],
        )
        session.add(message)
        await session.flush()

        if protected_items:
            await self._store_protected_items(session, message, text, protected_items)

        logger.info("message created", message_id=message.id, pii_findings=len(findings))
        return message

    async def rewrite(
        self,
        session: AsyncSession,
        *,
        source_message: str,
        audience: str = "",
        purpose: str = "",
        action: str = "",
        deadline: str = "",
        contact_path: str = "",
        tone: str = "warm, respectful, direct",
        risk_level: RiskLevel = RiskLevel.ROUTINE,
    ) -> tuple[RewriteOutput, list[PIIFinding], str, str]:
        """Run the plain-language engine.

        Args:
            session: Active database session.
            source_message: The text to revise.
            audience: Who the message is for.
            purpose: Why it is being sent.
            action: What the reader is asked to do.
            deadline: When a response is expected.
            contact_path: How to ask a question.
            tone: Desired tone.
            risk_level: The user's own risk assessment.

        Returns:
            A ``(output, pii_findings, provider, model)`` tuple.

        Raises:
            ValidationError: If the source is empty.
        """
        text = source_message.strip()
        if not text:
            msg = "There is no text to rewrite."
            raise ValidationError(msg)

        findings = screen_for_pii(text)

        request = AIRequest(
            task="rewrite",
            system_prompt=PLAIN_LANGUAGE_SYSTEM,
            user_prompt=PLAIN_LANGUAGE_USER.format(
                audience=audience or "families and community members",
                purpose=purpose or "not stated",
                action=action or "not stated",
                deadline=deadline or "not stated",
                contact_path=contact_path or "not stated",
                tone=tone,
                risk_level=risk_level.value,
                source_message=text,
            ),
            response_model=RewriteOutput,
            temperature=0.3,
        )
        response = await self._provider.complete(request)
        output = RewriteOutput.model_validate(response.data)

        if not output.protected_items_preserved:
            output.open_questions.append(
                "The rewrite may have altered a protected item. Compare the two "
                "versions before approving."
            )

        logger.info(
            "message rewritten",
            provider=response.provider,
            changes=len(output.changes),
            questions=len(output.open_questions),
        )
        return output, findings, response.provider, response.model

    async def apply_revision(
        self,
        session: AsyncSession,
        message: Message,
        output: RewriteOutput,
        pii_warnings: list[PIIFinding] | None = None,
    ) -> Message:
        """Store a revision on a workspace, moving it to ``REVISED``.

        Args:
            session: Active database session.
            message: The workspace to update.
            output: The rewrite result.
            pii_warnings: PII findings to persist.

        Returns:
            The updated :class:`Message`.
        """
        message.revised_message = output.rewritten_message
        message.changes = [change.model_dump() for change in output.changes]
        message.open_questions = list(output.open_questions)
        message.reading_level = output.reading_level
        if pii_warnings:
            message.pii_warnings = [self._finding_to_dict(f) for f in pii_warnings]
        message.state = MessageState.REVISED
        await session.flush()
        return message

    # --- Protected items ----------------------------------------------------

    async def refresh_protected_items(
        self, session: AsyncSession, message: Message
    ) -> list[ProtectedItem]:
        """Re-extract protected items from the approved text.

        Args:
            session: Active database session.
            message: The workspace whose approved text should be scanned.

        Returns:
            The stored :class:`ProtectedItem` rows.
        """
        text = message.approved_message or message.source_message
        result = extract_protected_items(text, get_locale(message.locale))
        message.open_questions = list(result.open_questions)

        # Explicitly reload the relationship. After a commit the attributes are
        # expired, and a lazy load in async context would raise MissingGreenlet.
        await session.refresh(message, ["protected_items"])

        for existing in list(message.protected_items):
            await session.delete(existing)
        message.protected_items = []

        for item in result.items:
            message.protected_items.append(
                ProtectedItem(
                    item_type=ProtectedItemType(item.item_type),
                    value=item.value,
                    placeholder=item.placeholder,
                    must_match_exactly=item.must_match_exactly,
                    start_offset=item.start_offset,
                    end_offset=item.end_offset,
                    context_sentence=item.context_sentence,
                    source=item.source,
                )
            )

        await session.flush()
        return message.protected_items

    async def _store_protected_items(
        self,
        session: AsyncSession,
        message: Message,
        text: str,
        declared: list[ProtectedItemInput],
    ) -> None:
        """Persist items the user explicitly declared.

        User-declared items are applied first so an explicit "this must not
        change" always outranks what the extractor infers.
        """
        user_items = [
            ExtractedItem(
                item_type=item.item_type.value,
                value=item.value,
                must_match_exactly=item.must_match_exactly,
                start_offset=text.find(item.value) if item.value in text else None,
            )
            for item in declared
        ]
        result = extract_protected_items(text, get_locale(message.locale), user_items)

        for item in result.items:
            if item.source != "user":
                continue
            message.protected_items.append(
                ProtectedItem(
                    item_type=ProtectedItemType(item.item_type),
                    value=item.value,
                    placeholder=item.placeholder,
                    must_match_exactly=item.must_match_exactly,
                    start_offset=item.start_offset,
                    end_offset=item.end_offset,
                    context_sentence=item.context_sentence,
                    source="user",
                )
            )
        await session.flush()

    async def delete(self, session: AsyncSession, message: Message) -> None:
        """Delete a workspace and everything cascading from it.

        This is the privacy deletion path, so translations and verification
        reports must go with it. The ORM cascade handles that.

        Args:
            session: Active database session.
            message: The workspace to remove.
        """
        message_id = message.id
        await session.delete(message)
        await session.flush()
        logger.info("message deleted", message_id=message_id)

    # --- Helpers ------------------------------------------------------------

    @staticmethod
    def _finding_to_dict(finding: PIIFinding) -> dict[str, Any]:
        """Convert a PII finding into the stored, user-facing shape."""
        return {
            "category": finding.category,
            "excerpt": finding.excerpt,
            "severity": finding.severity,
            "guidance": PRIVACY_WARNING,
        }
