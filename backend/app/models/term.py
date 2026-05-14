import enum
from datetime import date, datetime
from typing import Optional, List
from sqlalchemy import Text, Date, DateTime, Integer, ForeignKey, Enum, ARRAY
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db import Base


class TermCategory(str, enum.Enum):
    slogan        = "slogan"
    policy_phrase = "policy_phrase"
    ideological   = "ideological"
    economic      = "economic"
    diplomatic    = "diplomatic"
    technology    = "technology"
    other         = "other"


class Term(Base):
    __tablename__ = "terms"

    id:              Mapped[int]           = mapped_column(primary_key=True)
    term_zh:         Mapped[str]           = mapped_column(Text, nullable=False, unique=True)
    term_en:         Mapped[Optional[str]] = mapped_column(Text)
    category:        Mapped[TermCategory]  = mapped_column(
        Enum(TermCategory, name="term_category"), default=TermCategory.other
    )
    description:     Mapped[Optional[str]] = mapped_column(Text)
    first_seen_doc:  Mapped[Optional[int]] = mapped_column(ForeignKey("documents.id"))
    first_seen_date: Mapped[Optional[date]] = mapped_column(Date)
    added_by:        Mapped[str]           = mapped_column(Text, default="auto")
    created_at:      Mapped[datetime]      = mapped_column(DateTime(timezone=True), default=datetime.utcnow)

    occurrences: Mapped[List["TermOccurrence"]] = relationship(back_populates="term")
    gaps:        Mapped[List["TermGap"]]        = relationship(back_populates="term")


class TermOccurrence(Base):
    __tablename__ = "term_occurrences"

    id:               Mapped[int]          = mapped_column(primary_key=True)
    term_id:          Mapped[int]          = mapped_column(ForeignKey("terms.id"), nullable=False)
    document_id:      Mapped[int]          = mapped_column(ForeignKey("documents.id"), nullable=False)
    frequency:        Mapped[int]          = mapped_column(Integer, default=0)
    char_positions:   Mapped[Optional[List[int]]] = mapped_column(ARRAY(Integer))
    context_snippets: Mapped[Optional[List[str]]] = mapped_column(ARRAY(Text))

    term:     Mapped["Term"]     = relationship(back_populates="occurrences")
    document: Mapped["Document"] = relationship(back_populates="occurrences")  # type: ignore[name-defined]


class TermGap(Base):
    __tablename__ = "term_gaps"

    id:               Mapped[int]           = mapped_column(primary_key=True)
    term_id:          Mapped[int]           = mapped_column(ForeignKey("terms.id"), nullable=False)
    last_seen_doc:    Mapped[int]           = mapped_column(ForeignKey("documents.id"), nullable=False)
    last_seen_date:   Mapped[date]          = mapped_column(Date, nullable=False)
    gap_start_date:   Mapped[date]          = mapped_column(Date, nullable=False)
    gap_end_date:     Mapped[Optional[date]] = mapped_column(Date)
    gap_length_days:  Mapped[Optional[int]]  = mapped_column(Integer)
    meetings_missed:  Mapped[int]           = mapped_column(Integer, default=0)

    term: Mapped["Term"] = relationship(back_populates="gaps")
