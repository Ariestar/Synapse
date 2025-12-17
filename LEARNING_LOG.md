## [2025-12-10] Flask Markdown 前端渲染
- **Markdown 渲染**: 使用 marked + DOMPurify + highlight.js 在前端安全渲染笔记正文。
- **富文本编辑/复制**: 引入 Toast UI Editor 作为本地富文本查看/编辑器，并提供复制 Markdown 按钮。
- **接口消费**: 前端切换到 `/api/md/files` 与 `/api/md/file` 读取 Git 笔记数据，兼容 `status: publish` 过滤。
## [2025-12-10] 笔记新页面
- **列表+正文布局**: 新增 `notes_view.html`，左侧列表、右侧正文，调用 `/api/md/files`、`/api/md/file`。
- **Markdown 渲染**: 前端用 marked+DOMPurify+highlight.js 渲染正文，支持代码高亮。
- **操作工具**: 提供搜索、刷新、复制 Markdown；tags 字段兼容数组/字符串。
## [2025-12-10] MathJax 支持
- **LaTeX 渲染**: 为 `notes_view.html` 增加 MathJax 配置，支持 `$...$` 与 `$$...$$` 公式显示。
## [2025-12-10] MathJax 配置强化
- **配置**: 启用 processEscapes/processEnvironments，inline/display delimiters，marked 关闭 mangle/headerIds 并保留换行，提升矩阵等多行公式的渲染稳定性。
## [2025-12-10] 日志增加 Markdown API 调试信息
- **路由日志**: `/api/md/files`、`/api/md/file` 输出根路径、glob、发布过滤等信息，便于排查文件读取与过滤问题。
## [2025-12-10] 阻止 marked 破坏 $$ 块的换行
- **实现**: 在 `mathjax_helper.js` 先提取 `$$...$$` 为占位符，待 marked 渲染后再回填，避免 `\\` 变 `<br>` 导致矩阵折行失效。
## [2025-12-10] Chat 接口前端对齐
- **API 调用**: 前端改用相对路径 `/stream_generate`、`/list_providers`、`/list_models`，避免端口不一致导致请求失败；保留 `window.SERVER_PORT` 作为回退但优先同源。

## [2025-12-10] Flask RAG
- **RAG API**: `POST /api/rag/query` 返回带引用的回答，向量检索缺失时回退关键词搜索。
- **实现细节/语法**: `run_rag_pipeline(question, top_k, provider, model, ...)` -> 拼装编号上下文 + OpenAI 兼容客户端生成回答与 citations。
- **避坑/注意**: 索引元数据新增 `rel_path/title/tags` 字段，旧索引需重建以补齐引用信息。

## [2025-12-10] 前端接入 RAG 搜索
- **前端调用**: 笔记搜索弹窗改用 `/api/rag/query`，返回回答+引用+片段。
- **实现细节/语法**: `searchNotesInStorage()` -> 组装 provider/model/base_url/api_key/question，渲染 `renderRagAnswer`、`renderRagCitations`、`renderNotesSearchResults`。
- **避坑/注意**: 新增 DOM `notes-search-answer/notes-search-citations` 需保证模板存在；旧索引建议先 `/api/sync` 重建。

## [2025-12-10] Notes 页搜索弹窗
- **弹窗入口**: `notes.html` 增加“智能检索”按钮+弹窗，复用 RAG 接口展示回答、引用与片段。
- **实现细节/语法**: `searchNotesRag()` 直接 POST `/api/rag/query`，`renderRagAnswer/Citations/NotesSearchResults` 渲染结果，引用显示相似度与路径。
- **避坑/注意**: 需先触发 `/api/sync` 重建索引以包含 `rel_path/title/tags` 元数据，避免引用路径缺失。

## [2025-12-10] RAG 无引用排查
- **核心概念**: 引用取决于检索结果 `contexts`；无片段即无 citations。
- **实现细节/语法**: 索引构建仅包含 `status: publish` 的 Markdown（`NOTE_ONLY_PUBLISHED=true` 时），`/api/sync` 重建后 `faiss_meta.json` 应含 `rel_path/title/tags`。
- **避坑/注意**: 笔记未设置 `status: publish`、未重建索引或检索 top_k 太低都会导致 “暂无引用”。

