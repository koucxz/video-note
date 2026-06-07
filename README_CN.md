<div align="center">
  <h1>VideoNote</h1>
  <p><i>AI 视频笔记生成器 —— 上传视频，自动生成结构化 Markdown 笔记</i></p>

  <p>
    <img src="https://img.shields.io/badge/license-MIT-blue.svg" alt="license" />
    <img src="https://img.shields.io/badge/frontend-React%2019-blue" alt="frontend" />
    <img src="https://img.shields.io/badge/backend-FastAPI-green" alt="backend" />
    <img src="https://img.shields.io/badge/AI-OpenAI%20%7C%20Anthropic%20%7C%20%E5%85%BC%E5%AE%B9-orange" alt="ai" />
    <img src="https://img.shields.io/badge/Docker-ready-success" alt="docker" />
  </p>
</div>

---

## 项目简介

**VideoNote** 是一个开源的 AI 视频笔记工具：上传本地视频文件，自动完成「音频提取 → 关键帧抽取 → VLM 视觉分析 → LLM 笔记生成」，输出结构清晰、可导出的 Markdown 笔记。

- 支持 OpenAI 兼容协议和 Anthropic (Claude) 协议，可自由切换模型供应商
- 文件内容去重，相同视频不会重复处理
- 断点续传，长视频处理中断后可从断点恢复
- 任务并发控制，支持同时处理多个视频
- 五种笔记风格：标准、精简、行动清单、学术、创意

## 功能特性

| 模块 | 说明 |
| --- | --- |
| **智能笔记生成** | 基于 VLM（视觉模型）分析关键帧 + LLM 生成结构化笔记，支持中/英双语输出 |
| **多种笔记风格** | 标准笔记、精简摘要、行动清单、学术笔记、创意笔记，上传时可选 |
| **音频转写（可选）** | 支持 ASR 语音转文字（如 Whisper），也可跳过 ASR 直接用视觉分析 |
| **文件去重** | 基于 SHA-256 内容哈希，相同视频秒级返回已有结果 |
| **断点续传** | 处理流程分阶段保存进度，中断后重试从最后成功的阶段继续 |
| **并发控制** | 可配置最大并发任务数（1-5），前端滑块实时调整 |
| **高级处理选项** | 关键帧间隔、分段时长、并发数均可在上传页配置 |
| **历史记录** | 分页展示所有任务，支持搜索、重试、删除 |
| **笔记导出** | 单个下载 MD / PDF，批量打包 ZIP |
| **存储管理** | 查看上传文件列表、绝对路径、占用空间，支持清理 |
| **模型配置** | 在线切换 LLM / VLM / ASR 模型，支持 OpenAI 和 Anthropic 协议 |
| **实时进度** | WebSocket 推送处理进度，无需轮询 |
| **多语言界面** | 中英文一键切换 |

## 快速开始

### 方式一：Docker 部署（推荐）

```bash
git clone https://github.com/xiaokeaijqx/VideoNote.git
cd VideoNote
cp .env.example .env
# 编辑 .env 填入 API Key

docker compose up --build -d
```

- 前端：http://localhost:3000
- 后端 API：http://localhost:8000/api/docs

### 方式二：源码部署

```bash
# 1. 克隆仓库
git clone https://github.com/xiaokeaijqx/VideoNote.git
cd VideoNote
cp .env.example .env

# 2. 启动后端（Python 3.11+）
pip install -r requirements.txt
python -m uvicorn src.main:app --host 0.0.0.0 --port 8000

# 3. 启动前端（Node.js 18+）
cd frontend
npm install
npm run dev    # 开发服务器 http://localhost:3000
```

## 使用流程

1. **配置模型** —— 进入 设置 → 模型配置，填写 LLM / VLM 的 API Key 和模型名称。支持 OpenAI 兼容接口（DeepSeek、Moonshot、本地模型等）和 Anthropic Claude。
2. **上传视频** —— 在首页拖拽或点击上传视频文件（支持 mp4、avi、mov、mkv 等格式），选择输出语言和笔记风格。
3. **调整参数（可选）** —— 展开「高级选项」，可调整关键帧间隔、分段时长、并发数。
4. **等待生成** —— 实时查看处理进度：音频提取 → 关键帧 → 视觉分析 → 笔记生成。
5. **查看笔记** —— 生成完成后自动跳转笔记详情页，支持 Markdown 渲染、复制、下载 MD / PDF。

