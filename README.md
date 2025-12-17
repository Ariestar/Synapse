# KingStudy - 智能学习笔记系统

一个基于 Flask + RAG 的智能学习笔记管理系统，集成了 AI 对话、笔记管理、向量检索和 Git 同步等功能。

## ✨ 核心功能

### 🤖 AI 聊天室
- **多提供商支持**：集成 OpenAI、DeepSeek、Qwen、BigModel 等多个 AI 服务
- **流式对话**：实时流式响应，提供流畅的对话体验
- **智能笔记检索**：对话时自动检索相关笔记，基于笔记内容生成回答
- **可配置参数**：支持自定义温度、最大 token 数、角色设定等
- **工具函数调用**：支持 Function Calling，AI 可调用工具函数（如灵感合成、概念碰撞等）
- **助手配置**：可自定义助手名称和性格描述，个性化对话体验

### 📝 笔记管理
- **Markdown 支持**：完整的 Markdown 编辑和渲染
- **代码高亮**：使用 highlight.js 支持多种编程语言语法高亮
- **数学公式**：集成 MathJax，支持 LaTeX 数学公式渲染（整行公式居中、溢出滚动）
- **标签系统**：支持笔记标签分类和管理
- **目录组织**：支持多级目录结构，灵活组织笔记
- **富文本编辑**：集成 Toast UI Editor，提供可视化编辑体验
- **Alpine.js 驱动**：使用 Alpine.js 实现响应式列表筛选和状态管理
- **实时搜索**：支持标题、标签、路径、内容的多维度实时搜索

### 🔍 RAG 智能检索
- **向量检索**：基于 FAISS 的向量相似度搜索
- **关键词检索**：向量检索失败时自动回退到关键词搜索
- **引用来源**：检索结果包含引用来源和相似度评分
- **智能问答**：基于检索到的笔记内容生成回答，避免幻觉
- **批量索引**：支持批量索引重建，自动处理嵌入 API 限制

### 🔄 Git 同步
- **自动同步**：一键同步 Git 仓库中的笔记
- **增量更新**：智能检测变更，只更新修改的笔记
- **发布过滤**：支持按 `status: publish` 过滤笔记

### 💡 灵感合成
- **概念碰撞**：随机或反相似抽样两条笔记，通过 AI 生成创意灵感
- **多种模式**：支持随机模式和反相似模式，探索不同维度的创意

### ✨ 提示生成
- **维基采样**：随机获取维基百科词条作为灵感来源
- **LLM 提炼**：使用 AI 将维基内容提炼为可用的提示词
- **提示库管理**：支持存储和管理生成的提示词

### 🎨 现代化前端
- **响应式设计**：适配桌面和移动设备
- **Alpine.js**：轻量级响应式框架，无需复杂构建工具，实现 MVVM 数据绑定
- **设计令牌系统**：统一的 CSS 变量和工具类
- **组件化样式**：模块化的 CSS 架构，易于维护
- **实时交互**：防抖搜索、事件驱动更新，流畅的用户体验

## 🏗️ 技术架构

### 后端技术栈
- **Flask**：轻量级 Web 框架
- **FAISS**：高效的向量相似度搜索
- **LangChain**：RAG 流程编排
- **GitPython**：Git 仓库操作
- **PyYAML**：Markdown frontmatter 解析
- **OpenAI SDK**：统一的 AI API 接口
- **httpx**：异步 HTTP 客户端

### 前端技术栈
- **Alpine.js**：轻量级响应式框架（MVVM 数据绑定）
- **marked.js**：Markdown 解析
- **DOMPurify**：安全的 HTML 渲染
- **highlight.js**：代码语法高亮
- **MathJax**：数学公式渲染（支持 LaTeX 保护、居中显示、溢出滚动）

### AI 集成
- **OpenAI 兼容 API**：支持所有 OpenAI 兼容的服务
- **多提供商抽象**：统一的接口，轻松切换 AI 服务
- **嵌入模型**：支持 `embedding-2`、`embedding-3-pro` 等模型

## 🚀 快速开始

