from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from dotenv import load_dotenv

from agent import InterviewAgent
from report import InterviewReport

load_dotenv()

app = FastAPI(title="AI Interview Agent API")
@app.get("/")
def home():
    return {"message": "AI Interview Agent API is running!"}

# Store active interview sessions
sessions = {}

# ---------- Request Models ----------

class StartInterviewRequest(BaseModel):
    interview_type: str

class AnswerRequest(BaseModel):
    answer: str

# ---------- Start Interview ----------

@app.post("/interview/start")
def start_interview(data: StartInterviewRequest):

    agent = InterviewAgent(data.interview_type)

    response, raw = agent.ask_question(True)

    sessions["current"] = {
        "agent": agent,
        "report": InterviewReport(data.interview_type),
        "question_count": 1,
        "first_question": False,
        "practical_questions": response["is_practical"]
    }

    return {
        "question_number": 1,
        "question": response["next_question"]
    }

# ---------- Submit Answer ----------

@app.post("/interview/answer")
def submit_answer(data: AnswerRequest):

    if "current" not in sessions:
        raise HTTPException(status_code=404, detail="No active interview.")

    session = sessions["current"]

    agent = session["agent"]

    previous_raw = agent.last_ai_response

    agent.add_answer(previous_raw, data.answer)

    response, raw = agent.ask_question(False)

    agent.last_ai_response = raw

    session["question_count"] += 1

    if response["is_practical"]:
        session["practical_questions"] = True

    return {
        "evaluation": response["evaluation"],
        "question_number": session["question_count"],
        "question": response["next_question"]
    }

# ---------- Finish Interview ----------

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