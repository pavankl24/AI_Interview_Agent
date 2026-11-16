import json
import logging

from fastapi import APIRouter, HTTPException, Request

from backend.schemas import EvaluationRequest, EvaluationResponse, QuestionRequest, QuestionResponse
from backend.services.ai_service import InterviewAgent
from backend.rate_limit import limiter

router = APIRouter(prefix="/api", tags=["AI interview"])
logger = logging.getLogger(__name__)


@router.post("/question", response_model=QuestionResponse)
@limiter.limit("5/minute")
def create_question(request: Request, data: QuestionRequest):
    try:
        agent = InterviewAgent(data.topic.strip(), data.difficulty, data.interview_mode)
        agent.asked_questions = list(data.previous_questions)
        question, _raw = agent.ask_question(first_question=True)
        return QuestionResponse(question=question["next_question"], is_practical=question["is_practical"])
    except Exception as error:
        logger.exception("Could not generate an interview question")
        raise HTTPException(status_code=502, detail="The AI interview service could not generate a question.") from error


@router.post("/evaluate", response_model=EvaluationResponse)
@limiter.limit("10/minute")
def evaluate_answer(request: Request, data: EvaluationRequest):
    try:
        agent = InterviewAgent(data.topic.strip(), data.difficulty, data.interview_mode)
        agent.asked_questions = [data.question]
        prior_turn = (
            '{"evaluation":"","next_question":'
            + json.dumps(data.question)
            + ',"is_practical":false,"score":0}'
        )
        agent.add_answer(prior_turn, data.answer.strip())
        result, _raw = agent.ask_question(first_question=False)
        return EvaluationResponse(
            evaluation=result["evaluation"],
            score=result["score"],
            next_question=result["next_question"],
            is_practical=result["is_practical"],
        )
    except Exception as error:
        logger.exception("Could not evaluate an interview answer")
        raise HTTPException(status_code=502, detail="The AI interview service could not evaluate this answer.") from error
