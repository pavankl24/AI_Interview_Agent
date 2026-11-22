"""Private, persisted learning plans built from existing interview reports."""
import json
import logging
import os
from datetime import datetime, timezone
from typing import Literal

from groq import Groq
from pydantic import BaseModel, Field, ValidationError

from database import _client

logger = logging.getLogger(__name__)


class Exercise(BaseModel):
    title: str = Field(min_length=3, max_length=120)
    problem: str = Field(min_length=20, max_length=1500)
    difficulty: Literal["Easy", "Medium", "Hard"]
    input_example: str = Field(max_length=500)
    output_example: str = Field(max_length=500)
    constraints: list[str] = Field(default_factory=list, max_length=8)
    concepts: list[str] = Field(default_factory=list, max_length=8)
    tests: list[dict] = Field(default_factory=list, max_length=12)


class Task(BaseModel):
    topic: str = Field(min_length=1, max_length=120)
    description: str = Field(min_length=5, max_length=500)
    stage: Literal["Foundation", "Improvement", "Practice", "Advanced", "Assessment"]
    priority: Literal["High", "Medium", "Low"]
    understanding: Literal["Strong", "Revision", "Weak", "Not Assessed"]
    difficulty: Literal["Easy", "Medium", "Hard"]
    estimated_minutes: int = Field(ge=5, le=600)
    prerequisites: list[str] = Field(default_factory=list, max_length=8)
    completion_criteria: str = Field(min_length=5, max_length=400)
    exercises: list[Exercise] = Field(default_factory=list, max_length=5)


class Plan(BaseModel):
    tasks: list[Task] = Field(min_length=1, max_length=20)


def _reports(user_id: str) -> list[dict]:
    client = _client()
    if client is None:
        return []
    res = client.table("interview_sessions").select("id,topic,difficulty,overall_score,report,created_at").eq("client_id", user_id).order("created_at", desc=True).limit(50).execute()
    reports = res.data or []
    resume_rows = client.table("resume_interview_sessions").select("id,report,completed_at").eq("user_id", user_id).eq("status", "completed").order("completed_at", desc=True).limit(50).execute().data or []
    reports.extend({"id": row["id"], "topic": "Resume interview", "difficulty": "Intermediate", "overall_score": (row.get("report") or {}).get("overall_score"), "report": row.get("report") or {}, "created_at": row.get("completed_at")} for row in resume_rows)
    return reports


def sync_resume_interview(user_id: str) -> dict:
    """Append only new evidence-based topics to an existing roadmap, preserving progress."""
    client = _client()
    if client is None:
        return {"added": 0}
    roadmaps = client.table("learning_roadmaps").select("id").eq("user_id", user_id).order("created_at", desc=True).limit(1).execute().data or []
    if not roadmaps:
        return {"added": 0}
    roadmap_id = roadmaps[0]["id"]
    rows = client.table("learning_tasks").select("topic,sequence").eq("roadmap_id", roadmap_id).execute().data or []
    existing = {str(row["topic"]).casefold().strip() for row in rows}
    plan = generate_plan(_reports(user_id), None)
    sequence = max((int(row["sequence"]) for row in rows), default=-1) + 1
    added = 0
    for task in plan.tasks:
        key = task.topic.casefold().strip()
        if key in existing:
            continue
        payload = task.model_dump()
        payload.update({"roadmap_id": roadmap_id, "sequence": sequence + added, "status": "Not Started"})
        client.table("learning_tasks").insert(payload).execute()
        existing.add(key)
        added += 1
    return {"added": added}


