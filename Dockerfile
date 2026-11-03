FROM python:3.11-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    HF_ENDPOINT=https://hf-mirror.com \
    OMP_NUM_THREADS=1 \
    TOKENIZERS_PARALLELISM=false

# ffmpeg: 音视频处理
# libpango/libcairo/libgdk-pixbuf: weasyprint 渲染 PDF
# fonts-noto-cjk: 中文 PDF 不出方块
RUN apt-get update && apt-get install -y --no-install-recommends \
        ffmpeg \
        curl \
        libpango-1.0-0 \
        libpangoft2-1.0-0 \
        libharfbuzz-subset0 \
        libcairo2 \
        libgdk-pixbuf-2.0-0 \
        libglib2.0-0 \
        libffi8 \
        shared-mime-info \
        fonts-noto-cjk \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# 先装 CPU-only torch：否则 sentence-transformers 会拉 CUDA 版 torch(约 2.5GB)，
# 2C2G 机器上既费磁盘也容易构建 OOM。
RUN pip install --index-url https://download.pytorch.org/whl/cpu torch

COPY requirements.txt .
RUN pip install -r requirements.txt

COPY src/ src/
COPY config.yaml .

RUN mkdir -p data/db data/uploads data/output data/temp

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=60s --retries=3 \
    CMD curl -fsS http://127.0.0.1:8000/api/health || exit 1

CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8000", "--proxy-headers", "--forwarded-allow-ips", "*"]
