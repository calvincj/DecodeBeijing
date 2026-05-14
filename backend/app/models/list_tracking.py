from datetime import datetime
from typing import Optional, List
from sqlalchemy import Text, DateTime, Integer, ForeignKey, SmallInteger, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db import Base


class ListContext(Base):
    __tablename__ = "list_contexts"

    id:           Mapped[int]           = mapped_column(primary_key=True)
    document_id:  Mapped[int]           = mapped_column(ForeignKey("documents.id"), nullable=False)
    list_name_zh: Mapped[str]           = mapped_column(Text, nullable=False)
    list_name_en: Mapped[Optional[str]] = mapped_column(Text)
    extracted_at: Mapped[datetime]      = mapped_column(DateTime(timezone=True), default=datetime.utcnow)

    document: Mapped["Document"]      = relationship(back_populates="list_contexts")  # type: ignore[name-defined]
    entries:  Mapped[List["ListEntry"]] = relationship(back_populates="list_context", order_by="ListEntry.position")


class ListEntry(Base):
    __tablename__ = "list_entries"
    __table_args__ = (UniqueConstraint("list_context_id", "position"),)

    id:              Mapped[int]           = mapped_column(primary_key=True)
    list_context_id: Mapped[int]           = mapped_column(ForeignKey("list_contexts.id"), nullable=False)
    term_id:         Mapped[Optional[int]] = mapped_column(ForeignKey("terms.id"))
    raw_text_zh:     Mapped[str]           = mapped_column(Text, nullable=False)
    raw_text_en:     Mapped[Optional[str]] = mapped_column(Text)
    position:        Mapped[int]           = mapped_column(SmallInteger, nullable=False)

    list_context: Mapped["ListContext"] = relationship(back_populates="entries")
