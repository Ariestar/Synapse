"""
AI聊天相关API路由
"""

from flask import Blueprint, request, jsonify, Response, stream_with_context
from app.config.settings import settings
from app.api.services.notes import note
from app.api.services.indexer import note_indexer
from app.api.services.ai_providers import get_chat_client
from app.api.services.tools import tool_registry
import json
import os

# 创建聊天API蓝图
chat_bp = Blueprint('chat', __name__)


def get_provider_name(provider_id: str) -> str:
    """根据提供商ID获取中文名称"""
    provider_names = {
        'openai': 'OpenAI',
        'deepseek': 'DeepSeek',
        'qwen': '通义千问',
        'bigmodel': '智谱AI'
    }
    return provider_names.get(provider_id, provider_id)


@chat_bp.route('/list_providers', methods=['GET'])
def list_providers():
    """
    列出所有可用的AI提供商
    URL: /list_providers
    方法: GET
    返回:
        [
            {
                "id": "bigmodel",
                "name": "智谱AI (默认)"
            },
            ...
        ]
    """
    providers = []
    for provider_id in settings.AI_PROVIDERS.keys():
        name = get_provider_name(provider_id)
        if provider_id == settings.DEFAULT_PROVIDER:
            name += " (默认)"
        providers.append({
            'id': provider_id,
            'name': name
        })
    
    return jsonify(providers), 200


@chat_bp.route('/list_models', methods=['GET'])
def list_models():
    """
    列出指定提供商的模型列表
    URL: /list_models?provider=bigmodel
    方法: GET
    查询参数:
        provider: 提供商ID（可选，默认为bigmodel）
    返回:
        [
            {
                "id": "glm-4-flash",
                "name": "GLM-4 Flash (默认)"
            },
            ...
        ]
    """
    provider = request.args.get('provider', settings.DEFAULT_PROVIDER)
    
    if provider not in settings.PROVIDER_MODELS:
        return jsonify({'error': f'不支持的提供商: {provider}'}), 400
    
    models = settings.PROVIDER_MODELS[provider]
    return jsonify(models), 200


def create_openai_client(provider: str, base_url: str = None, api_key: str = None):
    """兼容旧命名，实际调用统一的 provider 客户端"""
    return get_chat_client(provider=provider, base_url=base_url, api_key=api_key)


def format_messages_for_openai(messages: list, persona: str = None) -> list:
    """将前端消息格式转换为OpenAI格式"""
    formatted_messages = []
    
    # 如果有角色设定，添加系统消息
    if persona:
        formatted_messages.append({
            "role": "system",
            "content": persona
        })
    
    for msg in messages:
        role = msg.get('sender', 'user')
        text = msg.get('text', '')
        
        # 跳过空消息
        if not text:
            continue
        
        # 将sender映射到OpenAI的role
        if role == 'user':
            openai_role = 'user'
        elif role == 'bot' or role == 'assistant':
            openai_role = 'assistant'
        elif role == 'system':
            openai_role = 'system'
        else:
            openai_role = 'user'
        
        formatted_messages.append({
            "role": openai_role,
            "content": text
        })
    
    return formatted_messages


def get_relevant_notes(query: str, top_k: int = 3) -> list:
    """从笔记中搜索相关内容"""
    try:
        # 优先使用向量搜索
        vec_results = note_indexer.search(query=query, top_k=top_k)
        if vec_results:
            return vec_results
        # 退化为关键词搜索
        return note.search_notes(query=query, top_k=top_k)
    except Exception:
        return []


@chat_bp.route('/api/chat', methods=['POST'])
def rag_chat():
    """
    RAG 问答接口（非流式）
    body:
    {
        "question": "...",
        "top_k": 5,
        "provider": "...",
        "model": "...",
        "persona": "...",
        "base_url": "...",
        "api_key": "..."
    }
    """
    data = request.get_json() or {}
    question = data.get('question')
    if not question:
        return jsonify({'error': 'question 不能为空'}), 400

    top_k = data.get('top_k', 5)
    provider = data.get('provider', settings.DEFAULT_PROVIDER)
    model = data.get('model', settings.AI_PROVIDERS.get(provider, {}).get('model'))
    base_url = data.get('base_url')
    api_key = data.get('api_key')
    persona = data.get('persona')

    # 检索上下文
    contexts = get_relevant_notes(question, top_k=top_k)
    context_text = ""
    for idx, c in enumerate(contexts, 1):
        context_text += f"[{idx}] ({c.get('file_path')}) {c.get('content', '')}\n"

    system_prompt = persona or "你是一个知识库助手，请基于提供的笔记上下文回答。"
    if context_text:
        system_prompt += "\n以下是相关笔记片段，请务必引用其中信息作答，并在回答末尾给出引用编号。\n" + context_text

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": question},
    ]

    try:
        client = create_openai_client(provider, base_url, api_key)
        resp = client.chat.completions.create(
            model=model,
            messages=messages,
            temperature=data.get('temperature', 0.7),
            max_tokens=data.get('max_tokens', 1024)
        )
        answer = resp.choices[0].message.content
    except Exception as e:
        return jsonify({'error': str(e)}), 500

    citations = [c.get('file_path') for c in contexts if c.get('file_path')]
    return jsonify({'answer': answer, 'citations': citations, 'contexts': contexts}), 200


