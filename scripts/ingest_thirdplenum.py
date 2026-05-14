#!/usr/bin/env python3
"""
Batch-ingest Third Plenary Session communiqués from thirdplenum/N_thirdplenum.txt.

Files are named N_thirdplenum.txt (or N_thirdplennum.txt) where N is the CC number (10–19).

Usage (from repo root, with backend venv active):
  python scripts/ingest_thirdplenum.py
  python scripts/ingest_thirdplenum.py --dry-run
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

MEETING_CATEGORY = "plenum"
MEETING_NAME_ZH  = "中央委员会全体会议"

NUM_ZH = {
    10: "十",  11: "十一", 12: "十二", 13: "十三", 14: "十四",
    15: "十五", 16: "十六", 17: "十七", 18: "十八", 19: "十九",
    20: "二十",
}

# Opening date of each 3rd Plenary Session
PLENUM_META: dict[int, tuple[date, str]] = {
    10: (date(1977,  7, 16), "中国共产党第十届中央委员会第三次全体会议公报"),
    11: (date(1978, 12, 18), "中国共产党第十一届中央委员会第三次全体会议公报"),
    12: (date(1984, 10, 20), "中国共产党第十二届中央委员会第三次全体会议公报"),
    13: (date(1988,  9, 26), "中国共产党第十三届中央委员会第三次全体会议公报"),
    14: (date(1993, 11, 11), "中国共产党第十四届中央委员会第三次全体会议公报"),
    15: (date(1998, 10, 12), "中国共产党第十五届中央委员会第三次全体会议公报"),
    16: (date(2003, 10, 11), "中国共产党第十六届中央委员会第三次全体会议公报"),
    17: (date(2008, 10,  9), "中国共产党第十七届中央委员会第三次全体会议公报"),
    18: (date(2013, 11,  9), "中国共产党第十八届中央委员会第三次全体会议公报"),
    19: (date(2018,  2, 26), "中国共产党第十九届中央委员会第三次全体会议公报"),
    20: (date(2024,  7, 15), "中国共产党第二十届中央委员会第三次全体会议公报"),
}


def clean_text(raw: str) -> str:
    lines = [line.strip() for line in raw.splitlines()]
    return "\n".join(lines).strip()


def _discover(tp_dir: Path) -> list[tuple[int, Path]]:
    pairs = []
    for p in sorted(tp_dir.iterdir()):
        # handle typo variant: 19_thirdplennum.txt
        m = re.match(r"^(\d+)_thirdplen+um\.txt$", p.name)
        if m:
            n = int(m.group(1))
            if n in PLENUM_META:
                pairs.append((n, p))
    return sorted(pairs)


async def ingest_all(tp_dir: Path, dry_run: bool) -> None:
    files = _discover(tp_dir)
    if not files:
        print(f"No N_thirdplenum.txt files found in {tp_dir}")
        return

    print(f"Found {len(files)} communiqués: {[n for n, _ in files]}\n")

    if dry_run:
        for n, path in files:
            d, title = PLENUM_META[n]
            print(f"  [dry-run] {path.name}  →  {title[:40]}  date={d}")
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
            print(f"ERROR: MeetingType '{MEETING_CATEGORY} / {MEETING_NAME_ZH}' not in DB.")
            return

    for n, path in files:
        plenum_date, title_zh = PLENUM_META[n]
        source_url = f"file://{path.resolve()}"
        raw_text   = clean_text(path.read_text(encoding="utf-8"))

        async with Session() as session:
            async with session.begin():
                if (await session.execute(
                    select(Document).where(Document.source_url == source_url)
                )).scalar_one_or_none():
                    print(f"  [{n}th CC 3rd Plenum] already in DB, skipping.")
                    continue

                doc = Document(
                    meeting_type_id=mt_row.id,
                    title_zh=title_zh,
                    meeting_date=plenum_date,
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
            f"  [{n}th CC 3rd Plenum] ingested  doc_id={doc.id}  "
            f"chars={len(raw_text):,}  terms_matched={n_terms}  lists={n_lists}  gap_changes={n_gaps}"
        )

    await engine.dispose()
    print(
        "\nDone.\n"
        "Next: python scripts/analyze_framing.py"
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--tp-dir",
        default=str(Path(__file__).parent.parent / "thirdplenum"),
        help="Directory containing N_thirdplenum.txt files (default: ./thirdplenum/)",
    )
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    asyncio.run(ingest_all(Path(args.tp_dir), args.dry_run))
