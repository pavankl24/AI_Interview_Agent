import json
import logging
import os
import re
from typing import Literal

from groq import Groq
from pydantic import BaseModel, Field, ValidationError, field_validator

logger = logging.getLogger(__name__)


class Evaluation(BaseModel):
    classification: Literal["Excellent", "Good", "Partially Correct", "Incorrect", "Incomplete"]
    correctness_score: float = Field(ge=0, le=10)
    understanding_level: Literal["Beginner", "Intermediate", "Advanced"]
    strengths: list[str] = Field(default_factory=list, max_length=6)
    missing_concepts: list[str] = Field(default_factory=list, max_length=8)
    feedback: str = Field(max_length=500)
    claim_supported: bool = True
    depth_score: float = Field(default=0, ge=0, le=10)
    clarity_score: float = Field(default=0, ge=0, le=10)
    practical_score: float = Field(default=0, ge=0, le=10)

    @field_validator("correctness_score", mode="before")
    @classmethod
    def numeric_score(cls, value):
        if isinstance(value, bool):
            raise ValueError("score must be numeric")
        return float(value)


class Decision(BaseModel):
    action: Literal["FOLLOW_UP", "NEXT_QUESTION"]
    reason: str = Field(max_length=300)
    next_difficulty: Literal["Easy", "Medium", "Hard"]
    next_question: str = Field(min_length=8, max_length=1600)
    topic: str = Field(min_length=1, max_length=100)


class AdaptiveResponse(BaseModel):
    evaluation: Evaluation
    interview_decision: Decision


class QuestionResponse(BaseModel):
    evaluation: str = ""
    next_question: str = Field(min_length=8, max_length=1600)
    is_practical: bool = False
    score: float = Field(default=0, ge=0, le=10)


def _difficulty(value: str) -> str:
    return {"Beginner": "Easy", "Intermediate": "Medium", "Advanced": "Hard"}.get(value, value)


def _legacy_difficulty(value: str) -> str:
    return {"Easy": "Beginner", "Medium": "Intermediate", "Hard": "Advanced"}[value]


