"""
Claude-powered term extractor.

Sends each document to Claude with a structured prompt asking it to identify:
  - New or emerging political slogans and their first appearance
  - Phrases whose prominence seems to be rising or falling
  - Ideological formulations, policy directives, and economic terms worth tracking
  - Any language that signals a shift in priorities

Returns structured JSON that gets written to candidate_terms for review.

Requires ANTHROPIC_API_KEY in environment.
"""

import json
import logging
from dataclasses import dataclass

import anthropic

from app.models.document import Document

logger = logging.getLogger(__name__)

EXTRACTION_PROMPT = """\
You are an expert analyst of Chinese Communist Party political documents. \
Your job is to identify politically significant language in the document below.

<document>
{text}
</document>

Analyze this document and identify phrases that are worth tracking over time. \
Focus on:
1. **New slogans** — formulations that sound like new political slogans \
   (e.g. 新质生产力, 中国式现代化, 共同富裕)
2. **Policy directives** — specific policy stances stated as fixed formulas \
   (e.g. 房住不炒, 统筹发展和安全, 双循环)
3. **Ideological terms** — abstract ideological concepts being foregrounded \
   (e.g. 两个维护, 全过程人民民主)
4. **Economic / structural terms** — technical economic or governance terms \
   used as recurring frames (e.g. 供给侧结构性改革, 高质量发展)
5. **Potential omissions** — if this document is about {meeting_type}, \
   note any standard phrases from this type of meeting that seem conspicuously absent.

Return a JSON array. Each element must have exactly these fields:
  - "term_zh": the Chinese phrase (2–12 characters)
  - "term_en": your English translation
  - "category": one of slogan | policy_phrase | ideological | economic | diplomatic | other
  - "significance": 1–2 sentences explaining why this phrase matters and what its presence signals
  - "first_appearance_likely": true if this phrase appears novel or newly foregrounded, false otherwise
  - "context": a ~80 char excerpt from the document showing the phrase in context

Return only the JSON array, no other text.\
"""


@dataclass
class ExtractedTerm:
    term_zh: str
    term_en: str
    category: str
    significance: str
    first_appearance_likely: bool
    context: str


def _build_prompt(doc: Document) -> str:
    meeting_type = (
        doc.meeting_type.name_en if doc.meeting_type else "this type of meeting"
    )
    # Truncate very long documents — Claude handles up to ~180k tokens but we
    # want to stay focused. 6000 chars covers most communiqués completely.
    text = doc.raw_text_zh[:6000]
    return EXTRACTION_PROMPT.format(text=text, meeting_type=meeting_type)


async def extract_terms_with_claude(
    doc: Document,
    api_key: str,
) -> list[ExtractedTerm]:
    """
    Call Claude to extract politically significant terms from a document.
    Returns a list of ExtractedTerm objects.
    """
    client = anthropic.AsyncAnthropic(api_key=api_key)

    try:
        message = await client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=2048,
            messages=[
                {
                    "role": "user",
                    "content": _build_prompt(doc),
                }
            ],
        )
    except anthropic.APIError as e:
        logger.error("Claude API error for doc %s: %s", doc.id, e)
        return []

    raw = message.content[0].text.strip()

    # Strip markdown code fences if Claude wraps it
    if raw.startswith("```"):
        raw = raw.split("\n", 1)[1].rsplit("```", 1)[0]

    try:
        items = json.loads(raw)
    except json.JSONDecodeError as e:
        logger.error("Claude returned invalid JSON for doc %s: %s\n%s", doc.id, e, raw[:300])
        return []

    results = []
    for item in items:
        try:
            results.append(ExtractedTerm(
                term_zh=item["term_zh"],
                term_en=item.get("term_en", ""),
                category=item.get("category", "other"),
                significance=item.get("significance", ""),
                first_appearance_likely=bool(item.get("first_appearance_likely", False)),
                context=item.get("context", ""),
            ))
        except KeyError:
            continue

    return results
