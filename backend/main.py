"""
FastAPI entrypoint for the Multi-Agent AI Customer Support Assistant.

Run with:
    uvicorn backend.main:app --reload --port 8000
(run from the project root, one level above backend/)
"""
import sys
import uuid
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parent.parent))

from fastapi import Depends, FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware

from backend import config
from backend.analytics import service as analytics_service
from backend.auth.jwt_handler import create_access_token, get_current_admin_user, get_current_user
from backend.auth.user_store import create_user, get_user_by_email, verify_password
from backend.memory import conversation_memory as memory
from backend.models import (
    AnalyticsSummary,
    ChatRequest,
    ChatResponse,
    HistoryResponse,
    HistoryTurn,
    LoginRequest,
    NewSessionResponse,
    SessionListResponse,
    SessionSummary,
    SignupRequest,
    SourceChunk,
    TokenResponse,
    UserOut,
)
from backend.agents.router import get_router

app = FastAPI(
    title="TechMart Multi-Agent Customer Support API",
    description="Routes customer queries to specialized AI agents backed by RAG.",
    version="1.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=config.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

_router = None  # lazily initialized on first request (loads embedding model + LLM client)


def _get_router():
    global _router
    if _router is None:
        _router = get_router()
    return _router


def _to_user_out(user: dict) -> UserOut:
    return UserOut(
        id=user["id"],
        email=user["email"],
        name=user["name"],
        is_admin=user["email"].lower() in config.ADMIN_EMAILS,
    )


@app.get("/api/health")
def health():
    return {"status": "ok"}


# ---------------------------------------------------------------------------
# Auth
# ---------------------------------------------------------------------------

@app.post("/api/auth/signup", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
def signup(request: SignupRequest):
    try:
        user = create_user(request.email, request.name, request.password)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e))

    token = create_access_token(user["id"])
    return TokenResponse(access_token=token, user=_to_user_out(user))


@app.post("/api/auth/login", response_model=TokenResponse)
def login(request: LoginRequest):
    user = get_user_by_email(request.email)
    if not user or not verify_password(request.password, user["password_hash"]):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password.",
        )
    token = create_access_token(user["id"])
    return TokenResponse(access_token=token, user=_to_user_out(user))


@app.get("/api/auth/me", response_model=UserOut)
def me(current_user: dict = Depends(get_current_user)):
    return _to_user_out(current_user)


# ---------------------------------------------------------------------------
# Chat (all protected — every session belongs to exactly one authenticated user)
# ---------------------------------------------------------------------------

@app.post("/api/session", response_model=NewSessionResponse)
def create_session(current_user: dict = Depends(get_current_user)):
    session_id = str(uuid.uuid4())
    memory.create_session(current_user["id"], session_id)
    return NewSessionResponse(session_id=session_id)


def _authorize_session(session_id: str, current_user: dict) -> None:
    """Ensure session_id belongs to current_user. Auto-adopts unowned/unknown
    session ids (so older clients created before login still work), but
    rejects sessions that belong to someone else."""
    owner = memory.get_session_owner(session_id)
    if owner is None:
        memory.create_session(current_user["id"], session_id)
    elif owner != current_user["id"]:
        # Don't reveal that the session exists at all.
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found.")


@app.post("/api/chat", response_model=ChatResponse)
def chat(request: ChatRequest, current_user: dict = Depends(get_current_user)):
    if not request.message.strip():
        raise HTTPException(status_code=400, detail="Message cannot be empty.")

    _authorize_session(request.session_id, current_user)

    router = _get_router()
    conversation_context = memory.get_recent_context(request.session_id)

    result = router.route(request.message, conversation_context)

    memory.add_turn(request.session_id, "user", request.message)
    memory.add_turn(
        request.session_id,
        "assistant",
        result["reply"],
        agents_used=result["agents_used"],
        intents=result["intents"],
        escalated=result["escalated"],
    )

    return ChatResponse(
        session_id=request.session_id,
        reply=result["reply"],
        intents=result["intents"],
        agents_used=result["agents_used"],
        escalated=result["escalated"],
        sources=[SourceChunk(**s) for s in result["sources"]],
    )


@app.get("/api/sessions", response_model=SessionListResponse)
def list_sessions(current_user: dict = Depends(get_current_user)):
    sessions = memory.list_sessions_for_user(current_user["id"])
    return SessionListResponse(sessions=[SessionSummary(**s) for s in sessions])


@app.get("/api/history/{session_id}", response_model=HistoryResponse)
def history(session_id: str, current_user: dict = Depends(get_current_user)):
    _authorize_session(session_id, current_user)
    turns = memory.get_history(session_id)
    return HistoryResponse(
        session_id=session_id,
        turns=[HistoryTurn(**t) for t in turns],
    )


# ---------------------------------------------------------------------------
# Analytics (Module 9) — admin-only
# ---------------------------------------------------------------------------

@app.get("/api/analytics/summary", response_model=AnalyticsSummary)
def analytics_summary(
    days: int = 14,
    _admin: dict = Depends(get_current_admin_user),
):
    return AnalyticsSummary(**analytics_service.get_summary(days=days))


@app.get("/api/analytics/me", response_model=AnalyticsSummary)
def analytics_me(
    days: int = 14,
    current_user: dict = Depends(get_current_user),
):
    return AnalyticsSummary(**analytics_service.get_summary_for_user(current_user["id"], days=days))