## [2025-12-10] Postman 检测 RAG
- **核心概念**: 先 `/api/sync` 重建索引，再 `/api/rag/query` 提问，检查 `contexts/citations` 非空。
- **实现细节/语法**: Postman 设 `POST http://localhost:8008/api/rag/query`，Headers `Content-Type: application/json`，Body raw JSON: `{"question":"...","top_k":8,"provider":"bigmodel","model":"glm-4-flash","api_key":"<可选>","base_url":"<可选>"}`。
- **避坑/注意**: 若 `NOTE_ONLY_PUBLISHED=true` 需保证笔记 frontmatter 有 `status: publish`；无返回时提高 `top_k` 并确认索引文件存在。

## [2025-12-10] 索引为 0 的常见原因
- **核心概念**: `/api/sync` 的 `indexed_chunks` 受嵌入阶段异常影响，未捕获日志但会返回 0。
- **实现细节/语法**: `NoteIndexer._upsert_chunks` 遇到嵌入错误（如缺少 `EMBEDDING_API_KEY/LLM_API_KEY` 或 `EMBEDDING_BASE_URL` 配置错误）直接返回 0。
- **避坑/注意**: 在启动服务前设置 `EMBEDDING_API_KEY`（或 `LLM_API_KEY`），必要时指定 `EMBEDDING_BASE_URL`；重启后重跑 `/api/sync`，期望 `indexed_chunks > 0`。

## [2025-12-10] 嵌入配置与可用提供商
- **核心概念**: RAG 索引依赖文本嵌入接口，当前代码仅实现 OpenAI 兼容 embeddings（`text-embedding-3-small`）。
- **实现细节/语法**: 环境变量优先级 `EMBEDDING_API_KEY` -> `OPENAI_API_KEY` -> `LLM_API_KEY`，`EMBEDDING_PROVIDER=openai`，`EMBEDDING_BASE_URL=https://api.openai.com`。
- **避坑/注意**: bigmodel 未在嵌入层适配，需提供 OpenAI 兼容的 embedding 服务或扩展代码新增 bigmodel 嵌入端点后再用。

## [2025-12-10] RAG 原理速记
- **核心概念**: Retrieval-Augmented Generation = 先检索相关文本片段，再把片段放进 LLM 提示里生成回答，避免幻觉并返回可引用来源。
- **实现细节/语法**: 典型流程：1) 用嵌入向量索引文档；2) 查询向量近邻检索 top_k 片段；3) 把片段拼成带编号的上下文，连同用户问题喂给 LLM；4) LLM 输出回答并引用编号。
- **避坑/注意**: 索引数据新鲜度取决于重建/增量更新；检索召回不足会导致回答缺引用，需调大 top_k 或优化分块/嵌入模型。

## [2025-12-10] bigmodel 嵌入接入思路
- **核心概念**: 若 bigmodel 提供 OpenAI 兼容 embedding 接口，可用 `EMBEDDING_PROVIDER=bigmodel` + `EMBEDDING_BASE_URL=https://open.bigmodel.cn/api/paas/v4` + `EMBEDDING_API_KEY=你的key`，模型如 `embedding-2`。
- **实现细节/语法**: 请求体（兼容 OpenAI 风格）通常为 `{"model":"embedding-2","input":["text1","text2"]}`，Authorization `Bearer <key>`。
- **避坑/注意**: 若接口非完全兼容，需要在 `ai_providers.get_embedding_callable` 增加 bigmodel 分支用 httpx 手动 POST；配置好后需重启服务并 `/api/sync` 重建索引。

## [2025-12-10] 代码适配 bigmodel 嵌入
- **核心概念**: 新增 bigmodel 嵌入分支（httpx POST `/embeddings`），默认嵌入提供商改为 bigmodel，模型默认 `embedding-2`。
- **实现细节/语法**: `get_embedding_callable` 若 provider=bigmodel -> `endpoint = f"{base}/embeddings"`，Headers `Authorization: Bearer <key>`，Body `{"model": model, "input": texts}`。
- **避坑/注意**: 更新环境变量 `EMBEDDING_API_KEY/BIGMODEL_API_KEY` 并重启后 `/api/sync` 重建索引；若仍失败，检查 base_url 与 key 是否匹配。

## [2025-12-10] 嵌入密钥优先级说明
- **核心概念**: 现在精简为单一 key：`EMBEDDING_API_KEY`，缺省回退 `LLM_API_KEY`。
- **实现细节/语法**: 优先级 `EMBEDDING_API_KEY -> LLM_API_KEY`，一个 key 即可；默认嵌入提供商仍为 bigmodel。
- **避坑/注意**: 更新环境变量后需重启服务，再 `/api/sync` 重建索引。

