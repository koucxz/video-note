"""Vector embedding and search service for RAG.
Supports Milvus (production) with numpy fallback (local dev).
Uses sentence-transformers for embeddings."""
import logging
import json
import os
import re
import threading
import numpy as np
from pathlib import Path
from typing import List, Dict, Optional

logger = logging.getLogger(__name__)

CHUNK_SIZE = 500
CHUNK_OVERLAP = 50

class VectorService:
    """Vector index with SiliconFlow/OpenAI embeddings and local fallback."""

    def __init__(self, index_dir: str = "./data/db/vector"):
        self.index_dir = Path(index_dir)
        self.index_dir.mkdir(parents=True, exist_ok=True)
        self._model = None
        self._embedding_client = None
        self._lock = threading.Lock()
        self._milvus = None
        self._milvus_ready = False

        # Read these lazily because .env is loaded by the application config
        # before the engine is instantiated, not necessarily before imports.
        self.embedding_provider = os.getenv(
            "EMBEDDING_PROVIDER",
            "siliconflow" if os.getenv("SILICONFLOW_API_KEY") or os.getenv("EMBEDDING_API_KEY") else "local",
        ).strip().lower()
        self.embedding_api_key = os.getenv("SILICONFLOW_API_KEY") or os.getenv("EMBEDDING_API_KEY", "")
        self.embedding_base_url = os.getenv("EMBEDDING_BASE_URL", "https://api.siliconflow.cn/v1")
        self.embedding_model = os.getenv(
            "EMBEDDING_MODEL",
            "BAAI/bge-m3" if self.embedding_provider in {"siliconflow", "openai"} else "all-MiniLM-L6-v2",
        )
        default_dimension = 1024 if self.embedding_model.lower() == "baai/bge-m3" else 384
        try:
            self.embedding_dimension = int(os.getenv("EMBEDDING_DIMENSION", str(default_dimension)))
        except ValueError:
            self.embedding_dimension = default_dimension
        self._local_fallback = os.getenv("EMBEDDING_FALLBACK_LOCAL", "true").lower() in {"1", "true", "yes", "on"}
        self._milvus_uri = os.getenv("MILVUS_URI", "")
        model_tag = re.sub(r"[^a-z0-9]+", "_", self.embedding_model.lower()).strip("_")
        self.collection_name = os.getenv(
            "MILVUS_COLLECTION",
            f"videonote_chunks_{model_tag}_{self.embedding_dimension}",
        )

        # Numpy fallback state
        self._index: Dict[str, List[dict]] = {}
        self._embeddings_matrix = None
        self._chunk_meta: List[dict] = []
        self._loaded = False

        # Try connecting to Milvus
        self._init_milvus()

    def _init_milvus(self):
        if not self._milvus_uri:
            logger.info("No MILVUS_URI set, using numpy vector search")
            return
        try:
            from pymilvus import MilvusClient
            self._milvus = MilvusClient(uri=self._milvus_uri)
            # Create collection if not exists
            if not self._milvus.has_collection(self.collection_name):
                self._milvus.create_collection(
                    collection_name=self.collection_name,
                    dimension=self.embedding_dimension,
                    metric_type="COSINE",
                    auto_id=True,
                )
                logger.info("Created Milvus collection: %s", self.collection_name)
            self._milvus_ready = True
            logger.info("Milvus connected at %s", self._milvus_uri)
        except Exception as exc:
            logger.warning("Milvus unavailable (%s), falling back to numpy", exc)
            self._milvus = None
            self._milvus_ready = False

    def _get_model(self):
        if self._model is None:
            from sentence_transformers import SentenceTransformer
            model_name = "all-MiniLM-L6-v2"
            logger.info("Loading embedding model: %s", model_name)
            self._model = SentenceTransformer(model_name)
        return self._model

    def _get_embeddings(self, texts: List[str]):
        """Encode text with the configured remote API or local fallback."""
        if self.embedding_provider in {"siliconflow", "openai"} and self.embedding_api_key:
            try:
                from openai import OpenAI
                if self._embedding_client is None:
                    self._embedding_client = OpenAI(
                        api_key=self.embedding_api_key,
                        base_url=self.embedding_base_url,
                    )
                vectors = []
                # Keep request payloads bounded for hosted embedding services.
                for start in range(0, len(texts), 32):
                    batch = texts[start:start + 32]
                    response = self._embedding_client.embeddings.create(
                        model=self.embedding_model,
                        input=batch,
                        encoding_format="float",
                    )
                    vectors.extend(item.embedding for item in sorted(response.data, key=lambda item: item.index))
                matrix = np.asarray(vectors, dtype=np.float32)
                if matrix.ndim != 2 or matrix.shape[1] != self.embedding_dimension:
                    raise ValueError(
                        f"Embedding dimension mismatch: expected {self.embedding_dimension}, got {matrix.shape}"
                    )
                norms = np.linalg.norm(matrix, axis=1, keepdims=True)
                return matrix / np.maximum(norms, 1e-12)
            except Exception as exc:
                if not self._local_fallback or self.embedding_dimension != 384:
                    raise
                logger.warning("Embedding API failed (%s), using local fallback", exc)

        model = self._get_model()
        matrix = np.asarray(model.encode(texts, show_progress_bar=False, normalize_embeddings=True), dtype=np.float32)
        if matrix.ndim != 2 or matrix.shape[1] != self.embedding_dimension:
            raise ValueError(f"Local embedding dimension mismatch: expected {self.embedding_dimension}, got {matrix.shape}")
        return matrix

    def _split_text(self, text: str) -> List[str]:
        chunks = []
        paragraphs = text.split("\n\n")
        current = ""
        for para in paragraphs:
            if len(current) + len(para) > CHUNK_SIZE:
                if current:
                    chunks.append(current.strip())
                current = para
            else:
                current = (current + "\n\n" + para) if current else para
        if current.strip():
            chunks.append(current.strip())
        result = []
        for chunk in chunks:
            if len(chunk) > CHUNK_SIZE * 2:
                for i in range(0, len(chunk), CHUNK_SIZE - CHUNK_OVERLAP):
                    result.append(chunk[i:i + CHUNK_SIZE])
            else:
                result.append(chunk)
        return [c for c in result if len(c) > 20]

    def index_note(self, task_id: str, content: str) -> int:
        chunks = self._split_text(content)
        if not chunks:
            return 0
        embeddings = self._get_embeddings(chunks)

        if self._milvus_ready:
            return self._index_milvus(task_id, chunks, embeddings)
        else:
            return self._index_numpy(task_id, chunks, embeddings)

    def _index_milvus(self, task_id: str, chunks: List[str], embeddings) -> int:
        try:
            # Delete old entries for this task
            self._milvus.delete(
                collection_name=self.collection_name,
                filter=f'task_id == "{task_id}"',
            )
            # Insert new
            data = [
                {"task_id": task_id, "chunk_idx": i, "text": chunk, "embedding": emb.tolist()}
                for i, (chunk, emb) in enumerate(zip(chunks, embeddings))
            ]
            self._milvus.insert(collection_name=self.collection_name, data=data)
            logger.info("Milvus indexed %d chunks for task %s", len(chunks), task_id[:8])
            return len(chunks)
        except Exception as exc:
            logger.error("Milvus index failed: %s, falling back to numpy", exc)
            return self._index_numpy(task_id, chunks, embeddings)

    def _index_numpy(self, task_id: str, chunks: List[str], embeddings) -> int:
        with self._lock:
            self._index[task_id] = []
            for i, (chunk, emb) in enumerate(zip(chunks, embeddings)):
                self._index[task_id].append({
                    "id": f"{task_id}_{i}",
                    "text": chunk,
                    "embedding": emb,
                })
            self._rebuild_matrix()
            self._save_index()
        logger.info("Numpy indexed %d chunks for task %s", len(chunks), task_id[:8])
        return len(chunks)

    def remove_note(self, task_id: str):
        if self._milvus_ready:
            try:
                self._milvus.delete(
                    collection_name=self.collection_name,
                    filter=f'task_id == "{task_id}"',
                )
            except Exception:
                pass
        with self._lock:
            self._index.pop(task_id, None)
            self._rebuild_matrix()
            self._save_index()

    def search(self, query: str, top_k: int = 5, task_ids: Optional[List[str]] = None) -> List[dict]:
        if self._milvus_ready:
            return self._search_milvus(query, top_k, task_ids)
        return self._search_numpy(query, top_k, task_ids)

    def _search_milvus(self, query: str, top_k: int, task_ids: Optional[List[str]]) -> List[dict]:
        query_emb = self._get_embeddings([query])[0].tolist()
        try:
            filter_expr = ""
            if task_ids:
                ids_str = ", ".join(f'"{tid}"' for tid in task_ids)
                filter_expr = f"task_id in [{ids_str}]"
            results = self._milvus.search(
                collection_name=self.collection_name,
                data=[query_emb],
                limit=top_k,
                output_fields=["task_id", "chunk_idx", "text"],
                filter=filter_expr or None,
            )
            out = []
            for hit in results[0]:
                entity = hit.get("entity", {})
                out.append({
                    "task_id": entity.get("task_id", ""),
                    "chunk_id": f'{entity.get("task_id", "")}_{entity.get("chunk_idx", 0)}',
                    "text": entity.get("text", ""),
                    "score": hit.get("distance", 0.0),
                })
            return out
        except Exception as exc:
            logger.error("Milvus search failed: %s, falling back to numpy", exc)
            return self._search_numpy(query, top_k, task_ids)

    def _search_numpy(self, query: str, top_k: int, task_ids: Optional[List[str]]) -> List[dict]:
        with self._lock:
            if not self._chunk_meta or self._embeddings_matrix is None:
                return []
        query_emb = self._get_embeddings([query])[0]
        with self._lock:
            scores = np.dot(self._embeddings_matrix, query_emb)
            if task_ids:
                task_set = set(task_ids)
                for i, meta in enumerate(self._chunk_meta):
                    if meta["task_id"] not in task_set:
                        scores[i] = -1
            top_indices = np.argsort(scores)[::-1][:top_k]
            results = []
            for idx in top_indices:
                if scores[idx] < 0.05:
                    continue
                meta = self._chunk_meta[idx]
                results.append({
                    "task_id": meta["task_id"],
                    "chunk_id": meta["chunk_id"],
                    "text": meta["text"],
                    "score": float(scores[idx]),
                })
            return results

    def rebuild_from_notes(self, notes: List[dict]):
        logger.info("Rebuilding vector index from %d notes...", len(notes))
        total = 0
        for note in notes:
            total += self.index_note(note["task_id"], note["content"])
        logger.info("Vector index rebuilt: %d notes, %d chunks", len(notes), total)

    def _rebuild_matrix(self):
        self._chunk_meta = []
        embeddings = []
        for task_id, chunks in self._index.items():
            for chunk in chunks:
                self._chunk_meta.append({"task_id": task_id, "chunk_id": chunk["id"], "text": chunk["text"]})
                embeddings.append(chunk["embedding"])
        self._embeddings_matrix = np.array(embeddings, dtype=np.float32) if embeddings else None

    def _save_index(self):
        save_data = {"__meta__": {
            "provider": self.embedding_provider,
            "model": self.embedding_model,
            "dimension": self.embedding_dimension,
        }}
        for task_id, chunks in self._index.items():
            save_data[task_id] = [{
                "id": c["id"], "text": c["text"],
                "embedding": c["embedding"].tolist() if hasattr(c["embedding"], "tolist") else c["embedding"],
            } for c in chunks]
        (self.index_dir / "vector_index.json").write_text(json.dumps(save_data, ensure_ascii=False), encoding="utf-8")

    def load_index(self):
        path = self.index_dir / "vector_index.json"
        if not path.exists():
            return
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            meta = data.get("__meta__", {}) if isinstance(data, dict) else {}
            if meta:
                if meta.get("model") != self.embedding_model or int(meta.get("dimension", 0)) != self.embedding_dimension:
                    logger.warning("Ignoring vector index created by another embedding model: %s", meta)
                    return
            for task_id, chunks in data.items():
                if task_id == "__meta__":
                    continue
                if chunks and len(chunks[0].get("embedding", [])) != self.embedding_dimension:
                    logger.warning("Ignoring vector index with incompatible dimension for task %s", task_id[:8])
                    return
                self._index[task_id] = [{"id": c["id"], "text": c["text"], "embedding": np.array(c["embedding"], dtype=np.float32)} for c in chunks]
            self._rebuild_matrix()
            self._loaded = True
            logger.info("Loaded numpy vector index: %d tasks, %d chunks", len(self._index), sum(len(v) for v in self._index.values()))
        except Exception as exc:
            logger.error("Failed to load vector index: %s", exc)

    @property
    def backend(self) -> str:
        return "milvus" if self._milvus_ready else "numpy"


_vector_service = None

def get_vector_service() -> VectorService:
    global _vector_service
    if _vector_service is None:
        _vector_service = VectorService()
        _vector_service.load_index()
    return _vector_service
