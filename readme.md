# 企业知识库智能助手

一个面向企业内部知识管理场景的 RAG 智能问答系统。项目支持知识库创建、文档上传、向量化处理、知识库检索问答、来源引用展示和大模型调用，适合用于企业制度、流程规范、内部文档等资料的检索增强问答。

> 当前上传版本为项目初版，重点验证知识库管理、向量化、RAG 检索问答和引用来源展示等核心链路。默认模型使用本地 Ollama + `qwen2:0.5b`，主要用于低成本开发、课程实验和演示。后续会继续向企业级工程方向演进，支持更完善的多模型接入、权限控制、部署运维和安全治理。

## 项目亮点

- 企业知识库管理：支持创建知识库、上传文档、查看向量化状态。
- RAG 智能问答：聊天页可开启知识库问答，按所选知识库执行检索增强生成。
- 来源可追溯：回答可展示引用来源、文件名和内容片段，便于核对依据。
- 本地演示友好：默认使用 Ollama 本地模型 `qwen2:0.5b`，适合低配置机器开发和演示。
- 向量化状态可见：知识库列表和聊天页都会提示是否已完成向量化。
- 企业化界面：登录页、知识库页、聊天页已围绕“企业知识库智能助手”进行整理。
- 防幻觉约束：针对制度类问答增加上下文裁剪和抽取式回答保护，减少无关条款混入。

## 技术栈

| 模块 | 技术 |
| --- | --- |
| 前端 | Vue 3, TypeScript, Vite, TDesign Vue Next |
| 后端 | FastAPI, Python |
| 数据库 | MySQL |
| 向量检索 | FAISS |
| RAG | LangChain / Native RAG 兼容链路 |
| 默认演示模型 | Ollama, `qwen2:0.5b` |
| 企业模型扩展 | 可扩展云端模型 API 或企业内网模型服务 |
| 部署辅助 | Docker Compose |

## 模型使用说明

当前初版默认使用本地 Ollama 模型，原因是部署门槛低、成本低、适合在个人电脑上验证完整链路。

真实企业使用时，建议按实际安全与成本要求选择模型方案：

- 本地开发 / 课程演示：使用 Ollama + `qwen2:0.5b`。
- 中小团队试用：接入云端模型 API，例如 DeepSeek、OpenAI、通义千问、智谱、腾讯混元等。
- 高安全企业场景：接入企业内网私有化模型服务，后端通过统一模型路由调用。

本项目会保留本地模型作为默认开发配置，同时继续演进多模型适配能力。

## 核心功能

### 1. 用户登录与企业入口

- 支持账号注册、登录。
- 登录页已清理第三方 QQ / 微信入口，更贴近企业内部系统。
- 后端用户资料表兼容个人中心展示字段。

### 2. 知识库管理

- 新建企业知识库。
- 上传本地文档。
- 执行向量化处理。
- 查看知识库是否已完成向量化。
- 向量化完成后可直接进入智能问答。

### 3. RAG 智能问答

- 聊天页支持普通聊天和知识库问答模式。
- 知识库问答模式下可选择目标知识库和检索策略。
- 后端根据 `kb_id` 自动加载对应向量库。
- 回答支持来源引用展示。
- 当知识库没有提供答案时，尽量拒绝编造。

### 4. 演示测试能力

推荐使用“员工制度测试库”进行演示：

- 直接答案问题：`员工迟到会怎么处理？`
- 部分相关问题：`员工请病假有什么要求？`
- 无答案问题：`年终奖怎么算？`

预期效果：

- 有答案时基于文档条款回答。
- 回答展示引用来源。
- 没有明确规定时提示知识库未提供相关内容。

## 项目结构

```text
KnowledgeRAG-GZHU-master/
├── RagBackend/                 # FastAPI 后端
│   ├── chat_units/             # 聊天接口与会话管理
│   ├── document_processing/    # 文档处理与向量化
│   ├── RAG_M/                  # RAG 检索与生成逻辑
│   ├── local-KLB-files/        # 本地知识库文件目录，建议不要上传到 GitHub
│   ├── knowledge_base/         # 向量库目录，建议不要上传到 GitHub
│   └── main.py                 # 后端入口
├── RagFrontend/                # Vue 前端
│   ├── src/views/Chat.vue      # 智能问答页
│   ├── src/views/KnowledgePages/
│   └── src/components/
├── docker-compose.yml          # Docker Compose 编排
├── dev.ps1                     # Windows 本地开发启动脚本
├── RUNBOOK.md                  # VSCode 终端启动说明
├── PROJECT_BRIEF.md            # 当前项目进度摘要
├── PAGE_MAP.md                 # 页面与功能映射
├── DATA_MAP.md                 # 数据与接口映射
└── CHANGELOG.md                # 修改记录
```

