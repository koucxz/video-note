# 🎬 VideoNote - 智能视频笔记生成器

将视频内容自动转化为结构化笔记的工具。

## ✨ 特性

- 🤖 **AI 驱动**: 使用云端 AI API（OpenAI GPT-4o + Whisper）
- 🔄 **断点续传**: 支持长视频处理中断后恢复
- 📁 **文件去重**: 基于内容 hash 自动去重
- 📝 **结构化输出**: 生成 Markdown 格式笔记
- ⚙️ **可配置**: 支持多种 AI 提供商

## 📋 前置要求

- Python 3.10+
- Node.js 18+
- FFmpeg（用于音视频处理）
- OpenAI API Key

## 🚀 快速开始

### 1. 安装后端依赖

```bash
cd D:/code/video-note
pip install -r requirements.txt
```

### 2. 配置环境变量

复制 `.env.example` 为 `.env` 并填入 API Key：

```bash
cp .env.example .env
# 编辑 .env 文件，填入 OPENAI_API_KEY
```

### 3. 启动后端服务

```bash
python -m uvicorn src.main:app --host 0.0.0.0 --port 8000 --reload
```

### 4. 安装并启动前端

```bash
cd frontend
npm install
npm run dev
```

前端将在 http://localhost:3000 启动。

## 📁 项目结构

```
video-note/
├── src/
│   ├── core/           # 核心引擎
│   │   ├── engine.py   # 主处理引擎
│   │   ├── checkpoint.py # 断点续传
│   │   └── dedup.py    # 文件去重
│   ├── services/       # 服务层
│   │   ├── ai_service.py  # AI 模型调用
│   │   ├── audio_service.py # 音频处理
│   │   └── video_service.py # 视频处理
│   ├── api/            # API 路由
│   ├── models/         # 数据模型
│   └── config/         # 配置
├── frontend/           # React 前端
├── data/               # 数据目录
│   ├── db/             # 数据库
│   ├── uploads/        # 上传文件
│   └── output/         # 输出笔记
├── config.yaml         # 配置文件
└── requirements.txt    # Python 依赖
```

## 🔧 配置说明

编辑 `config.yaml` 自定义配置：

```yaml
provider:
  type: "openai"
  api_key: "your-api-key"
  model: "gpt-4o"
  base_url: "https://api.openai.com/v1"

processing:
  keyframe_interval: 30  # 关键帧提取间隔（秒）
  max_retries: 3         # 失败重试次数
```

## 📖 API 文档

启动后端后访问 http://localhost:8000/docs 查看 API 文档。

### 主要接口

- `POST /api/upload` - 上传视频
- `GET /api/task/{id}/status` - 获取任务状态
- `POST /api/task/{id}/retry` - 重试失败任务
- `GET /api/history` - 获取历史记录
- `GET /api/note/{id}` - 下载笔记

## 🐳 Docker 部署（可选）

```bash
docker build -t videonote .
docker run -p 8000:8000 -e OPENAI_API_KEY=your-key videonote
```

## 📄 许可证

MIT License
