"""
灵感合成（概念碰撞）API 路由。
"""

from __future__ import annotations

from typing import Any, Dict

from flask import Blueprint, jsonify, request
from flask.typing import ResponseReturnValue

from app.api.services.brainstorm import brainstorm_idea
from app.config.settings import settings

brainstorm_bp = Blueprint("brainstorm", __name__, url_prefix="/api")


@brainstorm_bp.route("/brainstorm", methods=["POST"])
def brainstorm() -> ResponseReturnValue:
    """
    概念碰撞：随机/反相似抽样两条笔记并生成创意。
    """
    data: Dict[str, Any] = request.get_json(silent=True) or {}
    mode = data.get("mode", "random")
    provider = data.get("provider", settings.DEFAULT_PROVIDER)
    model = data.get("model", settings.AI_PROVIDERS.get(provider, {}).get("model"))
    base_url = data.get("base_url")
    api_key = data.get("api_key")

    try:
        result = brainstorm_idea(
            mode=mode,
            provider=provider,
            model=model,
            base_url=base_url,
            api_key=api_key,
        )
        return jsonify(result), 200
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400
    except Exception as exc:  # noqa: BLE001
        return jsonify({"error": str(exc)}), 500



