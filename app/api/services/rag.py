"""
RAG 检索与生成服务。
"""

from typing import Any, Dict, List, Optional

from app.api.services.ai_providers import get_chat_client
from app.api.services.indexer import note_indexer
from app.api.services.notes import note
from app.config.settings import settings

DEFAULT_SYSTEM_PROMPT = "你是一个知识库助手，请基于提供的笔记内容回答问题，优先使用中文，并在回答末尾注明引用编号，例如 [1][2]。"


def search_contexts(question: str, top_k: int) -> List[Dict[str, Any]]:
    """执行优先向量、次级关键词的检索，返回标准化片段列表。"""
    import logging
    logger = logging.getLogger(__name__)
    
    # 优先使用向量搜索
    vector_results = note_indexer.search(query=question, top_k=top_k)
    logger.info(f"向量搜索返回 {len(vector_results)} 条结果")
    if vector_results:
        return vector_results

    # 如果向量搜索没有结果，使用关键词搜索
    logger.info("向量搜索无结果，尝试关键词搜索")
    keyword_results = note.search_notes(query=question, top_k=top_k)
    logger.info(f"关键词搜索返回 {len(keyword_results)} 条结果")
    
    normalized: List[Dict[str, Any]] = []
    for item in keyword_results:
        # 处理不同的字段名：Notes 类返回的笔记有 source 字段
        content = item.get("content") or item.get("text", "")
        source = item.get("source", "")
        title = item.get("title", "") or source or "未命名"
        tags = item.get("tags", [])
        score = float(item.get("similarity") or item.get("score", 0.0))
        
        normalized.append(
            {
                "content": content,
                "file_path": source,  # Notes 类使用 source 字段
                "rel_path": source,   # Notes 类使用 source 字段
                "title": title,
                "tags": tags,
                "score": score,
            }
        )
    return normalized


def build_context_prompt(results: List[Dict[str, Any]]) -> str:
    """将检索结果组装为带编号的提示文本。"""
    lines: List[str] = []
    for idx, item in enumerate(results, 1):
        title = item.get("title") or "未命名"
        rel_path = item.get("rel_path") or item.get("file_path") or "未知路径"
        content = item.get("content") or ""
        lines.append(f"[{idx}] {title} ({rel_path})\n{content}")
    return "\n\n".join(lines)


def run_rag_pipeline(
    question: str,
    top_k: int = 5,
    provider: Optional[str] = None,
    model: Optional[str] = None,
    base_url: Optional[str] = None,
    api_key: Optional[str] = None,
    temperature: float = 0.3,
    max_tokens: int = 800,
    persona: Optional[str] = None,
) -> Dict[str, Any]:
    """执行 RAG 流程：检索上下文并生成带引用的回答。"""
    import logging
    logger = logging.getLogger(__name__)
    
    contexts = search_contexts(question, top_k=top_k)
    logger.info(f"检索到 {len(contexts)} 条笔记上下文")
    
    # 确保 contexts 是列表，即使为空
    if not contexts:
        contexts = []
    
    context_prompt = build_context_prompt(contexts) if contexts else ""

    system_prompt = persona or DEFAULT_SYSTEM_PROMPT
    if context_prompt:
        system_prompt += "\n以下是相关笔记片段，请严格基于其中信息回答，并在回答末尾附上引用编号。"

    provider_to_use = provider or settings.DEFAULT_PROVIDER
    model_to_use = model or settings.AI_PROVIDERS.get(provider_to_use, {}).get("model")

    messages = [
        {"role": "system", "content": system_prompt + ("\n\n" + context_prompt if context_prompt else "")},
        {"role": "user", "content": question},
    ]

    client = get_chat_client(provider=provider_to_use, base_url=base_url, api_key=api_key)
    resp = client.chat.completions.create(
        model=model_to_use,
        messages=messages,
        temperature=temperature,
        max_tokens=max_tokens,
    )
    answer = resp.choices[0].message.content

    citations = [
        {
            "title": ctx.get("title") or "未命名",
            "file_path": ctx.get("file_path") or "",
            "rel_path": ctx.get("rel_path") or ctx.get("file_path") or "",
            "score": ctx.get("score", 0.0),
            "snippet": (ctx.get("content") or "")[:400],
            "tags": ctx.get("tags", []),
        }
        for ctx in contexts
    ]

    return {
        "answer": answer,
        "citations": citations,
        "contexts": contexts,  # 确保返回列表，即使为空
    }


