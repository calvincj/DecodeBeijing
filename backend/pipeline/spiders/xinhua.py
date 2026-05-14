"""
Xinhua spider — scrapes official meeting readouts from xinhuanet.com.

Target URL patterns:
  https://www.xinhuanet.com/politics/  (政治 section)
  https://www.xinhuanet.com/2024-xx/xx/c_xxxxxxx.htm  (individual articles)

Keyword filters identify political meeting communiqués.
"""

import re
from datetime import date
from typing import Generator
import scrapy
from scrapy import Spider, Request
from scrapy.http import Response

from pipeline.items import DocumentItem
from pipeline.utils import classify_meeting_type, extract_text_from_html


MEETING_KEYWORDS = [
    "中央政治局", "全体会议", "中央经济工作会议",
    "全国人民代表大会", "政府工作报告", "全国政协",
    "党的.*大.*开幕", "党的.*大.*闭幕",
]

KEYWORD_RE = re.compile("|".join(MEETING_KEYWORDS))


class XinhuaSpider(Spider):
    name = "xinhua"
    allowed_domains = ["xinhuanet.com"]

    # Entry points: Xinhua politics section archives by year
    # Extend this list to go further back
    start_urls = [
        "https://www.xinhuanet.com/politics/leaders/",
        "https://www.xinhuanet.com/politics/",
    ]

    custom_settings = {
        "DOWNLOAD_DELAY": 2,
        "RANDOMIZE_DOWNLOAD_DELAY": True,
        "CONCURRENT_REQUESTS_PER_DOMAIN": 1,
        "ROBOTSTXT_OBEY": True,
        "USER_AGENT": "Mozilla/5.0 (compatible; academic-research-bot/1.0)",
        "ITEM_PIPELINES": {"pipeline.db_pipeline.PostgresPipeline": 300},
    }

    def parse(self, response: Response) -> Generator:
        # Find article links on listing pages
        for link in response.css("a::attr(href)").getall():
            if re.search(r"/\d{4}-\d{2}/\d{2}/c_\d+\.htm", link):
                yield response.follow(link, callback=self.parse_article)

        # Follow pagination if present
        next_page = response.css("a.next::attr(href)").get()
        if next_page:
            yield response.follow(next_page, callback=self.parse)

    def parse_article(self, response: Response) -> Generator:
        title = (
            response.css("h1.title::text").get()
            or response.css("h1::text").get()
            or ""
        ).strip()

        if not KEYWORD_RE.search(title):
            return

        body_html = response.css("div.article").get() or response.css("div#detail").get() or ""
        text = extract_text_from_html(body_html) if body_html else ""

        if len(text) < 200:
            return

        pub_date = self._parse_date(response)
        meeting_type_hint = classify_meeting_type(title + text[:500])

        yield DocumentItem(
            source_url=response.url,
            title_zh=title,
            raw_text_zh=text,
            meeting_date=pub_date,
            meeting_type_hint=meeting_type_hint,
        )

    def _parse_date(self, response: Response) -> date:
        # Try meta tag first
        meta_date = response.css("meta[name='publishdate']::attr(content)").get()
        if meta_date:
            try:
                return date.fromisoformat(meta_date[:10])
            except ValueError:
                pass

        # Fall back to URL pattern: /2024-03/15/c_xxx.htm
        m = re.search(r"/(\d{4})-(\d{2})/(\d{2})/", response.url)
        if m:
            return date(int(m.group(1)), int(m.group(2)), int(m.group(3)))

        return date.today()