## [2025-12-10] Postman 调用 bigmodel embeddings
- **核心概念**: 直接请求 bigmodel `/embeddings` 验证 key/模型是否可用。
- **实现细节/语法**: URL `https://open.bigmodel.cn/api/paas/v4/embeddings`，Headers `Authorization: Bearer <key>`、`Content-Type: application/json`，Body `{"model":"embedding-2","input":["hello world"]}`。
- **避坑/注意**: 200 时 `data[0].embedding` 应有向量；401/403 多为 key/域名错误，404/400 多为模型名或路径错误。

## [2025-12-10] bigmodel 调用 500 Content-Type 错误
- **核心概念**: 服务端报 `Content type 'text/plain;charset=UTF-8' not supported`，因请求未设置 JSON 头或 Body 非 JSON。
- **实现细节/语法**: Postman 需设置 `Headers: Content-Type: application/json`，Body 选择 raw+JSON，示例 `{"model":"embedding-2","input":["hello world"]}`。
- **避坑/注意**: 避免 form-data/x-www-form-urlencoded；确认 URL 使用 https，仍报错则检查网关是否要求额外 header。

## [2025-12-10] bigmodel embeddings 打通
- **核心概念**: 已通过 Postman 调用 `embedding-2` 返回向量，证明嵌入服务可用。
- **实现细节/语法**: 请求返回 `data[0].embedding`，可用于索引重建。
- **避坑/注意**: 接下来重启服务后 `/api/sync` 重建索引即可让 RAG 使用 bigmodel 嵌入。

## [2025-12-10] 索引嵌入错误可见性
- **核心概念**: `NoteIndexer` 在嵌入失败时记录日志，便于排查 `indexed_chunks=0`。
- **实现细节/语法**: `_upsert_chunks` 捕获异常 `self.logger.error("embedding/upsert failed: %s", exc, exc_info=True)`。
- **避坑/注意**: 查看服务日志可定位嵌入报错（网络/鉴权/模型名）。

## [2025-12-10] bigmodel 400 报错定位
- **核心概念**: 嵌入接口返回 400 时需要读响应体定位问题。
- **实现细节/语法**: bigmodel 分支在 4xx 时抛出 `HTTPStatusError`，包含 `resp.text`，便于日志输出具体错误。
- **避坑/注意**: 仍报 400 时，检查响应体常见是模型名/参数不符合或输入超限。

## [2025-12-10] bigmodel 嵌入批量上限处理
- **核心概念**: bigmodel embeddings `input` 数组最大 64 条。
- **实现细节/语法**: `NoteIndexer._upsert_chunks` 以 64 批次调用嵌入，逐批写 entries。
- **避坑/注意**: 超过 64 自动分批，重跑 `/api/sync` 不再触发 1214 错误。

## [2025-12-10] bigmodel 400 参数报错处理
- **核心概念**: 过滤空白 chunk，避免 `input` 包含空字符串导致 1210 参数错误。
- **实现细节/语法**: `_upsert_chunks` 跳过 `text.strip()==""` 的分块后再批量嵌入。
- **避坑/注意**: 若仍 400，需查看响应体（模型名/字段/输入长度）。当前默认 `model=embedding-2`。

## [2025-12-10] bigmodel None 结果防护
- **核心概念**: 当批次清洗后无有效文本时直接返回空列表，避免 `embedding_fn returned None`。
- **实现细节/语法**: `embed_bigmodel` 若 `sanitized` 为空则 `return []`，保持长度匹配。
- **避坑/注意**: 若仍报错，检查是否嵌入返回数与输入数不一致或 HTTP 4xx。

## [2025-12-10] bigmodel JSON/空返回健壮性
- **核心概念**: bigmodel 嵌入返回缺省或非 JSON 时，显式报错；正常时过滤 None embedding，回退单条。
- **实现细节/语法**: `_post` 尝试解析 JSON，缺失 data 列表时返回空列表；批量失败时单条重试；最终保证 `embed_bigmodel` 返回列表（或抛 HTTPStatusError）。
- **避坑/注意**: 若仍出现 None，检查网关是否返回非预期结构。

