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
            repo = Repo(self.local_path)
            # 关键修复：确保找到的 git 仓库根目录与 local_path 一致
            # 防止 local_path 仅仅是主项目的一个子目录时，误操作了主项目仓库
            if Path(repo.working_dir).resolve() != self.local_path.resolve():
                print(f"GitSync Warning: Found repo at {repo.working_dir} but expected at {self.local_path}. Treating as no repo.")
                return None
            return repo
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
            print(f"GitSync: Cloning from {self.repo_url} to {self.local_path}...")
            repo = Repo.clone_from(self.repo_url, self.local_path, branch=self.branch)
            return repo
        except Exception as e:
            print(f"GitSync Clone Error: {e}")
            return None

    def pull(self) -> bool:
        """执行 pull，失败返回 False"""
        try:
            repo = self.ensure_repo()
            if not repo:
                print(f"GitSync Error: Repo not found or invalid. URL: {self.repo_url}, Path: {self.local_path}")
                return False
            
            # 记录当前 HEAD
            old_commit = repo.head.commit.hexsha
            
            repo.git.checkout(self.branch)
            repo.remote().pull()
            
            new_commit = repo.head.commit.hexsha
            if old_commit != new_commit:
                print(f"GitSync: Pulled changes from {old_commit[:7]} to {new_commit[:7]}")
            else:
                print("GitSync: Already up to date.")
                
            return True
        except Exception as e:
            print(f"GitSync Exception during pull: {e}")
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


