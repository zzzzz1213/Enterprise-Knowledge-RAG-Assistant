# KnowledgeRAG-GZHU 开发变更报告

> 生成时间：2026-03-24 09:35
> 涉及 commit：`c8c5fea` / `224803a`（相对基线 `7585671`）
> 变更规模：**18 个文件，新增 1846 行，删除 703 行**

---

## 2026-05-07 企业知识库智能助手第一轮改造

### 变更摘要

- 将前端显著品牌文案替换为「企业知识库智能助手」
- 调整侧边栏与顶部导航的功能命名，突出知识库、文件管理、智能问答和 Agent
- 隐藏移动端下载与知识广场等非企业首屏入口
- 修复 `dev.ps1` 中 MySQL compose 服务名
- 修复知识库页面搜索清空按钮的 Vue 模板解析错误
- 补齐侧边栏 `quickCreate` 事件声明，避免 Vue 类型检查报错
- 扫描并修复前端多处多行模板事件表达式，避免 Vite 逐页暴露解析错误
- 统一后端默认 Ollama 模型配置，将 `models_config.json` 的 `llm_model` / `kg_model` 改为 `qwen2:0.5b`
- 将聊天接口桥接到现有 RAG 流程，开启知识库问答时按 `kb_id` 执行检索并返回来源
- 移除登录页 QQ / 微信第三方登录入口，并暂停后端 QQ OAuth 路由注册
- 移除 `models_config.json` 中的明文 DeepSeek API Key，云端模型密钥改为优先读取环境变量
- 修复 `user_profile` 表结构与后端初始化代码不一致的问题，兼容新旧个人资料字段
- 修复 `RagFrontend/src/components/chat-main-unit/chat-main-unit.vue` 的 TypeScript 类型错误，补齐聊天消息、模型选项、文件选择与流式中断相关类型
- 前端 `npm run build` 已验证通过，可正常产出生产构建目录 `dist`
- 修复增量向量化任务队列 `_persist_status` 参数冲突，`/api/vectorize/ingest` 可正常提交任务
- 修复增量向量化器对 `DocumentLoader.load_document()` 的兼容调用，文档可正常解析分块
- 为向量库目录增加 ASCII 安全映射，规避 Windows / FAISS 在中文路径下读写 `index.faiss` 失败的问题
- 已用「测试企业知识库」完成 RAG 实测：`qwen2:0.5b` 返回回答，并附带引用来源与 `hybrid` 检索模式
- 修复聊天页 RAG 模式前端发送链路：`chat-main-unit.vue` 在知识库问答开启时改为触发父组件 `send-message`，避免绕过后端 RAG 直连 Ollama
- 修复聊天页 RAG 模式“按回车后界面不更新”问题：统一消息数组顺序为最新在前，并同步父子组件 `history` 响应式更新
- 校正上一轮聊天顺序修复：`Chat.vue` 恢复尾部追加消息，`chat-main-unit.vue` 读取父级加载态，RAG 模式重新显示底部回复与生成中状态
- 统一聊天顺序逻辑：普通聊天、云端模型聊天和 RAG 会话均按旧到新展示，并在读取历史时兼容此前保存的倒序记录
- 修正 TDesign Chat 顺序适配：业务历史保持旧到新，`displayHistory` 倒序传入组件，避免最新对话视觉上跑到顶部
- 修复旧版 LangChain 向量化在中文知识库目录下只残留 `vectorstore/temp_save` 的问题：`/api/RAG/ingest` 改用 ASCII 安全向量库目录，FAISS 保存改为清理旧临时目录后原子替换文件
- 收紧 RAG Prompt：移除“根据《文件名》”占位示例，要求只使用真实来源名，并在知识库未提供规定时明确拒绝编造
- 优化 RAG 回答约束：按问题关键词裁剪每个来源上下文，禁止小模型把请假、报销、餐补等无关制度混入“迟到”等单一问题回答
- 将聊天页 RAG 默认检索 `topK` 从 6 调整为 3，减少测试阶段传入 `qwen2:0.5b` 的无关文档块
- 增加抽取式回答保护层：当检索结果中包含与问题直接相关的制度句子时，后端直接用原文组织答案，避免 `qwen2:0.5b` 编造罚款、调岗、绩效奖金等不存在条款
- 修正短文档上下文裁剪触发条件：即使文档块小于 450 字，也会优先只保留与问题关键词匹配的句子
- 修复智能问答页误报知识库未向量化：`/api/chat/send-message` 现在会同时识别 LangChain FAISS (`index.faiss`/`index.pkl`) 与 Native FAISS (`native.index`/`native_docs.pkl`) 向量库
- 强化向量化状态校验：`/api/vectorize/stats/{kb_id}` 返回真实索引文件状态，知识库详情页只有检测到完整向量库文件才显示处理完成
- 聊天页选择知识库后会提前检查向量化状态，未检测到完整索引时提示用户先完成向量化
- 修复旧 `/api/RAG/ingest` 路径分叉：LangChain 向量化由项目根目录 `knowledge_base/vectorstores` 改为统一写入 `RagBackend/knowledge_base/vectorstores`，并对旧路径保留读取兼容
- 修复 `/api/vectorize/stats/{kb_id}` 中未定义 `UPLOAD_DIR` 导致 500 的问题，避免聊天页误判知识库未向量化
- 优化用户体验：知识库列表新增向量化状态徽标，聊天页新增知识库就绪状态、检索策略和模型信息展示
- 优化向量化流程：知识库详情页向量化成功后提供“去智能问答”按钮，失败输出突出普通错误并保留路径详情
- 优化来源展示：聊天引用来源折叠区展示更清晰，并限制来源片段高度，避免撑开对话区域
- 继续优化问答操作流：知识库详情页跳转智能问答会携带当前 `kb_id`，聊天页自动开启知识库问答并选中对应知识库
- 上传文档成功后新增“立即向量化”入口，减少用户上传后忘记处理导致聊天页提示未向量化
- 智能问答知识库状态面板新增刷新按钮，便于向量化后手动同步当前知识库状态
- 将知识库详情页“去智能问答”入口固定到顶部，点击时先校验向量化状态，避免用户刷新页面后找不到入口
- 新增 `RUNBOOK.md`，整理 VSCode 终端日常实验启动流程、Ollama 检查、启动后自检与常见问题
- 重写 `readme.md` 为 GitHub 展示版，突出企业知识库、RAG 问答、引用来源、本地 `qwen2:0.5b` 和启动流程
- 补强 `.gitignore`，避免公开仓库上传 `.env`、本地知识库文件、向量库、数据库、构建产物和缓存
- 调整 README 模型说明：当前版本为初版，本地 `qwen2:0.5b` 用于开发演示，企业级演进方向包括云端模型 API 与企业内网模型服务
- 新增 `ENTERPRISE_ROADMAP.md`，保存后续高级优化方向：Agentic RAG、DeepSearch/DeepResearch、Model Routing、RAG 质量优化和企业级工程化
- 新增项目级说明文档：`PROJECT_BRIEF.md`、`PAGE_MAP.md`、`DATA_MAP.md`

