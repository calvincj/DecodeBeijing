#!/usr/bin/env python3
"""
Manually ingest a document from a URL or local file.

Usage:
  python scripts/ingest_manual.py --url https://www.xinhuanet.com/...
  python scripts/ingest_manual.py --file path/to/document.txt --title "..." --date 2023-12-11 --type economic_work_conference

This is useful for backfilling historical documents before the automated scraper runs.
"""

import argparse
import asyncio
import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "backend"))

import httpx
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker

from app.config import settings
from app.db import Base
from app.models.document import Document, MeetingType
from pipeline.utils import extract_text_from_html, classify_meeting_type
from pipeline.processors.term_extractor import process_document_terms
from pipeline.processors.list_processor import process_document_lists
from pipeline.processors.gap_detector import run_gap_detection
from sqlalchemy import select


async def ingest(
    url: str | None,
    file: str | None,
    title: str,
    meeting_date: date,
    meeting_type: str,
):
    engine = create_async_engine(settings.database_url)
    Session = async_sessionmaker(engine, expire_on_commit=False)

    if url:
        print(f"Fetching {url}...")
        async with httpx.AsyncClient(timeout=30) as client:
            r = await client.get(url, headers={"User-Agent": settings.scraper_user_agent})
            r.raise_for_status()
            raw_text = extract_text_from_html(r.text)
        source_url = url
    elif file:
        raw_text = Path(file).read_text(encoding="utf-8")
        source_url = f"file://{Path(file).resolve()}"
    else:
        raise ValueError("Must provide --url or --file")

    if not meeting_type:
        meeting_type = classify_meeting_type(title + raw_text[:500])
    print(f"Classified as: {meeting_type}")
    print(f"Text length: {len(raw_text)} chars")

    async with Session() as session:
        async with session.begin():
            existing = await session.execute(select(Document).where(Document.source_url == source_url))
            if existing.scalar_one_or_none():
                print("Document already exists, skipping.")
                return

            mt_result = await session.execute(
                select(MeetingType).where(MeetingType.category == meeting_type)
            )
            mt = mt_result.scalars().first()

            doc = Document(
                meeting_type_id=mt.id if mt else None,
                title_zh=title,
                meeting_date=meeting_date,
                source_url=source_url,
                raw_text_zh=raw_text,
                word_count_zh=len(raw_text),
            )
            session.add(doc)
            await session.flush()

            n_terms = await process_document_terms(doc, session)
            n_lists = await process_document_lists(doc, session)
            n_gaps  = await run_gap_detection(doc, session)

            print(f"Done. doc_id={doc.id}, terms_found={n_terms}, lists={n_lists}, gap_changes={n_gaps}")

    await engine.dispose()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--url",   help="URL to fetch")
    parser.add_argument("--file",  help="Local .txt file path")
    parser.add_argument("--title", required=True)
    parser.add_argument("--date",  required=True, help="YYYY-MM-DD")
    parser.add_argument("--type",  default="", help="Meeting type category")
    args = parser.parse_args()

    asyncio.run(ingest(
        url=args.url,
        file=args.file,
        title=args.title,
        meeting_date=date.fromisoformat(args.date),
        meeting_type=args.type,
    ))
