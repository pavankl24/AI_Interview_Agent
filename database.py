"""Optional Supabase persistence for completed interview reports."""

import os
from functools import lru_cache

from dotenv import load_dotenv

load_dotenv()


def is_supabase_configured() -> bool:
    return bool(os.getenv("SUPABASE_URL") and os.getenv("SUPABASE_SECRET_KEY"))


@lru_cache(maxsize=1)
def _client():
    if not is_supabase_configured():
        return None
    from supabase import create_client

    return create_client(os.environ["SUPABASE_URL"], os.environ["SUPABASE_SECRET_KEY"])


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
