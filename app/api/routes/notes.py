"""
笔记相关API路由
"""

from flask import Blueprint, request, jsonify
from app.api.services.notes import note

# 创建笔记API蓝图
notes_bp = Blueprint('notes', __name__, url_prefix='/api')


@notes_bp.route('/note', methods=['POST'])
def add_note():
    """
    添加笔记
    URL: /api/note
    方法: POST
    请求体:
        {
            "content": "笔记内容",
            "title": "笔记标题" (可选),
            "tags": ["标签1", "标签2"] (可选),
            "source": "来源" (可选)
        }
    返回:
        {
            "id": "笔记ID"
        }
    """
    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': '请求体不能为空'}), 400
        
        content = data.get('content')
        if not content:
            return jsonify({'error': '笔记内容不能为空'}), 400
        
        title = data.get('title')
        tags = data.get('tags', [])
        source = data.get('source')
        
        note_id = note.add_note(
            content=content,
            title=title,
            tags=tags,
            source=source
        )
        
        return jsonify({'id': note_id}), 201
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@notes_bp.route('/notes/<note_id>', methods=['GET'])
def get_note(note_id):
    """
    根据ID获取笔记
    URL: /api/notes/<note_id>
    方法: GET
    返回:
        {
            "id": "笔记ID",
            "title": "笔记标题",
            "content": "笔记内容",
            "tags": ["标签1", "标签2"],
            "source": "来源",
            "created_at": "创建时间",
            "updated_at": "更新时间"
        }
    """
    try:
        note_data = note.get_note(note_id)
        if not note_data:
            return jsonify({'error': '笔记不存在'}), 404
        
        return jsonify(note_data), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@notes_bp.route('/notes', methods=['GET'])
def list_notes():
    """
    列出笔记
    URL: /api/notes
    方法: GET
    查询参数:
        limit: 限制返回数量(可选，默认为50)
        offset: 偏移量(可选，默认为0)
    返回:
        {
            "result": [
                {
                    "id": "ID",
                    "title": "笔记标题",
                    "content": "笔记内容",
                    "tags": ["标签1", "标签2"],
                    "source": "来源",
                    "created_at": "创建时间",
                    "updated_at": "更新时间"
                }
            ]
        }
    """
    try:
        limit = request.args.get('limit', 50, type=int)
        offset = request.args.get('offset', 0, type=int)
        
        # 限制limit的最大值
        limit = min(limit, 100)
        
        notes_list = note.list_notes(limit=limit, offset=offset)
        return jsonify({'result': notes_list}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@notes_bp.route('/note/<note_id>', methods=['DELETE'])
def delete_note(note_id):
    """
    删除笔记
    URL: /api/note/<note_id>
    方法: DELETE
    返回:
        {
            "message": "删除成功"
        }
    """
    try:
        success = note.delete_note(note_id)
        if not success:
            return jsonify({'error': '笔记不存在'}), 404
        
        return jsonify({'message': '删除成功'}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@notes_bp.route('/note/<note_id>', methods=['PUT'])
def update_note(note_id):
    """
    更新笔记
    URL: /api/note/<note_id>
    方法: PUT
    请求体:
        {
            "content": "新内容(可选)",
            "title": "新标题(可选)",
            "tags": ["新标签1", "新标签2"](可选),
            "source": "新来源(可选)"
        }
    返回:
        {
            "message": "更新成功"
        }
    """
    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': '请求体不能为空'}), 400
        
        content = data.get('content')
        title = data.get('title')
        tags = data.get('tags')
        source = data.get('source')
        
        success = note.update_note(
            note_id=note_id,
            content=content,
            title=title,
            tags=tags,
            source=source
        )
        
        if not success:
            return jsonify({'error': '笔记不存在'}), 404
        
        return jsonify({'message': '更新成功'}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@notes_bp.route('/note/search', methods=['POST'])
def search_notes():
    """
    搜索笔记
    URL: /api/note/search
    方法: POST
    请求体:
        {
            "query": "搜索查询",
            "top_k": 5 (可选，默认为5)
        }
    返回:
        [
            {
                "id": "笔记ID",
                "title": "笔记标题",
                "content": "笔记内容",
                "tags": ["标签1", "标签2"],
                "similarity": 相似度分数
            }
        ]
    """
    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': '请求体不能为空'}), 400
        
        query = data.get('query')
        if not query:
            return jsonify({'error': '搜索查询不能为空'}), 400
        
        top_k = data.get('top_k', 5)
        
        results = note.search_notes(query=query, top_k=top_k)
        return jsonify(results), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500