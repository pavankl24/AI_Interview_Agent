import os
import json
from dotenv import load_dotenv
from groq import Groq
load_dotenv()
print("====== AI INTERVIEW AGENT ======")
print("1,PYTHON")
print("2,OOP")
print("3,SQL")
print("4,AI/ML")
print("5,FULLSTACK")
choice=input("Select Interview Agent: ")
interview_types={
    "1":"Python",
    "2":"OOP",
    "3":"Sql",
    "4":"Ai/Ml",
    "5":"FullStack"
}
interview_type=interview_types.get(choice,"python")
max_question=int(input("How many maximum question do you want to attend :"))
print(f"\n Starting {interview_type} Interview....\n")
client=Groq(api_key=os.getenv("GROQ_API_KEY"))
messages=[
        {
            "role":"system",
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
            "role":"user",
            "content":f"hello i'm a fresher i'm here to take {interview_type} interview"
        }
    ]
print(f"Interview as been started (Type 'quit to exit)")

def generate_report(messages):
    report_prompt=f"""
Based only on the interview conversation above, generate a final interview report.

Interview type: {interview_type}

Include:

1. Interview Type
2. Knowledge demonstrated in {interview_type}, scored out of 10.
3. Problem-solving ability, scored out of 10 only if practical questions were asked.
4. Strengths.
5. Weaknesses.
6. Areas to improve.
7. Overall feedback.
8. Overall score out of 10.

IMPORTANT:
- Evaluate ONLY what the candidate actually demonstrated.
- Do not assume knowledge that was never tested.
- Do not give scores for unrelated topics.
- Do not invent strengths or weaknesses.
- Be honest and concise.
- Return your response ONLY as valid JSON.
- The JSON must contain exactly two keys: "evaluation" and "next_question".
- "evaluation" must contain the brief evaluation of the candidate's previous answer.
- "next_question" must contain exactly one new interview question.
- Do not include Markdown, code fences, or any text outside the JSON.
- Return your response as valid JSON.
"""
    report_messages = [
    {
        "role": "system",
        "content": f"""
You are an interview report generator.

Generate a final report for a {interview_type} interview.

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
"""
    }
]

    report_messages.append({
        "role":"user",
        "content":f"""
here iz the interview conversation
{messages[1:]}
Generate the final report now.
"""
    })
    response=client.chat.completions.create(
        model="openai/gpt-oss-20b",
        messages=report_messages
    )
    return response.choices[0].message.content
question_count=0
asked_questions=[]
first_question=True
while True:
    try:
        question_count+=1
        if first_question:
            question_instruction = f"""
        Ask the first {interview_type} interview question.

        There is no candidate answer yet.

        Do not evaluate anything.
        Return an empty evaluation.

        Previously asked questions: {asked_questions}

        Ask exactly one question.
        Do not repeat previous questions.
        """
        else:
            question_instruction = f"""
            Evaluate the candidate's previous answer briefly.

            Then ask exactly one new {interview_type} interview question.

            Previously asked questions: {asked_questions}

            Do not repeat previous questions.
        """

        response=client.chat.completions.create(
            model="openai/gpt-oss-20b",
            messages=messages+[
                {
                    "role":"user",
                    "content":question_instruction
                }
            ],
            response_format={"type":"json_object"}
        )
        ai_response=response.choices[0].message.content
        data=json.loads(ai_response)
        asked_questions.append(data["next_question"])
        print(f"\nEvaluation: {data['evaluation']}")
        print(f"\nNext_question: {data['next_question']}")
        candidate_answer=input("Your Answer : ")
        first_question = False
        if candidate_answer.strip().lower()=="quit":
            print("Ending the Interview GoodLuck!")
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
            report_data=json.loads(report)
            print("\n ======FINAL INTERVIEW REPORT======")
            print(f"\nInterview Type: {report_data['interview_type']}")
            print(f"Knowledge Score: {report_data['knowledge_score']}/10")
            print(f"Problem Solving Score: {report_data['problem_solving_score']}/10")
            print("\nStrengths: ")
            for strength in report_data["strengths"]:
                print(f"-{strength}")
            print(f"\nWeaknesses: ")
            for weakness in report_data["weaknesses"]:
                print(f"-{weakness}")
            for area in report_data["areas_to_improve"]:
                print(f"-{area}")
            print("\nOverall feedback")
            print(report_data["overall_feedback"])
            print(f"\nOverAll Score: {report_data['overall_score']}/10")

            break

    except Exception as e:
        print(f"An error occured:{e}")
        break