def analyze(reports: list[dict]) -> list[dict]:
    """Use explicit report evidence; unassessed concepts remain unclassified."""
    found: dict[str, dict] = {}
    for row in reports:
        report = row.get("report") if isinstance(row.get("report"), dict) else {}
        for key, label in (("strengths", "Strong"), ("weaknesses", "Weak"), ("areas_to_improve", "Revision"), ("topics_to_improve", "Revision")):
            values = report.get(key) or []
            if isinstance(values, str): values = [values]
            for raw in values:
                concept = str(raw).strip()[:120]
                if not concept: continue
                record = found.setdefault(concept.casefold(), {"concept": concept, "evidence": [], "scores": []})
                record["evidence"].append(label)
        for raw in report.get("topic_performance", []) if isinstance(report.get("topic_performance"), list) else []:
            if not isinstance(raw, dict): continue
            concept = str(raw.get("topic") or raw.get("name") or "").strip()
            value = raw.get("score")
            if concept and value is not None:
                record = found.setdefault(concept.casefold(), {"concept": concept, "evidence": [], "scores": []})
                record["scores"].append(float(value))
    output = []
    for record in found.values():
        kinds, scores = record["evidence"], record["scores"]
        weak_count, strong_count = kinds.count("Weak"), kinds.count("Strong")
        average = sum(scores)/len(scores) if scores else None
        if weak_count > strong_count or (average is not None and average < 5): state = "Weak"
        elif strong_count > weak_count and strong_count >= kinds.count("Revision") and (average is None or average >= 7): state = "Strong"
        elif "Revision" in kinds or (average is not None and average < 7): state = "Revision"
        elif strong_count: state = "Strong"
        else: state = "Revision"
        output.append({"concept": record["concept"], "status": state, "evidence_count": len(kinds)+len(scores), "average_score": round(sum(scores)/len(scores), 1) if scores else None})
    return output


def generate_plan(reports: list[dict], goal: str | None) -> Plan:
    gaps = analyze(reports)
    if not gaps and not goal:
        raise ValueError("Add a learning goal to create a starter roadmap, or complete an interview first.")
    evidence = {"gaps": gaps, "reports": [{"topic": r.get("topic"), "score": r.get("overall_score"), "report": r.get("report")} for r in reports[:10]], "goal": goal}
    prompt = "Create a specific, staged learning roadmap from this candidate evidence. Include only weak/revision concepts and explicitly stated goal topics; strong topics are context, not tasks. Unknown topics are not weak. Use stage exactly one of Foundation, Improvement, Practice, Advanced, Assessment; priority High, Medium, Low; understanding Strong, Revision, Weak, Not Assessed; and all task/exercise difficulties Easy, Medium, Hard. Include 1-3 progressively harder coding exercises for applicable programming concepts, with public sample examples and private tests as input/output pairs. Keep solutions out. Return JSON {tasks:[{topic,description,stage,priority,understanding,difficulty,estimated_minutes,prerequisites,completion_criteria,exercises:[{title,problem,difficulty,input_example,output_example,constraints,concepts,tests:[{input,output}]}]}]}. " + json.dumps(evidence, ensure_ascii=False)[:12000]
    client = Groq(api_key=os.getenv("GROQ_API_KEY"))
    response = client.chat.completions.create(model="openai/gpt-oss-20b", messages=[{"role":"system","content":"You are a precise learning designer. Ground every recommendation in given evidence. Never claim unassessed concepts are weak."},{"role":"user","content":prompt}], response_format={"type":"json_object"})
    try:
        return Plan.model_validate_json(response.choices[0].message.content)
    except (ValidationError, ValueError, TypeError) as error:
        logger.exception("Invalid learning plan from Groq")
        raise ValueError("The AI could not create a valid learning roadmap. Please retry.") from error


def get_learning(user_id: str) -> dict:
    client = _client()
    if client is None: raise RuntimeError("Learning storage is not configured.")
    roadmap = client.table("learning_roadmaps").select("id,goal,source,created_at,updated_at").eq("user_id", user_id).order("created_at", desc=True).limit(1).execute().data
    if not roadmap: return {"roadmap": None, "tasks": [], "gaps": analyze(_reports(user_id))}
    current = roadmap[0]
    tasks = client.table("learning_tasks").select("*").eq("roadmap_id", current["id"]).order("sequence").execute().data or []
    task_ids = [task["id"] for task in tasks]
    submissions = client.table("exercise_submissions").select("task_id,exercise_title,accuracy,created_at").in_("task_id", task_ids).eq("user_id", user_id).order("created_at", desc=True).execute().data if task_ids else []
    reassessments = client.table("learning_reassessments").select("task_id,score,outcome,prior_score,created_at").eq("user_id", user_id).order("created_at", desc=True).limit(100).execute().data or []
    latest_reassessment = {}
    for item in reassessments: latest_reassessment.setdefault(item["task_id"], item)
    results = {(item["task_id"], item["exercise_title"]): float(item["accuracy"]) for item in submissions or []}
    # Hidden test inputs remain server-side until submission.
    for task in tasks:
        for exercise in task.get("exercises", []):
            exercise.pop("tests", None)
            exercise["accuracy"] = results.get((task["id"], str(exercise.get("title"))), 0)
            exercise["completed"] = exercise["accuracy"] >= 100
        task["latest_reassessment"] = latest_reassessment.get(task["id"])
    gaps = analyze(_reports(user_id))
    gap_map = {item["concept"].casefold(): item for item in gaps}
    for task in tasks:
        result = task.get("latest_reassessment")
        if not result: continue
        concept = task["topic"].casefold()
        gap = gap_map.get(concept)
        if gap:
            gap["average_score"] = float(result["score"])
            gap["status"] = result["outcome"]
            gap["evidence_count"] += 1
        else:
            gap = {"concept":task["topic"],"status":result["outcome"],"average_score":float(result["score"]),"evidence_count":1}
            gaps.append(gap); gap_map[concept] = gap
    return {"roadmap": current, "tasks": tasks, "gaps": gaps}