## 项目结构

```
video-note/
├── src/
│   ├── core/              # 核心引擎
│   │   ├── engine.py      # 主处理引擎（断点续传、并发控制）
│   │   ├── checkpoint.py  # 进度检查点（SQLite）
│   │   └── dedup.py       # 文件去重
│   ├── services/          # 服务层
│   │   ├── ai_service.py  # AI 模型调用（OpenAI + Anthropic）
│   │   ├── audio_service.py
│   │   └── video_service.py
│   ├── api/               # API 路由
│   ├── models/            # 数据模型
│   ├── config/            # 配置管理
│   └── utils/             # 工具函数
├── frontend/              # React 前端
│   ├── src/
│   │   ├── pages/         # 页面（上传、历史、笔记、设置）
│   │   ├── components/    # 组件（Header、Toast、StageProgress）
│   │   ├── context/       # 上下文（语言、Toast）
│   │   └── api/           # API 客户端
│   └── nginx.conf         # Docker nginx 配置
├── tests/                 # 测试
├── data/                  # 数据目录（DB、上传、输出）
├── config.yaml            # 主配置文件
├── Dockerfile             # 后端镜像
├── docker-compose.yml     # 编排配置
└── requirements.txt       # Python 依赖
```

## 配置说明

### 环境变量（.env）

```bash
# LLM 模型（文本生成）
LLM_API_KEY=your-api-key
LLM_MODEL=gpt-5.5
LLM_BASE_URL=https://api.openai.com/v1

# VLM 模型（视觉分析）
VLM_API_KEY=your-api-key
VLM_MODEL=gpt-5.5
VLM_BASE_URL=https://api.openai.com/v1

# ASR 语音识别（可选）
ASR_ENABLED=false
ASR_API_KEY=your-api-key
ASR_MODEL=whisper-1

# 并发控制
MAX_CONCURRENT_TASKS=2
```

### Anthropic Claude 配置

在设置 → 模型配置页面，将协议切换为 `Anthropic (Claude)`，填入：

- **Base URL**：`https://api.anthropic.com`
- **Model**：`claude-sonnet-4-20250514`
- **API Key**：你的 Anthropic API Key

> 注意：Anthropic 不支持音频转写，ASR 功能会自动跳过。

## 技术栈

| 层 | 技术 |
| --- | --- |
| **后端** | Python 3.11+ · FastAPI · SQLite · FFmpeg · OpenAI SDK · Anthropic SDK |
| **前端** | React 19 · Vite · Lucide Icons · axios |
| **部署** | Docker / docker-compose · Nginx（WebSocket 代理） |
| **AI** | OpenAI 兼容协议 · Anthropic Claude · VLM 视觉分析 · 可选 ASR |

## 依赖说明

### FFmpeg

必须安装（Docker 镜像已内置）：

```bash
# macOS
brew install ffmpeg

# Ubuntu / Debian
sudo apt install ffmpeg

# Windows：从 https://ffmpeg.org/download.html 下载并加入 PATH
```

## Docker 部署 FAQ

**1. 容器启动后前端无法访问后端**
- 确认 nginx.conf 中 WebSocket 代理配置正确（`/ws/` 路径需要升级连接）
- 检查 `docker compose logs backend` 查看后端启动日志

**2. 大文件上传失败**
- nginx 默认限制 1MB，项目已配置为 2048MB
- 如仍失败，检查 Docker 网络或磁盘空间

**3. 处理中断后如何恢复**
- 点击任务的「重试」按钮，会从最后成功的阶段继续
- 中断原因会显示在任务详情中（网络错误 / API 错误 / FFmpeg 错误）

**4. 数据存储位置**
- 上传视频：`data/uploads/`（按内容哈希命名，避免重复）
- 生成笔记：`data/output/`
- 数据库：`data/db/videonote.db`

## License

本项目遵循 [MIT License](./LICENSE)。

---

欢迎 Issue、PR、Star ⭐️