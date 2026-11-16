from datetime import datetime, timezone

from agent import InterviewAgent
from database import (
    cleanup_expired_active_interviews,
    delete_active_interview,
    get_active_interview,
    save_active_interview,
)
from report import InterviewReport


def save_active_session(session: dict) -> None:
    state = {key: value for key, value in session.items() if key not in {"agent", "report"}}
    state["agent_state"] = session["agent"].export_state()
    state.setdefault("created_at", datetime.now(timezone.utc).isoformat())
    state["updated_at"] = datetime.now(timezone.utc).isoformat()
    session["created_at"] = state["created_at"]
    session["updated_at"] = state["updated_at"]
    save_active_interview(session["client_id"], session["session_id"], state)


def load_active_session(client_id: str, session_id: str | None = None) -> dict | None:
    state = get_active_interview(client_id)
    if state is None or (session_id and state.get("session_id") != session_id):
        return None
    agent_state = state.pop("agent_state")
    state["agent"] = InterviewAgent.from_state(agent_state)
    state["report"] = InterviewReport(agent_state["interview_type"])
    return state


def remove_active_session(client_id: str) -> None:
    delete_active_interview(client_id)


def cleanup_expired_sessions() -> int:
    return cleanup_expired_active_interviews()
