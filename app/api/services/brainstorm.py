"""
灵感合成（概念碰撞）服务。
"""

from __future__ import annotations

import json
import random
from typing import Any, Dict, List, Optional, Tuple

import numpy as np

from app.api.services.ai_providers import get_chat_client
from app.api.services.indexer import note_indexer
from app.api.services.prompt_engine import STORE_PATH, _fetch_random_wiki, refine_topic
from app.config.settings import settings

SYSTEM_PROMPT: str = (
    "你是一个极具洞察力的技术编辑和创新顾问。"
    "你的任务是进行\"概念合成\"：阅读用户提供的两篇不相关的笔记，"
    "找到它们底层的逻辑共性、互补性或冲突点，并据此生成一个新的创意选题。"
)

USER_PROMPT_TEMPLATE: str = (
    "【笔记 A】: {content_a}\n"
    "---\n"
    "【笔记 B】: {content_b}\n"
    "---\n"
    "{prompt_hint}"
    "请基于这两篇笔记，执行以下任务：\n"
    "1. 寻找连接点：一句话解释 A 和 B 之间可能存在的某种抽象联系（例如：结构相似、互为隐喻、问题与方法）。\n"
    "2. 生成选题：构思一个极具吸引力的文章标题或项目名称。\n"
    "3. 大纲设计：列出 3 个核心论点，说明如何结合 A 的技术/思想去解决 B 领域的问题（或反之）。\n"
    '输出格式为 JSON：{{"connection": "...", "title": "...", "outline": ["point1", "point2", "point3"]}}'
)

MAX_SNIPPET_LEN: int = 800


def _load_prompt_catalysts(limit: int = 1) -> List[Dict[str, Any]]:
    """
    Load recent prompt catalysts generated from Wikipedia.
    """
    if not STORE_PATH.exists():
        return []
    try:
        with STORE_PATH.open("r", encoding="utf-8") as f:
            data: List[Dict[str, Any]] = json.load(f)
    except Exception:
        return []
    return data[:limit]


