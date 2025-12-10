"""
配置文件
"""

import os
from typing import Dict


class Settings:
    """应用配置类"""

    def __init__(self):
        # TODO 需要填充sk
        self.AI_PROVIDERS = {
            'openai': {
                'base_url': os.getenv('OPENAI_BASE_URL', 'https://api.openai.com'),
                'api_key': os.getenv('OPENAI_API_KEY'),
                'model': os.getenv('OPENAI_MODEL', 'gpt-3.5-turbo')
            },
            'deepseek': {
                'base_url': os.getenv('DEEPSEEK_BASE_URL', 'https://api.deepseek.com'),
                # 'api_key': os.getenv('DEEPSEEK_API_KEY', 'sk-35a468ee5a204790a1dab478e07fae7a'),
                'api_key': os.getenv('DEEPSEEK_API_KEY'),

                'model': os.getenv('DEEPSEEK_MODEL', 'deepseek-chat')
            },
            'qwen': {
                'base_url': os.getenv('QWEN_BASE_URL', 'https://dashscope.aliyuncs.com'),
                'api_key': os.getenv('QWEN_API_KEY'),
                'model': os.getenv('QWEN_MODEL', 'qwen-turbo')
            },
            'bigmodel': {
                'base_url': os.getenv('BIGMODEL_BASE_URL', 'https://open.bigmodel.cn/api/paas/v4'),
                'api_key': os.getenv('BIGMODEL_API_KEY',''),
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

        self.SERVER_PORT = int(os.getenv('SERVER_PORT', 8008))
        self.SERVER_HOST = os.getenv('SERVER_HOST', '0.0.0.0')


# 创建全局配置实例

settings = Settings()