### 环境要求
- Python 3.8+
- Git
- 可访问的 AI API（OpenAI、DeepSeek、Qwen 或 BigModel）

### 安装步骤

1. **克隆项目**
```bash
git clone <repository-url>
cd flask_app
```

2. **安装依赖**
```bash
pip install -r requirements.txt
```

3. **配置环境变量**
```bash
# 必需：AI API Key
export LLM_API_KEY="your-api-key"

# 可选：指定提供商和模型
export DEFAULT_PROVIDER="bigmodel"
export BIGMODEL_MODEL="glm-4-flash"

# 嵌入配置（用于 RAG）
export EMBEDDING_API_KEY="your-embedding-key"
export EMBEDDING_MODEL="embedding-3-pro"

# 笔记路径配置
export NOTE_LOCAL_PATH="./app/notes"
```

4. **启动服务**
```bash
python main.py
```

5. **访问应用**
- 首页：http://localhost:5000/
- AI 聊天室：http://localhost:5000/aichat.html
- 笔记管理：http://localhost:5000/notes.html

### 初始化索引

首次使用需要构建向量索引：

```bash
# 使用 Postman 或 curl
curl -X POST http://localhost:5000/api/sync \
  -H "Content-Type: application/json"
```

## 📖 使用指南

### AI 聊天室

1. **配置 API**：点击设置按钮，配置 AI 提供商和 API Key
2. **开始对话**：在输入框输入问题，AI 会实时回复
3. **笔记检索**：启用"笔记检索"功能，AI 会基于笔记内容回答
4. **保存对话**：可以将重要的 Q&A 保存为笔记

### 笔记管理

1. **创建笔记**：点击顶部"新建笔记"按钮或侧边栏按钮
2. **编辑笔记**：在笔记详情页点击"编辑笔记"，支持标题和正文分离编辑
3. **智能检索**：使用"智能检索"功能搜索相关笔记
4. **标签管理**：为笔记添加标签，便于分类和检索
5. **实时搜索**：在笔记列表页输入关键词，实时筛选笔记
6. **Git 同步**：点击右上角同步按钮，一键同步远程仓库笔记
7. **删除笔记**：在笔记卡片上点击删除按钮（需确认）

### RAG 检索

1. **构建索引**：确保已运行 `/api/sync` 构建向量索引
2. **智能检索**：在笔记页面使用"智能检索"功能
3. **查看引用**：检索结果会显示引用来源和相似度

### 灵感合成

1. **概念碰撞**：在 AI 聊天室中启用工具函数，AI 会自动调用灵感合成功能
2. **手动触发**：调用 `/api/brainstorm` API，指定模式（random/anti-similar）
3. **查看结果**：AI 会基于两条随机笔记生成创意灵感

### 提示生成

1. **生成提示**：调用 `/api/prompts/generate` API，获取基于维基词条的提示词
2. **查看历史**：调用 `/api/prompts` API，查看已存储的提示词列表
3. **自定义语言**：支持指定语言（默认英文）生成提示词

## 🔧 配置说明

### AI 提供商配置

支持以下 AI 提供商：

- **OpenAI**：`gpt-3.5-turbo`、`gpt-4`、`gpt-4-turbo`、`gpt-4o`
- **DeepSeek**：`deepseek-chat`、`deepseek-coder`
- **Qwen**：`qwen-turbo`、`qwen-plus`、`qwen-max`
- **BigModel**：`glm-4-flash`、`glm-4`、`glm-3-turbo`

### 环境变量

| 变量名 | 说明 | 默认值 |
|--------|------|--------|
| `LLM_API_KEY` | 统一的 AI API Key | - |
| `DEFAULT_PROVIDER` | 默认 AI 提供商 | `bigmodel` |
| `EMBEDDING_API_KEY` | 嵌入模型 API Key | - |
| `EMBEDDING_MODEL` | 嵌入模型名称 | `embedding-3-pro` |
| `NOTE_LOCAL_PATH` | 笔记存储路径 | `./app/notes` |
| `NOTE_ONLY_PUBLISHED` | 前端仅显示已发布笔记（列表过滤），索引包含全部笔记 | `False` |

