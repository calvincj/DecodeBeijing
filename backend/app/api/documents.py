from typing import Optional
from datetime import date
from pathlib import Path
import urllib.parse
from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc
from sqlalchemy.orm import joinedload
from pydantic import BaseModel

from app.db import get_db
from app.models.document import Document, MeetingType
from app.models.term import Term, TermOccurrence


router = APIRouter(prefix="/documents", tags=["documents"])


class DocumentOut(BaseModel):
    id: int
    title_zh: str
    title_en: Optional[str]
    meeting_date: date
    source_url: str
    word_count_zh: Optional[int]
    meeting_type: Optional[str]
    meeting_category: Optional[str]

    class Config:
        from_attributes = True


class DocumentDetailOut(DocumentOut):
    raw_text_zh: str


class DocumentTermOut(BaseModel):
    term_zh: str
    term_en: Optional[str]
    category: str
    frequency: int


@router.get("/", response_model=list[DocumentOut])
async def list_documents(
    meeting_type: Optional[str] = Query(None),
    from_date: Optional[date] = Query(None),
    to_date: Optional[date] = Query(None),
    limit: int = Query(200, le=500),
    offset: int = Query(0),
    db: AsyncSession = Depends(get_db),
):
    q = select(Document).options(joinedload(Document.meeting_type)).order_by(desc(Document.meeting_date))

    if meeting_type:
        q = q.join(MeetingType).where(MeetingType.category == meeting_type)
    if from_date:
        q = q.where(Document.meeting_date >= from_date)
    if to_date:
        q = q.where(Document.meeting_date <= to_date)

    result = await db.execute(q.limit(limit).offset(offset))
    docs = result.scalars().all()
    return [_serialize(d) for d in docs]


@router.get("/{doc_id}/terms", response_model=list[DocumentTermOut])
async def get_document_terms(doc_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(Term, TermOccurrence.frequency)
        .join(TermOccurrence, TermOccurrence.term_id == Term.id)
        .where(TermOccurrence.document_id == doc_id)
        .order_by(TermOccurrence.frequency.desc())
    )
    rows = result.all()
    return [
        {"term_zh": t.term_zh, "term_en": t.term_en, "category": t.category, "frequency": freq}
        for t, freq in rows
    ]


@router.get("/{doc_id}", response_model=DocumentDetailOut)
async def get_document(doc_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(Document).options(joinedload(Document.meeting_type)).where(Document.id == doc_id)
    )
    doc = result.scalar_one_or_none()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")

    # For locally stored files, serve the original unmodified text so the viewer
    # shows the full document (including ToC) rather than the NLP-cleaned version.
    display_text = doc.raw_text_zh
    if doc.source_url.startswith("file://"):
        try:
            file_path = Path(urllib.parse.urlparse(doc.source_url).path)
            if file_path.exists():
                display_text = file_path.read_text(encoding="utf-8")
        except Exception:
            pass  # fall back to stored text

    return {**_serialize(doc), "raw_text_zh": display_text}


def _serialize(doc: Document) -> dict:
    mt_name = None
    mt_cat = None
    if doc.meeting_type:
        mt_name = doc.meeting_type.name_en
        mt_cat = doc.meeting_type.category.value if doc.meeting_type.category else None
    return {
        "id": doc.id,
        "title_zh": doc.title_zh,
        "title_en": doc.title_en,
        "meeting_date": doc.meeting_date,
        "source_url": doc.source_url,
        "word_count_zh": doc.word_count_zh,
        "meeting_type": mt_name,
        "meeting_category": mt_cat,
    }
