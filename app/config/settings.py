"""
配置文件
"""

import os
from typing import Dict


class Settings:
    """应用配置类"""

    def __init__(self) -> None:
        """
        初始化配置并处理路径兼容性。
        """
        # 统一 Key（LLM_API_KEY），若未设置则回退各自的专用变量
        self.UNIFIED_API_KEY = os.getenv('LLM_API_KEY')

        self.AI_PROVIDERS = {
            'openai': {
                'base_url': os.getenv('OPENAI_BASE_URL', 'https://api.openai.com'),
                'api_key': os.getenv('OPENAI_API_KEY') or self.UNIFIED_API_KEY,
                'model': os.getenv('OPENAI_MODEL', 'gpt-3.5-turbo')
            },
            'deepseek': {
                'base_url': os.getenv('DEEPSEEK_BASE_URL', 'https://api.deepseek.com'),
                'api_key': os.getenv('DEEPSEEK_API_KEY') or self.UNIFIED_API_KEY,
                'model': os.getenv('DEEPSEEK_MODEL', 'deepseek-chat')
            },
            'qwen': {
                'base_url': os.getenv('QWEN_BASE_URL', 'https://dashscope.aliyuncs.com'),
                'api_key': os.getenv('QWEN_API_KEY') or self.UNIFIED_API_KEY,
                'model': os.getenv('QWEN_MODEL', 'qwen-turbo')
            },
            'bigmodel': {
                'base_url': os.getenv('BIGMODEL_BASE_URL', 'https://open.bigmodel.cn/api/paas/v4'),
                'api_key': os.getenv('BIGMODEL_API_KEY') or self.UNIFIED_API_KEY,
                'model': os.getenv('BIGMODEL_MODEL', 'glm-4-flash')
            }
        }

        # 定义每个提供商的模型列表
        self.PROVIDER_MODELS = {
            'openai': [
                {'id': 'gpt-3.5-turbo', 'name': 'GPT-3.5 Turbo'},
                {'id': 'gpt-4', 'name': 'GPT-4'},
                {'id': 'gpt-4-turbo', 'name': 'GPT-4 Turbo'},
                {'id': 'gpt-4o', 'name': 'GPT-4o'}
            ],
            'deepseek': [
                {'id': 'deepseek-chat', 'name': 'DeepSeek Chat'},
                {'id': 'deepseek-coder', 'name': 'DeepSeek Coder'}
            ],
            'bigmodel': [
                {'id': 'glm-4-flash', 'name': 'GLM-4 Flash (默认)'},
                {'id': 'glm-4-air', 'name': 'GLM-4 Air'},
                {'id': 'glm-4-airx', 'name': 'GLM-4 AirX'},
                {'id': 'glm-4-long', 'name': 'GLM-4 Long'}
            ],
            'qwen': [
                {'id': 'qwen-turbo', 'name': 'Qwen Turbo'},
                {'id': 'qwen-plus', 'name': 'Qwen Plus'},
                {'id': 'qwen-max', 'name': 'Qwen Max'},
                {'id': 'qwen-long', 'name': 'Qwen Long'}
            ]
        }

        self.DEFAULT_PROVIDER = os.getenv('DEFAULT_AI_PROVIDER', 'bigmodel')
        # 嵌入模型配置（可与聊天 provider 不同）
        self.EMBEDDING_PROVIDER = os.getenv('EMBEDDING_PROVIDER', 'bigmodel')
        self.EMBEDDING_MODEL = os.getenv('EMBEDDING_MODEL', 'embedding-3-pro')  # 使用 embedding-3-pro 模型
        self.EMBEDDING_BASE_URL = os.getenv('EMBEDDING_BASE_URL', os.getenv('BIGMODEL_BASE_URL', 'https://open.bigmodel.cn/api/paas/v4'))
        self.EMBEDDING_API_KEY = os.getenv('EMBEDDING_API_KEY') or self.UNIFIED_API_KEY
        # 笔记仓库与索引配置
        self.NOTE_REPO_URL = os.getenv('NOTE_REPO_URL', '')
        self.NOTE_REPO_BRANCH = os.getenv('NOTE_REPO_BRANCH', 'main')
        # 默认将仓库克隆到项目根目录下的 notes
        project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        self.NOTE_LOCAL_PATH = os.getenv('NOTE_LOCAL_PATH', os.path.join(project_root, 'notes'))
        self.CHROMA_PERSIST_DIR = self._select_chroma_dir(project_root)
        self.NOTE_FILE_GLOB = os.getenv('NOTE_FILE_GLOB', '**/*.md')
        # 仅索引 frontmatter 中 status: published 的笔记（默认关闭以索引全部）
        self.NOTE_ONLY_PUBLISHED = os.getenv('NOTE_ONLY_PUBLISHED', 'false').lower() == 'true'

        self.SERVER_PORT = int(os.getenv('SERVER_PORT', 8008))
        self.SERVER_HOST = os.getenv('SERVER_HOST', '0.0.0.0')
        # Wikipedia 调用所需的 User-Agent，避免 403
        self.WIKI_USER_AGENT = os.getenv('WIKI_USER_AGENT', 'flask-app-prompt/1.0 (contact: dev@example.com)')

    def _select_chroma_dir(self, project_root: str) -> str:
        """
        选择 Chroma 持久化目录，若默认路径包含非 ASCII 字符且在 Windows 上，
        则回退到用户本地应用数据目录以避免 faiss 对非 ASCII 路径的兼容性问题。

        :param project_root: 项目根路径
        :return: 适用于当前平台的持久化目录
        """
        default_dir = os.getenv('CHROMA_PERSIST_DIR', os.path.join(project_root, '..', 'chroma_db'))
        if os.name == 'nt':
            try:
                default_dir.encode('ascii')
            except UnicodeEncodeError:
                fallback_base = os.getenv('LOCALAPPDATA') or os.path.expanduser('~')
                return os.path.join(fallback_base, 'flask_app_chroma_db')
        return default_dir


# 创建全局配置实例

settings = Settings()