import enum
from datetime import date, datetime, timezone

from sqlalchemy import Column, Date, DateTime, Enum, ForeignKey, String, Table, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.db import Base
from app.models.tag import Tag


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Difficulty(str, enum.Enum):
    beginner = "beginner"
    intermediate = "intermediate"
    advanced = "advanced"


entry_tags = Table(
    "entry_tags",
    Base.metadata,
    Column("entry_id", ForeignKey("entries.id", ondelete="CASCADE"), primary_key=True),
    Column("tag_id", ForeignKey("tags.id", ondelete="CASCADE"), primary_key=True),
)


class Entry(Base):
    __tablename__ = "entries"

    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str] = mapped_column(String(120))
    slug: Mapped[str] = mapped_column(String(100), unique=True, index=True)
    content: Mapped[str] = mapped_column(Text)
    code_snippet: Mapped[str | None] = mapped_column(Text, default=None)
    language: Mapped[str | None] = mapped_column(String(30), index=True, default=None)
    difficulty: Mapped[Difficulty] = mapped_column(Enum(Difficulty), default=Difficulty.beginner)
    reference_url: Mapped[str | None] = mapped_column(String(500), default=None)
    learned_on: Mapped[date] = mapped_column(Date, default=date.today, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)

    tags: Mapped[list[Tag]] = relationship(secondary=entry_tags, back_populates="entries", lazy="selectin")