def create_learning(user_id: str, goal: str | None) -> dict:
    client = _client()
    if client is None: raise RuntimeError("Learning storage is not configured.")
    existing = get_learning(user_id)
    if existing["roadmap"]:
        return existing
    reports = _reports(user_id)
    plan = generate_plan(reports, goal)
    source = "interview" if analyze(reports) else "goal"
    roadmap = client.table("learning_roadmaps").insert({"user_id": user_id, "goal": goal, "source": source}).execute().data[0]
    for index, task in enumerate(plan.tasks):
        payload = task.model_dump()
        payload.update({"roadmap_id": roadmap["id"], "sequence": index, "status": "Not Started"})
        client.table("learning_tasks").insert(payload).execute()
    return get_learning(user_id)


def update_task(user_id: str, task_id: str, status: str) -> dict:
    client = _client()
    if client is None: raise RuntimeError("Learning storage is not configured.")
    rows = client.table("learning_tasks").select("id,roadmap_id").eq("id", task_id).execute().data or []
    if not rows: raise LookupError("Learning task was not found.")
    roads = client.table("learning_roadmaps").select("id").eq("id", rows[0]["roadmap_id"]).eq("user_id", user_id).execute().data
    if not roads: raise LookupError("Learning task was not found.")
    now = datetime.now(timezone.utc).isoformat()
    changes = {"status": status, "updated_at": now}
    if status == "In Progress": changes["started_at"] = now
    if status == "Completed": changes["completed_at"] = now
    else: changes["completed_at"] = None
    client.table("learning_tasks").update(changes).eq("id", task_id).execute()
    return get_learning(user_id)


def hint_for_task(user_id: str, task_id: str, exercise_id: str) -> str:
    data = get_learning(user_id)
    task = next((item for item in data["tasks"] if item["id"] == task_id), None)
    if not task: raise LookupError("Learning task was not found.")
    exercise = next((item for item in task.get("exercises", []) if str(item.get("title")) == exercise_id), None)
    if not exercise: raise LookupError("Exercise was not found.")
    response = Groq(api_key=os.getenv("GROQ_API_KEY")).chat.completions.create(model="openai/gpt-oss-20b", messages=[{"role":"system","content":"Give one progressively useful hint, never code, final answer, or solution."},{"role":"user","content":json.dumps({"topic":task["topic"],"problem":exercise["problem"]})}])
    return response.choices[0].message.content or "Try breaking the problem into smaller steps."


