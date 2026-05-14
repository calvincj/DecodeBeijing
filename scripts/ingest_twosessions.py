#!/usr/bin/env python3
"""
Batch-ingest Two Sessions government work reports from twosessions/YYYY_twosesh.txt.

Usage (from repo root, with backend venv active):
  python scripts/ingest_twosessions.py
  python scripts/ingest_twosessions.py --dry-run
"""

import argparse
import asyncio
import re
import sys
from datetime import date
from pathlib import Path
from typing import Optional

sys.path.insert(0, str(Path(__file__).parent.parent / "backend"))

from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from sqlalchemy import select

from app.config import settings
from app.models.document import Document, MeetingType
from pipeline.processors.term_extractor import process_document_terms
from pipeline.processors.list_processor import process_document_lists
from pipeline.processors.gap_detector import run_gap_detection

MEETING_CATEGORY = "two_sessions_national"
MEETING_NAME_ZH  = "全国人民代表大会"

# NPC opening dates for each year's Government Work Report (政府工作报告).
# 2020 was delayed to May 22 due to COVID-19; all others open March 5.
YEAR_META: dict[int, tuple[date, str]] = {
    2010: (date(2010,  3,  5), "2010年政府工作报告"),
    2011: (date(2011,  3,  5), "2011年政府工作报告"),
    2012: (date(2012,  3,  5), "2012年政府工作报告"),
    2013: (date(2013,  3,  5), "2013年政府工作报告"),
    2014: (date(2014,  3,  5), "2014年政府工作报告"),
    2015: (date(2015,  3,  5), "2015年政府工作报告"),
    2016: (date(2016,  3,  5), "2016年政府工作报告"),
    2017: (date(2017,  3,  5), "2017年政府工作报告"),
    2018: (date(2018,  3,  5), "2018年政府工作报告"),
    2019: (date(2019,  3,  5), "2019年政府工作报告"),
    2020: (date(2020,  5, 22), "2020年政府工作报告"),
    2021: (date(2021,  3,  5), "2021年政府工作报告"),
    2022: (date(2022,  3,  5), "2022年政府工作报告"),
    2023: (date(2023,  3,  5), "2023年政府工作报告"),
    2024: (date(2024,  3,  5), "2024年政府工作报告"),
    2025: (date(2025,  3,  5), "2025年政府工作报告"),
    2026: (date(2026,  3,  5), "2026年政府工作报告"),
}


def clean_text(raw: str) -> str:
    """Minimal cleaning: strip leading/trailing whitespace from lines, drop blank runs."""
    lines = []
    for line in raw.splitlines():
        stripped = line.strip()
        lines.append(stripped)
    return "\n".join(lines).strip()


def _discover(ts_dir: Path) -> list[tuple[int, Path]]:
    pairs = []
    for p in sorted(ts_dir.glob("*_twosesh.txt")):
        m = re.match(r"^(\d{4})_twosesh\.txt$", p.name)
        if m:
            year = int(m.group(1))
            if year in YEAR_META:
                pairs.append((year, p))
    return sorted(pairs)


async def ingest_all(ts_dir: Path, dry_run: bool) -> None:
    files = _discover(ts_dir)
    if not files:
        print(f"No YYYY_twosesh.txt files found in {ts_dir}")
        return

    print(f"Found {len(files)} reports: {[y for y, _ in files]}\n")

    if dry_run:
        for year, path in files:
            report_date, title = YEAR_META[year]
            print(f"  [dry-run] {path.name}  →  {title}  date={report_date}")
        return

    engine = create_async_engine(settings.database_url)
    Session = async_sessionmaker(engine, expire_on_commit=False)

    async with Session() as session:
        mt_row = (
            await session.execute(
                select(MeetingType)
                .where(MeetingType.category == MEETING_CATEGORY)
                .where(MeetingType.name_zh   == MEETING_NAME_ZH)
            )
        ).scalars().first()
        if not mt_row:
            print(f"ERROR: MeetingType '{MEETING_CATEGORY} / {MEETING_NAME_ZH}' not in DB. Run setup first.")
            return

    for year, path in files:
        report_date, title_zh = YEAR_META[year]
        source_url = f"file://{path.resolve()}"
        raw_text   = clean_text(path.read_text(encoding="utf-8"))

        async with Session() as session:
            async with session.begin():
                if (await session.execute(
                    select(Document).where(Document.source_url == source_url)
                )).scalar_one_or_none():
                    print(f"  [{year}] already in DB, skipping.")
                    continue

                doc = Document(
                    meeting_type_id=mt_row.id,
                    title_zh=title_zh,
                    meeting_date=report_date,
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
        "Next: python scripts/analyze_framing.py  (to pre-compute framing for new docs)"
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--ts-dir",
        default=str(Path(__file__).parent.parent / "twosessions"),
        help="Directory containing YYYY_twosesh.txt files (default: ./twosessions/)",
    )
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    asyncio.run(ingest_all(Path(args.ts_dir), args.dry_run))
