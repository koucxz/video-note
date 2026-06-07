# VideoNote - Smart Video Notes Generator

Convert videos into structured notes using cloud AI (no local models needed).

## Features

- **No Local AI Models**: Uses cloud APIs exclusively (LLM + VLM). No GPU, no Whisper dependency.
- **ASR Optional**: If your provider lacks Whisper-compatible audio transcription, the engine falls back to pure VLM keyframe analysis.
- **Streaming Upload**: Large files (500MB+) upload without consuming memory.
- **File Deduplication**: Same video uploaded twice won't create duplicate files or tasks.
- **Checkpoint Resume**: If processing is interrupted (service restart, network issue), click "Retry" to resume from the last completed stage.
- **Concurrency Control**: Configurable limit on simultaneous video processing tasks.
- **5 Note Styles**: Standard, Summary, Action Checklist, Academic, Creative.
- **Bilingual**: Chinese and English UI and output.
- **Docker Ready**: One-command deployment with docker-compose.

## Quick Start

### Prerequisites

- Python 3.10+
- Node.js 18+
- FFmpeg (must be on PATH)
- API key for an OpenAI-compatible provider (e.g., OpenAI, DeepSeek)

### 1. Configure API Keys

```bash
cp .env.example .env
# Edit .env with your actual API key and base URL
```

### 2. Start Backend

```bash
pip install -r requirements.txt
python -m uvicorn src.main:app --host 0.0.0.0 --port 8000
```

### 3. Start Frontend

```bash
cd frontend
npm install
npm run dev
```

Frontend runs at http://localhost:3000. API docs at http://localhost:8000/docs.

## Docker Deployment

```bash
# Create .env first (see above)
docker compose up -d
```

Access the app at http://localhost:3000 (frontend via nginx) or http://localhost:8000 (API).

## Configuration

All secrets live in `.env` (git-ignored). `config.yaml` uses `${ENV_VAR}` placeholders:

| Variable | Description | Default |
|---|---|---|
| `LLM_API_KEY` | API key for text LLM | - |
| `LLM_BASE_URL` | LLM endpoint | `https://api.openai.com/v1` |
| `LLM_MODEL` | LLM model name | `gpt-4o-mini` |
| `VLM_API_KEY` | API key for vision model | Falls back to LLM key |
| `VLM_BASE_URL` | VLM endpoint | Falls back to LLM URL |
| `VLM_MODEL` | VLM model name | Falls back to LLM model |
| `ASR_ENABLED` | Enable Whisper transcription | `false` |
| `ASR_MODEL` | Whisper model name | `whisper-1` |
| `MAX_CONCURRENT_TASKS` | Max parallel video processing | `2` |

## API Endpoints

| Method | Path | Description |
|---|---|---|
| `POST` | `/api/upload` | Upload video (streaming, dedup) |
| `GET` | `/api/task/{id}/status` | Task status with error_kind |
| `POST` | `/api/task/{id}/retry` | Retry failed task |
| `DELETE` | `/api/task/{id}` | Delete task |
| `GET` | `/api/history` | All tasks (showing original filenames) |
| `GET` | `/api/note/{id}/content` | Get note content as JSON |
| `GET` | `/api/note/{id}` | Download note as .md file |
| `POST` | `/api/notes/download-zip` | Batch download notes as ZIP |
| `GET` | `/api/health` | Health check with ASR/model info |

## Architecture

```
src/
  core/
    engine.py       # Main pipeline with semaphore + task handles
    checkpoint.py   # SQLite + WAL + threading.Lock
    dedup.py        # Streaming SHA-256 hash
  services/
    ai_service.py   # LLM + VLM + optional ASR (OpenAI-compatible)
    audio_service.py # FFmpeg audio extraction
    video_service.py # FFmpeg keyframe extraction
  api/
    upload.py       # Streaming upload, dedup + instant return
    task.py         # Task status with error classification
    note.py         # Note retrieval + batch ZIP
  config/
    settings.py     # YAML + env var + .env loader
  models/
    task.py         # Task/Status/Stage enums + dataclass
```

## Development

```bash
# Install test dependencies
pip install pytest pytest-asyncio httpx

# Run tests
pytest tests/ -v
```

## Error Classification

When processing fails, the error is classified into categories shown to the user:

- **network**: Connection timeout, DNS failure, SSL error
- **api**: API key invalid, rate limited, server error
- **ffmpeg**: Video/audio processing failure
- **format**: Unsupported file format
- **interrupted**: Service was restarted during processing
