#!/usr/bin/env python3
"""
Run both statistical and Claude-based term detection on one or all documents.

Usage:
  # Analyze one document by ID
  python scripts/analyze_document.py --doc-id 1

  # Analyze all unanalyzed documents
  python scripts/analyze_document.py --all

  # Skip Claude (no API key yet)
  python scripts/analyze_document.py --all --no-claude

The ANTHROPIC_API_KEY must be set in .env or the environment for Claude to run.
"""

import argparse
import asyncio
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "backend"))

from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from sqlalchemy import select
from sqlalchemy.orm import joinedload

from app.config import settings
from app.models.document import Document
from pipeline.processors.statistical_detector import detect_statistical_candidates
from pipeline.processors.claude_extractor import extract_terms_with_claude
from pipeline.processors.candidate_writer import write_statistical_candidates, write_claude_candidates
from pipeline.processors.deepl_translator import translate_zh_to_en
from sqlalchemy import text as sql_text


async def analyze(doc: Document, session, use_claude: bool, api_key: str):
    print(f"\n  [{doc.id}] {doc.title_zh} ({doc.meeting_date})")

    # Statistical
    stat_candidates = await detect_statistical_candidates(doc, session)
    n_stat = await write_statistical_candidates(doc.id, stat_candidates, session)
    print(f"    Statistical: {n_stat} candidates ({', '.join(c.signal for c in stat_candidates[:5])}{'...' if len(stat_candidates) > 5 else ''})")

    for c in stat_candidates[:8]:
        print(f"      [{c.signal}] {c.phrase!r}  freq={c.frequency}  prior_avg={c.prior_avg:.1f}")

    # DeepL — translate statistical candidates that have no English translation yet
    if stat_candidates and settings.deepl_api_key.strip():
        phrases = [c.phrase for c in stat_candidates]
        translations = translate_zh_to_en(phrases)
        for phrase, en in zip(phrases, translations):
            if en:
                await session.execute(
                    sql_text(
                        "UPDATE candidate_terms SET term_en = :en "
                        "WHERE document_id = :doc_id AND term_zh = :zh AND (term_en IS NULL OR term_en = '')"
                    ),
                    {"en": en, "doc_id": doc.id, "zh": phrase},
                )
        translated_count = sum(1 for t in translations if t)
        print(f"    DeepL: translated {translated_count}/{len(phrases)} statistical candidates")
    elif stat_candidates:
        print("    DeepL: skipped (no DEEPL_API_KEY in .env)")

    # Claude
    if use_claude and api_key:
        claude_terms = await extract_terms_with_claude(doc, api_key)
        n_claude = await write_claude_candidates(doc.id, claude_terms, session)
        print(f"    Claude: {n_claude} terms extracted")
        for t in claude_terms:
            marker = " ★" if t.first_appearance_likely else ""
            print(f"      [{t.category}] {t.term_zh} — {t.term_en}{marker}")
    elif use_claude:
        print("    Claude: skipped (no ANTHROPIC_API_KEY in .env)")


async def main(doc_id, all_docs: bool, no_claude: bool):
    api_key = os.getenv("ANTHROPIC_API_KEY", "")
    use_claude = not no_claude

    engine = create_async_engine(settings.database_url)
    Session = async_sessionmaker(engine, expire_on_commit=False)

    # Fetch document list in one session, then process each in its own session
    async with Session() as session:
        if doc_id:
            result = await session.execute(
                select(Document).options(joinedload(Document.meeting_type)).where(Document.id == doc_id)
            )
            docs = list(result.scalars().all())
        else:
            result = await session.execute(
                select(Document).options(joinedload(Document.meeting_type))
            )
            docs = list(result.scalars().all())

    for doc in docs:
        async with Session() as session:
            async with session.begin():
                # Re-attach doc to this session
                merged = await session.merge(doc)
                await session.refresh(merged, ["meeting_type"])
                await analyze(merged, session, use_claude, api_key)

    await engine.dispose()
    print("\nDone. Review candidates at GET /candidates or POST /candidates/{id}/accept")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--doc-id", type=int)
    parser.add_argument("--all",      action="store_true")
    parser.add_argument("--no-claude", action="store_true")
    args = parser.parse_args()

    if not args.doc_id and not args.all:
        parser.error("Provide --doc-id N or --all")

    asyncio.run(main(args.doc_id, args.all, args.no_claude))
