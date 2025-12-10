"""
语义搜索接口
"""

from flask import Blueprint, request, jsonify

from app.api.services.indexer import note_indexer

search_bp = Blueprint("search", __name__, url_prefix="/api")


@search_bp.route("/search", methods=["GET"])
def semantic_search():
    """
    语义搜索
    GET /api/search?q=...
    """
    query = request.args.get("q")
    top_k = request.args.get("top_k", default=5, type=int)
    if not query:
        return jsonify({"error": "查询参数 q 不能为空"}), 400

    results = note_indexer.search(query=query, top_k=top_k)
    return jsonify({"result": results}), 200


