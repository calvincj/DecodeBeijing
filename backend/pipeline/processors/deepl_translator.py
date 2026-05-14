"""
DeepL translation utility.

Translates Chinese political phrases and context snippets to English.
The free-tier key (suffix :fx) supports 500k chars/month — ample for term
translation given the volume of documents in this project.
"""

import logging
from typing import Sequence

import deepl as _deepl

from app.config import settings

logger = logging.getLogger(__name__)


def _client() -> "_deepl.Translator | None":
    key = settings.deepl_api_key.strip()
    if not key:
        return None
    try:
        return _deepl.Translator(key)
    except Exception as e:
        logger.warning("Could not initialise DeepL client: %s", e)
        return None


def translate_zh_to_en(texts: Sequence[str]) -> list[str]:
    """
    Translate a list of Chinese strings to English.
    Returns a same-length list; on failure returns empty strings.
    """
    client = _client()
    if not client or not texts:
        return [""] * len(texts)

    # DeepL free tier has a per-request limit; chunk to 50 to be safe.
    results: list[str] = []
    chunk_size = 50
    texts = list(texts)
    for i in range(0, len(texts), chunk_size):
        chunk = texts[i : i + chunk_size]
        try:
            translated = client.translate_text(
                chunk,
                source_lang="ZH",
                target_lang="EN-US",
            )
            results.extend(r.text for r in translated)
        except Exception as e:
            logger.warning("DeepL translation failed for chunk %d: %s", i, e)
            results.extend("" for _ in chunk)

    return results
