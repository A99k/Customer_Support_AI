"""
Central configuration for the Multi-Agent Customer Support backend.
All values can be overridden with environment variables (see .env.example).
"""
import os
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent

# Load variables from a .env file in the project root (one level above
# backend/) into the process environment. Without this call, os.getenv()
# below would never see anything you put in .env.
load_dotenv(BASE_DIR / ".env")

# --- Hugging Face LLM settings ---
HF_TOKEN = os.getenv("HF_TOKEN", "")
# Any instruction-tuned chat model available on HF Inference Providers works here.
# Qwen2.5-7B-Instruct is ungated (no license click-through needed) and is served
# by several providers, which makes "auto" routing reliable.
HF_MODEL = os.getenv("HF_MODEL", "Qwen/Qwen2.5-7B-Instruct")
# "auto" lets HF pick the fastest available provider for HF_MODEL (Together,
# Fireworks, Groq, Cerebras, etc.). Set to a specific provider name (e.g.
# "together") in .env if you want to pin one.
HF_PROVIDER = os.getenv("HF_PROVIDER", "auto")
HF_MAX_TOKENS = int(os.getenv("HF_MAX_TOKENS", "512"))
HF_TEMPERATURE = float(os.getenv("HF_TEMPERATURE", "0.3"))

# --- Embeddings / RAG settings ---
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "sentence-transformers/all-MiniLM-L6-v2")
KNOWLEDGE_BASE_DIR = BASE_DIR / "knowledge_base"
VECTORSTORE_DIR = BASE_DIR / "backend" / "vectorstore"
CHUNK_SIZE = int(os.getenv("CHUNK_SIZE", "500"))
CHUNK_OVERLAP = int(os.getenv("CHUNK_OVERLAP", "80"))
TOP_K = int(os.getenv("TOP_K", "3"))

# --- Conversation memory ---
MEMORY_DB_PATH = BASE_DIR / "backend" / "memory" / "conversations.db"

# --- User store (MongoDB) ---
# Local dev default: `mongod` running on localhost with no auth. For
# deployment, set this to a MongoDB Atlas connection string, e.g.
# mongodb+srv://<user>:<password>@<cluster>.mongodb.net/?retryWrites=true&w=majority
MONGODB_URI = os.getenv("MONGODB_URI", "mongodb://localhost:27017")
MONGODB_DB_NAME = os.getenv("MONGODB_DB_NAME", "techmart_support")

# --- Escalation ---
COMPLAINT_ESCALATION_KEYWORDS = [
    "lawsuit", "lawyer", "sue", "scam", "fraud", "furious", "terrible",
    "worst", "unacceptable", "cancel my account", "never buying again",
]

# --- Auth / JWT ---
JWT_SECRET = os.getenv("JWT_SECRET", "")
if not JWT_SECRET:
    print(
        "WARNING: JWT_SECRET is not set in .env. Using an insecure, "
        "randomly-generated key for this process only — all existing "
        "tokens will become invalid on every restart. Set JWT_SECRET in "
        ".env before deploying anywhere real."
    )
    import secrets
    JWT_SECRET = secrets.token_hex(32)
JWT_ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")
JWT_EXPIRE_MINUTES = int(os.getenv("JWT_EXPIRE_MINUTES", "1440"))  # 24h

# Comma-separated emails allowed to view the analytics dashboard.
ADMIN_EMAILS = {
    e.strip().lower() for e in os.getenv("ADMIN_EMAILS", "").split(",") if e.strip()
}

# --- CORS ---
ALLOWED_ORIGINS = os.getenv("ALLOWED_ORIGINS", "*").split(",")
