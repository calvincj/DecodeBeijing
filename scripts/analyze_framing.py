#!/usr/bin/env python3
"""
Pre-compute government framing for all term × document pairs.

Batches all terms present in a document into ONE API call per document,
so ~30 total calls instead of hundreds.  Results are cached in term_framing;
running again only processes uncached pairs.

Usage (from repo root):
  python scripts/analyze_framing.py
  python scripts/analyze_framing.py --doc 35          # single document
  python scripts/analyze_framing.py --term 7          # single term
  python scripts/analyze_framing.py --refresh         # re-analyse even cached pairs
"""

import argparse
import asyncio
import sys
import time
from pathlib import Path
from typing import Optional

sys.path.insert(0, str(Path(__file__).parent.parent / "backend"))

from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from sqlalchemy import select, text

from app.config import settings
from app.models.term import Term, TermOccurrence
from app.models.document import Document
from pipeline.processors.framing_analyzer import (
    _ensure_table,
    analyze_document_batch,
)


async def run(
    only_doc: Optional[int],
    only_term: Optional[int],
    refresh: bool,
) -> None:
    engine = create_async_engine(settings.database_url)
    Session = async_sessionmaker(engine, expire_on_commit=False)

    async with Session() as session:
        await _ensure_table(session)

        # Load all documents (or just one)
        doc_q = select(Document).order_by(Document.meeting_date)
        if only_doc:
            doc_q = doc_q.where(Document.id == only_doc)
        docs = (await session.execute(doc_q)).scalars().all()
        print(f"Processing {len(docs)} document(s)…\n")

        for doc in docs:
            # Find all term occurrences in this document with context snippets
            occ_q = (
                select(TermOccurrence, Term)
                .join(Term, Term.id == TermOccurrence.term_id)
                .where(TermOccurrence.document_id == doc.id)
                .where(TermOccurrence.frequency > 0)
            )
            if only_term:
                occ_q = occ_q.where(TermOccurrence.term_id == only_term)

            rows = (await session.execute(occ_q)).all()
            if not rows:
                continue

            # Filter out already-cached pairs unless --refresh
            if not refresh:
                cached = {
                    r.term_id
                    for r in (
                        await session.execute(
                            text(
                                "SELECT term_id FROM term_framing WHERE document_id = :did"
                            ),
                            {"did": doc.id},
                        )
                    ).all()
                }
                rows = [(occ, term) for occ, term in rows if term.id not in cached]

            if not rows:
                print(f"  [{doc.id}] {doc.title_zh[:40]} — all cached, skipping")
                continue

            # Build term items for batch call
            term_items = [
                {
                    "term_id":  term.id,
                    "term_zh":  term.term_zh,
                    "term_en":  term.term_en,
                    "snippets": occ.context_snippets or [],
                }
                for occ, term in rows
                if occ.context_snippets
            ]

            if not term_items:
                continue

            print(
                f"  [{doc.id}] {doc.title_zh[:40]} ({doc.meeting_date})"
                f"  — {len(term_items)} terms to analyse…"
            )

            results = await analyze_document_batch(
                doc_id=doc.id,
                doc_title=doc.title_zh,
                doc_date=str(doc.meeting_date),
                term_items=term_items,
                session=session,
            )

            print(f"    → {len(results)} classifications cached")

            # Rate-limit: free tier allows ~1 req/s
            time.sleep(1.5)

    await engine.dispose()
    print("\nDone. Framing data available in the UI immediately.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--doc",     type=int, help="Analyse only this document ID")
    parser.add_argument("--term",    type=int, help="Analyse only this term ID")
    parser.add_argument("--refresh", action="store_true", help="Re-analyse cached pairs too")
    args = parser.parse_args()

    asyncio.run(run(args.doc, args.term, args.refresh))
