#!/usr/bin/env python3
"""
Seeds the database with realistic sample documents so you can test the API
without needing real scraped data.

Documents are simplified but structurally accurate excerpts modelled on
real Economic Work Conference and Politburo communiqués.
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent / "backend"))

import asyncio
from datetime import date
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from sqlalchemy import select

from app.config import settings
from app.models.document import Document, MeetingType
from app.models.term import Term
from pipeline.processors.term_extractor import process_document_terms
from pipeline.processors.list_processor import process_document_lists
from pipeline.processors.gap_detector import run_gap_detection


# ── Sample documents ─────────────────────────────────────────────────────────
# Modelled on real communiqué language. Each covers a different year so we
# can see frequency trends across time.

DOCUMENTS = [
    {
        "title_zh": "中央经济工作会议公报（2020年）",
        "meeting_date": date(2020, 12, 18),
        "source_url": "file://sample/cewc-2020",
        "meeting_type": "economic_work_conference",
        "text": """
中央经济工作会议于2020年12月16日至18日在北京举行。

会议要求，明年要抓好八项重点任务：
一、强化国家战略科技力量。
二、增强产业链供应链自主可控能力。
三、坚持扩大内需这个战略基点。
四、全面推进改革开放。
五、解决好种子和耕地问题。
六、强化反垄断和防止资本无序扩张。
七、解决好大城市住房突出问题，坚持房住不炒定位。
八、做好碳达峰、碳中和工作。

会议强调，要坚持供给侧结构性改革这条主线，注重需求侧管理。
要实现高质量发展，推动经济发展质量变革、效率变革、动力变革。
要坚持扩大内需战略同深化供给侧结构性改革有机结合，以创新驱动、高质量供给引领和创造新需求。
要统筹发展和安全，实现更高质量、更有效率、更加公平、更可持续、更为安全的发展。
""",
    },
    {
        "title_zh": "中央经济工作会议公报（2021年）",
        "meeting_date": date(2021, 12, 10),
        "source_url": "file://sample/cewc-2021",
        "meeting_type": "economic_work_conference",
        "text": """
中央经济工作会议于2021年12月8日至10日在北京举行。

会议明确了2022年经济工作的主要任务：
一、宏观政策要稳健有效。
二、微观政策要持续激发市场主体活力。
三、结构政策要着力畅通国民经济循环。
四、科技政策要扎实落地。
五、改革开放政策要激活发展动力。
六、区域政策要增强发展平衡性协调性。
七、社会政策要兜牢民生底线。

会议指出，要正确认识和把握实现共同富裕的战略目标和实践途径。
要推动房地产业良性循环和健康发展，坚持房住不炒定位，因城施策。
要做好双碳工作，坚持统筹发展和安全，实现高质量发展。
要发挥双循环的战略优势，畅通国内国际双循环，提升供给侧结构性改革质量。
要坚持底线思维，防范化解重大风险，守住不发生系统性风险的底线。
""",
    },
    {
        "title_zh": "中央经济工作会议公报（2022年）",
        "meeting_date": date(2022, 12, 15),
        "source_url": "file://sample/cewc-2022",
        "meeting_type": "economic_work_conference",
        "text": """
中央经济工作会议于2022年12月15日至16日在北京举行。

会议强调，2023年经济工作千头万绪，要从战略全局出发，从改善社会心理预期、提振发展信心入手，纲举目张做好工作。要着力扩大国内需求，着力优化供给侧结构。

会议部署了五项重点任务：
一、着力扩大国内需求，把恢复和扩大消费摆在优先位置。
二、加快建设现代化产业体系。
三、切实落实两个毫不动摇。
四、更大力度吸引和利用外资。
五、有效防范化解重大经济金融风险，坚持房住不炒。

会议指出，中国式现代化是我们党领导全国人民在长期探索和实践中历经千辛万苦、付出巨大代价取得的重大成果。
要大力发展数字经济，加快推动人工智能发展。要坚持高质量发展，统筹发展和安全。
要推进乡村振兴，保障国家粮食安全，底线思维要贯穿始终。
""",
    },
    {
        "title_zh": "中央经济工作会议公报（2023年）",
        "meeting_date": date(2023, 12, 11),
        "source_url": "file://sample/cewc-2023",
        "meeting_type": "economic_work_conference",
        "text": """
中央经济工作会议于2023年12月11日至12日在北京举行。

