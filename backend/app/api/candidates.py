"""
Candidate terms review API.

GET  /candidates/          — list unreviewed candidates
POST /candidates/{id}/accept  — promote to tracked terms table
POST /candidates/{id}/dismiss — mark as not significant
"""

from typing import Optional
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text, select
from pydantic import BaseModel
from datetime import datetime

from app.db import get_db
from app.models.term import Term, TermCategory

router = APIRouter(prefix="/candidates", tags=["candidates"])


class CandidateOut(BaseModel):
    id: int
    document_id: int
    term_zh: str
    term_en: Optional[str]
    category: str
    signal: str
    significance: Optional[str]
    frequency: Optional[int]
    prior_avg: Optional[float]
    context: Optional[str]
    created_at: str


@router.get("/", response_model=list[CandidateOut])
async def list_candidates(db: AsyncSession = Depends(get_db)):
    rows = await db.execute(
        text("SELECT * FROM candidate_terms WHERE NOT reviewed ORDER BY created_at DESC LIMIT 100")
    )
    return [dict(r._mapping) for r in rows.all()]


@router.post("/{candidate_id}/accept", response_model=dict)
async def accept_candidate(
    candidate_id: int,
    db: AsyncSession = Depends(get_db),
):
    """Promote this candidate into the tracked terms table."""
    row = await db.execute(
        text("SELECT * FROM candidate_terms WHERE id = :id"), {"id": candidate_id}
    )
    candidate = row.mappings().first()
    if not candidate:
        raise HTTPException(status_code=404, detail="Candidate not found")

    # Check if term already tracked
    existing = await db.execute(
        select(Term).where(Term.term_zh == candidate["term_zh"])
    )
    if existing.scalar_one_or_none():
        await db.execute(
            text("UPDATE candidate_terms SET reviewed=TRUE, accepted=TRUE WHERE id=:id"),
            {"id": candidate_id},
        )
        await db.commit()
        return {"status": "already_tracked", "term_zh": candidate["term_zh"]}

    # Determine category
    try:
        cat = TermCategory(candidate["category"])
    except ValueError:
        cat = TermCategory.other

    term = Term(
        term_zh=candidate["term_zh"],
        term_en=candidate["term_en"],
        category=cat,
        description=candidate["significance"],
        added_by="review",
    )
    db.add(term)
    await db.flush()

    await db.execute(
        text("UPDATE candidate_terms SET reviewed=TRUE, accepted=TRUE WHERE id=:id"),
        {"id": candidate_id},
    )
    await db.commit()
    return {"status": "accepted", "term_id": term.id, "term_zh": term.term_zh}


@router.post("/{candidate_id}/dismiss", response_model=dict)
async def dismiss_candidate(candidate_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        text("UPDATE candidate_terms SET reviewed=TRUE, accepted=FALSE WHERE id=:id RETURNING id"),
        {"id": candidate_id},
    )
    if not result.first():
        raise HTTPException(status_code=404, detail="Candidate not found")
    await db.commit()
    return {"status": "dismissed"}
