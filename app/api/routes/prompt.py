"""
Prompt generation routes: mine random wiki + refine via LLM.
"""

from __future__ import annotations

from typing import Any, Dict

from flask import Blueprint, jsonify, request
from flask.typing import ResponseReturnValue

from app.api.services.prompt_engine import generate_prompt_from_wiki, list_prompts
from app.config.settings import settings

prompt_bp = Blueprint("prompt", __name__, url_prefix="/api")


@prompt_bp.route("/prompts/generate", methods=["POST"])
def generate_prompt() -> ResponseReturnValue:
    """
    生成提示：随机维基词条 + LLM 提炼。
    """
    data: Dict[str, Any] = request.get_json(silent=True) or {}
    lang = data.get("lang", "en")
    mode_provider = data.get("provider", settings.DEFAULT_PROVIDER)
    model = data.get("model", settings.AI_PROVIDERS.get(mode_provider, {}).get("model"))
    base_url = data.get("base_url")
    api_key = data.get("api_key")
    try:
        result = generate_prompt_from_wiki(
            lang=lang,
            provider=mode_provider,
            model=model,
            base_url=base_url,
            api_key=api_key,
        )
        return jsonify(result), 200
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400
    except Exception as exc:  # noqa: BLE001
        return jsonify({"error": str(exc)}), 500


@prompt_bp.route("/prompts", methods=["GET"])
def list_prompt_items() -> ResponseReturnValue:
    """
    列出已存储的提示。
    """
    limit = request.args.get("limit", default=20, type=int)
    offset = request.args.get("offset", default=0, type=int)
    limit = min(max(limit, 1), 100)
    offset = max(offset, 0)
    try:
        items = list_prompts(limit=limit, offset=offset)
        return jsonify({"result": items, "limit": limit, "offset": offset}), 200
    except Exception as exc:  # noqa: BLE001
        return jsonify({"error": str(exc)}), 500

