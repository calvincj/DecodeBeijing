"""
Scrapy item pipeline: persists scraped DocumentItems to PostgreSQL,
then runs the NLP processing chain.
"""

import asyncio
from datetime import datetime
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from sqlalchemy import select

from pipeline.items import DocumentItem
from app.config import settings
from app.models.document import Document, MeetingType
from pipeline.processors.term_extractor import process_document_terms
from pipeline.processors.list_processor import process_document_lists
from pipeline.processors.gap_detector import run_gap_detection


class PostgresPipeline:
    def open_spider(self, spider):
        self.engine = create_async_engine(settings.database_url)
        self.Session = async_sessionmaker(self.engine, expire_on_commit=False)

    def close_spider(self, spider):
        asyncio.get_event_loop().run_until_complete(self.engine.dispose())

    def process_item(self, item: DocumentItem, spider):
        asyncio.get_event_loop().run_until_complete(self._save(item))
        return item

    async def _save(self, item: DocumentItem):
        async with self.Session() as session:
            async with session.begin():
                # Skip if already scraped
                existing = await session.execute(
                    select(Document).where(Document.source_url == item.source_url)
                )
                if existing.scalar_one_or_none():
                    return

                # Resolve meeting type
                mt_result = await session.execute(
                    select(MeetingType).where(MeetingType.category == item.meeting_type_hint)
                )
                meeting_type = mt_result.scalars().first()

                doc = Document(
                    meeting_type_id=meeting_type.id if meeting_type else None,
                    title_zh=item.title_zh,
                    title_en=item.title_en,
                    meeting_date=item.meeting_date,
                    source_url=item.source_url,
                    raw_text_zh=item.raw_text_zh,
                    raw_text_en=item.raw_text_en,
                    word_count_zh=len(item.raw_text_zh),
                )
                session.add(doc)
                await session.flush()

                # Run NLP chain
                await process_document_terms(doc, session)
                await process_document_lists(doc, session)
                await run_gap_detection(doc, session)

                doc.processed_at = datetime.utcnow()
