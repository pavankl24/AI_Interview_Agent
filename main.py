from dotenv import load_dotenv
from agent import InterviewAgent
from report import InterviewReport

load_dotenv()

print("====== AI INTERVIEW AGENT ======")
print("1,PYTHON")
print("2,OOP")
print("3,SQL")
print("4,AI/ML")
print("5,FULLSTACK")

choice = input("Select Interview Agent: ")

interview_types = {
    "1": "Python",
    "2": "OOP",
    "3": "SQL",
    "4": "AI/ML",
    "5": "FullStack"
}
def display_report(report_data):

    print("\n====== FINAL INTERVIEW REPORT ======")

    print(f"\nInterview Type: {report_data['interview_type']}")
    print(f"Knowledge Score: {report_data['knowledge_score']}/10")

    if report_data["problem_solving_score"] is None:
        print("Problem Solving Score: Not Assessed")
    else:
        print(
            f"Problem Solving Score: "
            f"{report_data['problem_solving_score']}/10"
        )

    print("\nStrengths:")
    for strength in report_data["strengths"]:
        print(f"- {strength}")

    print("\nWeaknesses:")
    for weakness in report_data["weaknesses"]:
        print(f"- {weakness}")

    print("\nAreas to Improve:")
    for area in report_data["areas_to_improve"]:
        print(f"- {area}")

    print("\nOverall Feedback:")
    print(report_data["overall_feedback"])

    print(f"\nOverall Score: {report_data['overall_score']}/10")

interview_type = interview_types.get(choice, "Python")

max_question = int(input("How many maximum question do you want to attend : "))

print(f"\nStarting {interview_type} Interview....\n")

agent = InterviewAgent(interview_type)
report_generator=InterviewReport(interview_type)

print("Interview has been started (Type 'quit' to exit)")

question_count = 0
first_question = True
practical_questions_asked = False

while True:

    try:
        question_count += 1

        data, ai_response = agent.ask_question(first_question)
        question = data["next_question"]

        if any(keyword in question.lower() for keyword in [
            "write a program",
            "write a function",
            "write code",
            "implement",
            "coding",
            "code",
            "solve",
            "algorithm",
            "list comprehension"
        ]):
            practical_questions_asked = True

        if first_question:
            print(f"\nQuestion {question_count}: {data['next_question']}")
        else:
            print(f"\nEvaluation: {data['evaluation']}")
            print(f"\nQuestion {question_count}: {data['next_question']}")

        candidate_answer = input("Your Answer : ")

        if candidate_answer.strip().lower() == "quit":
            print("Ending the Interview. Good Luck!")
            break

        agent.add_answer(ai_response, candidate_answer)

        first_question = False

        if question_count == max_question:

            print("\nInterview Completed")

            report_data = report_generator.generate_report(agent.messages)
            display_report(report_data)

            break

    except Exception as e:
        print(f"An error occurred: {e}")
        break