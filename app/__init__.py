"""
主应用文件
"""

from flask import Flask
from .api.routes import main_bp
from .api.routes.notes import notes_bp
from .api.routes.chat import chat_bp
from .api.routes.search import search_bp
from .api.routes.analyze import analyze_bp
from .api.routes.markdown import markdown_bp
from .api.routes.brainstorm import brainstorm_bp
from .api.routes.prompt import prompt_bp
from .api.routes.rag import rag_bp
from flask_cors import CORS
import os


# 允许所有来源的跨域请求（开发环境）


def create_app() -> Flask:
    """创建并返回 Flask 应用实例。"""
    # 获取项目根目录
    project_root = os.path.dirname(os.path.abspath(__file__))
    template_dir = os.path.join(project_root, 'templates')
    static_dir = os.path.join(project_root, 'static')

    app = Flask(__name__,
                template_folder=template_dir,
                static_folder=static_dir)
    CORS(app)
    # 注册主路由
    app.register_blueprint(main_bp)
    # 注册笔记API路由
    app.register_blueprint(notes_bp)
    # 注册聊天API路由
    app.register_blueprint(chat_bp)
    # 注册语义搜索
    app.register_blueprint(search_bp)
    # 注册 RAG 检索问答
    app.register_blueprint(rag_bp)
    # 注册灵感合成
    app.register_blueprint(brainstorm_bp)
    # 注册提示生成（维基采样 + LLM 提炼）
    app.register_blueprint(prompt_bp)
    # 注册同步与分析
    app.register_blueprint(analyze_bp)
    # 注册 Markdown 浏览
    app.register_blueprint(markdown_bp)

    # 添加全局错误处理器
    app.register_error_handler(500, lambda e: ({'error': str(e)}, 500))

    return app


if __name__ == '__main__':
    app = create_app()
    app.run(debug=True, host='0.0.0.0', port=8000)