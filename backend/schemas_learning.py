from typing import Literal

from pydantic import BaseModel, Field


class GoalRequest(BaseModel):
    goal: str | None = Field(default=None, max_length=200)


class TaskUpdate(BaseModel):
    status: Literal["Not Started", "In Progress", "Completed"]


class HintRequest(BaseModel):
    exercise_id: str
    request: Literal["hint"] = "hint"


class ReassessmentRequest(BaseModel):
    question: str | None = Field(default=None, max_length=1600)
    answer: str | None = Field(default=None, max_length=10000)


class ExerciseSubmission(BaseModel):
    exercise_id: str = Field(min_length=3, max_length=120)
    language_id: int = Field(ge=1, le=10000)
    source_code: str = Field(min_length=1, max_length=20000)

