"""
同步、标签与关系建议接口
"""

from typing import List, Optional

from flask import Blueprint, request, jsonify
from flask.typing import ResponseReturnValue
from pathlib import Path

from app.config.settings import settings
from app.api.services.git_sync import git_sync
from app.api.services.markdown_io import read_markdown_files, upsert_tags_to_frontmatter
from app.api.services.indexer import note_indexer
from app.api.services.ai_providers import get_chat_client

analyze_bp = Blueprint("analyze", __name__, url_prefix="/api")


@analyze_bp.route("/sync", methods=["POST"])
def sync_repo_and_index() -> ResponseReturnValue:
    """
    触发 Git pull 并重建向量索引
    """
    if not settings.NOTE_REPO_URL:
        return jsonify({"error": "未配置 NOTE_REPO_URL，请在 .env 文件中设置笔记仓库地址。"}), 400

    pulled = git_sync.pull()
    
    if not pulled:
        return jsonify({"error": "Git pull 执行失败，请检查服务端日志以获取详情（如网络问题、权限错误或冲突）。"}), 500

    files = read_markdown_files(settings.NOTE_LOCAL_PATH, settings.NOTE_FILE_GLOB)
    indexed = note_indexer.rebuild_index(files)
    return jsonify(
        {
            "pulled": pulled,
            "indexed_chunks": indexed,
            "files": len(files),
        }
    ), 200


def _generate_tags_via_llm(
    content: str,
    provider: str,
    model: str,
    base_url: Optional[str],
    api_key: Optional[str],
) -> List[str]:
    """调用 LLM 生成 tags"""
    client = get_chat_client(provider=provider, base_url=base_url, api_key=api_key)
    messages = [
        {"role": "system", "content": "你是一个笔记标签助手，请给出 3-5 个核心标签，简洁、用中文。仅返回逗号分隔标签列表。"},
        {"role": "user", "content": content[:4000]},
    ]
    resp = client.chat.completions.create(
        model=model,
        messages=messages,
        max_tokens=128,
        temperature=0.3,
    )
    text = resp.choices[0].message.content
    tags = [t.strip() for t in text.replace("，", ",").split(",") if t.strip()]
    return tags[:5]


@analyze_bp.route("/analyze/tags", methods=["POST"])
def auto_tags() -> ResponseReturnValue:
    """
    自动打标签：POST /api/analyze/tags
    body: {"file_path": "...", "commit": true} 或 {"content": "..."}
    """
    data = request.get_json() or {}
    file_path = data.get("file_path")
    content = data.get("content")
    commit_after = bool(data.get("commit", False))
    provider = data.get("provider", settings.DEFAULT_PROVIDER)
    model = data.get("model", settings.AI_PROVIDERS.get(provider, {}).get("model", "gpt-3.5-turbo"))
    base_url = data.get("base_url")
    api_key = data.get("api_key") or settings.AI_PROVIDERS.get(provider, {}).get("api_key")

    if not content:
        if not file_path:
            return jsonify({"error": "file_path 或 content 必须提供"}), 400
        try:
            content = Path(file_path).read_text(encoding="utf-8")
        except Exception as e:
            return jsonify({"error": f"读取文件失败: {e}"}), 400

    try:
        tags = _generate_tags_via_llm(content, provider, model, base_url, api_key)
    except Exception as e:
        return jsonify({"error": f"生成标签失败: {e}"}), 500

    updated_content = content
    if file_path:
        try:
            updated = upsert_tags_to_frontmatter(content, tags)
            Path(file_path).write_text(updated, encoding="utf-8")
            updated_content = updated
        except Exception as e:
            return jsonify({"error": f"写入标签失败: {e}"}), 500
        if commit_after:
            git_sync.commit_and_push(message=f"chore: auto tag {Path(file_path).name}")

    # 重新索引该文件
    if file_path:
        note_indexer.upsert_files([{"path": file_path, "content": updated_content}])

    return jsonify({"tags": tags}), 200


@analyze_bp.route("/analyze/relations", methods=["POST"])
def suggest_relations() -> ResponseReturnValue:
    """
    双向链接建议
    body: {"file_path": "...", "top_k": 5} 或 {"content": "...", "query": "..."}
    """
    data = request.get_json() or {}
    file_path = data.get("file_path")
    query = data.get("query")
    content = data.get("content")
    top_k = data.get("top_k", 5)

    if file_path and not content:
        try:
            content = Path(file_path).read_text(encoding="utf-8")
        except Exception as e:
            return jsonify({"error": f"读取文件失败: {e}"}), 400

    search_text = query or (content[:500] if content else None)
    if not search_text:
        return jsonify({"error": "需要 query 或 content/file_path"}), 400

    candidates = note_indexer.search(search_text, top_k=top_k + 1)
    suggestions = []
    for c in candidates:
        if file_path and c.get("file_path") == file_path:
            continue
        suggestions.append(
            {
                "file_path": c.get("file_path"),
                "reason": c.get("content", "")[:160],
                "score": c.get("score"),
            }
        )
        if len(suggestions) >= top_k:
            break

    return jsonify({"suggestions": suggestions}), 200

