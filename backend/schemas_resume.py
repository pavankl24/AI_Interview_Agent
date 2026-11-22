from typing import Literal

from pydantic import BaseModel, Field, model_validator


class ResumeProfile(BaseModel):
    name: str = ""
    summary: str = ""
    education: list[str] = Field(default_factory=list, max_length=20)
    technical_skills: list[str] = Field(default_factory=list, max_length=80)
    programming_languages: list[str] = Field(default_factory=list, max_length=40)
    frameworks_tools: list[str] = Field(default_factory=list, max_length=60)
    projects: list[dict] = Field(default_factory=list, max_length=30)
    experience: list[dict] = Field(default_factory=list, max_length=30)
    certifications: list[str] = Field(default_factory=list, max_length=40)


class ProfileUpdate(BaseModel):
    profile: ResumeProfile


class MatchRequest(BaseModel):
    job_description: str = Field(min_length=20, max_length=20000)


class InterviewStart(BaseModel):
    resume_id: str = Field(min_length=1, max_length=80)
    mode: Literal["Resume Interview", "Resume + Job Description Interview", "Project Deep-Dive Interview", "Technical Skills Interview", "HR and Behavioral Interview"] = "Resume Interview"
    target_role: str = Field(default="", max_length=120)
    experience_level: Literal["Beginner", "Intermediate", "Advanced"] = "Intermediate"
    difficulty: Literal["Easy", "Medium", "Hard"] = "Medium"
    question_count: int = Field(default=5, ge=1, le=20)
    job_description: str = Field(default="", max_length=20000)

    @model_validator(mode="after")
    def require_job_description_for_job_mode(self):
        if self.mode == "Resume + Job Description Interview" and len(self.job_description.strip()) < 20:
            raise ValueError("Add a job description of at least 20 characters for this interview mode.")
        return self


class AnswerSubmission(BaseModel):
    answer: str = Field(min_length=1, max_length=20000)
