"""
Batch framing analyzer — one API call per document, all its terms together.

Run via:  python scripts/analyze_framing.py
Results cached in term_framing table; endpoint reads cache only (no real-time calls).

Model: nvidia/nemotron-3-super-120b-a12b:free (262K ctx, US-based, avoids censorship)
"""

import json
import logging
import re

import httpx
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text

from app.config import settings

logger = logging.getLogger(__name__)

OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"
MODEL = "nvidia/nemotron-3-super-120b-a12b:free"

_SYSTEM = (
    "You are an expert analyst of Chinese Communist Party official documents. "
    "Your job is to classify the government's rhetorical ATTITUDE toward specific "
    "political/policy terms based on the words and phrases immediately surrounding them."
)

_USER = """\
Document: {title} ({date})

For each term below, classify the government's attitude toward it in this document,
based ONLY on the context snippets provided (the surrounding text).

Attitude options:
  "promoting"   — actively pushing, expanding, accelerating, developing, strengthening
                  Pre-term signals: 大力、加快、深化、积极、着力、强化、提升、扩大、推进
                  Post-term signals: 要不断发展、要持续推进、是重要支撑
  "cautioning"  — framing as risk to manage, restrict, or guard against
                  Pre-term signals: 防止、防范、遏制、管控、严控、严禁、打击、化解
                  Post-term signals: 面临风险、存在隐患、仍需警惕
  "stabilizing" — holding steady, maintaining the status quo, continuing unchanged
                  Pre-term signals: 坚持、维护、确保、保持、巩固、落实、贯彻
                  Post-term signals: 要贯穿始终、要长期坚持、始终不变
  "neutral"     — mentioned without clear directional framing; or context is a table of
                  contents / chapter heading / page number (classify those as neutral)

IMPORTANT: only consider the modifier immediately adjacent to the term (within the same
comma-clause). Ignore modifiers from earlier clauses in the same snippet.

Terms and context snippets:
{terms_block}

key_phrase MUST be the single modifier word or short compound (2–6 characters MAX) that
signals the attitude — e.g. "推动", "加快", "防止", "坚持". NEVER return the full clause,
the term itself, or any surrounding text as key_phrase.

Return ONLY a JSON array — no prose, no markdown fences:
[{{"term_id": 1, "attitude": "promoting", "key_phrase": "加快", "explanation": "One sentence."}}]
"""


async def _ensure_table(session: AsyncSession) -> None:
    await session.execute(text("""
        CREATE TABLE IF NOT EXISTS term_framing (
            id          SERIAL PRIMARY KEY,
            term_id     INTEGER NOT NULL REFERENCES terms(id),
            document_id INTEGER NOT NULL REFERENCES documents(id),
            attitude    VARCHAR NOT NULL,
            key_phrase  VARCHAR,
            explanation TEXT,
            model_used  VARCHAR,
            created_at  TIMESTAMP DEFAULT NOW(),
            UNIQUE(term_id, document_id)
        )
    """))
    await session.commit()


async def fetch_cached_for_term(term_id: int, session: AsyncSession) -> list[dict]:
    rows = await session.execute(
        text("""
            SELECT tf.document_id, d.meeting_date,
                   tf.attitude, tf.key_phrase, tf.explanation
            FROM term_framing tf
            JOIN documents d ON d.id = tf.document_id
            WHERE tf.term_id = :tid
            ORDER BY d.meeting_date
        """),
        {"tid": term_id},
    )
    return [dict(r._mapping) for r in rows.all()]


async def analyze_document_batch(
    doc_id: int,
    doc_title: str,
    doc_date: str,
    term_items: list[dict],  # [{term_id, term_zh, term_en, snippets: [str]}]
    session: AsyncSession,
) -> dict[int, dict]:
    """
    Analyze all terms for one document in a single API call.
    Returns {term_id: {attitude, key_phrase, explanation}}.
    """
    api_key = (settings.openr_api_key or "").strip()
    if not api_key:
        logger.warning("OPENR_API_KEY not set — skipping framing analysis")
        return {}

    # Build the terms block (cap at 8 to avoid truncated responses)
    term_items = term_items[:8]
    lines = []
    for item in term_items:
        lines.append(f"\n--- term_id={item['term_id']} | {item['term_zh']} ({item['term_en'] or '—'}) ---")
        for s in item["snippets"][:3]:
            clean = re.sub(r"\s+", " ", s).strip()
            lines.append(f"  …{clean[:200]}…")
    terms_block = "\n".join(lines)

    prompt = _USER.format(
        title=doc_title,
        date=doc_date,
        terms_block=terms_block,
    )

    try:
        async with httpx.AsyncClient(timeout=60) as client:
            resp = await client.post(
                OPENROUTER_URL,
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json",
                    "HTTP-Referer": "http://localhost:3000",
                    "X-Title": "Decode Beijing",
                },
                json={
                    "model": MODEL,
                    "messages": [
                        {"role": "system", "content": _SYSTEM},
                        {"role": "user",   "content": prompt},
                    ],
                    "temperature": 0.1,
                },
            )
            resp.raise_for_status()
    except httpx.HTTPError as e:
        logger.error("OpenRouter request failed for doc %s: %s", doc_id, e)
        return {}

    body = resp.json()
    if "choices" not in body:
        logger.error("OpenRouter error (doc %s): %s", doc_id, body)
        return {}

    raw = body["choices"][0]["message"]["content"].strip()
    if raw.startswith("```"):
        raw = raw.split("\n", 1)[1].rsplit("```", 1)[0].strip()

    # If response was truncated, salvage complete objects before the cut-off
    if not raw.endswith("]"):
        last = raw.rfind("},")
        if last != -1:
            raw = raw[: last + 1] + "]"
        else:
            logger.error("Unrecoverable truncated JSON from OpenRouter (doc %s)", doc_id)
            return {}

    try:
        items = json.loads(raw)
    except json.JSONDecodeError as e:
        logger.error("Invalid JSON from OpenRouter (doc %s): %s\n%.200s", doc_id, e, raw)
        return {}

    results: dict[int, dict] = {}
    for item in items:
        tid = item.get("term_id")
        if tid:
            results[int(tid)] = {
                "attitude":    item.get("attitude", "neutral"),
                "key_phrase":  item.get("key_phrase"),
                "explanation": item.get("explanation"),
            }

    # Persist to cache
    for tid, data in results.items():
        await session.execute(
            text("""
                INSERT INTO term_framing
                    (term_id, document_id, attitude, key_phrase, explanation, model_used)
                VALUES (:tid, :did, :att, :kp, :exp, :model)
                ON CONFLICT (term_id, document_id) DO UPDATE SET
                    attitude = EXCLUDED.attitude,
                    key_phrase = EXCLUDED.key_phrase,
                    explanation = EXCLUDED.explanation,
                    model_used = EXCLUDED.model_used,
                    created_at = NOW()
            """),
            {
                "tid":   tid,
                "did":   doc_id,
                "att":   data["attitude"],
                "kp":    data.get("key_phrase"),
                "exp":   data.get("explanation"),
                "model": MODEL,
            },
        )
    await session.commit()
    return results