def reassess(user_id: str, task_id: str, question: str | None, answer: str | None) -> dict:
    data = get_learning(user_id)
    task = next((item for item in data["tasks"] if item["id"] == task_id), None)
    if not task: raise LookupError("Learning task was not found.")
    client = _client()
    if not answer:
        response = Groq(api_key=os.getenv("GROQ_API_KEY")).chat.completions.create(
            model="openai/gpt-oss-20b", response_format={"type": "json_object"},
            messages=[{"role":"system","content":"You are an adaptive interviewer. Return JSON {question:string}. Ask one targeted, diagnostic question about the given concept at the learner's current level. Do not include a solution."},
                      {"role":"user","content":json.dumps({"topic":task["topic"],"description":task["description"],"difficulty":task["difficulty"],"criteria":task["completion_criteria"]})}])
        return {"question": json.loads(response.choices[0].message.content)["question"]}
    if not question: raise ValueError("A reassessment question is required with an answer.")
    response = Groq(api_key=os.getenv("GROQ_API_KEY")).chat.completions.create(
        model="openai/gpt-oss-20b", response_format={"type": "json_object"},
        messages=[{"role":"system","content":"Assess only the candidate response to the targeted question. Return JSON {score:number from 0 to 10, feedback:string, missing_concepts:[string]}. Do not give the answer."},
                  {"role":"user","content":json.dumps({"topic":task["topic"],"question":question,"answer":answer,"criteria":task["completion_criteria"]})}])
    evaluated = json.loads(response.choices[0].message.content)
    score = max(0.0, min(10.0, float(evaluated["score"])))
    history = client.table("learning_reassessments").select("score").eq("task_id", task_id).eq("user_id", user_id).order("created_at", desc=True).limit(1).execute().data or []
    prior = float(history[0]["score"]) if history and history[0].get("score") is not None else None
    initial = next((gap.get("average_score") for gap in data["gaps"] if gap["concept"].casefold() == task["topic"].casefold()), None)
    baseline = prior if prior is not None else initial
    if score >= 8 and baseline is not None and score > baseline and int(next((gap["evidence_count"] for gap in data["gaps"] if gap["concept"].casefold() == task["topic"].casefold()), 0)) >= 2:
        outcome = "Mastered"
    elif score >= 5 and (baseline is None or score >= baseline): outcome = "Improving"
    else: outcome = "Needs Improvement"
    client.table("learning_reassessments").insert({"task_id":task_id,"user_id":user_id,"question":question,"response":answer,"score":round(score,2),"outcome":outcome,"prior_score":baseline}).execute()
    return {"score":round(score,1),"feedback":str(evaluated.get("feedback") or ""),"missing_concepts":evaluated.get("missing_concepts",[]),"outcome":outcome,"prior_score":baseline}


async def submit_exercise(user_id: str, task_id: str, exercise_id: str, language_id: int, source_code: str) -> dict:
    import asyncio
    import httpx
    client = _client()
    data = get_learning(user_id)
    task = next((item for item in data["tasks"] if item["id"] == task_id), None)
    if not task: raise LookupError("Learning task was not found.")
    # Fetch private tests directly from storage after ownership was established.
    row = client.table("learning_tasks").select("exercises").eq("id", task_id).execute().data[0]
    exercise = next((item for item in row["exercises"] if str(item.get("title")) == exercise_id), None)
    if not exercise: raise LookupError("Exercise was not found.")
    tests = exercise.get("tests", [])
    if not tests: raise ValueError("This exercise has no runnable test cases yet.")
    base = os.getenv("JUDGE0_API_URL", "https://ce.judge0.com").rstrip("/")
    headers = {"Content-Type":"application/json"}
    if os.getenv("JUDGE0_API_KEY"): headers["X-Auth-Token"] = os.environ["JUDGE0_API_KEY"]
    passed = 0
    async with httpx.AsyncClient(timeout=httpx.Timeout(12, connect=4)) as runner:
        for test in tests[:10]:
            queued = await runner.post(f"{base}/submissions/?base64_encoded=false&wait=false", headers=headers, json={"language_id":language_id,"source_code":source_code,"stdin":str(test.get("input", "")),"cpu_time_limit":2,"wall_time_limit":5,"memory_limit":128000,"max_file_size":1024})
            queued.raise_for_status()
            token = queued.json().get("token")
            if not token: raise RuntimeError("Judge0 did not return a submission ID.")
            result = None
            for _ in range(20):
                await asyncio.sleep(0.4)
                response = await runner.get(f"{base}/submissions/{token}/?base64_encoded=false&fields=status,stdout,stderr,compile_output,message", headers=headers)
                response.raise_for_status(); result = response.json()
                if (result.get("status") or {}).get("id") not in (1,2): break
            if not result or (result.get("status") or {}).get("id") in (1,2): raise TimeoutError("Code execution took too long.")
            if (result.get("status") or {}).get("id") == 3 and (result.get("stdout") or "").strip() == str(test.get("output", "")).strip(): passed += 1
    total = min(len(tests), 10); accuracy = round(passed / total * 100, 2)
    client.table("exercise_submissions").insert({"task_id":task_id,"user_id":user_id,"exercise_title":exercise_id,"language_id":language_id,"source_code":source_code,"passed":passed,"total_tests":total,"accuracy":accuracy}).execute()
    return {"passed":passed,"total":total,"accuracy":accuracy,"complete":passed == total}
