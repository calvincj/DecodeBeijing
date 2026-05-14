#!/usr/bin/env python3
"""
Batch-ingest Five-Year Plan documents from fiveyearplans/N_fyp.txt.

Files are named N_fyp.txt where N is the plan number (6–15).
Dates are the NPC sessions that approved each plan.

Usage (from repo root):
  python scripts/ingest_fiveyearplans.py
  python scripts/ingest_fiveyearplans.py --dry-run
"""

import argparse
import asyncio
import re
import sys
from datetime import date
from pathlib import Path


_HEADING_RE = re.compile(r"^第[一二三四五六七八九十百]+[篇章节]")

def clean_text(raw: str) -> str:
    """Strip ToC lines (dot leaders, ellipsis, or bare chapter headings after 目录)."""
    result = []
    in_toc = False

    for line in raw.splitlines():
        stripped = line.strip()

        # Dot-leader / ellipsis ToC lines (most FYPs)
        if re.search(r"\.{4,}|…{2,}", stripped):
            continue

        # 14th-FYP style: 目录 heading → enter bare-heading ToC mode
        if re.fullmatch(r"目\s*录", stripped):
            in_toc = True
            continue

        if in_toc:
            if not stripped:
                continue
            # Chapter/section headings or short wrap-continuation lines stay skipped
            if _HEADING_RE.match(stripped) or len(stripped) < 30:
                continue
            # Substantial line with sentence punctuation → body has started
            if re.search(r"[，。！？；]", stripped):
                in_toc = False
                result.append(line)
            elif len(stripped) >= 30:
                # Long non-heading line without punctuation still signals body start
                in_toc = False
                result.append(line)
            # else: still ToC-like, skip
        else:
            result.append(line)

    return "\n".join(result).strip()

sys.path.insert(0, str(Path(__file__).parent.parent / "backend"))

from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from sqlalchemy import select

from app.config import settings
from app.models.document import Document, MeetingType
from pipeline.processors.term_extractor import process_document_terms
from pipeline.processors.list_processor import process_document_lists
from pipeline.processors.gap_detector import run_gap_detection

MEETING_TYPE = "five_year_plan"

# NPC approval dates for each plan
PLAN_META: dict[int, tuple[date, str]] = {
    6:  (date(1982, 12, 10), "中华人民共和国国民经济和社会发展第六个五年计划"),
    7:  (date(1986,  4, 12), "中华人民共和国国民经济和社会发展第七个五年计划"),
    8:  (date(1991,  4,  9), "中华人民共和国国民经济和社会发展第八个五年计划"),
    9:  (date(1996,  3, 17), "中华人民共和国国民经济和社会发展第九个五年计划"),
    10: (date(2001,  3, 15), "中华人民共和国国民经济和社会发展第十个五年计划"),
    11: (date(2006,  3, 14), "中华人民共和国国民经济和社会发展第十一个五年规划"),
    12: (date(2011,  3, 14), "中华人民共和国国民经济和社会发展第十二个五年规划"),
    13: (date(2016,  3, 17), "中华人民共和国国民经济和社会发展第十三个五年规划"),
    14: (date(2021,  3, 11), "中华人民共和国国民经济和社会发展第十四个五年规划"),
    15: (date(2026,  3,  5), "中华人民共和国国民经济和社会发展第十五个五年规划"),
}


def _discover(fyp_dir: Path) -> list[tuple[int, Path]]:
    pairs = []
    for p in sorted(fyp_dir.glob("*_fyp.txt")):
        m = re.match(r"^(\d+)_fyp\.txt$", p.name)
        if m:
            n = int(m.group(1))
            if n in PLAN_META:
                pairs.append((n, p))
    return sorted(pairs)


async def ingest_all(fyp_dir: Path, dry_run: bool) -> None:
    files = _discover(fyp_dir)
    if not files:
        print(f"No N_fyp.txt files found in {fyp_dir}")
        return

    print(f"Found {len(files)} plans: {[n for n, _ in files]}\n")

    if dry_run:
        for n, path in files:
            approved, title = PLAN_META[n]
            print(f"  [dry-run] {path.name}  →  {title[:30]}…  date={approved}")
        return

    engine = create_async_engine(settings.database_url)
    Session = async_sessionmaker(engine, expire_on_commit=False)

    async with Session() as session:
        mt_row = (
            await session.execute(
                select(MeetingType).where(MeetingType.category == MEETING_TYPE)
            )
        ).scalars().first()
        if not mt_row:
            print(f"ERROR: MeetingType '{MEETING_TYPE}' not in DB. Run the setup first.")
            return

    for n, path in files:
        approved, title_zh = PLAN_META[n]
        source_url = f"file://{path.resolve()}"
        raw_text = clean_text(path.read_text(encoding="utf-8"))

        async with Session() as session:
            async with session.begin():
                if (await session.execute(
                    select(Document).where(Document.source_url == source_url)
                )).scalar_one_or_none():
                    print(f"  [{n}th FYP] already in DB, skipping.")
                    continue

                doc = Document(
                    meeting_type_id=mt_row.id,
                    title_zh=title_zh,
                    meeting_date=approved,
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
            f"  [{n}th FYP] ingested  doc_id={doc.id}  "
            f"chars={len(raw_text):,}  terms_matched={n_terms}  lists={n_lists}  gap_changes={n_gaps}"
        )

    await engine.dispose()
    print(
        "\nDone.\n"
        "Next: python scripts/analyze_document.py --all --no-claude"
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--fyp-dir",
        default=str(Path(__file__).parent.parent / "fiveyearplans"),
        help="Directory containing N_fyp.txt files (default: ./fiveyearplans/)",
    )
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    asyncio.run(ingest_all(Path(args.fyp_dir), args.dry_run))
