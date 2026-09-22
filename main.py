import os
from dotenv import load_dotenv
from groq import Groq
load_dotenv()
client=Groq(api_key=os.getenv("GROQ_API_KEY"))
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
print(f"Interview as been started (Type 'quit to exit)")
while True:
    try:
        response=client.chat.completions.create(
            model="openai/gpt-oss-20b",
            messages=messages
        )
        ai_response=response.choices[0].message.content
        print(f"\nInterviewer Question : {ai_response}")
        candidate_answer=input("Your Answer : ")
        if candidate_answer.strip().lower()=="quit":
            print("Ending the Interviiew GoodLuck!")
            break
        messages.append({
            "role":"assistant",
            "content":ai_response
        })
        messages.append({
            "role":"user",
            "content":candidate_answer
        })

    except Exception as e:
        print(f"An error occured:{e}")

