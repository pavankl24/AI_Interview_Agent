from pathlib import Path
from typing import Literal
import logging
import asyncio
import os

import httpx

from fastapi import FastAPI, HTTPException, Header
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field
from dotenv import load_dotenv

from agent import InterviewAgent
from report import InterviewReport
from database import get_interviews, is_supabase_configured, save_interview, verify_access_token, get_leaderboard

load_dotenv()

app = FastAPI(title="Cogniv AI Interview Coach API")

WEB_DIR = Path(__file__).parent / "web"
FRONTEND_DIR = WEB_DIR / "dist"


@app.get("/app", include_in_schema=False)
def web_app():
    return FileResponse(FRONTEND_DIR / "index.html")


@app.get("/", include_in_schema=False)
def home():
    return FileResponse(FRONTEND_DIR / "index.html")

sessions = {}
logger = logging.getLogger(__name__)


class StartInterviewRequest(BaseModel):
    interview_type: str
    max_questions: int = Field(default=5, ge=1, le=50)
    difficulty: Literal["Beginner", "Intermediate", "Advanced"] = "Intermediate"
    interview_mode: Literal[
        "Balanced", "Technical conversation", "Coding & problem solving"
    ] = "Balanced"


class AnswerRequest(BaseModel):
    answer: str


class CompilerRequest(BaseModel):
    language_id: int = Field(ge=1)
    source_code: str = Field(min_length=1, max_length=20000)
    stdin: str = Field(default="", max_length=5000)


def judge0_url() -> str:
    return os.getenv("JUDGE0_API_URL", "https://ce.judge0.com").rstrip("/")


def judge0_headers() -> dict[str, str]:
    headers = {"Content-Type": "application/json"}
    api_key = os.getenv("JUDGE0_API_KEY")
    if api_key:
        headers["X-Auth-Token"] = api_key
    return headers


@app.get("/compiler/languages")
async def compiler_languages(authorization: str | None = Header(default=None)):
    authenticated_user(authorization)
    try:
        async with httpx.AsyncClient(timeout=httpx.Timeout(10, connect=4)) as client:
            response = await client.get(f"{judge0_url()}/languages/", headers=judge0_headers())
            response.raise_for_status()
            languages = response.json()
            return [{"id": item["id"], "name": item["name"]} for item in languages if "id" in item and "name" in item]
    except (httpx.HTTPError, ValueError, KeyError) as error:
        logger.warning("Could not load compiler languages: %s", error)
        raise HTTPException(status_code=503, detail="The compiler is unavailable right now.") from error


@app.post("/compiler/execute")
async def compiler_execute(data: CompilerRequest, authorization: str | None = Header(default=None)):
    authenticated_user(authorization)
    base_url = judge0_url()
    headers = judge0_headers()
    async with httpx.AsyncClient(timeout=httpx.Timeout(12, connect=4)) as client:
        try:
            submission = await client.post(
                f"{base_url}/submissions/?base64_encoded=false&wait=false",
                headers=headers,
                json={
                    "language_id": data.language_id,
                    "source_code": data.source_code,
                    "stdin": data.stdin,
                    "cpu_time_limit": 2,
                    "wall_time_limit": 5,
                    "memory_limit": 128000,
                    "max_file_size": 1024,
                },
            )
            submission.raise_for_status()
            token = submission.json().get("token")
            if not token:
                raise HTTPException(status_code=502, detail="The compiler did not return a submission ID.")

            result = None
            for _ in range(20):
                await asyncio.sleep(0.4)
                poll = await client.get(
                    f"{base_url}/submissions/{token}/?base64_encoded=false&fields=status,stdout,stderr,compile_output,message,time,memory",
                    headers=headers,
                )
                poll.raise_for_status()
                result = poll.json()
                status_id = (result.get("status") or {}).get("id")
                if status_id not in (1, 2):
                    break
            if not result or (result.get("status") or {}).get("id") in (1, 2):
                raise HTTPException(status_code=504, detail="The compiler took too long. Try again.")
            return {
                "status": (result.get("status") or {}).get("description", "Finished"),
                "stdout": result.get("stdout") or "",
                "stderr": result.get("stderr") or "",
                "compile_output": result.get("compile_output") or "",
                "message": result.get("message") or "",
                "time": result.get("time"),
                "memory": result.get("memory"),
            }
        except HTTPException:
            raise
        except httpx.HTTPStatusError as error:
            logger.warning("Judge0 returned HTTP %s", error.response.status_code)
            detail = "The compiler service rejected the request. Check its configuration and try again."
            if error.response.status_code == 429:
                detail = "The compiler is busy. Wait a moment and try again."
            raise HTTPException(status_code=503, detail=detail) from error
        except httpx.HTTPError as error:
            logger.warning("Compiler request failed: %s", error)
            raise HTTPException(status_code=503, detail="Could not reach the compiler. Try again shortly.") from error
        except (ValueError, TypeError, AttributeError) as error:
            logger.warning("Compiler returned an invalid response: %s", error)
            raise HTTPException(status_code=503, detail="The compiler returned an invalid response. Try again shortly.") from error


