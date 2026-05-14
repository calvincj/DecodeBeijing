"""
Writes detected candidates (from both statistical and Claude detectors)
into the candidate_terms table for human review.
"""

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text

from pipeline.processors.statistical_detector import Candidate
from pipeline.processors.claude_extractor import ExtractedTerm


async def write_statistical_candidates(
    doc_id: int,
    candidates: list[Candidate],
    session: AsyncSession,
) -> int:
    written = 0
    for c in candidates:
        await session.execute(
            text("""
                INSERT INTO candidate_terms
                  (document_id, term_zh, signal, frequency, prior_avg, context)
                VALUES (:doc_id, :term_zh, :signal, :freq, :avg, :ctx)
                ON CONFLICT (document_id, term_zh) DO NOTHING
            """),
            {
                "doc_id": doc_id,
                "term_zh": c.phrase,
                "signal": c.signal,
                "freq": c.frequency,
                "avg": c.prior_avg,
                "ctx": c.context,
            },
        )
        written += 1
    return written


async def write_claude_candidates(
    doc_id: int,
    terms: list[ExtractedTerm],
    session: AsyncSession,
) -> int:
    written = 0
    for t in terms:
        await session.execute(
            text("""
                INSERT INTO candidate_terms
                  (document_id, term_zh, term_en, category, signal, significance, context)
                VALUES (:doc_id, :term_zh, :term_en, :cat, 'CLAUDE', :sig, :ctx)
                ON CONFLICT (document_id, term_zh) DO UPDATE
                  SET term_en      = EXCLUDED.term_en,
                      category     = EXCLUDED.category,
                      significance = EXCLUDED.significance
            """),
            {
                "doc_id": doc_id,
                "term_zh": t.term_zh,
                "term_en": t.term_en,
                "cat": t.category,
                "sig": t.significance,
                "ctx": t.context,
            },
        )
        written += 1
    return written
