import json
data={
    "evaluation":"Your answer is partially correct",
    "next_question":"What is a dictionary in python"
}
print(json.dumps(data))
json_data = '{"evaluation": "Good answer", "next_question": "What is a tuple?"}'
results=json.loads(json_data)
print(results["evaluation"])
print(results["next_question"])