def authenticated_user(authorization: str | None = Header(default=None)) -> str:
    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(status_code=401, detail="Sign in with Google to continue.")
    user_id = verify_access_token(authorization[7:].strip())
    if not user_id:
        raise HTTPException(status_code=401, detail="Your sign-in session is invalid or expired. Sign in again.")
    return user_id


@app.post("/interview/start")
def start_interview(data: StartInterviewRequest, authorization: str | None = Header(default=None)):

    user_id = authenticated_user(authorization)

    interview_type = data.interview_type.strip()

    if not interview_type:
        raise HTTPException(status_code=400, detail="Interview type is required.")

    agent = InterviewAgent(interview_type, data.difficulty, data.interview_mode)

    response, raw = agent.ask_question(True)
    agent.last_ai_response = raw

    sessions[user_id] = {
        "agent": agent,
        "report": InterviewReport(interview_type),
        "question_count": 1,
        "max_questions": data.max_questions,
        "difficulty": data.difficulty,
        "interview_mode": data.interview_mode,
        "client_id": user_id,
        "practical_questions": bool(response["is_practical"])
    }

    return {
        "question_number": 1,
        "max_questions": data.max_questions,
        "question": response["next_question"],
        "interview_completed": False
    }


@app.post("/interview/answer")
def submit_answer(data: AnswerRequest, authorization: str | None = Header(default=None)):

    user_id = authenticated_user(authorization)

    if user_id not in sessions:
        raise HTTPException(status_code=404, detail="No active interview.")

    session = sessions[user_id]
    agent = session["agent"]

    agent.add_answer(agent.last_ai_response, data.answer)
    if session["question_count"] >= session["max_questions"]:

        report = session["report"].generate_report(
            agent.messages,
            session["practical_questions"]
        )

        try:
            save_interview({
                "client_id": session["client_id"],
                "topic": session["agent"].interview_type,
                "difficulty": session["difficulty"],
                "interview_mode": session["interview_mode"],
                "max_questions": session["max_questions"],
                "overall_score": report.get("overall_score", report.get("knowledge_score")),
                "report": report,
            })
            history_persisted = is_supabase_configured()
        except Exception:
            logger.exception("Could not save completed interview report to Supabase")
            history_persisted = False

        del sessions[user_id]

        return {
            "evaluation": "Interview completed.",
            "interview_completed": True,
            "report": report,
            "history_persisted": history_persisted,
        }


    response, raw = agent.ask_question(False)
    agent.last_ai_response = raw

    session["question_count"] += 1

    if response["is_practical"]:
        session["practical_questions"] = True

    return {
        "evaluation": response["evaluation"],
        "question_number": session["question_count"],
        "max_questions": session["max_questions"],
        "question": response["next_question"],
        "interview_completed": False
    }


@app.post("/interview/finish")
def finish_interview(authorization: str | None = Header(default=None)):

    user_id = authenticated_user(authorization)

    if user_id not in sessions:
        raise HTTPException(status_code=404, detail="No active interview.")

    session = sessions[user_id]

    report = session["report"].generate_report(
        session["agent"].messages,
        session["practical_questions"]
    )

    try:
        save_interview({
            "client_id": session["client_id"],
            "topic": session["agent"].interview_type,
            "difficulty": session["difficulty"],
            "interview_mode": session["interview_mode"],
            "max_questions": session["max_questions"],
            "overall_score": report.get("overall_score", report.get("knowledge_score")),
            "report": report,
        })
        history_persisted = is_supabase_configured()
    except Exception:
        logger.exception("Could not save ended interview report to Supabase")
        history_persisted = False

    del sessions[user_id]

    return {"report": report, "history_persisted": history_persisted}


@app.get("/interview/history")
def interview_history(authorization: str | None = Header(default=None)):
    user_id = authenticated_user(authorization)
    try:
        return {"configured": is_supabase_configured(), "sessions": get_interviews(user_id)}
    except Exception as error:
        logger.exception("Could not load interview history from Supabase")
        raise HTTPException(status_code=503, detail="Could not load saved interview history.") from error


@app.get("/leaderboard")
def leaderboard(authorization: str | None = Header(default=None)):
    authenticated_user(authorization)
    try:
        return get_leaderboard(20)
    except Exception as error:
        logger.exception("Could not load leaderboard from Supabase")
        raise HTTPException(status_code=503, detail="Could not load leaderboard.") from error


app.mount("/", StaticFiles(directory=FRONTEND_DIR, html=True), name="web")
