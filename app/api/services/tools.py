import json
from typing import List, Dict, Any, Callable, Optional, Union
from app.api.services.notes import note
from app.api.services.indexer import note_indexer
from app.api.services.brainstorm import brainstorm_idea

class ToolRegistry:
    def __init__(self):
        self._tools: Dict[str, Callable] = {}
        self._schemas: Dict[str, Dict[str, Any]] = {}

    def register(self, name: str, func: Callable, schema: Dict[str, Any]):
        """注册工具"""
        self._tools[name] = func
        self._schemas[name] = schema

    def get_tool_func(self, name: str) -> Optional[Callable]:
        """获取工具函数"""
        return self._tools.get(name)

    def get_schemas(self, enabled_tools: Optional[List[str]] = None) -> List[Dict[str, Any]]:
        """获取工具定义的 Schema 列表"""
        if not enabled_tools:
            return []
        
        schemas = []
        for name in enabled_tools:
            if name in self._schemas:
                schemas.append(self._schemas[name])
        return schemas

    def execute(self, name: str, context: Optional[Dict[str, Any]] = None, **kwargs) -> Any:
        """
        执行工具
        :param name: 工具名称
        :param context: 上下文数据（可选，用于回调或 side-channel）
        :param kwargs: 工具参数
        """
        func = self.get_tool_func(name)
        if not func:
            return f"Error: Tool '{name}' not found."
        try:
            # 检查函数是否接受 context 参数
            import inspect
            sig = inspect.signature(func)
            if 'context' in sig.parameters:
                kwargs['context'] = context
                
            return func(**kwargs)
        except Exception as e:
            return f"Error executing tool '{name}': {str(e)}"

# --- 工具函数实现 ---

def search_notes(query: str, top_k: int = 5, context: Optional[Dict[str, Any]] = None) -> str:
    """
    从本地笔记中搜索相关内容。
    """
    try:
        # 优先使用向量搜索
        vec_results = note_indexer.search(query=query, top_k=top_k)
        results = vec_results if vec_results else note.search_notes(query=query, top_k=top_k)
        
        if not results:
            return "未找到相关笔记。"
        
        # 如果存在上下文回调，将结构化数据传出去
        if context and 'on_artifact' in context:
            context['on_artifact']({
                'type': 'citations',
                'data': results
            })
        
        # 格式化结果（给 LLM 看的文本）
        response = f"找到 {len(results)} 条相关笔记：\n\n"
        for idx, item in enumerate(results, 1):
            title = item.get('title', '无标题')
            path = item.get('rel_path') or item.get('file_path') or '未知路径'
            content = item.get('content', '')[:500]  # 截取前500字符
            response += f"[{idx}] {title} ({path})\n{content}\n\n"
            
        return response
    except Exception as e:
        return f"搜索笔记出错: {str(e)}"

def brainstorm(mode: str = "random", context: Optional[Dict[str, Any]] = None) -> str:
    """
    执行概念碰撞，随机抽取两条笔记并生成创意连接。
    """
    try:
        # 调用 brainstorm service
        # 注意：这里我们无法直接获取 LLM 配置，因此 brainstorm_idea 会使用默认配置
        # 如果需要更复杂的控制，需要将 LLM 配置也通过 kwargs 传入
        result = brainstorm_idea(mode=mode)
        
        source_notes = result.get("source_notes", [])
        idea = result.get("idea", {})
        
        # 如果有 artifact 回调，可以将源笔记传给前端展示
        if context and 'on_artifact' in context:
            # 构造 artifact 数据
             context['on_artifact']({
                'type': 'citations',
                'data': [
                    {
                        'title': n.get('title'), 
                        'rel_path': n.get('rel_path'), 
                        'content': f"（概念碰撞源笔记）"
                    } for n in source_notes
                ]
            })

        connection = idea.get("connection", "无连接")
        title = idea.get("title", "无标题")
        outline = idea.get("outline", [])
        
        response = f"**概念碰撞结果**\n\n"
        response += f"**选题**：{title}\n"
        response += f"**连接点**：{connection}\n\n"
        response += "**大纲**：\n"
        for point in outline:
            response += f"- {point}\n"
            
        return response
    except Exception as e:
        return f"概念碰撞执行出错: {str(e)}"

def search_internet(query: str) -> str:
    """
    联网搜索（模拟）。
    """
    # 实际项目中可接入 Google SERP, Bing API 或 DuckDuckGo
    return f"[模拟搜索结果] 关于 '{query}' 的网络搜索结果：\n1. {query} 的维基百科页面...\n2. 最新关于 {query} 的新闻报道..."

# --- 工具 Schema 定义 ---

search_notes_schema = {
    "type": "function",
    "function": {
        "name": "search_notes",
        "description": "查询用户的本地笔记知识库。当用户询问关于'笔记'、'知识库'内容或需要查找特定信息时使用。",
        "parameters": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "搜索关键词或问题"
                },
                "top_k": {
                    "type": "integer",
                    "description": "返回结果数量",
                    "default": 5
                }
            },
            "required": ["query"]
        }
    }
}

brainstorm_schema = {
    "type": "function",
    "function": {
        "name": "brainstorm",
        "description": "执行概念碰撞（Brainstorming）。随机抽取两条笔记发现潜在联系并生成创意。当用户想要寻找灵感、进行头脑风暴或探索笔记间的隐性关联时使用。",
        "parameters": {
            "type": "object",
            "properties": {
                "mode": {
                    "type": "string",
                    "description": "模式：'random' (完全随机) 或 'mmr' (寻找差异最大)",
                    "enum": ["random", "mmr"],
                    "default": "random"
                }
            },
            "required": []
        }
    }
}

search_internet_schema = {
    "type": "function",
    "function": {
        "name": "search_internet",
        "description": "联网搜索信息。当用户询问实时新闻、天气或笔记中不存在的外部知识时使用。",
        "parameters": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "搜索关键词"
                }
            },
            "required": ["query"]
        }
    }
}

# --- 全局注册 ---

tool_registry = ToolRegistry()
tool_registry.register("search_notes", search_notes, search_notes_schema)
tool_registry.register("brainstorm", brainstorm, brainstorm_schema)
tool_registry.register("search_internet", search_internet, search_internet_schema)
