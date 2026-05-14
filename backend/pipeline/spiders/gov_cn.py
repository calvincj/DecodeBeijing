"""
gov.cn spider — scrapes the State Council news release page.

Target: https://www.gov.cn/xinwen/  (新闻 section)
Also covers NPC government work reports at npc.gov.cn.

gov.cn is the authoritative source for:
  - State Council executive meetings
  - NPC / CPPCC full text documents
  - Economic Work Conference communiqués
"""

import re
from datetime import date
from typing import Generator
import scrapy
from scrapy import Spider
from scrapy.http import Response

from pipeline.items import DocumentItem
from pipeline.utils import classify_meeting_type, extract_text_from_html


MEETING_KEYWORDS = [
    "中央经济工作会议",
    "政府工作报告",
    "全国人民代表大会.*开幕",
    "全国人民代表大会.*闭幕",
    "中央政治局.*会议",
    "全体会议.*公报",
    "政治局常委",
]

KEYWORD_RE = re.compile("|".join(MEETING_KEYWORDS))


class GovCnSpider(Spider):
    name = "gov_cn"
    allowed_domains = ["www.gov.cn", "npc.gov.cn"]

    start_urls = [
        "https://www.gov.cn/xinwen/",
        "https://www.gov.cn/ldhd/",          # 领导活动
    ]

    custom_settings = {
        "DOWNLOAD_DELAY": 3,
        "RANDOMIZE_DOWNLOAD_DELAY": True,
        "CONCURRENT_REQUESTS_PER_DOMAIN": 1,
        "ROBOTSTXT_OBEY": True,
        "USER_AGENT": "Mozilla/5.0 (compatible; academic-research-bot/1.0)",
        "ITEM_PIPELINES": {"pipeline.db_pipeline.PostgresPipeline": 300},
    }

    def parse(self, response: Response) -> Generator:
        for link in response.css("a::attr(href)").getall():
            if re.search(r"/\d{4}-\d{2}/\d{2}/content_\d+\.htm", link):
                yield response.follow(link, callback=self.parse_article)

        next_page = response.css("a.page-next::attr(href), a[rel='next']::attr(href)").get()
        if next_page:
            yield response.follow(next_page, callback=self.parse)

    def parse_article(self, response: Response) -> Generator:
        title = (
            response.css("h1.article-title::text").get()
            or response.css("h1::text").get()
            or ""
        ).strip()

        if not KEYWORD_RE.search(title):
            return

        body_html = (
            response.css("div.article-content").get()
            or response.css("div#UCAP-CONTENT").get()
            or ""
        )
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
        meta = response.css("meta[name='pubdate']::attr(content), meta[name='date']::attr(content)").get()
        if meta:
            try:
                return date.fromisoformat(meta[:10])
            except ValueError:
                pass

        m = re.search(r"/(\d{4})-(\d{2})/(\d{2})/", response.url)
        if m:
            return date(int(m.group(1)), int(m.group(2)), int(m.group(3)))

        return date.today()
