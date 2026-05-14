"""
List processor: extracts numbered policy lists from documents and stores them
with positional ranking so we can track priority shifts over time.
"""

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.models.document import Document
from app.models.list_tracking import ListContext, ListEntry
from app.models.term import Term
from pipeline.utils import extract_policy_lists


async def process_document_lists(doc: Document, session: AsyncSession) -> int:
    """
    Extract numbered lists from doc.raw_text_zh, link entries to known terms,
    and persist to list_contexts + list_entries. Returns number of lists found.
    """
    raw_lists = extract_policy_lists(doc.raw_text_zh)
    if not raw_lists:
        return 0

    # Load all terms for matching
    terms_result = await session.execute(select(Term))
    terms: list[Term] = terms_result.scalars().all()
    term_lookup = {t.term_zh: t.id for t in terms}

    for raw_list in raw_lists:
        ctx = ListContext(
            document_id=doc.id,
            list_name_zh=raw_list["heading"] or "未标题列表",
        )
        session.add(ctx)
        await session.flush()  # get ctx.id

        for position, item_text in raw_list["items"]:
            # Try to match item text to a known tracked term
            matched_term_id = None
            for term_zh, term_id in term_lookup.items():
                if term_zh in item_text:
                    matched_term_id = term_id
                    break

            entry = ListEntry(
                list_context_id=ctx.id,
                term_id=matched_term_id,
                raw_text_zh=item_text[:500],
                position=position,
            )
            session.add(entry)

    await session.flush()
    return len(raw_lists)