class InterviewAgent:
    MAX_FOLLOWUPS = 2

    def __init__(self, interview_type, difficulty="Intermediate", interview_mode="Balanced", context=None):
        self.interview_type = interview_type
        self.difficulty = difficulty
        self.interview_mode = interview_mode
        self.client = Groq(api_key=os.getenv("GROQ_API_KEY"))
        self.context = context or {}
        grounding = (" Candidate context (use only these facts; never invent projects, skills, employers, or achievements): " + json.dumps(self.context, ensure_ascii=False)[:16000]) if self.context else ""
        self.messages = [{"role": "system", "content": f"You are a professional, concise technical interviewer for {interview_type}. Ask one question at a time. Never reveal answers or give unsolicited hints. Interview format: {interview_mode}." + grounding}, {"role": "user", "content": f"Start a {interview_type} interview."}]
        self.asked_questions = []
        self.last_ai_response = ""
        self.evaluation_history = []

    def export_state(self):
        return {"interview_type": self.interview_type, "difficulty": self.difficulty,
                "interview_mode": self.interview_mode, "messages": self.messages, "context": self.context,
                "asked_questions": self.asked_questions, "last_ai_response": self.last_ai_response,
                "evaluation_history": self.evaluation_history}

    @classmethod
    def from_state(cls, state):
        agent = cls(state["interview_type"], state["difficulty"], state["interview_mode"])
        agent.messages = state["messages"]
        agent.context = state.get("context", {})
        agent.asked_questions = state.get("asked_questions", [])
        agent.last_ai_response = state.get("last_ai_response", "")
        agent.evaluation_history = state.get("evaluation_history", [])
        return agent

    def set_difficulty(self, difficulty):
        self.difficulty = difficulty

    def _completion(self, messages):
        try:
            return self.client.chat.completions.create(model="openai/gpt-oss-20b", messages=messages,
                response_format={"type": "json_object"})
        except Exception as error:
            logger.exception("Groq interview request failed")
            raise ValueError("The interviewer service is unavailable. Please retry shortly.") from error

    @staticmethod
    def _parse(content, schema):
        if not content:
            raise ValueError("The AI returned an empty response.")
        try:
            data = json.loads(content)
            return schema.model_validate(data)
        except (json.JSONDecodeError, ValidationError, TypeError) as error:
            logger.warning("Groq returned invalid structured interview data: %s", error)
            raise ValueError("The interviewer returned an invalid response. Please retry.") from error

    def ask_question(self, first_question=False, question_only=False):
        prompt = f"""Generate exactly one {self.interview_type} interview question at {_difficulty(self.difficulty)} difficulty.
Interview mode: {self.interview_mode}. Return JSON with keys evaluation (empty string), next_question, is_practical (boolean), score (0).
Do not repeat any previous question. Previously asked: {self.asked_questions[-20:]}
Candidate context: {json.dumps(self.context, ensure_ascii=False)[:16000]}. Use only supported context facts."""
        response = self._completion(self.messages + [{"role": "user", "content": prompt}])
        try:
            data = QuestionResponse.model_validate_json(response.choices[0].message.content)
            question = data.next_question.strip()
            if len(question) < 8 or any(question.casefold() == q.casefold() for q in self.asked_questions):
                raise ValueError("The interviewer returned a duplicate or empty question.")
        except (json.JSONDecodeError, KeyError, TypeError, ValueError) as error:
            logger.warning("Groq returned invalid initial question: %s", error)
            raise ValueError("The interviewer could not generate a valid question. Please retry.") from error
        result = {"evaluation": "", "next_question": question,
                  "is_practical": data.is_practical, "score": 0}
        self.asked_questions.append(question)
        self.last_ai_response = json.dumps(result)
        return result, self.last_ai_response

    def assess_answer(self, question, answer, followup_count=0, previous_answers=None, concepts_tested=None):
        prompt = f"""Assess the answer to this current interview question. Base the assessment on the candidate's actual response.
Topic: {self.interview_type}; current difficulty: {_difficulty(self.difficulty)}; format: {self.interview_mode}.
Current question: {question}
Candidate answer: {answer}
Prior answers (for repetition detection): {previous_answers or []}
Concepts already tested: {concepts_tested or []}
Candidate context: {json.dumps(self.context, ensure_ascii=False)[:16000]}. Treat this as the only source of resume facts; distinguish an unsupported claim from an incorrect technical answer.
Follow-ups already asked for this main question: {followup_count} of {self.MAX_FOLLOWUPS}.
Return JSON matching: {{"evaluation":{{"classification":"Excellent|Good|Partially Correct|Incorrect|Incomplete","correctness_score":0,"depth_score":0,"clarity_score":0,"practical_score":0,"claim_supported":true,"understanding_level":"Beginner|Intermediate|Advanced","strengths":[],"missing_concepts":[],"feedback":"concise"}},"interview_decision":{{"action":"FOLLOW_UP|NEXT_QUESTION","reason":"...","next_difficulty":"Easy|Medium|Hard","next_question":"one question only","topic":"..."}}}}.
Incomplete answers need a focused clarification. Partially Correct answers investigate a stated gap. Incorrect answers get a simpler diagnostic question. Good answers move to a related concept or harder level; excellent answers get a deeper challenge. Ask a follow-up only when useful and follow-up count is under {self.MAX_FOLLOWUPS}; otherwise move to the next main question. Never ask an unrelated question or repeat a previous question. Do not reveal the answer or give a hint. Keep feedback concise. Set a justified difficulty based on demonstrated performance."""
        raw = self._completion(self.messages + [{"role": "user", "content": prompt}]).choices[0].message.content
        parsed = self._parse(raw, AdaptiveResponse)
        evaluation = parsed.evaluation
        decision = parsed.interview_decision
        # Enforce bounded follow-ups and sensible actions on the server.
        if followup_count >= self.MAX_FOLLOWUPS:
            decision.action = "NEXT_QUESTION"
        if evaluation.classification in ("Incorrect", "Incomplete", "Partially Correct") and followup_count < self.MAX_FOLLOWUPS:
            decision.action = "FOLLOW_UP"
        score = round(max(0, min(10, evaluation.correctness_score)), 1)
        if any(decision.next_question.casefold() == q.casefold() for q in self.asked_questions):
            decision.action = "NEXT_QUESTION"
            decision.next_question = self._generate_distinct_question(decision.next_question)
        if decision.action == "FOLLOW_UP":
            current_level = _difficulty(self.difficulty)
            decision.next_difficulty = (
                "Medium" if current_level == "Hard" else "Easy" if current_level == "Medium" else "Easy"
            ) if evaluation.classification == "Incorrect" else current_level
        elif score >= 8 and _difficulty(self.difficulty) != "Hard":
            decision.next_difficulty = "Hard" if _difficulty(self.difficulty) == "Medium" and score >= 9 else "Medium"
        elif score < 5 and _difficulty(self.difficulty) != "Easy":
            decision.next_difficulty = "Easy" if _difficulty(self.difficulty) == "Medium" else "Medium"
        self.difficulty = _legacy_difficulty(decision.next_difficulty)
        self.asked_questions.append(decision.next_question)
        result = {"evaluation": evaluation.feedback, "score": score,
                  "classification": evaluation.classification,
                  "correctness_score": evaluation.correctness_score,
                  "depth_score": evaluation.depth_score,
                  "clarity_score": evaluation.clarity_score,
                  "practical_score": evaluation.practical_score,
                  "claim_supported": evaluation.claim_supported,
                  "understanding_level": evaluation.understanding_level,
                  "strengths": evaluation.strengths, "missing_concepts": evaluation.missing_concepts,
                  "action": decision.action, "reason": decision.reason,
                  "next_difficulty": decision.next_difficulty,
                  "topic": decision.topic or self.interview_type,
                  "next_question": decision.next_question,
                  "is_practical": self.interview_mode != "Technical conversation" and bool(re.search(r"\b(code|implement|write|algorithm|query|function|solve)\b", decision.next_question, re.I))}
        self.evaluation_history.append({"question": question, "answer": answer, **result})
        return result, json.dumps(result)

    def _generate_distinct_question(self, duplicate):
        prompt = f"Generate one distinct, relevant {self.interview_type} interview question at {_difficulty(self.difficulty)} difficulty. Do not repeat: {self.asked_questions[-20:]}. This question was rejected as duplicate: {duplicate}. Return JSON with next_question, is_practical, evaluation, score."
        response = self._completion(self.messages + [{"role": "user", "content": prompt}])
        data = json.loads(response.choices[0].message.content)
        question = str(data.get("next_question", "")).strip()
        if len(question) < 8 or any(question.casefold() == q.casefold() for q in self.asked_questions):
            raise ValueError("The interviewer could not generate a distinct question. Please retry.")
        return question

    def score_answer(self, question, answer):
        result, _ = self.assess_answer(question, answer, followup_count=self.MAX_FOLLOWUPS)
        return result["score"]

    def add_answer(self, ai_response, candidate_answer):
        self.messages.append({"role": "assistant", "content": ai_response})
        self.messages.append({"role": "user", "content": candidate_answer})
