"""
Assistant role configuration APIs.
"""

from __future__ import annotations

from typing import Any, Dict

from flask import Blueprint, jsonify, request
from flask.typing import ResponseReturnValue

from app.api.services.assistant_config import load_assistant_config, save_assistant_config

assistant_bp = Blueprint("assistant", __name__, url_prefix="/api/assistant")


@assistant_bp.route("", methods=["GET"])
def get_assistant() -> ResponseReturnValue:
    """
    获取当前助手名称与性格描述。
    """
    cfg: Dict[str, str] = load_assistant_config()
    return jsonify(cfg), 200


@assistant_bp.route("", methods=["PUT"])
def update_assistant() -> ResponseReturnValue:
    """
    更新助手名称与性格描述（部分字段可选）。
    请求体:
    {
        "name": "助手名称",
        "persona": "性格/提示词描述"
    }
    """
    data: Dict[str, Any] = request.get_json(silent=True) or {}
    name = data.get("name")
    persona = data.get("persona")
    if name is None and persona is None:
        return jsonify({"error": "name 与 persona 至少提供一项"}), 400
    if name is not None and not isinstance(name, str):
        return jsonify({"error": "name 必须为字符串"}), 400
    if persona is not None and not isinstance(persona, str):
        return jsonify({"error": "persona 必须为字符串"}), 400

    cfg = save_assistant_config(name=name, persona=persona)
    return jsonify(cfg), 200









