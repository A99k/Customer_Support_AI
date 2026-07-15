# TechMart Support backend — FastAPI + multi-agent RAG pipeline.
FROM python:3.11-slim

WORKDIR /app

# System deps needed by faiss-cpu / sentence-transformers wheels on slim images.
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

COPY backend/requirements.txt backend/requirements.txt
RUN pip install --no-cache-dir -r backend/requirements.txt

COPY backend/ backend/
COPY knowledge_base/ knowledge_base/
RUN mkdir -p backend/vectorstore backend/memory

# Railway (and most PaaS providers) inject $PORT at runtime; default to 8000
# for local `docker run`.
ENV PORT=8000
EXPOSE 8000

CMD ["sh", "-c", "uvicorn backend.main:app --host 0.0.0.0 --port ${PORT}"]
