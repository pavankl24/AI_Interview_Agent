"""Optional Supabase persistence for completed interview reports."""

import os
from functools import lru_cache

from dotenv import load_dotenv

load_dotenv()


def is_supabase_configured() -> bool:
    return bool(os.getenv("SUPABASE_URL") and (os.getenv("SUPABASE_SECRET_KEY") or os.getenv("SUPABASE_SERVICE_ROLE_KEY")))


@lru_cache(maxsize=1)
def _client():
    if not is_supabase_configured():
        return None
    from supabase import create_client

    key = os.getenv("SUPABASE_SECRET_KEY") or os.environ["SUPABASE_SERVICE_ROLE_KEY"]
    return create_client(os.environ["SUPABASE_URL"], key)


def verify_access_token(access_token: str) -> str | None:
    """Return the authenticated Supabase user ID only after Auth verifies the token."""
    client = _client()
    if client is None:
        return None
    try:
        response = client.auth.get_user(access_token)
        return str(response.user.id) if response.user else None
    except Exception:
        return None


def save_interview(payload: dict) -> None:
    client = _client()
    if client is not None:
        client.table("interview_sessions").insert(payload).execute()


def get_interviews(client_id: str) -> list[dict]:
    client = _client()
    if client is None:
        return []
    response = (
        client.table("interview_sessions")
        .select("id,topic,difficulty,interview_mode,max_questions,overall_score,report,created_at")
        .eq("client_id", client_id)
        .order("created_at", desc=True)
        .limit(100)
        .execute()
    )
    return response.data or []


def get_leaderboard(limit: int = 20) -> list[dict]:
    """Return top scores (best score per user per topic) for the leaderboard."""
    client = _client()
    if client is None:
        return []
    response = (
        client.table("interview_sessions")
        .select("client_id,topic,overall_score,created_at")
        .order("overall_score", desc=True)
        .limit(200)
        .execute()
    )
    rows = response.data or []
    # Keep only the best score per (client_id, topic)
    seen: dict[tuple, dict] = {}
    for row in rows:
        key = (row["client_id"], row["topic"])
        if key not in seen:
            seen[key] = row
    # Sort by score descending and take top `limit`
    top = sorted(seen.values(), key=lambda r: float(r.get("overall_score") or 0), reverse=True)[:limit]
    result = []
    for rank, row in enumerate(top, 1):
        uid = str(row["client_id"])
        result.append({
            "rank": rank,
            "user_tag": f"User #{uid[:4].upper()}",
            "topic": row["topic"],
            "score": float(row.get("overall_score") or 0),
            "date": row.get("created_at", "")[:10],
        })
    return result
