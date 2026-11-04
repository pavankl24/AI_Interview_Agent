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
