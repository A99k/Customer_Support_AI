"""
Module 9: Analytics.

Read-only aggregation queries over the conversation_memory SQLite DB. Kept
separate from conversation_memory.py so the hot path (add_turn/get_history)
stays simple, and analytics queries can evolve independently.
"""
import sys
from collections import Counter
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parent.parent.parent))
from backend.memory.conversation_memory import _conn, _lock  # reuse the same connection


def _rows(query: str, params: tuple = ()) -> list[tuple]:
    with _lock:
        return _conn.execute(query, params).fetchall()


def get_summary(days: int = 30, recent_escalation_limit: int = 10) -> dict:
    total_conversations = _rows("SELECT COUNT(*) FROM sessions")[0][0]
    total_users = _rows("SELECT COUNT(DISTINCT user_id) FROM sessions")[0][0]

    user_turns = _rows("SELECT COUNT(*) FROM turns WHERE role = 'user'")[0][0]
    assistant_turns = _rows("SELECT COUNT(*) FROM turns WHERE role = 'assistant'")[0][0]
    total_messages = user_turns + assistant_turns

    escalated_count = _rows(
        "SELECT COUNT(*) FROM turns WHERE role = 'assistant' AND escalated = 1"
    )[0][0]
    escalation_rate = (escalated_count / assistant_turns) if assistant_turns else 0.0

    avg_messages_per_conversation = (
        (total_messages / total_conversations) if total_conversations else 0.0
    )

    intent_counter = Counter()
    for (intents_str,) in _rows(
        "SELECT intents FROM turns WHERE role = 'assistant' AND intents IS NOT NULL"
    ):
        for intent in intents_str.split(","):
            if intent:
                intent_counter[intent] += 1

    agent_counter = Counter()
    for (agents_str,) in _rows(
        "SELECT agents_used FROM turns WHERE role = 'assistant' AND agents_used IS NOT NULL"
    ):
        for agent in agents_str.split(","):
            if agent:
                agent_counter[agent] += 1

    # Messages per day, most recent `days` days that have data.
    day_rows = _rows(
        "SELECT substr(timestamp, 1, 10) AS day, COUNT(*) FROM turns "
        "GROUP BY day ORDER BY day DESC LIMIT ?",
        (days,),
    )
    messages_by_day = [{"date": day, "count": count} for day, count in reversed(day_rows)]

    escalation_rows = _rows(
        "SELECT session_id, content, timestamp FROM turns "
        "WHERE role = 'assistant' AND escalated = 1 "
        "ORDER BY id DESC LIMIT ?",
        (recent_escalation_limit,),
    )
    recent_escalations = [
        {"session_id": sid, "message": content, "timestamp": ts}
        for sid, content, ts in escalation_rows
    ]

    return {
        "total_conversations": total_conversations,
        "total_messages": total_messages,
        "total_users": total_users,
        "escalation_rate": round(escalation_rate, 4),
        "avg_messages_per_conversation": round(avg_messages_per_conversation, 2),
        "intent_counts": dict(intent_counter),
        "agent_counts": dict(agent_counter),
        "messages_by_day": messages_by_day,
        "recent_escalations": recent_escalations,
    }


def get_summary_for_user(user_id: str, days: int = 30) -> dict:
    """Same shape as summary(), scoped to one user's own sessions."""
    session_ids = [row[0] for row in _rows(
        "SELECT session_id FROM sessions WHERE user_id = ?", (user_id,)
    )]
    total_conversations = len(session_ids)
    if not session_ids:
        return {
            "total_conversations": 0,
            "total_messages": 0,
            "total_users": 1,
            "escalation_rate": 0.0,
            "avg_messages_per_conversation": 0.0,
            "intent_counts": {},
            "agent_counts": {},
            "messages_by_day": [],
            "recent_escalations": [],
        }

    placeholders = ",".join("?" * len(session_ids))

    total_messages = _rows(
        f"SELECT COUNT(*) FROM turns WHERE session_id IN ({placeholders})",
        tuple(session_ids),
    )[0][0]

    assistant_turns = _rows(
        f"SELECT COUNT(*) FROM turns WHERE session_id IN ({placeholders}) AND role = 'assistant'",
        tuple(session_ids),
    )[0][0]

    escalated_count = _rows(
        f"SELECT COUNT(*) FROM turns WHERE session_id IN ({placeholders}) "
        "AND role = 'assistant' AND escalated = 1",
        tuple(session_ids),
    )[0][0]
    escalation_rate = (escalated_count / assistant_turns) if assistant_turns else 0.0
    avg_messages_per_conversation = (
        (total_messages / total_conversations) if total_conversations else 0.0
    )

    intent_counter = Counter()
    for (intents_str,) in _rows(
        f"SELECT intents FROM turns WHERE session_id IN ({placeholders}) "
        "AND role = 'assistant' AND intents IS NOT NULL",
        tuple(session_ids),
    ):
        for intent in intents_str.split(","):
            if intent:
                intent_counter[intent] += 1

    agent_counter = Counter()
    for (agents_str,) in _rows(
        f"SELECT agents_used FROM turns WHERE session_id IN ({placeholders}) "
        "AND role = 'assistant' AND agents_used IS NOT NULL",
        tuple(session_ids),
    ):
        for agent in agents_str.split(","):
            if agent:
                agent_counter[agent] += 1

    day_rows = _rows(
        f"SELECT substr(timestamp, 1, 10) AS day, COUNT(*) FROM turns "
        f"WHERE session_id IN ({placeholders}) GROUP BY day ORDER BY day DESC LIMIT ?",
        tuple(session_ids) + (days,),
    )
    messages_by_day = [{"date": day, "count": count} for day, count in reversed(day_rows)]

    escalation_rows = _rows(
        f"SELECT session_id, content, timestamp FROM turns "
        f"WHERE session_id IN ({placeholders}) AND role = 'assistant' AND escalated = 1 "
        "ORDER BY id DESC LIMIT 10",
        tuple(session_ids),
    )
    recent_escalations = [
        {"session_id": sid, "message": content, "timestamp": ts}
        for sid, content, ts in escalation_rows
    ]

    return {
        "total_conversations": total_conversations,
        "total_messages": total_messages,
        "total_users": 1,
        "escalation_rate": round(escalation_rate, 4),
        "avg_messages_per_conversation": round(avg_messages_per_conversation, 2),
        "intent_counts": dict(intent_counter),
        "agent_counts": dict(agent_counter),
        "messages_by_day": messages_by_day,
        "recent_escalations": recent_escalations,
    }
