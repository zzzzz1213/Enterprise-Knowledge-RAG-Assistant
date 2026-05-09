# RUNBOOK

本文件记录「企业知识库智能助手」日常实验启动流程，适合在 VSCode 终端中直接执行。

## 每次实验要启动什么

必须启动：

- MySQL：保存用户、登录态、知识库元数据。
- 后端 FastAPI：提供登录、知识库、向量化、聊天接口。
- 前端 Vite：打开浏览器页面。
- Ollama：提供本地大模型 `qwen2:0.5b`。

推荐访问地址：

- 前端：http://localhost:5173
- 后端文档：http://localhost:8000/docs
- Ollama 本地服务：http://localhost:11434

## 方式一：推荐一键启动

在 VSCode 打开项目根目录：

```powershell
cd E:\University\agent\program\KnowledgeRAG-GZHU-master
```

启动 MySQL、后端和前端：

```powershell
powershell -ExecutionPolicy Bypass -File .\dev.ps1
```

查看状态：

```powershell
powershell -ExecutionPolicy Bypass -File .\dev.ps1 -Status
```

停止本地前后端：

```powershell
powershell -ExecutionPolicy Bypass -File .\dev.ps1 -Stop
```

注意：`dev.ps1 -Stop` 只停止前端和后端，不会停止 Docker 里的 MySQL。

## Ollama 启动与模型检查

如果你是 Windows 本机安装的 Ollama，通常打开 Ollama 应用后后台服务会自动运行。

检查 Ollama 是否可用：

```powershell
ollama list
```

如果没有 `qwen2:0.5b`，先拉取：

```powershell
ollama pull qwen2:0.5b
```

如果聊天时报 Ollama 连接失败，确认本机 `11434` 端口可用，或重新打开 Ollama 应用。

## 方式二：四个 VSCode 终端手动启动

如果你想看每个服务的日志，可以手动开 4 个终端。

### 终端 1：MySQL

```powershell
cd E:\University\agent\program\KnowledgeRAG-GZHU-master
docker compose up -d mysql
```

检查 MySQL 容器：

```powershell
docker compose ps mysql
```

### 终端 2：后端

```powershell
cd E:\University\agent\program\KnowledgeRAG-GZHU-master\RagBackend
python -m uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

启动后打开：

```text
http://localhost:8000/docs
```

### 终端 3：前端

```powershell
cd E:\University\agent\program\KnowledgeRAG-GZHU-master\RagFrontend
npm run dev
```

启动后打开：

```text
http://localhost:5173
```

### 终端 4：Ollama 检查

```powershell
ollama list
```

需要拉模型时执行：

```powershell
ollama pull qwen2:0.5b
```

## 启动后快速自检

按这个顺序检查：

1. 浏览器打开 `http://localhost:8000/docs`，能看到 FastAPI 文档。
2. 浏览器打开 `http://localhost:5173`，能看到前端登录页。
3. 登录成功后进入知识库页面。
4. 进入测试知识库，确认顶部能看到“去智能问答”。
5. 智能问答页开启知识库问答后，确认已选中目标知识库且状态为“已就绪”。
6. 提问 `员工迟到会怎么处理？`，确认回答引用知识库来源。

## 常见问题

### 前端控制台出现 ECONNREFUSED

通常是后端没启动，或后端不是 `8000` 端口。先检查：

```powershell
http://localhost:8000/docs
```

### 聊天提示 Ollama 连接失败

先执行：

```powershell
ollama list
```

如果命令失败，重新启动 Ollama 应用。

### 聊天页提示知识库未向量化

进入知识库详情页，先上传文档，再点击“立即向量化”或“执行向量化处理”。完成后点击顶部“去智能问答”。

### 端口被占用

常用端口：

- 前端：`5173`
- 后端：`8000`
- Ollama：`11434`
- Docker MySQL：项目 compose 中映射为 `3307:3306`，`dev.ps1` 会检查容器 `ragf-mysql`

如果前端 5173 被占用，Vite 可能自动切换到 5174，请以终端输出的 Local 地址为准。

