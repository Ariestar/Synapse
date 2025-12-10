"""
笔记模块
负责笔记的存储、检索、管理
"""

import json
import os
import uuid
from datetime import datetime
from typing import List, Dict, Optional
from pathlib import Path


class Notes:
    """笔记类
    1. 初始化笔记存储路径，加载已有笔记
    2. 添加笔记
        2.1 自动生成笔记ID
        2.2 存储笔记内容、标题、标签、创建时间、更新时间
        2.3 保存笔记到文件
    3. 搜索笔记
        3.1 根据ID获取笔记
    4. 更新笔记
     4.1 根据ID更新笔记内容、标题、标签、更新时间
    5. 删除笔记
        5.1 根据ID删除笔记
    6. 列出笔记
        6.1 支持分页查询
    """

    def __init__(self, storage: str = "notes_storage"):
        """
        初始化笔记存储路径，加载已有笔记
        :param storage: 存储目录名
        """
        # 获取项目根目录
        project_root = Path(__file__).parent.parent.parent.parent
        self.storage_dir = project_root / storage
        self.storage_dir.mkdir(exist_ok=True)
        
        self.notes_file = self.storage_dir / "notes.json"
        self.notes: Dict[str, Dict] = {}
        self._load_notes()

    def _load_notes(self):
        """加载已有笔记"""
        if self.notes_file.exists():
            try:
                with open(self.notes_file, 'r', encoding='utf-8') as f:
                    self.notes = json.load(f)
            except (json.JSONDecodeError, IOError):
                self.notes = {}
        else:
            self.notes = {}

    def _save_notes(self):
        """保存笔记到文件"""
        try:
            with open(self.notes_file, 'w', encoding='utf-8') as f:
                json.dump(self.notes, f, ensure_ascii=False, indent=2)
        except IOError as e:
            raise Exception(f"保存笔记失败: {str(e)}")

    def _generate_id(self) -> str:
        """生成唯一的笔记ID"""
        return str(uuid.uuid4())

    def add_note(self, content: str, title: Optional[str] = None, 
                 tags: Optional[List[str]] = None, source: Optional[str] = None) -> str:
        """
        添加笔记
        :param content: 笔记内容
        :param title: 笔记标题（可选）
        :param tags: 标签列表（可选）
        :param source: 来源（可选）
        :return: 笔记ID
        """
        note_id = self._generate_id()
        now = datetime.now().isoformat()
        
        # 如果没有提供标题，从内容中提取前50个字符
        if not title:
            title = content[:50] + "..." if len(content) > 50 else content
        
        note = {
            "id": note_id,
            "title": title,
            "content": content,
            "tags": tags or [],
            "source": source or "",
            "created_at": now,
            "updated_at": now
        }
        
        self.notes[note_id] = note
        self._save_notes()
        return note_id

    def get_note(self, note_id: str) -> Optional[Dict]:
        """
        根据ID获取笔记
        :param note_id: 笔记ID
        :return: 笔记字典，如果不存在返回None
        """
        return self.notes.get(note_id)

    def update_note(self, note_id: str, content: Optional[str] = None,
                   title: Optional[str] = None, tags: Optional[List[str]] = None,
                   source: Optional[str] = None) -> bool:
        """
        更新笔记
        :param note_id: 笔记ID
        :param content: 新内容（可选）
        :param title: 新标题（可选）
        :param tags: 新标签列表（可选）
        :param source: 新来源（可选）
        :return: 是否更新成功
        """
        if note_id not in self.notes:
            return False
        
        note = self.notes[note_id]
        
        if content is not None:
            note["content"] = content
        if title is not None:
            note["title"] = title
        if tags is not None:
            note["tags"] = tags
        if source is not None:
            note["source"] = source
        
        note["updated_at"] = datetime.now().isoformat()
        self._save_notes()
        return True

    def delete_note(self, note_id: str) -> bool:
        """
        删除笔记
        :param note_id: 笔记ID
        :return: 是否删除成功
        """
        if note_id in self.notes:
            del self.notes[note_id]
            self._save_notes()
            return True
        return False

    def list_notes(self, limit: int = 50, offset: int = 0) -> List[Dict]:
        """
        列出笔记，支持分页
        :param limit: 限制返回数量
        :param offset: 偏移量
        :return: 笔记列表
        """
        notes_list = list(self.notes.values())
        # 按更新时间倒序排序
        notes_list.sort(key=lambda x: x.get("updated_at", ""), reverse=True)
        
        # 分页
        start = offset
        end = offset + limit
        return notes_list[start:end]

    def search_notes(self, query: str, top_k: int = 5) -> List[Dict]:
        """
        搜索笔记
        使用简单的文本匹配计算相似度
        :param query: 搜索查询
        :param top_k: 返回前k个结果
        :return: 笔记列表（按相似度排序）
        """
        if not query:
            return []
        
        query_lower = query.lower()
        results = []
        
        for note_id, note in self.notes.items():
            # 计算相似度分数
            score = 0.0
            content = note.get("content", "").lower()
            title = note.get("title", "").lower()
            tags = [tag.lower() for tag in note.get("tags", [])]
            
            # 标题匹配权重最高
            if query_lower in title:
                score += 10.0
            elif any(word in title for word in query_lower.split()):
                score += 5.0
            
            # 内容匹配
            if query_lower in content:
                score += 3.0
            else:
                # 计算匹配的单词数
                query_words = set(query_lower.split())
                content_words = set(content.split())
                matched_words = query_words.intersection(content_words)
                if matched_words:
                    score += len(matched_words) * 0.5
            
            # 标签匹配
            for tag in tags:
                if query_lower in tag or any(word in tag for word in query_lower.split()):
                    score += 2.0
            
            if score > 0:
                note_copy = note.copy()
                note_copy["similarity"] = score
                results.append(note_copy)
        
        # 按相似度排序
        results.sort(key=lambda x: x.get("similarity", 0), reverse=True)
        
        # 返回前k个结果
        return results[:top_k]


# 创建全局笔记实例
note = Notes()