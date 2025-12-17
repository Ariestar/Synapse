"""
Markdown 文件浏览与写入 API
"""

from typing import Any, Dict
from datetime import datetime
from pathlib import Path
import re
import yaml

from flask import Blueprint, jsonify, request, current_app
from flask.typing import ResponseReturnValue

from app.config.settings import settings
from app.api.services.markdown_io import (
    filter_published_files,
    list_markdown_metadata,
    read_markdown_content,
    write_markdown_content,
    parse_frontmatter,
)

markdown_bp = Blueprint("markdown", __name__, url_prefix="/api/md")


@markdown_bp.route("/files", methods=["GET"])
def list_files() -> ResponseReturnValue:
    """
    列出 Markdown 文件元数据
    GET /api/md/files?include_unpublished=false
    """
    include_unpublished = request.args.get("include_unpublished", "false").lower() == "true"
    require_published = settings.NOTE_ONLY_PUBLISHED and not include_unpublished
    current_app.logger.info(
        "md_list_files: require_published=%s include_unpublished=%s root=%s glob=%s",
        require_published,
        include_unpublished,
        settings.NOTE_LOCAL_PATH,
        settings.NOTE_FILE_GLOB,
    )
    meta = list_markdown_metadata(
        root_dir=settings.NOTE_LOCAL_PATH,
        glob_pattern=settings.NOTE_FILE_GLOB,
        require_published=require_published,
    )
    return jsonify({"result": meta}), 200


@markdown_bp.route("/file", methods=["GET"])
def get_file() -> ResponseReturnValue:
    """
    获取指定 Markdown 内容
    GET /api/md/file?path=relative/path.md
    """
    rel_path = request.args.get("path")
    if not rel_path:
        return jsonify({"error": "path 参数必填"}), 400

    current_app.logger.info("md_get_file: path=%s root=%s", rel_path, settings.NOTE_LOCAL_PATH)
    data = read_markdown_content(settings.NOTE_LOCAL_PATH, rel_path)
    if not data:
        return jsonify({"error": "文件不存在或路径非法"}), 404

    return jsonify(data), 200


@markdown_bp.route("/file", methods=["PUT"])
def update_file() -> ResponseReturnValue:
    """
    更新指定 Markdown 文件内容。
    请求体:
    {
        "path": "相对路径",
        "content": "新的 markdown 全量内容"
    }
    """
    payload: Dict[str, Any] = request.get_json() or {}
    rel_path = payload.get("path")
    content = payload.get("content")

    if not rel_path or not content:
        return jsonify({"error": "path 与 content 均不能为空"}), 400

    current_app.logger.info("md_update_file: path=%s root=%s", rel_path, settings.NOTE_LOCAL_PATH)
    success = write_markdown_content(settings.NOTE_LOCAL_PATH, rel_path, content)
    if not success:
        return jsonify({"error": "路径非法或写入失败"}), 400

    return jsonify({"message": "更新成功"}), 200


@markdown_bp.route("/file", methods=["POST"])
def create_file() -> ResponseReturnValue:
    """
    创建新的 Markdown 文件
    请求体:
    {
        "title": "笔记标题",
        "content": "笔记内容（不含 frontmatter）",
        "tags": ["标签1", "标签2"],
        "subdir": "可选子目录，如 'Chat' 或 'AI问答'"
    }
    """
    payload: Dict[str, Any] = request.get_json() or {}
    title = payload.get("title", "").strip()
    content = payload.get("content", "").strip()
    tags = payload.get("tags", [])
    subdir = payload.get("subdir", "Chat")  # 默认保存到 Chat 子目录
    
    if not title and not content:
        return jsonify({"error": "title 或 content 至少需要一个"}), 400
    
    # 如果没有标题，从内容中提取
    if not title:
        title = content[:50].replace("\n", " ").strip()
        if len(content) > 50:
            title += "..."
    
    # 生成安全的文件名（移除特殊字符）
    safe_title = re.sub(r'[<>:"/\\|?*]', '', title)
    safe_title = re.sub(r'\s+', '_', safe_title)
    if len(safe_title) > 100:
        safe_title = safe_title[:100]
    
    # 如果文件名为空，使用时间戳
    if not safe_title:
        safe_title = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    # 构建文件路径
    if subdir:
        rel_path = f"{subdir}/{safe_title}.md"
    else:
        rel_path = f"{safe_title}.md"
    
    # 检查文件是否已存在，如果存在则添加时间戳
    base_path = Path(settings.NOTE_LOCAL_PATH) / rel_path
    if base_path.exists():
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        name_part = base_path.stem
        rel_path = f"{subdir}/{name_part}_{timestamp}.md" if subdir else f"{name_part}_{timestamp}.md"
    
    # 构建 frontmatter
    frontmatter = {
        "title": title,
        "date": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "status": "publish",
    }
    if tags:
        frontmatter["tags"] = tags
    
    # 组装完整的 Markdown 内容
    fm_str = "---\n" + yaml.safe_dump(frontmatter, allow_unicode=True, sort_keys=False) + "---\n\n"
    full_content = fm_str + content
    
    current_app.logger.info("md_create_file: path=%s root=%s", rel_path, settings.NOTE_LOCAL_PATH)
    success = write_markdown_content(settings.NOTE_LOCAL_PATH, rel_path, full_content)
    
    if not success:
        return jsonify({"error": "路径非法或写入失败"}), 400
    
    return jsonify({
        "message": "文件创建成功",
        "path": rel_path,
        "title": title
    }), 201

