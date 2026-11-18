import os
from groq import Groq
import json
from pydantic import BaseModel, Field, ValidationError


class ReportData(BaseModel):
    interview_type: str
    knowledge_score: float = Field(ge=0, le=10)
    problem_solving_score: float | None = Field(default=None, ge=0, le=10)
    strengths: list[str] = Field(default_factory=list)
    weaknesses: list[str] = Field(default_factory=list)
    areas_to_improve: list[str] = Field(default_factory=list)
    overall_feedback: str = ""
    overall_score: float = Field(ge=0, le=10)
    topic_performance: list[dict] = Field(default_factory=list)
    difficulty_progression: list[str] = Field(default_factory=list)
    followup_question_count: int = Field(default=0, ge=0)
    personalized_recommendations: list[str] = Field(default_factory=list)


class InterviewReport:

    def __init__(self, interview_type):
        self.interview_type = interview_type
        self.client = Groq(api_key=os.getenv("GROQ_API_KEY"))

    def generate_report(self, messages,practical_questions_asked, interview_context=None):

        report_messages = [
            {
                "role": "system",
                "content": f"""
You are an interview report generator.

Generate a final report for a {self.interview_type} interview.

Analyze only what the candidate actually answered.

Do not act as the interviewer.
Do not ask another interview question.
Do not provide evaluation and next_question.

Return ONLY valid JSON.

The JSON must contain exactly these keys:

interview_type
knowledge_score
problem_solving_score
strengths
weaknesses
areas_to_improve
overall_feedback
overall_score

Data type requirements:

- strengths must be a JSON array of short strings.
- weaknesses must be a JSON array of short strings.
- areas_to_improve must be a JSON array of short strings.
- knowledge_score must be a number from 0 to 10.
- Only give a problem_solving_score if the interview actually included a question requiring the candidate to write code, solve a programming problem, or design an algorithm.
- Conceptual questions such as "What is a list?", "What is OOP?", or "What is mutable vs immutable?" do NOT count as problem-solving questions.
- If no practical coding/problem-solving question was asked, problem_solving_score must be null.
- If practical coding/problem-solving questions were asked, problem_solving_score must be a number from 0 to 10.
Also include topic_performance (array of objects with topic and score), difficulty_progression (array of Easy/Medium/Hard strings), followup_question_count (integer), and personalized_recommendations (array of short strings).
"""
            }
        ]

        report_messages.append({
            "role": "user",
            "content": f"""
Here is the interview conversation:

{messages}

Structured interview evaluations and state:
{json.dumps(interview_context or {}, ensure_ascii=False)}

Generate the final report now.
"""
        })

        response = self.client.chat.completions.create(
            model="openai/gpt-oss-20b",
            messages=report_messages
        )

        report = response.choices[0].message.content

        if not report:
            raise ValueError("The AI returned an empty interview report.")

        report = report.strip()

        # Remove Markdown code fences if present
        if report.startswith("```"):
            report = report.split("\n", 1)[1]
            report = report.rsplit("```", 1)[0].strip()

        result = json.loads(report)

        # Ensure the parsed report is a dictionary
        if isinstance(result, str):
            result = json.loads(result)

        if not isinstance(result, dict):
            raise ValueError("The AI report must be a JSON object.")

        if not practical_questions_asked:
            result["problem_solving_score"] = None
        result.setdefault("topic_performance", [])
        result.setdefault("difficulty_progression", [])
        result.setdefault("followup_question_count", 0)
        result.setdefault("personalized_recommendations", result.get("areas_to_improve", []))
        context = interview_context or {}
        history = context.get("evaluations", [])
        if context:
            result["difficulty_progression"] = context.get("difficulty_progression", [])
            result["followup_question_count"] = int(context.get("followup_question_count", 0))
            by_topic = {}
            for item in history:
                topic = item.get("topic") or self.interview_type
                by_topic.setdefault(topic, []).append(float(item.get("score", 0)))
            result["topic_performance"] = [
                {"topic": topic, "score": round(sum(scores) / len(scores), 1)}
                for topic, scores in by_topic.items() if scores
            ]
        try:
            return ReportData.model_validate(result).model_dump()
        except ValidationError as error:
            raise ValueError("The AI returned an invalid interview report.") from error
