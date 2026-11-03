from pathlib import Path
from typing import Literal
from uuid import UUID

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field
from dotenv import load_dotenv

from agent import InterviewAgent
from report import InterviewReport
from database import get_interviews, is_supabase_configured, save_interview

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


class StartInterviewRequest(BaseModel):
    client_id: UUID
    interview_type: str
    max_questions: int = Field(default=5, ge=1, le=50)
    difficulty: Literal["Beginner", "Intermediate", "Advanced"] = "Intermediate"
    interview_mode: Literal[
        "Balanced", "Technical conversation", "Coding & problem solving"
    ] = "Balanced"


class AnswerRequest(BaseModel):
    answer: str


@app.post("/interview/start")
def start_interview(data: StartInterviewRequest):

    interview_type = data.interview_type.strip()

    if not interview_type:
        raise HTTPException(status_code=400, detail="Interview type is required.")

    agent = InterviewAgent(interview_type, data.difficulty, data.interview_mode)

    response, raw = agent.ask_question(True)
    agent.last_ai_response = raw

    sessions["current"] = {
        "agent": agent,
        "report": InterviewReport(interview_type),
        "question_count": 1,
        "max_questions": data.max_questions,
        "difficulty": data.difficulty,
        "interview_mode": data.interview_mode,
        "client_id": str(data.client_id),
        "practical_questions": bool(response["is_practical"])
    }

    return {
        "question_number": 1,
        "max_questions": data.max_questions,
        "question": response["next_question"],
        "interview_completed": False
    }


@app.post("/interview/answer")
def submit_answer(data: AnswerRequest):

    if "current" not in sessions:
        raise HTTPException(status_code=404, detail="No active interview.")

    session = sessions["current"]
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
            history_persisted = False

        del sessions["current"]

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
def finish_interview():

    if "current" not in sessions:
        raise HTTPException(status_code=404, detail="No active interview.")

    session = sessions["current"]

    report = session["report"].generate_report(
        session["agent"].messages,
        session["practical_questions"]
    )

    save_interview({
        "client_id": session["client_id"],
        "topic": session["agent"].interview_type,
        "difficulty": session["difficulty"],
        "interview_mode": session["interview_mode"],
        "max_questions": session["max_questions"],
        "overall_score": report.get("overall_score", report.get("knowledge_score")),
        "report": report,
    })

    del sessions["current"]

    return report


@app.get("/interview/history")
def interview_history(client_id: UUID):
    try:
        return {"configured": is_supabase_configured(), "sessions": get_interviews(str(client_id))}
    except Exception as error:
        raise HTTPException(status_code=503, detail="Could not load saved interview history.") from error


app.mount("/", StaticFiles(directory=FRONTEND_DIR, html=True), name="web")