@chat_bp.route('/stream_generate', methods=['POST'])
def stream_generate():
    """
    流式生成AI回复 (支持 Function Calling)
    URL: /stream_generate
    方法: POST
    """
    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': '请求体不能为空'}), 400
        
        messages = data.get('messages', [])
        base_url = data.get('base_url')
        api_key = data.get('api_key')
        model = data.get('model')
        provider = data.get('provider', settings.DEFAULT_PROVIDER)
        persona = data.get('persona')
        
        # 处理工具
        enabled_tools = data.get('enabled_tools', [])
        # 兼容旧版 search_notes 参数
        if data.get('search_notes', False) and 'search_notes' not in enabled_tools:
            enabled_tools.append('search_notes')
            
        tools_schemas = tool_registry.get_schemas(enabled_tools)
        
        # 获取模型名称
        if not model:
            model = settings.AI_PROVIDERS.get(provider, {}).get('model', 'glm-4-flash')
        
        # 格式化消息
        formatted_messages = format_messages_for_openai(messages, persona)
        
        # 创建OpenAI客户端
        client = create_openai_client(provider, base_url, api_key)
        
        def generate():
            current_messages = formatted_messages
            
            # 最大迭代次数，防止无限循环
            max_iterations = 5
            iteration = 0
            
            while iteration < max_iterations:
                iteration += 1
                
                try:
                    stream = client.chat.completions.create(
                        model=model,
                        messages=current_messages,
                        stream=True,
                        temperature=data.get('temperature', 0.7),
                        max_tokens=data.get('max_tokens', 2048),
                        tools=tools_schemas if tools_schemas else None
                    )
                    
                    tool_calls_buffer = []
                    
                    for chunk in stream:
                        if not chunk.choices:
                            continue
                            
                        delta = chunk.choices[0].delta
                        
                        # 处理内容流式输出
                        if delta.content:
                            response_data = {
                                "text": delta.content,
                                "reason": False
                            }
                            yield f"data: {json.dumps(response_data, ensure_ascii=False)}\n\n"
                        
                        # 处理工具调用流式数据
                        if delta.tool_calls:
                            for tc_chunk in delta.tool_calls:
                                if len(tool_calls_buffer) <= tc_chunk.index:
                                    tool_calls_buffer.append({
                                        "id": "",
                                        "function": {"name": "", "arguments": ""},
                                        "type": "function"
                                    })
                                
                                tc = tool_calls_buffer[tc_chunk.index]
                                if tc_chunk.id:
                                    tc["id"] += tc_chunk.id
                                if tc_chunk.function.name:
                                    tc["function"]["name"] += tc_chunk.function.name
                                if tc_chunk.function.arguments:
                                    tc["function"]["arguments"] += tc_chunk.function.arguments

                    # 如果没有工具调用，说明对话结束
                    if not tool_calls_buffer:
                        break
                        
                    # 执行工具调用
                    current_messages.append({
                        "role": "assistant",
                        "tool_calls": tool_calls_buffer
                    })
                    
                    for tc in tool_calls_buffer:
                        func_name = tc["function"]["name"]
                        func_args_str = tc["function"]["arguments"]
                        
                        # 发送工具执行提示
                        tool_tips = {
                            "brainstorm": "\n\n*(正在进行概念碰撞，抽取笔记并生成创意中...)*\n\n",
                            "search_notes": "\n\n*(正在检索本地笔记...)*\n\n",
                            "search_internet": "\n\n*(正在联网搜索...)*\n\n"
                        }
                        if func_name in tool_tips:
                            yield f"data: {json.dumps({'text': tool_tips[func_name], 'reason': False}, ensure_ascii=False)}\n\n"
                        
                        try:
                            func_args = json.loads(func_args_str)
                            
                            # 注入上下文回调，用于 side-channel 数据传输
                            artifacts = []
                            def collect_artifact(a):
                                artifacts.append(a)
                                
                            context = {'on_artifact': collect_artifact}
                            result = tool_registry.execute(func_name, context=context, **func_args)
                            
                            # 发送收集到的 artifacts
                            for art in artifacts:
                                event = {
                                    "text": "",
                                    "reason": False,
                                    "artifact": art
                                }
                                yield f"data: {json.dumps(event, ensure_ascii=False)}\n\n"
                                
                        except Exception as e:
                            result = f"Error parsing arguments: {str(e)}"
                            
                        # 添加工具执行结果到上下文
                        current_messages.append({
                            "role": "tool",
                            "tool_call_id": tc["id"],
                            "content": str(result)
                        })
                        
                except Exception as e:
                    error_data = {"text": f"Error: {str(e)}", "reason": False}
                    yield f"data: {json.dumps(error_data, ensure_ascii=False)}\n\n"
                    break
        
        return Response(
            stream_with_context(generate()),
            mimetype='text/event-stream',
            headers={
                'Cache-Control': 'no-cache',
                'X-Accel-Buffering': 'no'
            }
        )
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500

