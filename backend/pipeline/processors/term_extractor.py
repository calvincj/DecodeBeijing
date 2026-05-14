"""
Term extractor: finds all tracked terms in a document and records positions + context snippets.

Uses exact substring matching — more reliable than tokenization for fixed political phrases.
"""

from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete
from app.models.term import Term, TermOccurrence
from app.models.document import Document


CONTEXT_WINDOW = 80  # chars on each side of a match


def _find_occurrences(text: str, term: str) -> tuple[list[int], list[str]]:
    positions: list[int] = []
    snippets: list[str] = []
    start = 0
    while True:
        idx = text.find(term, start)
        if idx == -1:
            break
        positions.append(idx)
        lo = max(0, idx - CONTEXT_WINDOW)
        hi = min(len(text), idx + len(term) + CONTEXT_WINDOW)
        snippets.append(text[lo:hi])
        start = idx + 1
    return positions, snippets


async def process_document_terms(doc: Document, session: AsyncSession) -> int:
    """
    Scan doc.raw_text_zh against all tracked terms.
    Upserts TermOccurrence rows. Returns count of terms found.
    """
    terms_result = await session.execute(select(Term))
    terms: list[Term] = terms_result.scalars().all()

    found = 0
    for term in terms:
        positions, snippets = _find_occurrences(doc.raw_text_zh, term.term_zh)

        # Check if this is the first time we've seen this term
        if positions and term.first_seen_date is None:
            term.first_seen_doc = doc.id
            term.first_seen_date = doc.meeting_date
            session.add(term)

        # Upsert occurrence row
        existing = await session.execute(
            select(TermOccurrence).where(
                TermOccurrence.term_id == term.id,
                TermOccurrence.document_id == doc.id,
            )
        )
        occ = existing.scalar_one_or_none()

        if occ is None:
            occ = TermOccurrence(term_id=term.id, document_id=doc.id)
            session.add(occ)

        occ.frequency = len(positions)
        occ.char_positions = positions if positions else None
        occ.context_snippets = snippets[:10] if snippets else None  # cap at 10 snippets

        if positions:
            found += 1

    await session.flush()
    return found
