FROM python:3.11-slim AS backend

RUN apt-get update && apt-get install -y --no-install-recommends ffmpeg curl && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY src/ src/
# Never bake the developer's config.yaml (which may contain secrets) into the image.
COPY config.yaml.example ./config.yaml

RUN mkdir -p data/db data/uploads data/output data/temp

RUN useradd --create-home --shell /usr/sbin/nologin app \
    && chown -R app:app /app
USER app

EXPOSE 8000
CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8000"]
