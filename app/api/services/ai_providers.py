"""
AI 提供商统一封装：聊天与嵌入
"""

from typing import Any, Callable, Dict, List, Optional
import httpx
from openai import OpenAI

from app.config.settings import settings


def resolve_provider_config(provider: str, base_url: Optional[str], api_key: Optional[str]):
    cfg = settings.AI_PROVIDERS.get(provider, {})
    # 优先显式传入，其次 provider 配置，再次统一 LLM_API_KEY
    final_base = base_url or cfg.get("base_url")
    final_key = api_key or cfg.get("api_key") or settings.UNIFIED_API_KEY
    return final_base, final_key, cfg.get("model")


def get_chat_client(provider: str, base_url: Optional[str] = None, api_key: Optional[str] = None) -> OpenAI:
    base_url, api_key, _ = resolve_provider_config(provider, base_url, api_key)
    if not api_key:
        raise ValueError(f"未配置 {provider} 的 API Key")
    return OpenAI(base_url=base_url, api_key=api_key)


def get_embedding_callable(
    provider: Optional[str] = None,
    model: Optional[str] = None,
    base_url: Optional[str] = None,
    api_key: Optional[str] = None,
) -> Callable[[List[str]], List[List[float]]]:
    """
    返回一个可调用对象，输入文本列表，输出 embedding 列表。
    支持 OpenAI 兼容接口；对 bigmodel 走专门 HTTP 调用。
    """
    provider = provider or settings.EMBEDDING_PROVIDER
    model = model or settings.EMBEDDING_MODEL
    base_url = base_url or settings.EMBEDDING_BASE_URL
    api_key = api_key or settings.EMBEDDING_API_KEY

    # bigmodel 专用适配（OpenAI embeddings 不兼容时走 HTTP 手调）
    if provider == "bigmodel":
        final_base, final_key, _ = resolve_provider_config(provider, base_url, api_key)
        if not final_key:
            raise ValueError("未配置 bigmodel 嵌入的 API Key")
        client = httpx.Client(timeout=30)
        endpoint = f"{final_base.rstrip('/')}/embeddings"

        def embed_bigmodel(texts: List[str]) -> List[List[float]]:
            sanitized: List[str] = [str(t)[:2000] for t in texts if str(t).strip()]
            if not sanitized:
                return []

            def _post(batch: List[str]) -> List[List[float]]:
                payload: Dict[str, Any] = {"model": model, "input": batch}
                resp = client.post(
                    endpoint,
                    headers={"Authorization": f"Bearer {final_key}"},
                    json=payload,
                )
                if resp.status_code >= 400:
                    detail = resp.text
                    raise httpx.HTTPStatusError(
                        f"bigmodel embeddings error {resp.status_code}: {detail}",
                        request=resp.request,
                        response=resp,
                    )
                try:
                    data = resp.json()
                except ValueError as exc:  # JSON decode error
                    raise httpx.HTTPStatusError(
                        f"bigmodel embeddings invalid json: {resp.text}",
                        request=resp.request,
                        response=resp,
                    ) from exc
                items = data.get("data") or []
                return [item.get("embedding") for item in items if item.get("embedding") is not None]

            try:
                return _post(sanitized)
            except httpx.HTTPStatusError as exc:
                # 若批量失败，尝试单条回退以定位问题
                if len(sanitized) > 1:
                    embeddings: List[List[float]] = []
                    for item in sanitized:
                        embeddings.extend(_post([item]))
                    return embeddings
                raise exc
            return _post(sanitized) or []

        return embed_bigmodel

    # 默认 OpenAI 兼容
    base_url, api_key, _ = resolve_provider_config(provider, base_url, api_key)
    if not api_key:
        raise ValueError(f"未配置嵌入模型的 API Key ({provider})")

    client = OpenAI(base_url=base_url, api_key=api_key, http_client=httpx.Client(timeout=30))

    def embed(texts: List[str]) -> List[List[float]]:
        resp = client.embeddings.create(model=model, input=texts)
        return [item.embedding for item in resp.data]

    return embed


