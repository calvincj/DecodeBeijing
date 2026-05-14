"""
Gap detector: tracks when a term disappears from political discourse globally.

A gap opens when a term (seen in ≥2 documents across any type) is absent from a new doc
AND hasn't been seen in any other document more recently.
A gap closes when the term reappears in any document type.
"""

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from app.models.document import Document
from app.models.term import TermOccurrence, TermGap


async def run_gap_detection(new_doc: Document, session: AsyncSession) -> int:
    """
    Global gap detection across all document types.
    Returns number of gaps opened or updated.
    """
    # Terms present in this doc
    present_result = await session.execute(
        select(TermOccurrence.term_id).where(
            TermOccurrence.document_id == new_doc.id,
            TermOccurrence.frequency > 0,
        )
    )
    present_ids = set(present_result.scalars().all())

    # Terms that have appeared in ≥2 documents globally (any type)
    qualifying_result = await session.execute(
        select(TermOccurrence.term_id)
        .where(TermOccurrence.frequency > 0)
        .group_by(TermOccurrence.term_id)
        .having(func.count() >= 2)
    )
    qualifying_ids = {row.term_id for row in qualifying_result}

    changes = 0

    for term_id in qualifying_ids:
        # Find any open gap for this term
        open_gap_result = await session.execute(
            select(TermGap).where(
                TermGap.term_id == term_id,
                TermGap.gap_end_date.is_(None),
            )
        )
        open_gap = open_gap_result.scalar_one_or_none()

        if term_id in present_ids:
            # Term present — close any open gap regardless of which doc type opened it
            if open_gap:
                open_gap.gap_end_date = new_doc.meeting_date
                session.add(open_gap)
                changes += 1
        else:
            # Term absent from this doc — check if it was seen more recently in any other doc
            last_result = await session.execute(
                select(Document.id, Document.meeting_date)
                .join(TermOccurrence, TermOccurrence.document_id == Document.id)
                .where(
                    TermOccurrence.term_id == term_id,
                    TermOccurrence.frequency > 0,
                    Document.meeting_date < new_doc.meeting_date,
                )
                .order_by(Document.meeting_date.desc())
                .limit(1)
            )
            last_row = last_result.first()

            if not last_row:
                continue  # term never seen before this doc

            if open_gap:
                # Only update if this doc is after the gap started
                if new_doc.meeting_date > open_gap.gap_start_date:
                    open_gap.meetings_missed += 1
                    session.add(open_gap)
                    changes += 1
            else:
                # Open a new gap only if there's no more-recent appearance in any other doc
                # (i.e., last_row is the most recent appearance and it's before this doc)
                gap = TermGap(
                    term_id=term_id,
                    last_seen_doc=last_row.id,
                    last_seen_date=last_row.meeting_date,
                    gap_start_date=new_doc.meeting_date,
                    gap_length_days=(new_doc.meeting_date - last_row.meeting_date).days,
                    meetings_missed=1,
                )
                session.add(gap)
                changes += 1

    await session.flush()
    return changes
