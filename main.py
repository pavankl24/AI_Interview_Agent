import os
from dotenv import load_dotenv
from groq import Groq
load_dotenv()
client=Groq(api_key=os.getenv("GROQ_API_KEY"))
response=client.chat.completions.create(
    model="openai/gpt-oss-20b",
    messages=[
        {
            "role":"system",
            "content": """
    You are a Python technical interviewer for a fresher.
    Ask one interview question at a time.
    Do not give the answer immediately.
    After the candidate answers, evaluate their answer briefly
    and then ask the next question.
    """
        },
        {
            "role":"user",
            "content":"hello i'm a fresher i'm here to take interview"
        }
    ]
)
ai_question=response.choices[0].message.content
print(f"\nInterviewer : {ai_question}")
answer=input("Your answer :")
response_evaluation=client.chat.completions.create(
    model="openai/gpt-oss-20b",
    messages=[
        {
            "role":"system",
            "content":"you are a python interviewer for a fresher"
        },
        {
            "role":"assistant",
            "content":ai_question
        },
        {
            "role":"user",
            "content":answer
        }

    ]
)
print(f"\nInterviewer : {response_evaluation.choices[0].message.content}")