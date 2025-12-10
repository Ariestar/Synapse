"""
AI聊天相关API路由
"""

from flask import Blueprint, request, jsonify, Response, stream_with_context
from app.config.settings import settings
from app.api.services.notes import note
from app.api.services.indexer import note_indexer
from app.api.services.ai_providers import get_chat_client
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
    流式生成AI回复
    URL: /stream_generate
    方法: POST
    请求体:
        {
            "messages": [...],
            "base_url": "...",
            "api_key": "...",
            "model": "...",
            "provider": "...",
            "temperature": 0.7,
            "max_tokens": 2048,
            "persona": "...",
            "search_notes": true,
            "newMessage": "..."
        }
    返回: Server-Sent Events流
        data: {"text": "...", "reason": null}
        data: {"text": "...", "reason": true}
        ...
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
        search_notes_enabled = data.get('search_notes', False)
        new_message = data.get('newMessage', '')
        
        # 如果启用了笔记搜索，从笔记中检索相关信息
        context_messages = messages.copy()
        relevant_notes = []
        
        # 优先使用前端传递的笔记（如果已检索）
        related_notes_from_frontend = data.get('related_notes', [])
        if related_notes_from_frontend:
            relevant_notes = related_notes_from_frontend
        elif search_notes_enabled and new_message:
            # 如果前端没有传递，后端自己检索
            relevant_notes = get_relevant_notes(new_message, top_k=6)
        
        if relevant_notes:
            # 构建更详细的笔记上下文
            note_context = "\n\n以下是相关笔记内容，请基于这些信息回答用户问题，并在回答中适当引用：\n\n"
            for idx, note_item in enumerate(relevant_notes, 1):
                title = note_item.get('title', '无标题')
                content = note_item.get('content', '')
                file_path = note_item.get('file_path') or note_item.get('rel_path', '')
                note_context += f"[{idx}] {title} ({file_path})\n{content}\n\n"
            
            note_context += "请基于以上笔记内容回答用户问题，尽量使用笔记中的信息，并在回答末尾注明引用的笔记编号。"
            
            # 将笔记上下文添加到系统消息或persona
            if persona:
                persona += "\n\n" + note_context
            else:
                # 如果没有persona，创建一个系统消息
                context_messages.insert(0, {
                    "sender": "system",
                    "text": "你是一个知识库助手，请基于提供的笔记内容回答问题。" + note_context
                })
        
        # 获取模型名称，如果没有提供则使用默认值
        if not model:
            model = settings.AI_PROVIDERS.get(provider, {}).get('model', 'glm-4-flash')
        
        # 格式化消息
        formatted_messages = format_messages_for_openai(context_messages, persona)
        
        # 创建OpenAI客户端
        client = create_openai_client(provider, base_url, api_key)
        
        # 生成流式响应
        def generate():
            try:
                stream = client.chat.completions.create(
                    model=model,
                    messages=formatted_messages,
                    stream=True,
                    temperature=data.get('temperature', 0.7),
                    max_tokens=data.get('max_tokens', 2048)
                )
                
                for chunk in stream:
                    if chunk.choices:
                        choice = chunk.choices[0]
                        delta = choice.delta
                        
                        # 处理内容
                        if delta.content:
                            # 检查是否是reasoning字段（某些模型可能支持）
                            is_reason = getattr(delta, 'reason', False) if hasattr(delta, 'reason') else False
                            
                            response_data = {
                                "text": delta.content,
                                "reason": is_reason
                            }
                            
                            # 以SSE格式发送数据
                            yield f"data: {json.dumps(response_data, ensure_ascii=False)}\n\n"
            
            except Exception as e:
                error_data = {
                    "text": f"错误: {str(e)}",
                    "reason": False
                }
                yield f"data: {json.dumps(error_data, ensure_ascii=False)}\n\n"
        
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