## 本地启动

详细启动说明见 [RUNBOOK.md](./RUNBOOK.md)。

### 前置要求

- Node.js
- Python
- Docker Desktop
- Ollama

### 1. 准备本地模型

```powershell
ollama pull qwen2:0.5b
ollama list
```

### 2. 一键开发启动

在 VSCode 终端中执行：

```powershell
cd E:\University\agent\program\KnowledgeRAG-GZHU-master
powershell -ExecutionPolicy Bypass -File .\dev.ps1
```

启动后访问：

- 前端：http://localhost:5173
- 后端 API 文档：http://localhost:8000/docs

### 3. 手动启动方式

启动 MySQL：

```powershell
cd E:\University\agent\program\KnowledgeRAG-GZHU-master
docker compose up -d mysql
```

启动后端：

```powershell
cd E:\University\agent\program\KnowledgeRAG-GZHU-master\RagBackend
python -m uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

启动前端：

```powershell
cd E:\University\agent\program\KnowledgeRAG-GZHU-master\RagFrontend
npm run dev
```

检查 Ollama：

```powershell
ollama list
```

## 使用流程

1. 启动 MySQL、后端、前端和 Ollama。
2. 打开 `http://localhost:5173`。
3. 注册或登录账号。
4. 创建知识库，例如“员工制度测试库”。
5. 上传制度文档。
6. 点击“立即向量化”或“执行向量化处理”。
7. 点击知识库详情页顶部“去智能问答”。
8. 在聊天页确认知识库问答已开启，并选中了目标知识库。
9. 输入问题，查看回答和引用来源。

## 环境变量与敏感信息

不要把真实密钥提交到 GitHub。

建议使用：

```text
RagBackend/.env
```

并将示例配置保存在：

```text
RagBackend/.env.example
```

常见变量：

```text
DB_HOST=localhost
DB_PORT=3306
DB_USER=root
DB_PASSWORD=your_password
DB_NAME=rag_user_db
JWT_SECRET=your_jwt_secret
MODEL=qwen2:0.5b
DEEPSEEK_API_KEY=
OPENAI_API_KEY=
```

## 上传到 GitHub 前检查

建议执行：

```powershell
git status
```

确认不要提交以下内容：

- `RagBackend/.env`
- `node_modules/`
- `dist/`
- 本地知识库文件
- 本地向量库
- 数据库文件
- 日志和缓存文件

## GitHub 上传步骤

在 GitHub 新建一个空仓库，例如：

```text
Enterprise-Knowledge-RAG-Assistant
```

然后在本地执行：

```powershell
cd E:\University\agent\program\KnowledgeRAG-GZHU-master
git init
git add .
git commit -m "Initial commit"
git branch -M main
git remote add origin https://github.com/你的用户名/Enterprise-Knowledge-RAG-Assistant.git
git push -u origin main
```

如果仓库已经初始化过，只需要设置远程仓库并推送：

```powershell
git remote add origin https://github.com/你的用户名/Enterprise-Knowledge-RAG-Assistant.git
git branch -M main
git push -u origin main
```

## 当前状态

- 后端 FastAPI 可运行。
- 前端 Vite 可运行并已通过生产构建验证。
- MySQL Docker 可用。
- Ollama + `qwen2:0.5b` 可用于本地开发与演示问答。
- 知识库向量化与聊天页 RAG 问答链路已验证。
- 引用来源展示与无答案拒答能力已做基础优化。

## 后续优化方向

- 补充更完整的演示截图或 GIF。
- 增加自动化测试覆盖 RAG 关键链路。
- 优化大文档分块策略和来源预览体验。
- 完善多模型路由，支持云端 API 与企业内网模型服务切换。
- 增加更完善的权限管理和企业成员协作功能。
- 增强企业级部署能力，包括配置管理、日志、监控、权限和安全审计。
- 清理历史测试数据，保留标准演示知识库。

## 说明

本项目当前版本主要用于企业知识库智能问答系统的学习、实验和初版演示。上传公开 GitHub 前，请务必确认敏感配置、私有文档和本地向量库没有被提交。
