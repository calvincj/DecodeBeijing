"""
Statistical new-term detector.

For each new document:
  1. Tokenize with jieba, extract 2–6 char n-grams that look like political phrases.
  2. Compare against historical frequency in the same meeting-type series.
  3. Flag:
       - DEBUT:  phrase never seen before in any document
       - SPIKE:  frequency ≥ 5× its rolling average across prior docs
       - RETURN: phrase absent for ≥ 2 prior meetings but reappears

Results are stored in candidate_terms so a human (or Claude) can review them.
"""

import re
from collections import Counter
from typing import NamedTuple

import jieba
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, text

from app.models.document import Document
from app.models.term import Term


# ── Filters ──────────────────────────────────────────────────────────────────

# Chinese political phrases are almost always 2–8 chars and avoid punctuation.
_VALID_PHRASE = re.compile(r"^[一-鿿]{2,8}$")

# Common stopwords that appear constantly and carry no signal.
# Rule: if a word appears in essentially every political document regardless
# of policy content, it belongs here. If its presence or absence could
# signal something, keep it out.
_STOPWORDS = {
    # Ubiquitous meeting/speech verbs — zero signal
    "会议", "指出", "强调", "要求", "提出", "认为", "表示", "指明",
    "部署", "研究", "讨论", "审议", "通过", "决定",

    # Generic action verbs — appear in every document
    "坚持", "推进", "推动", "加强", "加快", "深化", "扩大", "促进",
    "保障", "维护", "完善", "健全", "优化", "提升", "提高", "增强",
    "落实", "实施", "统筹", "协调", "做好", "抓好", "抓紧",

    # Generic nouns with no discriminating power
    "工作", "问题", "政策", "任务", "目标", "措施", "方向", "重点",
    "方面", "领域", "过程", "情况", "关系", "体系", "机制", "格局",
    "能力", "水平", "质量", "效率", "活力", "动力", "潜力",

    # Country / party / people boilerplate
    "中国", "全国", "国家", "党的", "人民", "社会", "我们", "我国",
    "中央", "政府", "地方",

    # Broad economic terms too generic to track
    "经济", "建设", "发展", "改革", "开放",

    # Evaluation adjectives — filler
    "重要", "主要", "基本", "关键", "核心", "全面", "深入", "积极",
    "有效", "切实", "稳健", "稳步", "扎实", "持续", "系统", "科学",

    # Generic verbs that form phrase fragments
    "解决", "处理", "应对", "防止", "避免", "确保", "保证",
    "了解", "认识", "把握", "运用", "发挥", "形成", "构建",

    # Common connective / structural words
    "需要", "用来", "实现", "包括", "通过", "按照", "围绕", "聚焦",
    "的是", "方式", "变革",

    # Adverbs / intensifiers — always glued to a real phrase, never standalone
    "着力", "切实", "大力", "努力", "全力", "有力", "合力",

    # Geographic / directional modifiers — too generic alone
    "国内", "境内", "城乡", "区域",

    # Adjective suffixes that appear as fragments from jieba splitting longer terms
    # e.g. "结构性" is part of "供给侧结构性改革", not a standalone term
    "结构性", "系统性", "战略性", "根本性", "全局性", "长期性",

    # Safety / stability boilerplate — present in almost every document
    "稳定", "安全",
}

# 3-char minimum cuts most generic 2-char verbs that slip past the stoplist.
# Real political phrases are almost always ≥ 3 chars (新质生产力, 房住不炒, etc.)
MIN_PHRASE_LEN = 3
MAX_PHRASE_LEN = 8


class Candidate(NamedTuple):
    phrase: str
    signal: str          # "DEBUT" | "SPIKE" | "RETURN"
    frequency: int       # in the new document
    prior_avg: float     # average frequency in prior same-type docs (0 for DEBUT)
    context: str         # one excerpt showing the phrase in context


def _extract_phrases(text: str) -> "Counter[str]":
    """
    Tokenize and extract candidate political phrases using jieba.
    Returns Counter of {phrase: frequency}.
    """
    tokens = [t for t in jieba.cut(text) if _VALID_PHRASE.match(t) and t not in _STOPWORDS]
    counts: Counter = Counter()

    # Single tokens
    for tok in tokens:
        if MIN_PHRASE_LEN <= len(tok) <= MAX_PHRASE_LEN:
            counts[tok] += 1

    # Bigrams of adjacent tokens (catches multi-token phrases jieba splits)
    for i in range(len(tokens) - 1):
        bigram = tokens[i] + tokens[i + 1]
        if MIN_PHRASE_LEN <= len(bigram) <= MAX_PHRASE_LEN:
            counts[bigram] += 1

    return counts


def _get_context(text: str, phrase: str, window: int = 60) -> str:
    idx = text.find(phrase)
    if idx == -1:
        return ""
    lo = max(0, idx - window)
    hi = min(len(text), idx + len(phrase) + window)
    return text[lo:hi]


async def _get_historical_freq(
    phrase: str,
    meeting_type_id: int,
    exclude_doc_id: int,
    session: AsyncSession,
) -> list[int]:
    """Return per-document frequency for this phrase in prior same-type docs."""
    rows = await session.execute(
        text("""
            SELECT
                array_length(
                    regexp_matches(d.raw_text_zh, :phrase, 'g')::text[],
                    1
                ) as freq
            FROM documents d
            WHERE d.meeting_type_id = :mt_id
              AND d.id != :doc_id
              AND d.raw_text_zh ILIKE :ilike
        """),
        {
            "phrase": re.escape(phrase),
            "mt_id": meeting_type_id,
            "doc_id": exclude_doc_id,
            "ilike": f"%{phrase}%",
        },
    )
    return [r.freq or 0 for r in rows.all()]


async def detect_statistical_candidates(
    doc: Document,
    session: AsyncSession,
    min_freq: int = 2,
    spike_threshold: float = 4.0,
) -> list[Candidate]:
    """
    Run statistical detection on a newly ingested document.
    Returns a list of Candidate phrases worth reviewing.
    """
    if doc.meeting_type_id is None:
        return []

    # Phrases already in our terms table — skip these, we track them separately
    existing_result = await session.execute(select(Term.term_zh))
    known_terms = {r for (r,) in existing_result.all()}

    phrase_counts = _extract_phrases(doc.raw_text_zh)
    candidates: list[Candidate] = []

    for phrase, freq in phrase_counts.most_common(60):
        if freq < min_freq:
            break
        if phrase in known_terms:
            continue
        # Reject bigrams that are just a stopword glued to a real token
        # (e.g. "着力国内" = 着力 + 国内, both generic)
        if any(phrase.startswith(sw) or phrase.endswith(sw) for sw in _STOPWORDS):
            continue

        historical = await _get_historical_freq(
            phrase, doc.meeting_type_id, doc.id, session
        )
        prior_avg = sum(historical) / len(historical) if historical else 0.0
        context = _get_context(doc.raw_text_zh, phrase)

        if not historical:
            candidates.append(Candidate(phrase, "DEBUT", freq, 0.0, context))
        elif prior_avg == 0 and freq >= min_freq:
            candidates.append(Candidate(phrase, "DEBUT", freq, 0.0, context))
        elif prior_avg > 0 and freq >= spike_threshold * prior_avg:
            candidates.append(Candidate(phrase, "SPIKE", freq, prior_avg, context))
        elif all(h == 0 for h in historical[-2:]) and freq >= min_freq:
            candidates.append(Candidate(phrase, "RETURN", freq, prior_avg, context))

    return candidates
