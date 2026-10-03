import os
from groq import Groq
import json


class InterviewReport:

    def __init__(self, interview_type):
        self.interview_type = interview_type
        self.client = Groq(api_key=os.getenv("GROQ_API_KEY"))

    def generate_report(self, messages,practical_questions_asked):

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
"""
            }
        ]

        report_messages.append({
            "role": "user",
            "content": f"""
Here is the interview conversation:

{messages}

Generate the final report now.
"""
        })

        response = self.client.chat.completions.create(
            model="openai/gpt-oss-20b",
            messages=report_messages
        )

        report = response.choices[0].message.content
        result=json.loads(report)
        return result