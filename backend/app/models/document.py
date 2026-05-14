import enum
from datetime import date, datetime
from typing import Optional, List
from sqlalchemy import String, Text, Date, DateTime, Integer, ForeignKey, Enum, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db import Base


class MeetingCategory(str, enum.Enum):
    party_congress           = "party_congress"
    plenum                   = "plenum"
    two_sessions_national    = "two_sessions_national"
    two_sessions_local       = "two_sessions_local"
    economic_work_conference = "economic_work_conference"
    politburo                = "politburo"
    five_year_plan           = "five_year_plan"


class MeetingType(Base):
    __tablename__ = "meeting_types"
    __table_args__ = (UniqueConstraint("category", "name_zh"),)

    id:       Mapped[int]             = mapped_column(primary_key=True)
    category: Mapped[MeetingCategory] = mapped_column(Enum(MeetingCategory, name="meeting_category"))
    name_zh:  Mapped[str]             = mapped_column(Text, nullable=False)
    name_en:  Mapped[str]             = mapped_column(Text, nullable=False)

    documents: Mapped[List["Document"]] = relationship(back_populates="meeting_type")


class Document(Base):
    __tablename__ = "documents"

    id:              Mapped[int]            = mapped_column(primary_key=True)
    meeting_type_id: Mapped[Optional[int]]  = mapped_column(ForeignKey("meeting_types.id"))
    title_zh:        Mapped[str]            = mapped_column(Text, nullable=False)
    title_en:        Mapped[Optional[str]]  = mapped_column(Text)
    meeting_date:    Mapped[date]           = mapped_column(Date, nullable=False)
    source_url:      Mapped[str]            = mapped_column(Text, nullable=False, unique=True)
    raw_text_zh:     Mapped[str]            = mapped_column(Text, nullable=False)
    raw_text_en:     Mapped[Optional[str]]  = mapped_column(Text)
    word_count_zh:   Mapped[Optional[int]]  = mapped_column(Integer)
    scraped_at:      Mapped[datetime]       = mapped_column(DateTime(timezone=True), default=datetime.utcnow)
    processed_at:    Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))

    meeting_type: Mapped[Optional[MeetingType]] = relationship(back_populates="documents")
    occurrences:  Mapped[List["TermOccurrence"]] = relationship(back_populates="document")  # type: ignore[name-defined]
    list_contexts: Mapped[List["ListContext"]]   = relationship(back_populates="document")  # type: ignore[name-defined]
