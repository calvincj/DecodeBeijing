"""
Term endpoints — the core of the analysis tool.

Key endpoints:
  GET /terms/                     list all tracked terms
  GET /terms/{id}/frequency       time-series frequency across documents
  GET /terms/{id}/gaps            omission history
  GET /terms/compare              compare two terms side-by-side
  GET /terms/rankings             priority order tracking across documents
  POST /terms/                    add a new term to track
"""

from typing import Optional
from datetime import date
from fastapi import APIRouter, Depends, Query, HTTPException, Body
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc, asc, exists, func, extract
from sqlalchemy.orm import joinedload
from pydantic import BaseModel

from app.db import get_db
from app.models.term import Term, TermOccurrence, TermGap, TermCategory
from app.models.document import Document
from app.models.list_tracking import ListContext, ListEntry


router = APIRouter(prefix="/terms", tags=["terms"])


# ── Schemas ──────────────────────────────────────────────────────────────────

class TermOut(BaseModel):
    id: int
    term_zh: str
    term_en: Optional[str]
    category: str
    description: Optional[str]
    first_seen_date: Optional[date]
    added_by: str
    total_mentions: int = 0
    first_year: Optional[int] = None
    last_year: Optional[int] = None

    class Config:
        from_attributes = True


class FrequencyPoint(BaseModel):
    document_id: int
    title_zh: str
    meeting_date: date
    frequency: int
    context_snippets: Optional[list[str]]
    first_char_position: Optional[int]
    doc_word_count: Optional[int]
    meeting_category: Optional[str]


class GapOut(BaseModel):
    last_seen_date: date
    gap_start_date: date
    gap_end_date: Optional[date]
    gap_length_days: Optional[int]
    meetings_missed: int


class RankingPoint(BaseModel):
    document_id: int
    title_zh: str
    meeting_date: date
    list_name_zh: str
    position: int
    raw_text_zh: str


class FramingPoint(BaseModel):
    document_id: int
    meeting_date: date
    attitude: str
    key_phrase: Optional[str]
    explanation: Optional[str]


class TermCreate(BaseModel):
    term_zh: str
    term_en: Optional[str] = None
    category: TermCategory = TermCategory.other
    description: Optional[str] = None


# ── Routes ───────────────────────────────────────────────────────────────────

@router.get("/", response_model=list[TermOut])
async def list_terms(
    category: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db),
):
    total      = func.coalesce(func.sum(TermOccurrence.frequency), 0).label("total_mentions")
    first_year = func.min(
        extract("year", Document.meeting_date)
    ).filter(TermOccurrence.frequency > 0).label("first_year")
    last_year  = func.max(
        extract("year", Document.meeting_date)
    ).filter(TermOccurrence.frequency > 0).label("last_year")

    q = (
        select(Term, total, first_year, last_year)
        .outerjoin(TermOccurrence, TermOccurrence.term_id == Term.id)
        .outerjoin(Document, Document.id == TermOccurrence.document_id)
        .group_by(Term.id)
        .having(total > 0)
        .order_by(desc(total))
    )
    if category:
        q = q.where(Term.category == category)
    result = await db.execute(q)
    rows = result.all()
    out = []
    for term, mentions, fy, ly in rows:
        d = TermOut.model_validate(term)
        d.total_mentions = mentions
        d.first_year = int(fy) if fy else None
        d.last_year  = int(ly) if ly else None
        out.append(d)
    return out


@router.post("/", response_model=TermOut, status_code=201)
async def create_term(body: TermCreate, db: AsyncSession = Depends(get_db)):
    existing = await db.execute(select(Term).where(Term.term_zh == body.term_zh))
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=409, detail="Term already exists")
    term = Term(**body.model_dump(), added_by="manual")
    db.add(term)
    await db.commit()
    await db.refresh(term)
    return term


@router.get("/search/frequency", response_model=list[FrequencyPoint])
async def search_frequency(q: str = Query(..., min_length=1), db: AsyncSession = Depends(get_db)):
    """On-the-fly frequency of any arbitrary term across all documents."""
    result = await db.execute(
        select(Document)
        .options(joinedload(Document.meeting_type))
        .where(Document.raw_text_zh.contains(q))
        .order_by(Document.meeting_date)
    )
    docs = result.scalars().all()

    points = []
    for doc in docs:
        text  = doc.raw_text_zh
        count = 0
        idx   = 0
        snippets: list[str] = []
        while (idx := text.find(q, idx)) != -1:
            count += 1
            snippets.append(text[max(0, idx - 60): idx + len(q) + 60])
            idx += len(q)
        if count == 0:
            continue
        points.append(FrequencyPoint(
            document_id=doc.id,
            title_zh=doc.title_zh,
            meeting_date=doc.meeting_date,
            frequency=count,
            context_snippets=snippets[:5],
            first_char_position=None,
            doc_word_count=doc.word_count_zh,
            meeting_category=doc.meeting_type.category.value if doc.meeting_type else None,
        ))
    return points


