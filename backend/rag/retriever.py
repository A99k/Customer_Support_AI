"""
Loads the persisted FAISS index (building it on first use if missing) and
exposes a simple `retrieve(query, k)` API used by the specialized agents.
"""
import json
import sys
import threading
from pathlib import Path

import faiss
import numpy as np
from sentence_transformers import SentenceTransformer

sys.path.append(str(Path(__file__).resolve().parent.parent.parent))
from backend import config
from backend.rag.ingest import build_index


class Retriever:
    _lock = threading.Lock()

    def __init__(self):
        self._model: SentenceTransformer | None = None
        self._index = None
        self._metadata: list[dict] = []
        self._load()

    def _load(self):
        index_path = config.VECTORSTORE_DIR / "index.faiss"
        meta_path = config.VECTORSTORE_DIR / "metadata.json"

        if not index_path.exists() or not meta_path.exists():
            print("No existing vector index found — building one from the "
                  "knowledge base now (this happens once).")
            build_index()

        self._index = faiss.read_index(str(index_path))
        with open(meta_path, "r", encoding="utf-8") as f:
            self._metadata = json.load(f)
        self._model = SentenceTransformer(config.EMBEDDING_MODEL)

    def retrieve(self, query: str, k: int = None) -> list[dict]:
        """Return the top-k most relevant chunks as [{source, text, score}, ...]."""
        k = k or config.TOP_K
        with self._lock:
            query_vec = self._model.encode([query], normalize_embeddings=True)
        query_vec = np.asarray(query_vec, dtype="float32")

        scores, indices = self._index.search(query_vec, k)
        results = []
        for score, idx in zip(scores[0], indices[0]):
            if idx == -1:
                continue
            meta = self._metadata[idx]
            results.append({
                "source": meta["source"],
                "text": meta["text"],
                "score": float(score),
            })
        return results


_retriever_instance: Retriever | None = None
_instance_lock = threading.Lock()


def get_retriever() -> Retriever:
    """Lazily instantiate a single shared Retriever (loading models is expensive)."""
    global _retriever_instance
    if _retriever_instance is None:
        with _instance_lock:
            if _retriever_instance is None:
                _retriever_instance = Retriever()
    return _retriever_instance
