from datetime import datetime
from typing import Optional
from sqlalchemy import Text, DateTime, Integer, ForeignKey, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column
from app.db import Base


class DocumentDiff(Base):
    __tablename__ = "document_diffs"
    __table_args__ = (UniqueConstraint("doc_a_id", "doc_b_id"),)

    id:          Mapped[int]           = mapped_column(primary_key=True)
    doc_a_id:    Mapped[int]           = mapped_column(ForeignKey("documents.id"), nullable=False)
    doc_b_id:    Mapped[int]           = mapped_column(ForeignKey("documents.id"), nullable=False)
    diff_json:   Mapped[dict]          = mapped_column(JSONB, nullable=False)
    summary_en:  Mapped[Optional[str]] = mapped_column(Text)
    computed_at: Mapped[datetime]      = mapped_column(DateTime(timezone=True), default=datetime.utcnow)
