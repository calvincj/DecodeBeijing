#!/usr/bin/env python3
"""
Batch-ingest all Central Economic Work Conference (中央经济工作会议) records
from the econconf/ directory.

Files are named YYYY_econconf.txt.  The conference is held in mid-December each
year, so we use December 15 as the canonical date for each entry.

Usage (from repo root):
  python scripts/ingest_econconf.py
  python scripts/ingest_econconf.py --dry-run
  python scripts/ingest_econconf.py --econconf-dir path/to/dir
"""

import argparse
import asyncio
import re
import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "backend"))

from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from sqlalchemy import select

from app.config import settings
from app.models.document import Document, MeetingType
from pipeline.processors.term_extractor import process_document_terms
from pipeline.processors.list_processor import process_document_lists
from pipeline.processors.gap_detector import run_gap_detection


MEETING_TYPE = "economic_work_conference"

# Conference convenes in mid-December; 15th is a safe canonical date.
CONF_MONTH, CONF_DAY = 12, 15


def _discover(econconf_dir: Path) -> list[tuple[int, Path]]:
    pairs = []
    for p in sorted(econconf_dir.glob("*_econconf.txt")):
        m = re.match(r"^(\d{4})_econconf\.txt$", p.name)
        if m:
            pairs.append((int(m.group(1)), p))
    return pairs


async def ingest_all(econconf_dir: Path, dry_run: bool) -> None:
    files = _discover(econconf_dir)
    if not files:
        print(f"No *_econconf.txt files found in {econconf_dir}")
        return

    print(f"Found {len(files)} files: {[y for y, _ in files]}\n")

    if dry_run:
        for year, path in files:
            print(f"  [dry-run] {path.name}  →  date={year}-{CONF_MONTH:02d}-{CONF_DAY:02d}  type={MEETING_TYPE}")
        return

    engine = create_async_engine(settings.database_url)
    Session = async_sessionmaker(engine, expire_on_commit=False)

    # Resolve MeetingType once
    async with Session() as session:
        mt_row = (
            await session.execute(select(MeetingType).where(MeetingType.category == MEETING_TYPE))
        ).scalars().first()
        if not mt_row:
            print(
                f"WARNING: MeetingType '{MEETING_TYPE}' not in DB — "
                "run migrations/seed first.  Documents will be stored without a type link.\n"
            )

    for year, path in files:
        meeting_date = date(year, CONF_MONTH, CONF_DAY)
        source_url = f"file://{path.resolve()}"
        raw_text = path.read_text(encoding="utf-8").strip()
        title_zh = f"中央经济工作会议（{year}年）"

        async with Session() as session:
            async with session.begin():
                if (await session.execute(
                    select(Document).where(Document.source_url == source_url)
                )).scalar_one_or_none():
                    print(f"  [{year}] already in DB, skipping.")
                    continue

                doc = Document(
                    meeting_type_id=mt_row.id if mt_row else None,
                    title_zh=title_zh,
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

        print(
            f"  [{year}] ingested  doc_id={doc.id}  "
            f"chars={len(raw_text):,}  terms_matched={n_terms}  lists={n_lists}  gap_changes={n_gaps}"
        )

    await engine.dispose()
    print(
        "\nDone.\n"
        "Next steps:\n"
        "  python scripts/analyze_document.py --all          # statistical + Claude candidates\n"
        "  python scripts/analyze_document.py --all --no-claude  # statistical only"
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--econconf-dir",
        default=str(Path(__file__).parent.parent / "econconf"),
        help="Directory containing YYYY_econconf.txt files (default: ./econconf/)",
    )
    parser.add_argument("--dry-run", action="store_true", help="Preview without touching the DB")
    args = parser.parse_args()

    asyncio.run(ingest_all(Path(args.econconf_dir), args.dry_run))