def _fetch_prompt_terms(
    lang: str = "zh",
    provider: Optional[str] = None,
    model: Optional[str] = None,
    base_url: Optional[str] = None,
    api_key: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Fetch a fresh prompt catalyst directly from Wikipedia + LLM without persisting.
    """
    provider_to_use = provider or settings.DEFAULT_PROVIDER
    model_to_use = _resolve_model(provider_to_use, model)
    try:
        topic = _fetch_random_wiki(lang=lang)
        prompt_item = refine_topic(
            topic,
            provider=provider_to_use,
            model=model_to_use,
            base_url=base_url,
            api_key=api_key,
        )
        return prompt_item.get("prompt", {}) or {}
    except Exception:
        return {}


def _build_prompt_hint(
    provider: Optional[str],
    model: Optional[str],
    base_url: Optional[str],
    api_key: Optional[str],
    prompt_lang: str,
) -> str:
    """
    Build a hint text from stored prompts to perturb brainstorming.
    """
    # Prefer fresh prompt terms to增加多样性；若失败则回退本地缓存。
    prompt = _fetch_prompt_terms(
        lang=prompt_lang,
        provider=provider,
        model=model,
        base_url=base_url,
        api_key=api_key,
    )
    if not prompt:
        catalysts = _load_prompt_catalysts(limit=1)
        prompt = (catalysts[0].get("prompt", {}) if catalysts else {}) or {}
    model_name = prompt.get("model_name") or ""
    principle = prompt.get("core_principle") or ""
    transfer = prompt.get("transfer_analogy") or ""
    starters = prompt.get("application_starters") or []
    starter = starters[0] if starters else ""
    hint_lines = [
        "【提示扰动】以下为最近生成的跨域思维模型，请参考其抽象方式再进行概念碰撞：",
        f"- model_name: {model_name}",
        f"- core_principle: {principle}",
        f"- transfer_analogy: {transfer}",
        f"- starter: {starter}",
        "---\n",
    ]
    return "\n".join([line for line in hint_lines if line.strip()])


def _truncate(text: str, max_len: int = MAX_SNIPPET_LEN) -> str:
    """截断文本避免 token 过长。"""
    if len(text) <= max_len:
        return text
    return text[:max_len] + "..."


def _ensure_notes_available(min_count: int) -> None:
    """确保索引中存在足够的条目。"""
    if len(note_indexer.entries) < min_count:
        raise ValueError("笔记数量不足，无法碰撞")


def _pick_file_level_indices() -> List[int]:
    """
    基于文件粒度抽样：每个文件只取一个索引，避免同文件多 chunk 被反复抽中。
    """
    buckets: Dict[str, int] = {}
    for idx, entry in enumerate(note_indexer.entries):
        metadata: Dict[str, Any] = entry.get("metadata", {}) or {}
        file_key = str(
            metadata.get("rel_path")
            or metadata.get("file_path")
            or metadata.get("title")
            or f"entry_{idx}"
        )
        if file_key not in buckets:
            buckets[file_key] = idx
    return list(buckets.values())


def _pick_shorter_indices(max_candidates: int = 50) -> List[int]:
    """
    优先选择较短文本的索引集合，增加随机性同时避免总是长文。
    """
    lengths: List[int] = [len(str(entry.get("text", ""))) for entry in note_indexer.entries]
    if not lengths:
        return []
    median_len = float(np.median(lengths))
    threshold = median_len * 1.2 or 1.0
    candidates = [idx for idx, length in enumerate(lengths) if length <= threshold]
    if len(candidates) < 2:
        # 回退：取最短的前若干条再随机
        sorted_indices = [idx for idx, _ in sorted(enumerate(lengths), key=lambda item: item[1])]
        candidates = sorted_indices[: max_candidates or 2]
    return candidates


def _entry_to_note(entry: Dict[str, Any]) -> Dict[str, str]:
    """将索引条目转换为笔记字典。"""
    metadata: Dict[str, Any] = entry.get("metadata", {}) or {}
    return {
        "content": _truncate(entry.get("text", "")),
        "title": str(metadata.get("title") or metadata.get("rel_path") or metadata.get("file_path") or "未命名笔记"),
        "rel_path": str(metadata.get("rel_path") or metadata.get("file_path") or ""),
    }


def _pick_least_similar(base_idx: int) -> int:
    """基于余弦相似度选出与基向量最不相似的索引。"""
    embeddings: List[List[float]] = [entry.get("embedding", []) for entry in note_indexer.entries]
    if not embeddings or len(embeddings) <= 1:
        return base_idx

    try:
        emb_matrix = np.array(embeddings, dtype="float32")
        base_emb = emb_matrix[base_idx]
        base_norm = np.linalg.norm(base_emb) + 1e-12
        norms = np.linalg.norm(emb_matrix, axis=1) + 1e-12
        sims = (emb_matrix @ base_emb) / (norms * base_norm)
        sims[base_idx] = 1.0
        least_idx = int(np.argmin(sims))
        return least_idx
    except Exception:
        return base_idx


def pick_notes(mode: str = "random") -> List[Dict[str, str]]:
    """
    选择两条用于概念碰撞的笔记。

    :param mode: 选择模式，支持 "random" 或 "mmr"（基于最不相似）。
    :return: 包含两条笔记内容与元数据的列表。
    """
    _ensure_notes_available(2)
    total = len(note_indexer.entries)

    if mode == "mmr":
        idx_a = random.randrange(total)
        idx_b = _pick_least_similar(idx_a)
        if idx_b == idx_a:
            indices = random.sample(range(total), 2)
        else:
            indices = [idx_a, idx_b]
    else:
        file_pool = _pick_file_level_indices()
        pool = _pick_shorter_indices()
        # 先按文件去重，再按长度过滤；若不足则回退。
        primary_pool = [idx for idx in pool if idx in file_pool]
        if len(primary_pool) >= 2:
            indices = random.sample(primary_pool, 2)
        elif len(file_pool) >= 2:
            indices = random.sample(file_pool, 2)
        elif len(pool) >= 2:
            indices = random.sample(pool, 2)
        else:
            indices = random.sample(range(total), 2)

    return [_entry_to_note(note_indexer.entries[i]) for i in indices]


def _build_messages(
    note_a: Dict[str, str],
    note_b: Dict[str, str],
    provider: Optional[str],
    model: Optional[str],
    base_url: Optional[str],
    api_key: Optional[str],
    prompt_lang: str,
) -> List[Dict[str, str]]:
    """构造 LLM 聊天消息，并注入 prompt 扰动。"""
    prompt_hint = _build_prompt_hint(
        provider=provider,
        model=model,
        base_url=base_url,
        api_key=api_key,
        prompt_lang=prompt_lang,
    )
    user_prompt = USER_PROMPT_TEMPLATE.format(
        content_a=note_a["content"],
        content_b=note_b["content"],
        prompt_hint=prompt_hint,
    )
    return [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": user_prompt},
    ]


def _resolve_model(provider: str, model: str | None) -> str:
    """解析模型名称，若缺失则使用 provider 默认模型。"""
    if model:
        return model
    model_from_cfg = settings.AI_PROVIDERS.get(provider, {}).get("model")
    if model_from_cfg:
        return model_from_cfg
    raise ValueError(f"未找到提供商 {provider} 的模型配置")


def brainstorm_idea(
    mode: str = "random",
    provider: str | None = None,
    model: str | None = None,
    base_url: str | None = None,
    api_key: str | None = None,
    prompt_lang: str = "zh",
) -> Dict[str, Any]:
    """
    执行概念碰撞并返回合成结果。

    :param mode: 选择笔记的模式，random 或 mmr。
    :param provider: LLM 提供商。
    :param model: 模型名称。
    :param base_url: LLM 基础地址。
    :param api_key: LLM API Key。
    :return: 结果字典，包含源笔记与生成的创意。
    """
    provider_to_use = provider or settings.DEFAULT_PROVIDER
    model_to_use = _resolve_model(provider_to_use, model)

    notes = pick_notes(mode=mode)
    note_a, note_b = notes

    client = get_chat_client(provider=provider_to_use, base_url=base_url, api_key=api_key)
    messages = _build_messages(
        note_a,
        note_b,
        provider=provider_to_use,
        model=model_to_use,
        base_url=base_url,
        api_key=api_key,
        prompt_lang=prompt_lang,
    )

    completion = client.chat.completions.create(
        model=model_to_use,
        messages=messages,
        response_format={"type": "json_object"},
    )
    content = completion.choices[0].message.content or "{}"
    try:
        idea = json.loads(content)
    except json.JSONDecodeError:
        idea = {"raw": content}

    return {
        "source_notes": [
            {"title": note_a["title"], "rel_path": note_a["rel_path"]},
            {"title": note_b["title"], "rel_path": note_b["rel_path"]},
        ],
        "idea": idea,
        "mode": mode,
        "model": model_to_use,
        "provider": provider_to_use,
    }



