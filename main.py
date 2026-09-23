import os
from dotenv import load_dotenv
from groq import Groq
load_dotenv()
client=Groq(api_key=os.getenv("GROQ_API_KEY"))
messages=[
        {
            "role":"system",
            "content": """
You are a python interviewer interviewing a fresher
rules:
1,Ask one question at a time
2,start with python basic questions
3,gradually increase the difficulty level
4,after the candidate answers,breifly evaluate the answer 
5,Then ask the next question
6,Do not give answer immediately
7,Focus on python,OOP,SQL,AI/ML and software development

    """
        },
        {
            "role":"user",
            "content":"hello i'm a fresher i'm here to take interview"
        }
    ]
print(f"Interview as been started (Type 'quit to exit)")
question_count=0
max_question=5

while True:
    try:
        question_count+=1
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
        if question_count==max_question:
            print("\n Interview Completed")
            break

    except Exception as e:
        print(f"An error occured:{e}")

