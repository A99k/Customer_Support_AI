"""
Ingests every document in knowledge_base/ (.md, .txt, .pdf), splits it into
overlapping chunks, embeds the chunks with a sentence-transformers model,
and persists a FAISS index + metadata to disk so the API doesn't have to
re-embed on every restart.

Run manually with:
    python -m backend.rag.ingest
It also runs automatically on server startup if no index is found.
"""
import json
import sys
from pathlib import Path

import faiss
import numpy as np
from sentence_transformers import SentenceTransformer

sys.path.append(str(Path(__file__).resolve().parent.parent.parent))
from backend import config


def _read_pdf(path: Path) -> str:
    from pypdf import PdfReader
    reader = PdfReader(str(path))
    return "\n".join(page.extract_text() or "" for page in reader.pages)


def load_documents() -> list[dict]:
    """Return a list of {source, text} dicts for every file in the knowledge base."""
    docs = []
    for path in sorted(config.KNOWLEDGE_BASE_DIR.glob("*")):
        if path.suffix.lower() in (".md", ".txt"):
            text = path.read_text(encoding="utf-8")
        elif path.suffix.lower() == ".pdf":
            text = _read_pdf(path)
        else:
            continue
        docs.append({"source": path.name, "text": text})
    return docs


def chunk_text(text: str, chunk_size: int, overlap: int) -> list[str]:
    """Simple word-based sliding-window chunker."""
    words = text.split()
    if not words:
        return []
    chunks = []
    step = max(chunk_size - overlap, 1)
    for start in range(0, len(words), step):
        chunk_words = words[start:start + chunk_size]
        if not chunk_words:
            break
        chunks.append(" ".join(chunk_words))
        if start + chunk_size >= len(words):
            break
    return chunks


def build_index() -> None:
    config.VECTORSTORE_DIR.mkdir(parents=True, exist_ok=True)

    documents = load_documents()
    if not documents:
        raise RuntimeError(f"No documents found in {config.KNOWLEDGE_BASE_DIR}")

    print(f"Loaded {len(documents)} documents from {config.KNOWLEDGE_BASE_DIR}")

    chunks: list[str] = []
    metadata: list[dict] = []
    for doc in documents:
        doc_chunks = chunk_text(doc["text"], config.CHUNK_SIZE, config.CHUNK_OVERLAP)
        for chunk in doc_chunks:
            chunks.append(chunk)
            metadata.append({"source": doc["source"], "text": chunk})

    print(f"Split into {len(chunks)} chunks. Loading embedding model "
          f"'{config.EMBEDDING_MODEL}'...")

    model = SentenceTransformer(config.EMBEDDING_MODEL)
    embeddings = model.encode(chunks, show_progress_bar=True, normalize_embeddings=True)
    embeddings = np.asarray(embeddings, dtype="float32")

    dimension = embeddings.shape[1]
    index = faiss.IndexFlatIP(dimension)  # cosine similarity via normalized vectors
    index.add(embeddings)

    faiss.write_index(index, str(config.VECTORSTORE_DIR / "index.faiss"))
    with open(config.VECTORSTORE_DIR / "metadata.json", "w", encoding="utf-8") as f:
        json.dump(metadata, f, ensure_ascii=False, indent=2)

    print(f"Saved FAISS index ({index.ntotal} vectors, dim={dimension}) "
          f"to {config.VECTORSTORE_DIR}")


if __name__ == "__main__":
    build_index()
