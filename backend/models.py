"""Pydantic request/response schemas used by the FastAPI routes."""
from typing import List, Optional
from pydantic import BaseModel, EmailStr, Field


class SignupRequest(BaseModel):
    email: EmailStr
    name: str = Field(..., min_length=1, max_length=100)
    password: str = Field(..., min_length=8, description="At least 8 characters")


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class UserOut(BaseModel):
    id: str
    email: str
    name: str
    is_admin: bool = False  # derived from config.ADMIN_EMAILS, not stored in the DB


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserOut


class ChatRequest(BaseModel):
    session_id: str = Field(..., description="Client-generated session identifier")
    message: str = Field(..., min_length=1, description="The customer's message")


class SourceChunk(BaseModel):
    source: str
    text: str


class ChatResponse(BaseModel):
    session_id: str
    reply: str
    intents: List[str]
    agents_used: List[str]
    escalated: bool
    sources: List[SourceChunk]


class HistoryTurn(BaseModel):
    role: str  # "user" | "assistant"
    content: str
    agents_used: Optional[List[str]] = None
    escalated: bool = False
    timestamp: str


class HistoryResponse(BaseModel):
    session_id: str
    turns: List[HistoryTurn]


class NewSessionResponse(BaseModel):
    session_id: str


class SessionSummary(BaseModel):
    session_id: str
    created_at: str
    preview: str
    last_activity: str
    message_count: int


class SessionListResponse(BaseModel):
    sessions: List[SessionSummary]


class DailyCount(BaseModel):
    date: str
    count: int


class EscalatedConversation(BaseModel):
    session_id: str
    message: str
    timestamp: str


class AnalyticsSummary(BaseModel):
    total_conversations: int
    total_messages: int
    total_users: int
    escalation_rate: float
    avg_messages_per_conversation: float
    intent_counts: dict
    agent_counts: dict
    messages_by_day: List[DailyCount]
    recent_escalations: List[EscalatedConversation]
