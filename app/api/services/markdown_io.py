"""
Markdown 读取与 Frontmatter 处理
"""

from pathlib import Path
from typing import Dict, List, Optional, Tuple
import re
import yaml

FRONTMATTER_PATTERN = re.compile(r"^---\s*\n(.*?)\n---\s*\n", re.DOTALL)


def read_markdown_files(root_dir: str, glob_pattern: str = "**/*.md") -> List[Dict]:
    """
    遍历 root_dir 下的 Markdown 文件
    返回: [{"path": str, "content": str}]
    """
    root = Path(root_dir)
    files = []
    if not root.exists():
        return files

    for md_path in root.glob(glob_pattern):
        if md_path.is_file():
            try:
                text = md_path.read_text(encoding="utf-8")
                files.append({"path": str(md_path), "content": text})
            except Exception:
                continue
    return files


def parse_frontmatter(content: str) -> Tuple[Dict, str]:
    """
    提取 frontmatter 与正文
    """
    match = FRONTMATTER_PATTERN.match(content)
    if not match:
        return {}, content
    fm_raw = match.group(1)
    try:
        data = yaml.safe_load(fm_raw) or {}
    except yaml.YAMLError:
        data = {}
    body = content[match.end():]
    return data, body


def upsert_tags_to_frontmatter(content: str, tags: List[str]) -> str:
    """
    在 frontmatter 中更新 tags 字段
    """
    data, body = parse_frontmatter(content)
    data["tags"] = tags
    new_fm = "---\n" + yaml.safe_dump(data, allow_unicode=True, sort_keys=False) + "---\n"
    return new_fm + body


def filter_published_files(files: List[Dict], require_published: bool) -> List[Dict]:
    """
    过滤出 frontmatter 中 status: publish 的文件（可选）
    """
    if not require_published:
        return files

    published_files: List[Dict] = []
    for f in files:
        content = f.get("content", "")
        frontmatter, _ = parse_frontmatter(content)
        status = str(frontmatter.get("status", "")).lower()
        if status == "publish":
            published_files.append(f)
    return published_files


def list_markdown_metadata(
    root_dir: str,
    glob_pattern: str,
    require_published: bool,
) -> List[Dict]:
    """
    返回 Markdown 文件的元数据列表
    """
    files = read_markdown_files(root_dir, glob_pattern)
    files = filter_published_files(files, require_published)
    root = Path(root_dir).resolve()
    meta_list: List[Dict] = []
    for f in files:
        abs_path = Path(f["path"]).resolve()
        try:
            rel_path = abs_path.relative_to(root)
        except ValueError:
            rel_path = abs_path.name
        frontmatter, _ = parse_frontmatter(f.get("content", ""))
        title = frontmatter.get("title") or abs_path.stem
        status = frontmatter.get("status", "")
        tags = frontmatter.get("tags", [])
        meta_list.append(
            {
                "path": str(rel_path).replace("\\", "/"),
                "title": title,
                "status": status,
                "tags": tags,
                "content": f.get("content", ""),
            }
        )
    return meta_list


def read_markdown_content(root_dir: str, rel_path: str) -> Optional[Dict]:
    """
    按相对路径读取 Markdown 内容与 frontmatter
    """
    base = Path(root_dir).resolve()
    target = (base / rel_path).resolve()
    try:
        target.relative_to(base)
    except ValueError:
        return None
    if not target.exists() or not target.is_file():
        return None
    content = target.read_text(encoding="utf-8")
    fm, body = parse_frontmatter(content)
    return {
        "path": rel_path.replace("\\", "/"),
        "frontmatter": fm,
        "content": content,
        "body": body,
    }


def write_markdown_content(root_dir: str, rel_path: str, content: str) -> bool:
    """
    将内容写回指定的 Markdown 文件。
    """
    base = Path(root_dir).resolve()
    target = (base / rel_path).resolve()
    try:
        target.relative_to(base)
    except ValueError:
        return False

    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(content, encoding="utf-8")
    return True


def delete_markdown_file(root_dir: str, rel_path: str) -> bool:
    """
    删除指定的 Markdown 文件
    """
    base = Path(root_dir).resolve()
    target = (base / rel_path).resolve()
    try:
        target.relative_to(base)
    except ValueError:
        return False
        
    if not target.exists() or not target.is_file():
        return False
        
    try:
        target.unlink()
        return True
    except Exception:
        return False


