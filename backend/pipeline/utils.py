import re
from typing import Optional

try:
    import trafilatura
    _HAS_TRAFILATURA = True
except ImportError:
    _HAS_TRAFILATURA = False

from html.parser import HTMLParser


# ── Text extraction ──────────────────────────────────────────────────────────

class _HTMLStripper(HTMLParser):
    def __init__(self):
        super().__init__()
        self.parts = []

    def handle_data(self, data):
        self.parts.append(data)

    def get_text(self):
        return "".join(self.parts)


def extract_text_from_html(html: str) -> str:
    if _HAS_TRAFILATURA:
        result = trafilatura.extract(html, include_comments=False, include_tables=False)
        if result:
            return result.strip()
    stripper = _HTMLStripper()
    stripper.feed(html)
    return re.sub(r"\s+", " ", stripper.get_text()).strip()


# ── Meeting type classification ──────────────────────────────────────────────

_MEETING_PATTERNS = [
    ("party_congress",           r"党的.*[二两]?十.*大|全国代表大会.*开幕|全国代表大会.*闭幕"),
    ("plenum",                   r"全体会议.*公报|届[一二三四五六七]中全会|中全会"),
    ("economic_work_conference", r"中央经济工作会议"),
    ("five_year_plan",           r"五年规划|五年计划"),
    ("two_sessions_national",    r"全国人民代表大会|全国政协|政府工作报告"),
    ("politburo",                r"中央政治局.*会议|政治局常委.*会议"),
]

_COMPILED = [(cat, re.compile(pat)) for cat, pat in _MEETING_PATTERNS]


def classify_meeting_type(text: str) -> str:
    for category, pattern in _COMPILED:
        if pattern.search(text):
            return category
    return "other"


# ── Chinese list extraction ──────────────────────────────────────────────────

# Matches items like: 一、xxx  二是xxx  （三）xxx  第四，xxx
_LIST_ITEM_RE = re.compile(
    r"(?:^|[\n。；])\s*"
    r"(?:第?[一二三四五六七八九十百]+[、是：:，,。]|（[一二三四五六七八九十]+）|\([一二三四五六七八九十]+\))"
    r"\s*(.{5,120})",
    re.MULTILINE,
)

# Heading patterns that typically precede a numbered list
_LIST_HEADING_RE = re.compile(
    r"((?:主要|重点|核心|关键)?[任目工举措](?:务|标|作|措).{0,20}[：:])",
    re.MULTILINE,
)


def extract_policy_lists(text: str) -> list[dict]:
    """
    Returns a list of dicts: {heading: str, items: [(position, text), ...]}
    """
    results = []
    # Split around headings to associate items with their heading
    segments = _LIST_HEADING_RE.split(text)

    # segments alternates: [pre-heading, heading, content, heading, content, ...]
    i = 1
    while i < len(segments) - 1:
        heading = segments[i].strip()
        content = segments[i + 1] if i + 1 < len(segments) else ""
        items = [
            (pos + 1, m.group(1).strip())
            for pos, m in enumerate(_LIST_ITEM_RE.finditer(content))
        ]
        if items:
            results.append({"heading": heading, "items": items})
        i += 2

    # Also try without a heading context (fallback)
    if not results:
        items = [
            (pos + 1, m.group(1).strip())
            for pos, m in enumerate(_LIST_ITEM_RE.finditer(text))
        ]
        if len(items) >= 3:
            results.append({"heading": "", "items": items})

    return results
