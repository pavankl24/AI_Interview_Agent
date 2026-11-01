from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field
from typing import Literal
from dotenv import load_dotenv

from agent import InterviewAgent
from report import InterviewReport

load_dotenv()

app = FastAPI(title="AI Interview Agent API")

WEB_DIR = Path(__file__).parent / "web"


@app.get("/app", include_in_schema=False)
def web_app():
    return FileResponse(WEB_DIR / "index.html")


@app.get("/", include_in_schema=False)
def home():
    return FileResponse(WEB_DIR / "index.html")

sessions = {}


class StartInterviewRequest(BaseModel):
    interview_type: str
    max_questions: int = Field(default=5, ge=1, le=50)
    difficulty: Literal["Beginner", "Intermediate", "Advanced"] = "Intermediate"


class AnswerRequest(BaseModel):
    answer: str


@app.post("/interview/start")
def start_interview(data: StartInterviewRequest):

    interview_type = data.interview_type.strip()

    if not interview_type:
        raise HTTPException(status_code=400, detail="Interview type is required.")

    agent = InterviewAgent(interview_type, data.difficulty)

    response, raw = agent.ask_question(True)
    agent.last_ai_response = raw

    sessions["current"] = {
        "agent": agent,
        "report": InterviewReport(interview_type),
        "question_count": 1,
        "max_questions": data.max_questions,
        "difficulty": data.difficulty,
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

        del sessions["current"]

        return {
            "evaluation": "Interview completed.",
            "interview_completed": True,
            "report": report
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

    del sessions["current"]

    return report


app.mount("/", StaticFiles(directory=WEB_DIR), name="web")
