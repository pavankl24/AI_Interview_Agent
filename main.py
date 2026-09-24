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
5,After the candidate answers:
- briefly evaluate their answer
- mention what was correct or missing
- then ask exactly one next question
6,do not provide the complete answer or complete code unless all questions are over,
when candidates give wrong answer
7,don't repeat the question
8,Focus on python,OOP,SQL,AI/ML and software development
9,give each question to a question number 

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
def generate_report(messages):
    report_prompt="""
based on the above interview conversation, generate final interview report
Include:
1,Python knowledge score out of 10.
2,OOP knowledge score out of 10.
3,Problem solving knowledge out of 10.
4,strengths.
5,weakness.
6,Areas to improve.
7,overall feedback and overall score out of 10


be honest interview the candidate based only on their genuine answer
"""
    report_messages=messages.copy()
    report_messages.append({
        "role":"user",
        "content":report_prompt
    })
    response=client.chat.completions.create(
        model="openai/gpt-oss-20b",
        messages=report_messages
    )
    return response.choices[0].message.content
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
            report=generate_report(messages)
            print("\n ======FINAL INTERVIEW REPORT======")
            print(report)
            break

    except Exception as e:
        print(f"An error occured:{e}")

