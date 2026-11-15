from typing import Literal

from pydantic import BaseModel, Field

Difficulty = Literal["Beginner", "Intermediate", "Advanced"]
InterviewMode = Literal["Balanced", "Technical conversation", "Coding & problem solving"]


class QuestionRequest(BaseModel):
    topic: str = Field(min_length=1, max_length=120)
    difficulty: Difficulty = "Intermediate"
    interview_mode: InterviewMode = "Balanced"
    previous_questions: list[str] = Field(default_factory=list, max_length=50)


class QuestionResponse(BaseModel):
    question: str
    is_practical: bool


class EvaluationRequest(BaseModel):
    topic: str = Field(min_length=1, max_length=120)
    question: str = Field(min_length=1, max_length=4000)
    answer: str = Field(min_length=1, max_length=20000)
    difficulty: Difficulty = "Intermediate"
    interview_mode: InterviewMode = "Balanced"


class EvaluationResponse(BaseModel):
    evaluation: str
    score: float = Field(ge=0, le=10)
    next_question: str
    is_practical: bool