## [2025-12-10] FAISS 写入路径修复
- **核心概念**: 在持久化前确保索引目录存在，避免 `faiss.index` 写入报 “No such file or directory”。
- **实现细节/语法**: `_save_index` 调用前 `self.persist_dir.mkdir(parents=True, exist_ok=True)`。
- **避坑/注意**: 若路径权限受限需调整 `CHROMA_PERSIST_DIR`。

## [2025-12-10] FAISS 路径规范化
- **核心概念**: 使用绝对路径避免 `..\` 导致 faiss 写入失败。
- **实现细节/语法**: `self.persist_dir = Path(persist_dir).resolve()`，索引/元数据文件基于规范化路径生成。
- **避坑/注意**: 修改后需重启服务，再 `/api/sync`。

## [2025-12-10] Postman 调用 /api/sync
- **核心概念**: 触发 Git pull + 全量向量索引重建。
- **实现细节/语法**: Method `POST`，URL `http://localhost:5000/api/sync`，Headers 仅需 `Content-Type: application/json`（可不带 body）。
- **避坑/注意**: 确认服务已重启且环境包含有效嵌入 key；期望响应 `indexed_chunks > 0`。

## [2025-12-10] Markdown CSS 模块化
- **核心概念**: 将 Markdown 样式提取到独立文件 `markdown.css`，提升可维护性。
- **实现细节/语法**: 创建 `app/static/css/markdown.css`，包含 `.markdown-body`、`.message-content` 等样式；在 `aichat.html`、`notes_view.html`、`notes.html` 中引入。
- **避坑/注意**: 样式文件需在 `styles.css` 之后引入，确保设计令牌可用。

## [2025-12-10] 新建笔记功能
- **核心概念**: 在导航栏侧边栏和笔记列表页添加"新建笔记"按钮，通过 Alpine.js 弹窗创建笔记。
- **实现细节/语法**: `newNoteModal()` Alpine 组件管理弹窗状态，调用 `POST /api/md/file` 创建笔记；支持标题、内容、标签、子目录；创建成功后刷新列表并跳转到新笔记。
- **避坑/注意**: 侧边栏按钮需在 Alpine.js 作用域内（`x-data`），使用 `$dispatch('open-new-note')` 触发弹窗；标签解析支持中英文逗号和空格分隔。

## [2025-12-10] 模态框关闭功能修复
- **核心概念**: 修复查看笔记和新建笔记模态框无法关闭的问题。
- **实现细节/语法**: `closeViewNoteModal()` 添加 `viewNoteModal.style.display = 'none'` 确保隐藏；添加背景点击和 ESC 键关闭事件；新建笔记弹窗使用 `@click.self="close()"` 支持背景点击关闭。
- **避坑/注意**: CSS 默认 `display: flex` 会与 Alpine.js `x-show` 冲突，需确保关闭函数显式设置 `display: none`；背景点击需使用 `@click.self` 而非 `@click`，避免内容区域点击触发关闭。

## [2025-12-10] 项目文档完善
- **核心概念**: 创建全面的 README.md 文档，总结项目功能、技术架构和使用指南。
- **实现细节/语法**: 包含核心功能说明、技术栈介绍、快速开始指南、配置说明、项目结构、核心优势等章节。
- **避坑/注意**: 文档需保持更新，与代码实现同步；环境变量配置需清晰说明默认值和必需项。

## [2025-12-10] Chat 页面 LaTeX 整行公式居中
- **核心概念**: 在聊天页面支持 LaTeX 渲染，整行公式（`$$...$$`）居中显示。
- **实现细节/语法**: `aichat.html` 添加 MathJax 配置和脚本；`renderMarkdown()` 先提取 `$$...$$` 为占位符，marked 渲染后回填为 `<span class="math-block">$$...$$</span>`；CSS `.math-block` 设置 `display: block; text-align: center;` 实现居中。
- **避坑/注意**: 需在 marked 处理前提取公式块，避免 `\\` 被转为 `<br>`；MathJax 渲染在 `setTimeout` 中异步触发，查找所有 `.message-content` 元素。

## [2025-12-10] Notes 预览页面布局优化
- **核心概念**: 美化 `notes_view.html` 页面，增加内容区域两侧留白，提升阅读体验。
- **实现细节/语法**: 添加 `.content-wrapper` 包装器，设置 `max-width: 900px`、`padding: 0 var(--spacing-2xl)`，响应式适配：1200px 以下 `padding: 0 var(--spacing-xl)`，768px 以下 `padding: 0 var(--spacing-lg)`。
- **避坑/注意**: 使用 `box-sizing: border-box` 确保 padding 不影响总宽度；内容卡片宽度设为 100% 以填充包装器。

