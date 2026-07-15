"""
Lightweight SQLite-backed conversation memory. Stores every user message and
AI response with a timestamp and session ID, per Module 8 of the spec.
"""
import sqlite3
import sys
import threading
from datetime import datetime, timezone
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parent.parent.parent))
from backend import config

_lock = threading.Lock()


def _migrate(conn: sqlite3.Connection) -> None:
    """Add columns to an existing DB created before analytics support existed.
    Safe to run every startup — ALTER TABLE ADD COLUMN is a no-op if the
    column is already there (guarded by checking PRAGMA table_info first)."""
    existing_cols = {row[1] for row in conn.execute("PRAGMA table_info(turns)").fetchall()}
    if "intents" not in existing_cols:
        conn.execute("ALTER TABLE turns ADD COLUMN intents TEXT")
    if "escalated" not in existing_cols:
        conn.execute("ALTER TABLE turns ADD COLUMN escalated INTEGER DEFAULT 0")
    conn.commit()


def _connect() -> sqlite3.Connection:
    config.MEMORY_DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(config.MEMORY_DB_PATH, check_same_thread=False)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS turns (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id TEXT NOT NULL,
            role TEXT NOT NULL CHECK(role IN ('user', 'assistant')),
            content TEXT NOT NULL,
            agents_used TEXT,
            intents TEXT,
            escalated INTEGER DEFAULT 0,
            timestamp TEXT NOT NULL
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS sessions (
            session_id TEXT PRIMARY KEY,
            user_id TEXT NOT NULL,
            created_at TEXT NOT NULL
        )
    """)
    conn.commit()
    _migrate(conn)
    return conn


_conn = _connect()


def create_session(user_id: str, session_id: str) -> None:
    with _lock:
        _conn.execute(
            "INSERT OR IGNORE INTO sessions (session_id, user_id, created_at) VALUES (?, ?, ?)",
            (session_id, user_id, datetime.now(timezone.utc).isoformat()),
        )
        _conn.commit()


def get_session_owner(session_id: str) -> str | None:
    with _lock:
        cursor = _conn.execute(
            "SELECT user_id FROM sessions WHERE session_id = ?", (session_id,)
        )
        row = cursor.fetchone()
    return row[0] if row else None


def add_turn(
    session_id: str,
    role: str,
    content: str,
    agents_used: list[str] = None,
    intents: list[str] = None,
    escalated: bool = False,
) -> None:
    with _lock:
        _conn.execute(
            "INSERT INTO turns (session_id, role, content, agents_used, intents, "
            "escalated, timestamp) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (
                session_id,
                role,
                content,
                ",".join(agents_used) if agents_used else None,
                ",".join(intents) if intents else None,
                1 if escalated else 0,
                datetime.now(timezone.utc).isoformat(),
            ),
        )
        _conn.commit()


def get_history(session_id: str, limit: int = 50) -> list[dict]:
    with _lock:
        cursor = _conn.execute(
            "SELECT role, content, agents_used, escalated, timestamp FROM turns "
            "WHERE session_id = ? ORDER BY id ASC LIMIT ?",
            (session_id, limit),
        )
        rows = cursor.fetchall()
    return [
        {
            "role": role,
            "content": content,
            "agents_used": agents_used.split(",") if agents_used else [],
            "escalated": bool(escalated),
            "timestamp": timestamp,
        }
        for role, content, agents_used, escalated, timestamp in rows
    ]


def get_recent_context(session_id: str, turns: int = 6) -> str:
    """Return the last `turns` messages formatted as plain text, for prompt context."""
    history = get_history(session_id, limit=turns)
    lines = []
    for turn in history[-turns:]:
        speaker = "Customer" if turn["role"] == "user" else "Assistant"
        lines.append(f"{speaker}: {turn['content']}")
    return "\n".join(lines)


def list_sessions_for_user(user_id: str, limit: int = 50) -> list[dict]:
    """Return this user's conversations, most recently active first, each with
    a short preview (first user message) for a conversation-history sidebar."""
    with _lock:
        rows = _conn.execute(
            """
            SELECT
                s.session_id,
                s.created_at,
                (SELECT content FROM turns
                 WHERE session_id = s.session_id AND role = 'user'
                 ORDER BY id ASC LIMIT 1) AS preview,
                (SELECT MAX(timestamp) FROM turns
                 WHERE session_id = s.session_id) AS last_activity,
                (SELECT COUNT(*) FROM turns
                 WHERE session_id = s.session_id) AS message_count
            FROM sessions s
            WHERE s.user_id = ?
            ORDER BY COALESCE(last_activity, s.created_at) DESC
            LIMIT ?
            """,
            (user_id, limit),
        ).fetchall()

    return [
        {
            "session_id": r[0],
            "created_at": r[1],
            "preview": r[2] or "(no messages yet)",
            "last_activity": r[3] or r[1],
            "message_count": r[4],
        }
        for r in rows
    ]
