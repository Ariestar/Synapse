"""
向量索引与检索
"""

import logging
from pathlib import Path
from typing import Any, Dict, List, Optional
import uuid
import json

import faiss
import numpy as np
from langchain_text_splitters import MarkdownHeaderTextSplitter, RecursiveCharacterTextSplitter

from app.config.settings import settings
from app.api.services.markdown_io import parse_frontmatter
from app.api.services.ai_providers import get_embedding_callable


class NoteIndexer:
    """负责构建 FAISS 向量索引并执行搜索"""

    def __init__(
        self,
        persist_dir: str,
        embedding_provider: str,
        embedding_model: str,
        embedding_base_url: Optional[str] = None,
        embedding_api_key: Optional[str] = None,
        note_root: Optional[str] = None,
    ) -> None:
        self.logger = logging.getLogger(__name__)
        self.persist_dir = Path(persist_dir).resolve()
        self.persist_dir.mkdir(parents=True, exist_ok=True)
        self.index_file = self.persist_dir / "faiss.index"
        self.meta_file = self.persist_dir / "faiss_meta.json"
        self.note_root = Path(note_root or settings.NOTE_LOCAL_PATH).resolve()

        self.embedding_fn = get_embedding_callable(
            provider=embedding_provider,
            model=embedding_model,
            base_url=embedding_base_url,
            api_key=embedding_api_key,
        )
        self.entries: List[Dict[str, Any]] = []
        self.index: Optional[faiss.IndexFlatIP] = None
        self._load_index()

    def _load_index(self) -> None:
        """加载已保存的索引和元数据。"""
        if self.index_file.exists() and self.meta_file.exists():
            try:
                self.index = faiss.read_index(str(self.index_file))
                with self.meta_file.open("r", encoding="utf-8") as f:
                    self.entries = json.load(f)
            except Exception:
                self.index = None
                self.entries = []
        else:
            self.index = None
            self.entries = []

    def _save_index(self) -> None:
        """持久化索引与元数据。"""
        if self.index is None:
            return
        self.persist_dir.mkdir(parents=True, exist_ok=True)
        faiss.write_index(self.index, str(self.index_file))
        with self.meta_file.open("w", encoding="utf-8") as f:
            json.dump(self.entries, f, ensure_ascii=False, indent=2)

    @staticmethod
    def _normalize(vecs: List[List[float]]) -> np.ndarray:
        """对向量进行单位化以便使用 Inner Product 近似余弦相似度。"""
        arr = np.array(vecs, dtype="float32")
        norms = np.linalg.norm(arr, axis=1, keepdims=True) + 1e-12
        return arr / norms

    def _rebuild_faiss(self) -> None:
        """根据 entries 重建 FAISS 索引。"""
        if not self.entries:
            self.index = None
            return
        embeddings = [e["embedding"] for e in self.entries]
        emb_arr = self._normalize(embeddings)
        dim = emb_arr.shape[1]
        self.index = faiss.IndexFlatIP(dim)
        self.index.add(emb_arr)
        self._save_index()

    def _chunk_markdown(self, file_path: str, content: str) -> List[Dict[str, Any]]:
        """将 markdown 内容分块，并携带层级标题信息与元数据。"""
        headers_to_split_on = [
            ("#", "h1"),
            ("##", "h2"),
            ("###", "h3"),
            ("####", "h4"),
        ]
        splitter = MarkdownHeaderTextSplitter(headers_to_split_on=headers_to_split_on, strip_headers=False)
        md_docs = splitter.split_text(content)

        # 再次按长度分割，保证 chunk 不过长
        recursive_splitter = RecursiveCharacterTextSplitter(
            chunk_size=800,
            chunk_overlap=100,
            separators=["\n## ", "\n### ", "\n", " "],
        )

        frontmatter, _ = parse_frontmatter(content)
        raw_tags = frontmatter.get("tags", []) if isinstance(frontmatter, dict) else []
        tags = raw_tags if isinstance(raw_tags, list) else [raw_tags]

        abs_path = Path(file_path).resolve()
        try:
            rel_path = abs_path.relative_to(self.note_root).as_posix()
        except ValueError:
            rel_path = abs_path.name

        title = frontmatter.get("title") if isinstance(frontmatter, dict) else None
        display_title = str(title or abs_path.stem)

        chunks: List[Dict[str, Any]] = []
        for doc in md_docs:
            sub_docs = recursive_splitter.split_text(doc.page_content)
            for idx, sub in enumerate(sub_docs):
                meta = {
                    "file_path": file_path,
                    "rel_path": rel_path,
                    "title": display_title,
                    "chunk_id": str(uuid.uuid4()),
                    "order": idx,
                    "chunk_count": len(sub_docs),
                    "tags": tags,
                }
                chunks.append(
                    {
                        "text": sub,
                        "metadata": meta,
                    }
                )
        return chunks

    def rebuild_index(self, files: List[Dict[str, Any]]) -> int:
        """
        全量重建索引。
        :param files: [{"path": str, "content": str}]
        :return: 索引的 chunk 数
        """
        self.entries = []
        return self._upsert_chunks(files)

    def upsert_files(self, files: List[Dict[str, Any]]) -> int:
        """
        增量更新指定文件。
        """
        target_paths = {f.get("path") for f in files}
        self.entries = [e for e in self.entries if e.get("metadata", {}).get("file_path") not in target_paths]
        return self._upsert_chunks(files)

    def _upsert_chunks(self, files: List[Dict[str, Any]]) -> int:
        texts: List[str] = []
        metas: List[Dict[str, Any]] = []
        for f in files:
            path = f.get("path")
            content = f.get("content", "")
            chunks = self._chunk_markdown(path, content)
            for chunk in chunks:
                text = chunk.get("text", "")
                if not text or not text.strip():
                    continue
                texts.append(text)
                metas.append(chunk["metadata"])

        if not texts:
            self._rebuild_faiss()
            return 0

        try:
            batch_size = 64  # bigmodel input 数组上限 64
            total = 0
            for start in range(0, len(texts), batch_size):
                end = start + batch_size
                batch_texts = texts[start:end]
                batch_metas = metas[start:end]
                embeddings = self.embedding_fn(batch_texts)
                if embeddings is None:
                    raise ValueError("embedding_fn returned None")
                if len(embeddings) != len(batch_texts):
                    raise ValueError(f"embedding size mismatch: got {len(embeddings)} for {len(batch_texts)} inputs")
                for text, meta, emb in zip(batch_texts, batch_metas, embeddings):
                    self.entries.append(
                        {
                            "text": text,
                            "metadata": meta,
                            "embedding": emb,
                        }
                    )
                total += len(batch_texts)
            self._rebuild_faiss()
            return total
        except Exception as exc:  # noqa: BLE001
            self.logger.error("embedding/upsert failed: %s", exc, exc_info=True)
            return 0

    def search(self, query: str, top_k: int = 5) -> List[Dict[str, Any]]:
        if not query:
            return []
        if self.index is None or not self.entries:
            return []

        try:
            query_emb = self._normalize(self.embedding_fn([query]))
            scores, idxs = self.index.search(query_emb, top_k)
        except Exception:
            return []

        docs: List[Dict[str, Any]] = []
        for score, idx in zip(scores[0], idxs[0]):
            if idx < 0 or idx >= len(self.entries):
                continue
            entry = self.entries[idx]
            meta = entry.get("metadata", {})
            docs.append(
                {
                    "content": entry.get("text"),
                    "file_path": meta.get("file_path"),
                    "rel_path": meta.get("rel_path") or meta.get("file_path"),
                    "title": meta.get("title"),
                    "tags": meta.get("tags", []),
                    "order": meta.get("order"),
                    "chunk_count": meta.get("chunk_count"),
                    "score": float(score),
                }
            )
        return docs


# 全局索引器
note_indexer = NoteIndexer(
    persist_dir=settings.CHROMA_PERSIST_DIR,
    embedding_provider=settings.EMBEDDING_PROVIDER,
    embedding_model=settings.EMBEDDING_MODEL,
    embedding_base_url=settings.EMBEDDING_BASE_URL,
    embedding_api_key=settings.EMBEDDING_API_KEY,
    note_root=settings.NOTE_LOCAL_PATH,
)

