"""A single fact that must survive translation unchanged."""

from __future__ import annotations

from enum import StrEnum
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:  # pragma: no cover
    from app.models.message import Message


class ProtectedItemType(StrEnum):
    """Categories of protected information.

    ``deadline``, ``action`` and ``condition`` are the semantic categories the
    comparator cares about most; the rest are literal values that must be
    reproduced character-for-character.
    """

    DATE = "date"
    TIME = "time"
    DATETIME = "datetime"
    NUMBER = "number"
    MONEY = "money"
    URL = "url"
    EMAIL = "email"
    PHONE = "phone"
    NAME = "name"
    PROGRAM = "program"
    PLACE = "place"
    DEADLINE = "deadline"
    ACTION = "action"
    CONDITION = "condition"
    CONTACT = "contact"
    ADDRESS = "address"
    CODE = "code"


#: Types whose value must be reproduced exactly, character for character.
EXACT_MATCH_TYPES: frozenset[ProtectedItemType] = frozenset(
    {
        ProtectedItemType.URL,
        ProtectedItemType.EMAIL,
        ProtectedItemType.CODE,
        ProtectedItemType.ADDRESS,
    }
)

#: Types compared digit-wise, ignoring punctuation and spacing.
NUMERIC_MATCH_TYPES: frozenset[ProtectedItemType] = frozenset(
    {ProtectedItemType.PHONE, ProtectedItemType.NUMBER, ProtectedItemType.MONEY}
)


class ProtectedItem(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """One protected fact, located in the approved source.

    Each item is assigned a placeholder (``P1``, ``P2``, ...) that replaces the
    value during the model call. The original value is restored afterwards and
    then verified, which is why a model can never "translate" a phone number.
    """

    __tablename__ = "protected_items"

    message_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("messages.id", ondelete="CASCADE"), nullable=False, index=True
    )
    item_type: Mapped[ProtectedItemType] = mapped_column(
        String(24), nullable=False, index=True
    )
    value: Mapped[str] = mapped_column(Text, nullable=False)
    placeholder: Mapped[str] = mapped_column(String(16), nullable=False)
    must_match_exactly: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    start_offset: Mapped[int | None] = mapped_column(Integer, nullable=True)
    end_offset: Mapped[int | None] = mapped_column(Integer, nullable=True)

    #: The sentence this item appears in. Used to isolate critical lines for
    #: back-translation.
    context_sentence: Mapped[str | None] = mapped_column(Text, nullable=True)

    #: Whether a human (rather than a regex) supplied this item.
    source: Mapped[str] = mapped_column(String(16), default="auto", nullable=False)

    message: Mapped[Message] = relationship(back_populates="protected_items")

    def __repr__(self) -> str:  # pragma: no cover - debugging aid
        return f"<ProtectedItem {self.item_type}:{self.value[:16]}>"