## [2025-12-11] 概念碰撞 Brainstorm API
- **概念碰撞**: 随机/反相似抽样两条笔记交给 LLM 做“概念合成”输出创意。
- **实现细节/语法**: `POST /api/brainstorm` -> `brainstorm_idea(mode, provider, model, base_url, api_key)`；随机使用 `random.sample`，MMR 通过最小余弦相似度 `_pick_least_similar`；LLM 调用 `client.chat.completions.create(..., response_format={"type": "json_object"})` 返回 JSON。
- **避坑/注意**: 笔记不足抛 400；模型缺失抛显式错误；大规模索引建议缓存 id/控制文本长度（截断 1200 字符）。 

## [2025-12-11] 前端概念碰撞接线
- **核心概念**: notes 页面新增“概念碰撞”按钮，调用 `/api/brainstorm` 并弹窗展示来源笔记与生成的连接/标题/大纲。
- **实现细节/语法**: `brainstorm-btn` + `brainstorm-mode` 触发 `runBrainstorm()`；fetch POST `{mode}`，解析 JSON（字符串返回时安全解析），填充 `brainstorm-body`/`brainstorm-sources`，遮罩点击关闭。
- **避坑/注意**: 笔记不足或接口错误提示 `showError`；outline 为空兜底；新增 `brain-outline/brain-row` 样式防止排版挤压。

## [2025-12-11] Wikipedia 随机提示生成（采样+提炼）
- **核心概念**: Wikipedia 随机词条 + LLM 提炼为可迁移的“提示模板”，存本地 JSON。
- **实现细节/语法**: `POST /api/prompts/generate` 调用 `generate_prompt_from_wiki(lang, provider, model, base_url, api_key)`；随机词条取 `https://{lang}.wikipedia.org/api/rest_v1/page/random/summary`，LLM `response_format={"type": "json_object"}`；结果持久化 `data/prompts.json`；`GET /api/prompts?limit&offset` 列表返回。
- **避坑/注意**: 模型缺失抛 400；请求失败 500；可按需截断摘要防长文本；确保 `data/` 可写。
- **命名调整**: 路由文件改为 `prompt.py`，服务文件 `prompt_engine.py`，路径去除比喻化命名。
## [2025-12-10] Notes 编辑分栏与留白收紧
- **核心概念**: 编辑模式左右分栏，左侧 Markdown 编辑，右侧实时预览，同时减少两侧留空。
- **实现细节/语法**: `notes_view.html` 调整 `.content-wrapper` 为 `max-width: 1200px`、padding 依次为 xl/lg/md；编辑区域新增 `edit-split` 双栏布局，`panel-header` 标题 + `preview-panel` 预览容器，textarea `@input` 调用 `updatePreview()` 触发 `renderMarkdownWithMath` 渲染。
- **避坑/注意**: 预览容器最小高度 240px；≤960px 自动切为单列；保持 `box-sizing: border-box` 避免 padding 影响宽度。

## [2025-12-11] Wikipedia API UA/重定向
- **核心概念**: Wikipedia REST 403/303 需自定义 User-Agent 并跟随重定向。
- **实现细节/语法**: `httpx.Client(headers={"User-Agent": settings.WIKI_USER_AGENT, "Accept": "application/json"}, follow_redirects=True)` -> `_fetch_random_wiki` 可直接获取随机词条。
- **避坑/注意**: UA 为空会被拒绝；若仍 4xx，检查网络或代理，必要时调整 `WIKI_USER_AGENT`。

## [2025-12-11] Prompt 生成存储路径
- **核心概念**: 生成的 prompt 本地持久化，便于复用/列表展示。
- **实现细节/语法**: `generate_prompt_from_wiki` 将结果插入开头后写入 `data/prompts.json`，字段含 `id/source/prompt/created_at/provider/model`。
- **避坑/注意**: 确保 `data/` 可写；批量生成会前插，注意文件大小与并发写入。

