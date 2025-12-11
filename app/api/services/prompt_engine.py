"""
Alchemy workflow: mine (Wikipedia random), refine (LLM), store catalysts.
"""

from __future__ import annotations

import json
import os
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

import httpx

from app.api.services.ai_providers import get_chat_client
from app.config.settings import settings

WIKI_RANDOM_ENDPOINT = "https://{lang}.wikipedia.org/api/rest_v1/page/random/summary"

DATA_DIR = Path(__file__).resolve().parents[2] / "data"
DATA_DIR.mkdir(parents=True, exist_ok=True)
STORE_PATH = DATA_DIR / "prompts.json"

SYSTEM_PROMPT = (
    "你是“炼金术士”型的知识提炼者。给你一个看似无关的维基百科词条，"
    "你需要抽取其中的结构/哲学内核，并把它转化为可以跨领域迁移的思维模型。"
    "输出严格为 JSON。"
)


def _utc_iso() -> str:
    """Return current UTC time in ISO format."""
    return datetime.now(timezone.utc).isoformat()


def _load_store() -> List[Dict[str, Any]]:
    """Load stored prompts."""
    if not STORE_PATH.exists():
        return []
    try:
        with STORE_PATH.open("r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return []


def _save_store(entries: List[Dict[str, Any]]) -> None:
    """Persist prompts to disk."""
    STORE_PATH.parent.mkdir(parents=True, exist_ok=True)
    with STORE_PATH.open("w", encoding="utf-8") as f:
        json.dump(entries, f, ensure_ascii=False, indent=2)


def _fetch_random_wiki(lang: str = "en") -> Dict[str, Any]:
    """Fetch a random Wikipedia summary with explicit user agent."""
    lang_code = lang or "en"
    url = WIKI_RANDOM_ENDPOINT.format(lang=lang_code)
    headers = {
        "User-Agent": settings.WIKI_USER_AGENT,
        "Accept": "application/json",
    }
    with httpx.Client(timeout=15, headers=headers, follow_redirects=True) as client:
        resp = client.get(url)
        resp.raise_for_status()
        data = resp.json()
        return {
            "title": data.get("title", ""),
            "summary": data.get("extract", ""),
            "url": data.get("content_urls", {}).get("desktop", {}).get("page", ""),
            "lang": lang_code,
        }


def _build_user_prompt(topic: Dict[str, Any]) -> str:
    """Build user prompt for refining."""
    return (
        f"来源词条（{topic.get('lang', 'en')}）：{topic.get('title')}\n"
        f"摘要：{topic.get('summary')}\n\n"
        "请输出 JSON，字段：\n"
        'model_name: 提炼后的思维模型名字；\n'
        'core_principle: 一句话说明核心原理；\n'
        'transfer_analogy: 一个跨领域类比；\n'
        'application_starters: 3 个不同领域的应用开端列表。'
    )


def refine_topic(
    topic: Dict[str, Any],
    provider: Optional[str] = None,
    model: Optional[str] = None,
    base_url: Optional[str] = None,
    api_key: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Generate a structured prompt (catalyst) from a topic via LLM.
    """
    provider_to_use = provider or settings.DEFAULT_PROVIDER
    model_to_use = model or settings.AI_PROVIDERS.get(provider_to_use, {}).get("model")
    if not model_to_use:
        raise ValueError(f"未找到提供商 {provider_to_use} 的模型配置")

    client = get_chat_client(provider=provider_to_use, base_url=base_url, api_key=api_key)
    user_prompt = _build_user_prompt(topic)
    completion = client.chat.completions.create(
        model=model_to_use,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt},
        ],
        response_format={"type": "json_object"},
    )
    raw = completion.choices[0].message.content or "{}"
    try:
        idea = json.loads(raw)
    except json.JSONDecodeError:
        idea = {"raw": raw}

    return {
        "id": str(uuid.uuid4()),
        "source": topic,
        "prompt": idea,
        "created_at": _utc_iso(),
        "provider": provider_to_use,
        "model": model_to_use,
    }


def generate_prompt_from_wiki(
    lang: str = "en",
    provider: Optional[str] = None,
    model: Optional[str] = None,
    base_url: Optional[str] = None,
    api_key: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Fetch a random Wikipedia entry and generate a structured prompt.
    """
    topic = _fetch_random_wiki(lang=lang)
    prompt_item = refine_topic(topic, provider=provider, model=model, base_url=base_url, api_key=api_key)
    entries = _load_store()
    entries.insert(0, prompt_item)
    _save_store(entries)
    return prompt_item


def list_prompts(limit: int = 20, offset: int = 0) -> List[Dict[str, Any]]:
    """
    List stored prompts.
    """
    entries = _load_store()
    return entries[offset : offset + limit]