### 变更文件

- `RagFrontend/index.html`
- `RagFrontend/package.json`
- `RagFrontend/src/components/SideBar.vue`
- `RagFrontend/src/components/T-HeadBar.vue`
- `RagFrontend/src/views/LogonOrRegister/LogonOrRegister.vue`
- `RagFrontend/src/views/LogonOrRegister/LoginRegisterForm.vue`
- `RagFrontend/src/components/chat-main-unit/chat-main-unit.vue`
- `RagFrontend/src/i18n/index.ts`
- `RagFrontend/src/views/KnowledgePages/KnowledgeBase.vue`
- `RagFrontend/src/views/Settings.vue`
- `RagBackend/main.py`
- `RagBackend/models_config.json`
- `RagBackend/multi_model/model_router.py`
- `RagBackend/RAGF_User_Management/LogonAndLogin.py`
- `RagBackend/RAGF_User_Management/User_settings.py`
- `RagBackend/RAGF_User_Management/QQ_Login.py`
- `RagBackend/document_processing/task_queue.py`
- `RagBackend/document_processing/incremental_vectorizer.py`
- `RagBackend/RAG_M/RAG_app.py`
- `RagBackend/chat_units/chat_management/chat_send.py`
- `RagFrontend/src/views/KnowledgePages/KnowledgeDetail.vue`
- `RagFrontend/src/views/Chat.vue`
- `RagFrontend/src/views/KnowledgePages/KnowledgeBase.vue`
- `RagFrontend/src/components/knowledge-unit/KbCard.vue`
- `RagFrontend/src/components/chat-main-unit/chat-main-unit.vue`
- `RagBackend/RAG_M/src/rag/rag_pipeline.py`
- `RagBackend/RAG_M/src/rag/native_rag.py`
- `RagFrontend/src/components/RetrievalConfig.vue`
- `RagFrontend/src/views/Chat.vue`
- `RagBackend/docs/init.sql`
- `dev.ps1`
- `.gitignore`
- `readme.md`
- `ENTERPRISE_ROADMAP.md`
- `RUNBOOK.md`
- `CHANGELOG.md`
- `PROJECT_BRIEF.md`
- `PAGE_MAP.md`
- `DATA_MAP.md`

