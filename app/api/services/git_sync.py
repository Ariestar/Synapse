"""
Git 仓库同步工具
"""

import os
from pathlib import Path
from typing import Optional

from git import Repo, GitCommandError, InvalidGitRepositoryError

from app.config.settings import settings


class GitSync:
    """负责 clone/pull/commit 的简单包装"""

    def __init__(self, repo_url: str, local_path: str, branch: str = "main"):
        self.repo_url = repo_url.strip()
        self.local_path = Path(local_path).resolve()
        self.branch = branch

        if not self.local_path.exists():
            self.local_path.mkdir(parents=True, exist_ok=True)

    def _open_repo(self) -> Optional[Repo]:
        """打开已有仓库，若不是 git 仓库则返回 None"""
        try:
            return Repo(self.local_path)
        except (InvalidGitRepositoryError, GitCommandError, OSError):
            return None

    def ensure_repo(self) -> Optional[Repo]:
        """
        如果缺失则 clone，存在则返回 Repo
        """
        if not self.repo_url:
            return None

        repo = self._open_repo()
        if repo:
            return repo

        # 空目录或非 git 目录，执行 clone
        try:
            repo = Repo.clone_from(self.repo_url, self.local_path, branch=self.branch)
            return repo
        except Exception:
            return None

    def pull(self) -> bool:
        """执行 pull，失败返回 False"""
        repo = self.ensure_repo()
        if not repo:
            return False
        try:
            repo.git.checkout(self.branch)
            repo.remote().pull()
            return True
        except Exception:
            return False

    def commit_and_push(self, message: str = "auto sync") -> bool:
        """
        将变更添加并推送
        """
        repo = self.ensure_repo()
        if not repo:
            return False
        try:
            repo.git.add(all=True)
            # 无变更时跳过
            if not repo.index.diff("HEAD") and not repo.untracked_files:
                return True
            repo.index.commit(message)
            repo.remote().push()
            return True
        except Exception:
            return False


# 全局实例，供路由调用
git_sync = GitSync(
    repo_url=settings.NOTE_REPO_URL,
    local_path=settings.NOTE_LOCAL_PATH,
    branch=settings.NOTE_REPO_BRANCH,
)


