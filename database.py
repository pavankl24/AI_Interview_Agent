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


def _candidate_name(client, user_id: str, report: dict | None, cache: dict[str, str]) -> str:
    saved = ""
    if isinstance(report, dict):
        saved = str(report.get("candidate_name") or "").strip()
    if saved:
        return saved
    if user_id in cache:
        return cache[user_id]
    name = ""
    try:
        response = client.auth.admin.get_user_by_id(user_id)
        user = getattr(response, "user", None)
        meta = getattr(user, "user_metadata", None) or {}
        email = getattr(user, "email", None) or ""
        name = str(meta.get("full_name") or meta.get("name") or email.split("@")[0] or "").strip()
    except Exception:
        name = ""
    cache[user_id] = name or f"Candidate {user_id[:4].upper()}"
    return cache[user_id]


def get_leaderboard(limit: int = 25, topic: str | None = None, viewer_id: str | None = None) -> dict:
    """Best score per candidate, optionally for one interview topic."""
    client = _client()
    if client is None:
        return {"topics": [], "entries": []}

    response = (
        client.table("interview_sessions")
        .select("client_id,topic,overall_score,created_at,report")
        .order("created_at", desc=True)
        .limit(1000)
        .execute()
    )
    rows = response.data or []
    topics = sorted({row["topic"] for row in rows if row.get("topic")})
    selected = (topic or "").strip()
    if selected and selected.lower() != "all":
        rows = [row for row in rows if row.get("topic") == selected]

    def row_score(row: dict) -> float | None:
        if row.get("overall_score") is not None:
            return float(row["overall_score"])
        report = row.get("report") if isinstance(row.get("report"), dict) else {}
        value = report.get("overall_score", report.get("knowledge_score"))
        return None if value is None else float(value)

    # One standing per candidate: their highest saved score in this view.
    best: dict[str, dict] = {}
    for row in rows:
        score = row_score(row)
        if score is None:
            continue
        row = {**row, "overall_score": score}
        user_id = str(row["client_id"])
        current = best.get(user_id)
        if current is None or score > float(current.get("overall_score") or 0):
            best[user_id] = row

    ranked = sorted(best.values(), key=lambda row: float(row.get("overall_score") or 0), reverse=True)
    names: dict[str, str] = {}
    entries = []
    viewer_entry = None
    for rank, row in enumerate(ranked, 1):
        user_id = str(row["client_id"])
        entry = {
            "rank": rank,
            "user_id": user_id,
            "name": _candidate_name(client, user_id, row.get("report"), names),
            "topic": row["topic"],
            "score": float(row.get("overall_score") or 0),
            "assessed_at": row.get("created_at") or "",
            "is_you": bool(viewer_id) and user_id == viewer_id,
        }
        if entry["is_you"]:
            viewer_entry = entry
        if rank <= limit:
            entries.append(entry)

    if viewer_entry and all(item["user_id"] != viewer_entry["user_id"] for item in entries):
        entries.append(viewer_entry)

    return {"topics": topics, "entries": entries}