@router.get("/{term_id}/frequency", response_model=list[FrequencyPoint])
async def get_term_frequency(
    term_id: int,
    meeting_type: Optional[str] = Query(None),
    from_date: Optional[date] = Query(None),
    to_date: Optional[date] = Query(None),
    db: AsyncSession = Depends(get_db),
):
    """
    Returns the frequency of a term across all documents, ordered by date.
    This is the primary data source for the time-series chart.
    """
    term = await db.get(Term, term_id)
    if not term:
        raise HTTPException(status_code=404, detail="Term not found")

    q = (
        select(TermOccurrence, Document)
        .join(Document, Document.id == TermOccurrence.document_id)
        .options(joinedload(Document.meeting_type))
        .where(TermOccurrence.term_id == term_id)
        .order_by(asc(Document.meeting_date))
    )
    if from_date:
        q = q.where(Document.meeting_date >= from_date)
    if to_date:
        q = q.where(Document.meeting_date <= to_date)

    result = await db.execute(q)
    rows = result.all()

    return [
        FrequencyPoint(
            document_id=doc.id,
            title_zh=doc.title_zh,
            meeting_date=doc.meeting_date,
            frequency=occ.frequency,
            context_snippets=occ.context_snippets,
            first_char_position=occ.char_positions[0] if occ.char_positions else None,
            doc_word_count=doc.word_count_zh,
            meeting_category=doc.meeting_type.category.value if doc.meeting_type else None,
        )
        for occ, doc in rows
    ]


@router.get("/{term_id}/gaps", response_model=list[GapOut])
async def get_term_gaps(term_id: int, db: AsyncSession = Depends(get_db)):
    """Returns all omission periods for this term."""
    term = await db.get(Term, term_id)
    if not term:
        raise HTTPException(status_code=404, detail="Term not found")

    result = await db.execute(
        select(TermGap)
        .where(TermGap.term_id == term_id)
        .order_by(asc(TermGap.gap_start_date))
    )
    return result.scalars().all()


@router.get("/{term_id}/rankings", response_model=list[RankingPoint])
async def get_term_rankings(term_id: int, db: AsyncSession = Depends(get_db)):
    """
    Shows where this term appears in policy priority lists across documents.
    Position 1 = first/most prominent. A rise or fall here is significant.
    """
    term = await db.get(Term, term_id)
    if not term:
        raise HTTPException(status_code=404, detail="Term not found")

    result = await db.execute(
        select(ListEntry, ListContext, Document)
        .join(ListContext, ListContext.id == ListEntry.list_context_id)
        .join(Document, Document.id == ListContext.document_id)
        .where(ListEntry.term_id == term_id)
        .order_by(asc(Document.meeting_date))
    )
    rows = result.all()

    return [
        RankingPoint(
            document_id=doc.id,
            title_zh=doc.title_zh,
            meeting_date=doc.meeting_date,
            list_name_zh=ctx.list_name_zh,
            position=entry.position,
            raw_text_zh=entry.raw_text_zh,
        )
        for entry, ctx, doc in rows
    ]


@router.get("/{term_id}/framing", response_model=list[FramingPoint])
async def get_term_framing(term_id: int, db: AsyncSession = Depends(get_db)):
    """
    Returns cached framing classifications from term_framing table.
    Populate the cache by running:  python scripts/analyze_framing.py
    """
    from pipeline.processors.framing_analyzer import fetch_cached_for_term, _ensure_table
    await _ensure_table(db)
    rows = await fetch_cached_for_term(term_id, db)
    return [
        FramingPoint(
            document_id=r["document_id"],
            meeting_date=r["meeting_date"],
            attitude=r["attitude"],
            key_phrase=r.get("key_phrase"),
            explanation=r.get("explanation"),
        )
        for r in rows
    ]


@router.get("/compare", response_model=dict)
async def compare_terms(
    a: int = Query(..., description="First term ID"),
    b: int = Query(..., description="Second term ID"),
    db: AsyncSession = Depends(get_db),
):
    """
    Side-by-side frequency comparison of two terms across shared documents.
    Returns aligned data suitable for a dual-line chart.
    """
    for term_id in [a, b]:
        if not await db.get(Term, term_id):
            raise HTTPException(status_code=404, detail=f"Term {term_id} not found")

    async def get_freq(term_id: int) -> dict[int, int]:
        result = await db.execute(
            select(TermOccurrence.document_id, TermOccurrence.frequency)
            .where(TermOccurrence.term_id == term_id)
        )
        return {row.document_id: row.frequency for row in result.all()}

    freq_a, freq_b = await get_freq(a), await get_freq(b)
    doc_ids = sorted(freq_a.keys() | freq_b.keys())

    docs_result = await db.execute(
        select(Document.id, Document.title_zh, Document.meeting_date)
        .where(Document.id.in_(doc_ids))
        .order_by(Document.meeting_date)
    )
    docs = {row.id: row for row in docs_result.all()}

    term_a = await db.get(Term, a)
    term_b = await db.get(Term, b)

    return {
        "term_a": {"id": a, "term_zh": term_a.term_zh, "term_en": term_a.term_en},
        "term_b": {"id": b, "term_zh": term_b.term_zh, "term_en": term_b.term_en},
        "series": [
            {
                "document_id": did,
                "title_zh": docs[did].title_zh,
                "meeting_date": docs[did].meeting_date,
                "freq_a": freq_a.get(did, 0),
                "freq_b": freq_b.get(did, 0),
            }
            for did in doc_ids
            if did in docs
        ],
    }