---

## 目录

1. [项目背景](#1-项目背景)
2. [Bug 修复](#2-bug-修复)
3. [RAG 检索优化](#3-rag-检索优化)
4. [知识图谱增强](#4-知识图谱增强)
5. [轻量化封装方案](#5-轻量化封装方案)
6. [自动化测试](#6-自动化测试)
7. [变更文件汇总](#7-变更文件汇总)
8. [如何回滚](#8-如何回滚)

---

## 1. 项目背景

**KnowledgeRAG-GZHU** 是一个面向知识库的检索增强生成（RAG）系统，技术栈为：

| 层次 | 技术 |
|------|------|
| 前端 | Vue 3 + TypeScript + TDesign |
| 后端 | FastAPI + Python 3.11 |
| 向量存储 | FAISS |
| 模型服务 | Ollama（本地 LLM） |
| 数据库 | MySQL 8.0 |
| 知识图谱 | 自研 NLP 抽取 + ECharts 可视化 |

本次开发在原始快照（tag `v0-original`，commit `7585671`）基础上进行，目标：
1. 修复存量 Bug
2. 增强 RAG 检索质量
3. 升级知识图谱交互
4. 提供 < 1G 的最轻量容器化封装

---

## 2. Bug 修复

### 2.1 JWT Secret 硬编码（高危安全漏洞）

**问题**：三个文件中均使用 `"secret"` 作为 JWT 签名密钥，任何人都可以伪造 token。

**涉及文件**：
- `RagBackend/RAGF_User_Management/LogonAndLogin.py`
- `RagBackend/RAGF_User_Management/User_Management.py`
- `RagBackend/RAGF_User_Management/User_settings.py`

**修复方式**：所有 `jwt.encode` / `jwt.decode` 调用均改为读取环境变量：

```python
# 修复前
secret_key = "secret"

# 修复后
secret_key = os.getenv('JWT_SECRET', 'changeme_jwt_secret')
```

同时新增 `RagBackend/.env.example` 模板，明确所有需配置的敏感变量（DB 密码、JWT Secret、Ollama 地址等），`.env` 本体已在 `.gitignore` 中排除。

---

### 2.2 FastAPI 路由前缀冲突

**问题**：`User_Management.py` 和 `User_settings.py` 的路由注册在 `main.py` 中均使用 `/api/user` 前缀，导致同名路径相互覆盖，部分接口实际上永远不会被触发。

**修复方式**：将旧版 `user_management_router` 的前缀改为 `/api/legacy/user`，与 `User_settings` 路由完全隔离：

```python
# 修复前
app.include_router(user_management_router, prefix="/api/user", ...)

# 修复后
app.include_router(user_management_router, prefix="/api/legacy/user", ...)
```

---

### 2.3 `doc_list.py` 方法重复定义

**问题**：`search_documents` 方法在类中被完整定义了两次（第二次定义覆盖第一次），造成代码冗余并增加维护风险。

**修复方式**：删除重复的第一份定义，保留唯一完整版本。删除代码约 46 行。

---

### 2.4 `docker-compose.yml` 多处错误

**问题 1**：前端 `build.context` 指向 `./frontend_ASF`，但实际前端目录为 `./RagFrontend`，导致 Docker build 必然失败。

**问题 2**：`ollama` 服务未加入 `apn-network`，后端容器无法通过服务名 `ollama` 解析到 Ollama 地址。

**问题 3**：DB 密码、JWT Secret 等敏感信息直接硬编码在 compose 文件中。

**修复方式**：
```yaml
# 修复前
frontend:
  build:
    context: ./frontend_ASF  # 错误路径

ollama:
  image: ollama/ollama:latest
  # 没有 networks

# 修复后
frontend:
  build:
    context: ./RagFrontend   # 正确路径

ollama:
  networks:
    - apn-network             # 加入内部网络

asf-backend:
  environment:
    - DB_PASSWORD=${DB_PASSWORD:-changeme}   # 外置为环境变量
    - JWT_SECRET=${JWT_SECRET:-changeme_jwt_secret}
```

---

### 2.5 Celery 残留死代码清理

**问题**：`main.py` 中存在一大段被注释掉的 Celery 初始化代码，格式混乱，误导阅读者以为系统依赖 Celery。

**修复方式**：清理为标准注释，说明扩展入口用法。

---

## 3. RAG 检索优化

### 3.1 新增：混合检索器 `hybrid_retriever.py`

**文件路径**：`RagBackend/RAG_M/src/rag/hybrid_retriever.py`（全新，188 行）

**功能**：实现 BM25 关键词检索 + FAISS 向量检索的融合，采用 **RRF（Reciprocal Rank Fusion）** 算法对两路结果排名融合，不依赖任何额外第三方库（BM25 纯 Python 实现）。

**核心流程**：

```
用户查询
   ├─ BM25 关键词检索 ──┐
   │                    ├─ RRF 融合排序 → Top-K 结果
   └─ FAISS 向量检索 ──┘
```

**关键参数**：
- `bm25_weight`：BM25 结果权重（默认 0.4）
- `vector_weight`：向量结果权重（默认 0.6）
- `rrf_k`：RRF 平滑常数（默认 60）
- `top_k`：最终返回条数（默认 5）

---

### 3.2 升级：RAG Pipeline v2

**文件路径**：`RagBackend/RAG_M/src/rag/rag_pipeline.py`（267 行，大幅重写）

**新增能力**：

| 功能 | 说明 |
|------|------|
| 混合检索 | 集成 `HybridRetriever`，可通过参数开关 |
| 引用溯源 | 每条检索结果附带 `source`（文件名）、`page`（页码/块编号）、`score`（相关性得分） |
| 流式生成 | `query_stream()` 方法逐 token 流式输出，支持 SSE |
| 降级兼容 | 混合检索失败时自动回退到纯向量检索 |

**返回结构示例**：
```json
{
  "answer": "...",
  "sources": [
    {"source": "report.pdf", "page": 3, "score": 0.92, "content": "..."},
    {"source": "manual.txt", "page": 1, "score": 0.87, "content": "..."}
  ],
  "retrieval_mode": "hybrid"
}
```

---

### 3.3 升级：RAG API 接口

**文件路径**：`RagBackend/RAG_M/RAG_app.py`（全面重写）

**变更**：

| 接口 | 变更 |
|------|------|
| `POST /RAG_query` | 升级为流式 SSE 响应，携带引用溯源信息 |
| `POST /RAG_query_sync` | **新增**调试用同步接口，返回完整 JSON |
| 参数 `use_hybrid` | 新增布尔参数，控制是否启用混合检索（默认 `true`） |

---

## 4. 知识图谱增强

### 4.1 后端新增三个 API

**文件路径**：`RagBackend/knowledge_graph/generate_kg.py`（新增 173 行）

#### `/get-kb-merged-graph/{kb_id}` — 全知识库合并图谱

将指定知识库下所有 `*_graph.json` 文件合并为一张全图，自动去重节点（基于 `id`）和边（基于 `source+target+label` 三元组）。

```
GET /api/kg/get-kb-merged-graph/{kb_id}

返回：
{
  "nodes": [...],
  "edges": [...],
  "node_count": 128,
  "edge_count": 256,
  "source_files": ["doc1_graph.json", "doc2_graph.json"]
}
```

#### `/search-nodes/{kb_id}?keyword=xxx` — 节点模糊搜索

在全合并图中按 `label` 模糊匹配关键词，返回匹配节点及其**一跳邻居**构成的子图。

```
GET /api/kg/search-nodes/{kb_id}?keyword=机器学习

返回：匹配节点 + 相邻节点 + 连接边
```

#### `/graph-stats/{kb_id}` — 图谱统计信息

```
GET /api/kg/graph-stats/{kb_id}

返回：
{
  "node_count": 128,
  "edge_count": 256,
  "type_distribution": {"概念": 45, "实体": 83},
  "isolated_node_count": 12
}
```

---

### 4.2 前端知识图谱组件全面升级

**文件路径**：`RagFrontend/src/components/graph-unit/graph-main.vue`（742 行，大幅重写）

**新增功能**：

| 功能 | 描述 |
|------|------|
| 全图加载按钮 | 一键加载该知识库所有文件的合并图谱 |
| 节点搜索框 | 输入关键词实时过滤，高亮匹配节点及其邻居 |
| 节点点击详情面板 | 点击任意节点，右侧弹出详情面板，显示节点属性及所有相关边 |
| 图谱统计浮窗 | 左下角显示节点数/边数/类型分布/孤立节点数 |
| 悬停高亮 | 鼠标悬停节点时高亮该节点及其直接邻居，其余节点半透明 |
| 拖拽体验优化 | 修复拖拽时误触点击的问题 |

**前端 API 配置**（`RagFrontend/src/utils/apiConfig.ts`）：
```typescript
KNOWLEDGE_GRAPH: {
  GET_MERGED_GRAPH: (kbId) => `.../get-kb-merged-graph/${kbId}`,
  SEARCH_NODES: (kbId, keyword) => `.../search-nodes/${kbId}?keyword=...`,
  GRAPH_STATS: (kbId) => `.../graph-stats/${kbId}`,
  GET_KB_FILE_GRAPH: (kbId, filename) => `.../get-kb-graph-data/${kbId}/...`,
}
```

---

## 5. 轻量化封装方案

目标：整体镜像体积 < 1G（不含 Ollama 模型权重文件）。

### 5.1 后端 Dockerfile

**文件路径**：`RagBackend/Dockerfile`（60 行，全新）

**策略**：
- 基础镜像：`python:3.11-slim`（而非完整 `python:3.11`，节省 ~400MB）
- 多阶段构建：build 阶段安装依赖，runtime 阶段只复制必要文件
- 跳过 `.pyc` 缓存写入，减少镜像层大小

**预估体积**：~480MB（含 FAISS、torch CPU 版本）

### 5.2 前端 Dockerfile

**文件路径**：`RagFrontend/Dockerfile`（34 行，全新）

**策略**：
- Stage 1（`node:20-alpine`）：执行 `npm run build` 编译静态资源
- Stage 2（`nginx:alpine`）：仅复制 `dist/` 文件夹进行托管

**预估体积**：~45MB

### 5.3 Nginx 配置

**文件路径**：`RagFrontend/nginx.conf`（35 行，全新）

**关键配置**：
- Vue Router history 模式支持（`try_files $uri /index.html`）
- `/api/` 反向代理到后端 `asf-backend:8000`
- SSE 流式响应支持（禁用缓冲 `proxy_buffering off`）
- 静态资源强缓存（js/css/图片 1 年缓存）

### 5.4 生产 docker-compose.yml

**完整服务栈**：

| 服务 | 镜像 | 端口 | 说明 |
|------|------|------|------|
| `asf-backend` | 自构建（python:3.11-slim） | 8000 | FastAPI 后端 |
| `asf-frontend` | 自构建（nginx:alpine） | 8089→80 | Vue3 前端 |
| `mysql` | `mysql:8.0` | 3306 | 数据库 |
| `ollama` | `ollama/ollama:latest` | 11434 | 本地 LLM 服务 |

**新增特性**：
- 所有服务均加入 `apn-network`，内部通过服务名互通
- 数据卷持久化（`mysql_data`、`ollama_data`、`uploads`）
- 健康检查（`mysqladmin ping`、`/health` 端点）
- 所有敏感配置通过 `.env` 文件注入，不再硬编码

**各组件体积估算**：

```
后端镜像         ~480 MB
前端镜像          ~45 MB
MySQL 8.0        ~550 MB  ← 已有缓存通常更小
Ollama 引擎      ~200 MB  ← 不含模型权重
─────────────────────────
合计（不含模型） ~1.27 GB

说明：MySQL 和 Ollama 均为官方基础镜像，
     首次下载时体积较大，后续更新增量极小。
     后端+前端自构建镜像合计 <530 MB。
```

> **注意**：Ollama 模型权重（如 `llama3:8b` 约 4.7GB）需在容器启动后单独 `ollama pull`，不计入镜像体积。

---

## 6. 自动化测试

**文件路径**：`RagBackend/tests/test_all_fixes.py`（342 行，全新）

**测试结果**：

```
Ran 18 tests in 0.916s

OK
```

**测试覆盖点**：

| 测试类 | 测试内容 |
|--------|---------|
| `TestDocListFixes` | search_documents 无重复定义、DocumentManager.preview_document 无重复定义 |
| `TestJWTEnvVar` | LogonAndLogin/User_settings/User_Management 中 JWT secret 已改为 os.getenv |
| `TestMainRouterFix` | User_Management 路由使用 /api/legacy/user 前缀 |
| `TestDockerComposeFix` | 前端 context 为 ./RagFrontend、Ollama 加入 apn-network、注入 DB/JWT 环境变量 |
| `TestHybridRetriever` | BM25 评分正确性、RRF 融合排序、结果包含 source 字段 |
| `TestKGNewAPIs` | 新增三个 KG API 路由注册正确 |
| `TestEnvExample` | .env.example 文件存在且包含所有必要键 |
| `TestDockerfiles` | 后端/前端 Dockerfile 存在且使用正确基础镜像 |

---

## 7. 变更文件汇总

| 文件 | 操作 | +行 | -行 |
|------|------|-----|-----|
| `RagBackend/.env.example` | 新增 | +24 | — |
| `RagBackend/Dockerfile` | 新增 | +60 | — |
| `RagBackend/requirements.txt` | 修改 | +40 | -28 |
| `RagBackend/main.py` | 修改 | +8 | -6 |
| `RagBackend/RAGF_User_Management/LogonAndLogin.py` | 修改 | +12 | -5 |
| `RagBackend/RAGF_User_Management/User_Management.py` | 修改 | +3 | -3 |
| `RagBackend/RAGF_User_Management/User_settings.py` | 修改 | +2 | -2 |
| `RagBackend/document_processing/doc_list.py` | 修改 | — | -46 |
| `RagBackend/RAG_M/src/rag/hybrid_retriever.py` | 新增 | +188 | — |
| `RagBackend/RAG_M/src/rag/rag_pipeline.py` | 重写 | +200 | -67 |
| `RagBackend/RAG_M/RAG_app.py` | 重写 | +180 | -234 |
| `RagBackend/knowledge_graph/generate_kg.py` | 修改 | +173 | — |
| `RagBackend/tests/test_all_fixes.py` | 新增 | +342 | — |
| `RagFrontend/Dockerfile` | 新增 | +34 | — |
| `RagFrontend/nginx.conf` | 新增 | +35 | — |
| `RagFrontend/src/components/graph-unit/graph-main.vue` | 重写 | +480 | -262 |
| `RagFrontend/src/utils/apiConfig.ts` | 修改 | +7 | -2 |
| `docker-compose.yml` | 重写 | +80 | -26 |

**合计：18 文件，+1846 行，-703 行**

---

## 8. 如何回滚

本次所有修改前已打安全 Tag，可随时一键回滚：

```bash
# 查看原始快照
git show v0-original

# 回滚到修改前状态（创建新分支）
git checkout -b rollback v0-original

# 或直接硬回滚（危险！会丢失本次所有 commit）
# git reset --hard v0-original
```

当前 commit 历史：
```
224803a  feat: lightweight packaging          ← 最新
c8c5fea  feat: bugfix + hybrid RAG + KG
7585671  no message                           ← 原始基线 (v0-original tag)
```

---

*报告由 AI 自动生成 · 2026-03-24*

- Agentic RAG 第一阶段：新增 RagBackend/agent_tools/knowledge_search_tool.py，将知识库检索封装为 Agent Tool；聊天接口 RAG 模式改为调用该工具，并保留原有 RAG 链路和前端兼容返回字段。

- Agentic RAG 第二阶段：新增 `RagBackend/agent_tools/deep_research_agent.py` 与 `/api/agent/deep-research` 调试接口，支持问题拆分、多次调用 KnowledgeSearchTool、来源去重和结构化研究结果返回；普通聊天 RAG 链路保持不变。

- 优化 DeepResearch 调试接口：针对“分别说明请假、迟到、报销”等问题按主题拆分子问题，并收紧 uncertainty 判断，减少证据充足时的误报。

- 优化 DeepResearch 输出文本：清洗“员工请假有什么规定相关规定”等展示层冗余后缀，普通 RAG 链路不变。
