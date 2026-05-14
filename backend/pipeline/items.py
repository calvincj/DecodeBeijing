from dataclasses import dataclass, field
from datetime import date
from typing import Optional


@dataclass
class DocumentItem:
    source_url:        str
    title_zh:          str
    raw_text_zh:       str
    meeting_date:      date
    meeting_type_hint: str          # e.g. "economic_work_conference"
    title_en:          Optional[str] = None
    raw_text_en:       Optional[str] = None