会议强调，要以科技创新引领现代化产业体系建设，大力推进新型工业化。要以新质生产力为重要抓手，加快发展方式绿色转型。

会议部署了九项重点任务：
一、以科技创新引领现代化产业体系建设，发展新质生产力。
二、着力扩大国内需求。
三、深化重点领域改革。
四、扩大高水平对外开放。
五、持续有效防范化解重点领域风险。
六、坚持不懈抓好"三农"工作，推进乡村振兴。
七、推动城乡融合、区域协调发展。
八、深入推进生态文明建设和绿色低碳发展。
九、切实保障和改善民生。

会议指出，新质生产力是创新起主导作用，摆脱传统经济增长方式、生产力发展路径，具有高科技、高效能、高质量特征，符合新发展理念的先进生产力质态。
要积极培育新兴产业和未来产业，积极发展绿色低碳经济。
要坚持中国式现代化道路，实现高质量发展，统筹发展和安全。
房地产市场方面，要完善相关基础性制度，因城施策用好政策工具箱，促进房地产市场平稳健康发展。
""",
    },
    {
        "title_zh": "中央政治局会议（2021年7月）",
        "meeting_date": date(2021, 7, 30),
        "source_url": "file://sample/politburo-2021-07",
        "meeting_type": "politburo",
        "text": """
中共中央政治局2021年7月30日召开会议，分析研究当前经济形势，部署下半年经济工作。

会议强调，要坚持房子是用来住的、不是用来炒的定位，稳地价、稳房价、稳预期，促进房地产市场平稳健康发展。
要统筹有序做好碳达峰、碳中和工作，尽快出台2030年前碳达峰行动方案。
要推动共同富裕取得更为明显的实质性进展。
要发挥好双循环格局优势，提升自主创新能力，保障产业链供应链安全稳定。
会议指出，要坚持底线思维，做到统筹发展和安全，切实维护社会稳定大局。
要坚持两个毫不动摇，鼓励支持民营经济、民营企业发展壮大。
""",
    },
    {
        "title_zh": "中央政治局会议（2023年4月）",
        "meeting_date": date(2023, 4, 28),
        "source_url": "file://sample/politburo-2023-04",
        "meeting_type": "politburo",
        "text": """
中共中央政治局2023年4月28日召开会议，分析研究当前经济形势和经济工作。

会议指出，当前我国经济运行好转主要是恢复性的，内生动力还不强，需求仍然不足，经济转型升级面临新的挑战。
要加快培育壮大新能源汽车、锂电池、光伏产品等新兴产业，培育新质生产力。
要重视通用人工智能发展，营造创新生态，重视防范风险。

会议强调，要坚持中国式现代化的发展道路，推进高质量发展，统筹发展和安全。
要继续坚持房住不炒的定位，但要适应我国房地产市场供求关系发生重大变化的新形势，适时调整优化房地产政策。
在共同富裕方面，要多措并举扩大中等收入群体规模，扎实推进乡村振兴。
要践行底线思维，防范化解金融风险，维护经济金融稳定大局。
""",
    },
]


async def seed():
    engine = create_async_engine(settings.database_url)
    Session = async_sessionmaker(engine, expire_on_commit=False)

    async with Session() as session:
        async with session.begin():
            for doc_data in DOCUMENTS:
                existing = await session.execute(
                    select(Document).where(Document.source_url == doc_data["source_url"])
                )
                if existing.scalar_one_or_none():
                    print(f"  skip (exists): {doc_data['title_zh']}")
                    continue

                mt = await session.execute(
                    select(MeetingType).where(MeetingType.category == doc_data["meeting_type"])
                )
                mt_row = mt.scalars().first()

                text = doc_data["text"].strip()
                doc = Document(
                    meeting_type_id=mt_row.id if mt_row else None,
                    title_zh=doc_data["title_zh"],
                    meeting_date=doc_data["meeting_date"],
                    source_url=doc_data["source_url"],
                    raw_text_zh=text,
                    word_count_zh=len(text),
                )
                session.add(doc)
                await session.flush()

                n_terms = await process_document_terms(doc, session)
                n_lists = await process_document_lists(doc, session)
                n_gaps  = await run_gap_detection(doc, session)
                print(f"  + {doc_data['title_zh']}  [terms={n_terms}, lists={n_lists}, gaps={n_gaps}]")

    await engine.dispose()
    print("\nDone. You can now query the API at http://localhost:8000/docs")


if __name__ == "__main__":
    asyncio.run(seed())