## 📁 项目结构

```
flask_app/
├── app/
│   ├── api/
│   │   ├── routes/          # API 路由
│   │   │   ├── chat.py      # AI 聊天
│   │   │   ├── rag.py       # RAG 检索
│   │   │   ├── search.py    # 语义搜索
│   │   │   ├── notes.py     # 笔记管理
│   │   │   ├── markdown.py  # Markdown API
│   │   │   ├── brainstorm.py # 灵感合成
│   │   │   ├── prompt.py    # 提示生成
│   │   │   ├── assistant.py # 助手配置
│   │   │   └── analyze.py   # 同步与分析
│   │   └── services/        # 业务逻辑
│   │       ├── rag.py       # RAG 服务
│   │       ├── indexer.py   # 向量索引
│   │       ├── ai_providers.py # AI 提供商抽象
│   │       ├── brainstorm.py  # 灵感合成服务
│   │       ├── prompt_engine.py # 提示生成引擎
│   │       ├── assistant_config.py # 助手配置
│   │       └── tools.py     # 工具函数注册
│   ├── config/
│   │   └── settings.py       # 配置管理
│   ├── templates/           # HTML 模板
│   │   ├── components/      # 组件模板
│   │   ├── aichat.html      # AI 聊天页
│   │   ├── notes.html       # 笔记列表页
│   │   └── notes_view.html  # 笔记详情/编辑页
│   ├── static/              # 静态资源
│   │   ├── css/             # 样式文件
│   │   ├── js/              # JavaScript
│   │   │   ├── scripts.js   # 主脚本
│   │   │   └── mathjax_helper.js # MathJax 辅助
│   │   └── img/             # 图片资源
│   ├── notes/               # 笔记存储
│   ├── data/                # 数据文件
│   │   ├── config.json      # 配置文件
│   │   └── prompts.json     # 提示词存储
│   └── utils/               # 工具函数
│       └── error_handler.py # 错误处理
├── faiss_index/             # 向量索引存储 (Faiss)
├── main.py                  # 应用入口
├── requirements.txt         # 依赖列表
└── LEARNING_LOG.md          # 开发日志
```

## 🎯 核心优势

### 1. **轻量级架构**
- 无需复杂构建工具，直接运行
- Alpine.js 替代 React/Vue，减少依赖
- 模块化设计，易于扩展

### 2. **智能检索**
- 向量检索 + 关键词检索双重保障
- 自动引用来源，避免幻觉
- 支持批量索引，处理大量笔记

### 3. **多 AI 支持**
- 统一的接口抽象，轻松切换提供商
- 支持流式响应，实时交互
- 灵活的配置系统

### 4. **优秀的用户体验**
- 响应式设计，适配各种设备
- 流畅的动画和过渡效果
- 直观的操作界面

### 5. **可维护性**
- 清晰的代码结构
- 完善的错误处理
- 详细的日志记录

### 6. **创新功能**
- 灵感合成：通过概念碰撞生成创意
- 提示生成：基于维基百科的提示词生成
- 工具函数调用：AI 可主动调用工具函数
- 助手配置：个性化 AI 助手角色

## 🔒 安全特性

- **XSS 防护**：使用 DOMPurify 安全渲染 HTML
- **路径验证**：文件操作前验证路径安全性
- **CORS 支持**：可配置的跨域策略
- **输入验证**：API 参数类型和格式验证
- **错误处理**：完善的异常捕获和错误响应

## 📝 开发日志

详细的开发记录和知识点总结请查看 [LEARNING_LOG.md](./LEARNING_LOG.md)

## 🤝 贡献指南

欢迎提交 Issue 和 Pull Request！

## 📄 许可证

详见 [LICENSE](./LICENSE) 文件

## 🙏 致谢

感谢以下开源项目：
- Flask
- FAISS
- Alpine.js
- marked.js
- highlight.js
- MathJax

---

**让学习更简单，让知识更智能** 🚀

