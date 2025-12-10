#!/usr/bin/env python
"""
启动脚本
"""

import sys
import os

# 添加项目根目录到Python路径
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_root)

from app import create_app
from app.config.settings import settings

if __name__ == '__main__':
    app = create_app()
    app.run(debug=True, host=settings.SERVER_HOST, port=settings.SERVER_PORT)