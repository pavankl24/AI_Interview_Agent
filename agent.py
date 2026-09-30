import os
import json
from groq import Groq


class InterviewAgent:

    def __init__(self, interview_type):
        self.interview_type = interview_type
        self.client = Groq(api_key=os.getenv("GROQ_API_KEY"))
        self.messages = [
            {
                "role": "system",
                "content": f"""
You are a strict technical interviewer conducting a {interview_type} interview for a fresher.

Your job is ONLY to:
1. Ask one interview question.
2. Wait for the candidate's answer.
3. Evaluate the candidate's answer briefly.
4. Then ask exactly ONE new question.

IMPORTANT RULES:

- NEVER answer your own question.
- NEVER provide an example answer before the candidate responds.
- NEVER provide the correct code unless explicitly asked for the answer.
- If the candidate says "don't know", "idk", gives nonsense, or gives an incomplete answer, briefly say what was missing and move to the next question.
- Do not turn the interview into a teaching session.
- Do not repeat previously asked questions.
- Start with basic questions and gradually increase difficulty.
- Keep the questions relevant to {interview_type}.
- Ask practical coding questions when appropriate.
- Keep evaluations short, around 1-3 sentences.
- Ask exactly one question at the end of every response.

The interview type is:
{interview_type}

Return your response as valid JSON.

The JSON must contain exactly two keys:
"evaluation" and "next_question".
"""
            },
            {
                "role": "user",
                "content": f"hello i'm a fresher i'm here to take {interview_type} interview"
            }
        ]

        self.asked_questions = []

    def ask_question(self, first_question=False):

        if first_question:
            question_instruction = f"""
Ask the first {self.interview_type} interview question.

There is no candidate answer yet.

Do not evaluate anything.
Return an empty evaluation.

Previously asked questions: {self.asked_questions}

Ask exactly one question.
Do not repeat previous questions.
"""
        else:
            question_instruction = f"""
Evaluate the candidate's previous answer briefly.

Then ask exactly one new {self.interview_type} interview question.

Previously asked questions: {self.asked_questions}

Do not repeat previous questions.
"""

        response = self.client.chat.completions.create(
            model="openai/gpt-oss-20b",
            messages=self.messages + [
                {
                    "role": "user",
                    "content": question_instruction
                }
            ],
            response_format={"type": "json_object"}
        )

        ai_response = response.choices[0].message.content

        data = json.loads(ai_response)

        self.asked_questions.append(data["next_question"])

        return data, ai_response

    def add_answer(self, ai_response, candidate_answer):

        self.messages.append({
            "role": "assistant",
            "content": ai_response
        })

        self.messages.append({
            "role": "user",
            "content": candidate_answer
        })