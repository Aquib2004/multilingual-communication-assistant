"""Declarative base and shared column conventions for all ORM models."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from sqlalchemy import DateTime, String
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


def utc_now() -> datetime:
    """Timezone-aware current UTC time.

    Every timestamp in this project is stored timezone-aware; naive datetimes
    are a recurring source of off-by-one-day verification bugs.
    """
    return datetime.now(UTC)


def new_uuid() -> str:
    """A new primary key, generated client-side so no DB extension is needed."""
    return str(uuid.uuid4())


class Base(DeclarativeBase):
    """Base class for every ORM model."""


class UUIDPrimaryKeyMixin:
    """Adds a portable string UUID primary key."""

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=new_uuid, index=True
    )


class TimestampMixin:
    """Adds ``created_at`` / ``updated_at``."""

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, nullable=False, index=True
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False
    )