## [2025-12-11] Brainstorm 注入 Prompt 扰动
- **核心概念**: 概念碰撞前附加最近的 Wikipedia 提示模型，作为思维扰动。
- **实现细节/语法**: `_build_prompt_hint` 读取 `data/prompts.json` 取最新 `model_name/core_principle/transfer_analogy/application_starters`，拼入用户提示；`_build_messages` 注入 `prompt_hint`。
- **避坑/注意**: 无本地 prompt 时不注入；`data/` 不可写或 JSON 异常会静默回退。

## [2025-12-11] Brainstorm 自动补充 Prompt 池
- **核心概念**: 每次概念碰撞先生成一条新 prompt，维持池子上限 100。
- **实现细节/语法**: `_refresh_prompt_pool(max_size=100)` -> 调用 `generate_prompt_from_wiki` 写入 `data/prompts.json`，若超出上限截断前 100 条；失败不阻塞 brainstorm。
- **避坑/注意**: 依赖 LLM/Wiki 可用性，写入失败时仅跳过；大量并发可能存在覆盖，必要时加锁。

## [2025-12-11] Brainstorm 即时拉取 Prompt 词（不落盘）
- **核心概念**: 概念碰撞时直接从 Wikipedia+LLM 拉取一条 prompt 词作为扰动，默认中文，不写入 `prompts.json`，失败则回退本地缓存首条。
- **实现细节/语法**: `_fetch_prompt_terms(lang="zh", provider/model/base_url/api_key)` 走 `_fetch_random_wiki` + `refine_topic`，`_build_prompt_hint` 优先用新词，缺失则 `_load_prompt_catalysts` 取本地第一条；`_build_messages` 将 hint 拼入用户提示。
- **避坑/注意**: Wiki/LLM 不可用时仅提示缺失，不阻塞；若需指定语言可传 `prompt_lang`。

## [2025-12-11] Brainstorm 选文重复与篇幅
- **核心概念**: 概念碰撞从向量索引 `note_indexer.entries` 随机/最不相似抽样，两篇文本均截断到 `MAX_SNIPPET_LEN=1200`。
- **实现细节/语法**: `pick_notes` 在条目少时 `random.sample` 容易重复同几篇；`_pick_least_similar` 仅在 embeddings 足够时生效。
- **避坑/注意**: 若总文档少或未刷新索引，会频繁抽到相同长文；可缩短 `MAX_SNIPPET_LEN`、增加笔记数量或加入“近期已用”排除逻辑以提升多样性。

## [2025-12-11] Brainstorm 短文优先随机
- **核心概念**: 抽样时优先从较短文本池随机，减少长文占比并提升多样性。
- **实现细节/语法**: 新增 `_pick_shorter_indices` 按文本长度中位数 *1.2 过滤候选，不足则取最短前 50；`pick_notes` 随机从候选取 2，仍不足则回退全量。`MAX_SNIPPET_LEN` 降至 800。
- **避坑/注意**: 候选不足时会回退全量；若索引少仍可能重复，需补充笔记或重建索引。

## [2025-12-11] Brainstorm 文件粒度抽样
- **核心概念**: 随机抽样改为以文件为单位去重，避免同一长文多个分块被频繁命中。
- **实现细节/语法**: `_pick_file_level_indices` 按 `rel_path/file_path/title` 聚合每个文件保留首个索引；`pick_notes` 先取文件去重池与短文池交集，再回退文件池/短文池/全量。
- **避坑/注意**: 当索引极少时仍会回退全量；若需更强随机可补充笔记并重建索引。

## [2025-12-11] 索引发布过滤默认关闭
- **核心概念**: 默认不再仅索引 `status: publish` 的笔记，全部纳入向量索引。
- **实现细节/语法**: `NOTE_ONLY_PUBLISHED` 默认从 `true` 调整为 `false`，仍可通过环境变量覆盖；`/api/sync` 将索引全部文件。
- **避坑/注意**: 若需恢复发布过滤，设置 `NOTE_ONLY_PUBLISHED=true` 后重跑 `/api/sync` 重建索引。

## [2025-12-11] Chat 前端 FC 提示恢复
- **核心概念**: 聊天发送前再次提示可能触发的 Function Call（RAG/概念碰撞）。
- **实现细节/语法**: `scripts.js` 新增 `insertToolNotice`，在 `generateResponse` 前展示“笔记检索(RAG)/概念碰撞，模型自动决定是否调用”。
- **避坑/注意**: 仅提示，不强制调用；需与后端 tools 对齐。

