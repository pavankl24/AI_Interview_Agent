from dotenv import load_dotenv
from agent import InterviewAgent

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
    "3": "Sql",
    "4": "Ai/Ml",
    "5": "FullStack"
}

interview_type = interview_types.get(choice, "Python")

max_question = int(input("How many maximum question do you want to attend : "))

print(f"\nStarting {interview_type} Interview....\n")

agent = InterviewAgent(interview_type)

print("Interview has been started (Type 'quit' to exit)")

question_count = 0
first_question = True

while True:

    try:
        question_count += 1

        data, ai_response = agent.ask_question(first_question)

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
            break

    except Exception as e:
        print(f"An error occurred: {e}")
        break