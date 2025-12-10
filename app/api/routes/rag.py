"""
RAG 检索与问答 API。
"""

from typing import Any, Dict

from flask import Blueprint, jsonify, request
from flask.typing import ResponseReturnValue

from app.api.services.rag import run_rag_pipeline
from app.config.settings import settings

rag_bp = Blueprint("rag", __name__, url_prefix="/api")


@rag_bp.route("/rag/query", methods=["POST"])
def rag_query() -> ResponseReturnValue:
    """提交问题并返回带引用的回答。"""
    data: Dict[str, Any] = request.get_json() or {}
    question = data.get("question")
    if not question:
        return jsonify({"error": "question 不能为空"}), 400

    top_k = int(data.get("top_k", 5))
    provider = data.get("provider", settings.DEFAULT_PROVIDER)
    model = data.get("model", settings.AI_PROVIDERS.get(provider, {}).get("model"))
    base_url = data.get("base_url")
    api_key = data.get("api_key")
    persona = data.get("persona")
    temperature = float(data.get("temperature", 0.3))
    max_tokens = int(data.get("max_tokens", 800))

    try:
        result = run_rag_pipeline(
            question=question,
            top_k=top_k,
            provider=provider,
            model=model,
            base_url=base_url,
            api_key=api_key,
            temperature=temperature,
            max_tokens=max_tokens,
            persona=persona,
        )
        return jsonify(result), 200
    except Exception as exc:  # noqa: BLE001
        return jsonify({"error": str(exc)}), 500