## [2025-12-11] 助手角色配置 API
- **核心概念**: 提供助手名称/性格描述的查询与更新，并持久化到 `config.json`。
- **实现细节/语法**: 新增 `assistant_config.py` 读写 `config.json`；路由 `/api/assistant` 支持 `GET` 获取、`PUT` 更新（支持部分字段），注册至应用。
- **避坑/注意**: `name/persona` 至少一项；文件缺失自动写入默认值；仅做基础校验。

## [2025-12-11] Chat 前端助手配置绑定
- **核心概念**: 前端设置弹窗可编辑助手名称/性格并落盘，聊天头像和 persona 自动应用。
- **实现细节/语法**: `assistantConfig` 全局存储；载入时拉取 `/api/assistant` 写入输入框并回填 persona；发送消息时若本地 persona 为空则使用助手 persona，并在系统提示中声明“你叫{assistantName}”；头像文字随助手名称变化。
- **避坑/注意**: 若未保存助手，默认名称为 AI；修改后需点击“保存助手”，失败提示不影响聊天。
## [2025-12-11] Chat 前端 FC 集成说明
- **核心概念**: AI 聊天室调用后端 `/stream_generate`，由模型自动决定是否触发工具（RAG/概念碰撞），前端仅需发送消息，无需额外开关。
- **实现细节/语法**: `scripts.js` 发送 `messages/newMessage/search_notes/provider/model/base_url/api_key/persona` 到后端；后端 tools 自动检索/碰撞并再流式补全，前端已有提示文案。
- **避坑/注意**: 若想关闭检索，只需在 UI 关闭“笔记检索”开关；FC 提示仅提示可能调用，是否调用由模型决策。

## [2025-12-11] 项目概览
- **项目简介**: Flask 微服务整合 RAG 与 GitHub API，前端静态资源提供聊天与笔记体验。
- **实现细节/语法**: `Flask` 路由 + `LangChain/ChromaDB` 检索生成；`GitPython/PyGithub` 拉取仓库；环境变量集中在 `settings.py` 管理。
- **避坑/注意**: 请求/应用上下文需正确使用；嵌入/LLM 密钥缺失会导致索引与生成失败。

## [2025-12-11] 项目创新细化
- **概念碰撞 Brainstorm**: 笔记向量索引随机/反相似抽样，结合 Wikipedia prompt 扰动，`/api/brainstorm` 返回 JSON 结构含 sources/outline。
- **Prompt 池自愈**: 调用 Wikipedia+LLM 动态生成 prompt 写入 `data/prompts.json`，超过 100 条截断，供后续 brainstorm 注入提示词。
- **RAG 召回稳健性**: LangChain/ChromaDB 检索缺片段时回退关键词搜索；bigmodel/OpenAI 兼容 embeddings 可切换，嵌入批量分片防 400。
- **前端智能提示**: 聊天前提示可能触发 RAG/概念碰撞工具，降低误用；MathJax+Markdown 渲染优化阅读体验。

## [2025-12-11] 项目创新章节化
- **章节1 概念碰撞 Brainstorm**: 以向量索引随机/反相似抽样笔记，叠加 Wikipedia prompt 扰动，接口 `/api/brainstorm` 以 JSON 提供 sources/连接/标题/大纲，强调可追溯性。
- **章节2 Prompt 池自愈**: 每次脑暴可拉取 Wikipedia+LLM 生成新 prompt，写入 `data/prompts.json` 并维持 100 条上限，为后续创意提供扰动基底。
- **章节3 RAG 召回稳健性**: LangChain/ChromaDB 检索缺片段时回退关键词搜索；嵌入层支持 bigmodel/OpenAI 兼容接口，批量分片与空文本过滤减低 400/None。
- **章节4 前端智能提示与体验**: 聊天前提示可能触发 RAG/概念碰撞，避免误用；MathJax+Markdown 样式优化阅读与代码高亮，配合弹窗展示引用与大纲。

## [2025-12-11] NOTE_ONLY_PUBLISHED 语义调整
- **核心概念**: 环境变量仅控制前端列表是否过滤未发布笔记，向量索引始终包含全部笔记。
- **实现细节/语法**: `/api/sync` 不再过滤 `status: publish`；Markdown 详情接口不再因未发布拒绝访问；README 更新变量说明。
- **避坑/注意**: 若仅想在列表展示发布笔记，可设置 `NOTE_ONLY_PUBLISHED=true`，但索引与检索仍会覆盖所有文件。