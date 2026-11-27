"""Private resume storage and resume-grounded interview workflows."""
import io
import json
import os
import re
import uuid
from datetime import datetime, timezone

from groq import Groq

from backend.schemas_resume import ResumeProfile
from backend.services.ai_service import InterviewAgent
from database import _client

MAX_UPLOAD = 5 * 1024 * 1024
ALLOWED = {"application/pdf", "application/vnd.openxmlformats-officedocument.wordprocessingml.document"}

RESUME_PROFILE_SCHEMA = {
    "type": "object",
    "properties": {
        "name": {"type": "string"},
        "summary": {"type": "string"},
        "education": {"type": "array", "items": {"type": "string"}},
        "technical_skills": {"type": "array", "items": {"type": "string"}},
        "programming_languages": {"type": "array", "items": {"type": "string"}},
        "frameworks_tools": {"type": "array", "items": {"type": "string"}},
        "projects": {"type": "array", "items": {"type": "object", "properties": {
            "name": {"type": "string"}, "description": {"type": "string"},
            "technologies": {"type": "array", "items": {"type": "string"}},
        }, "required": ["name", "description", "technologies"], "additionalProperties": False}},
        "experience": {"type": "array", "items": {"type": "object", "properties": {
            "title": {"type": "string"}, "organization": {"type": "string"},
            "description": {"type": "string"},
        }, "required": ["title", "organization", "description"], "additionalProperties": False}},
        "certifications": {"type": "array", "items": {"type": "string"}},
    },
    "required": ["name", "summary", "education", "technical_skills", "programming_languages",
                 "frameworks_tools", "projects", "experience", "certifications"],
    "additionalProperties": False,
}

JOB_MATCH_SCHEMA = {
    "type": "object",
    "properties": {
        "required_skills": {"type": "array", "items": {"type": "string"}},
        "preferred_skills": {"type": "array", "items": {"type": "string"}},
        "required_experience": {"type": "string"},
        "responsibilities": {"type": "array", "items": {"type": "string"}},
        "technologies": {"type": "array", "items": {"type": "string"}},
        "expectations": {"type": "array", "items": {"type": "string"}},
    },
    "required": ["required_skills", "preferred_skills", "required_experience", "responsibilities", "technologies", "expectations"],
    "additionalProperties": False,
}


def extract_document(filename: str, content_type: str, content: bytes) -> str:
    if len(content) > MAX_UPLOAD:
        raise ValueError("Resume files must be 5 MB or smaller.")
    ext = filename.lower().rsplit(".", 1)[-1] if "." in filename else ""
    if not ((ext == "pdf" and content_type == "application/pdf" and content.startswith(b"%PDF-")) or
            (ext == "docx" and content_type in {"application/vnd.openxmlformats-officedocument.wordprocessingml.document", "application/zip"} and content.startswith(b"PK"))):
        raise ValueError("Upload a valid PDF or DOCX resume.")
    try:
        if ext == "pdf":
            from pypdf import PdfReader
            text = "\n".join(page.extract_text() or "" for page in PdfReader(io.BytesIO(content)).pages)
        else:
            from docx import Document
            doc = Document(io.BytesIO(content))
            text = "\n".join([*(p.text for p in doc.paragraphs), *(" | ".join(c.text for c in row.cells) for table in doc.tables for row in table.rows)])
    except Exception as error:
        raise ValueError("This document could not be read. Please export it again as a text-based PDF or DOCX.") from error
    text = re.sub(r"\s+", " ", text).strip()
    if len(text) < 80:
        raise ValueError("No readable resume text was found. Scanned PDFs need OCR before upload.")
    return text[:40000]


def analyze_resume(text: str) -> ResumeProfile:
    response = Groq(api_key=os.getenv("GROQ_API_KEY")).chat.completions.create(
        model="openai/gpt-oss-20b", reasoning_effort="low",
        response_format={"type": "json_schema", "json_schema": {
            "name": "resume_profile", "strict": True, "schema": RESUME_PROFILE_SCHEMA}},
        messages=[{"role": "system", "content": "Extract only facts explicitly present in this resume. Never invent projects, skills, dates, or achievements. Put each education entry in one concise string. For missing values, use an empty string or empty array. Return only the requested resume profile."},
                  {"role": "user", "content": text}])
    return ResumeProfile.model_validate_json(response.choices[0].message.content)


def match_job(profile: dict, description: str) -> dict:
    candidate = {str(s).casefold(): str(s) for s in profile.get("technical_skills", []) + profile.get("programming_languages", []) + profile.get("frameworks_tools", [])}
    # Skills are the resume's explicitly extracted skill inventory. Score is matched required skills / identified required skills.
    response = Groq(api_key=os.getenv("GROQ_API_KEY")).chat.completions.create(
        model="openai/gpt-oss-20b", reasoning_effort="low",
        response_format={"type": "json_schema", "json_schema": {
            "name": "job_requirements", "strict": True, "schema": JOB_MATCH_SCHEMA}},
        messages=[{"role":"system","content":"Extract only explicit job requirements. Do not infer or invent requirements. Use empty strings or arrays when information is absent."},
                  {"role":"user","content":description}])
    job = json.loads(response.choices[0].message.content)
    required = list(dict.fromkeys(str(x).strip() for x in job.get("required_skills", []) if str(x).strip()))
    preferred = list(dict.fromkeys(str(x).strip() for x in job.get("preferred_skills", []) if str(x).strip()))
    def tokens(value: str) -> set[str]:
        return set(re.findall(r"[a-z0-9+#.]+", value.casefold()))
    matched = [skill for skill in required if any(re.sub(r"\s+", " ", skill.casefold()).strip() == re.sub(r"\s+", " ", item).strip() for item in candidate)]
    partial = [skill for skill in required if skill not in matched and any(len(tokens(skill) & tokens(item)) > 0 for item in candidate)]
    missing = [skill for skill in required if skill not in matched and skill not in partial]
    denominator = len(required)
    return {**job, "matching_skills": matched, "partially_matching_skills": partial, "missing_skills": missing,
            "score": round(100 * len(matched) / denominator) if denominator else None,
            "score_explanation": f"{len(matched)} of {denominator} explicitly identified required skills match the resume" if denominator else "No required skills were identified, so a score is unavailable.",
            "relevant_projects": [p for p in profile.get("projects", []) if any(str(skill).casefold() in json.dumps(p).casefold() for skill in matched)],
            "preparation_areas": missing + partial}


def _require_client():
    client = _client()
    if client is None: raise RuntimeError("Supabase storage is not configured.")
    return client


def create_resume(user_id: str, filename: str, content_type: str, content: bytes) -> dict:
    text = extract_document(filename, content_type, content)
    profile = analyze_resume(text).model_dump()
    client = _require_client()
    row = client.table("resumes").insert({"user_id": user_id, "filename": filename[:255], "content_type": content_type,
        "extracted_text": text, "profile": profile}).execute().data[0]
    return {"id": row["id"], "filename": row["filename"], "profile": row["profile"], "created_at": row["created_at"]}


def list_resumes(user_id: str) -> list[dict]:
    rows = _require_client().table("resumes").select("id,filename,profile,created_at").eq("user_id", user_id).order("created_at", desc=True).execute().data or []
    return rows


def get_resume(user_id: str, resume_id: str) -> dict:
    rows = _require_client().table("resumes").select("*").eq("id", resume_id).eq("user_id", user_id).limit(1).execute().data or []
    if not rows: raise LookupError("Resume was not found.")
    return rows[0]


def update_resume(user_id: str, resume_id: str, profile: dict) -> dict:
    row = _require_client().table("resumes").update({"profile": ResumeProfile.model_validate(profile).model_dump(), "updated_at": datetime.now(timezone.utc).isoformat()}).eq("id", resume_id).eq("user_id", user_id).execute().data
    if not row: raise LookupError("Resume was not found.")
    return row[0]


def delete_resume(user_id: str, resume_id: str) -> None:
    response = _require_client().table("resumes").delete().eq("id", resume_id).eq("user_id", user_id).execute()
    if not response.data: raise LookupError("Resume was not found.")


def start_session(user_id: str, data) -> dict:
    resume = get_resume(user_id, data.resume_id)
    session_id = str(uuid.uuid4())
    context = {"mode": data.mode, "role": data.target_role, "level": data.experience_level, "difficulty": data.difficulty,
               "limit": data.question_count, "job_description": data.job_description, "profile": resume["profile"], "turns": [], "asked": []}
    level = {"Easy": "Beginner", "Medium": "Intermediate", "Hard": "Advanced"}[data.difficulty]
    agent = InterviewAgent(f"{data.mode} for {data.target_role or 'the target role'}", level, data.mode,
                           {"resume": resume["profile"], "job_description": data.job_description, "target_role": data.target_role,
                            "mode_guidance": data.mode})
    question_data, _ = agent.ask_question(first_question=True)
    question = question_data["next_question"]
    context["agent_state"] = agent.export_state()
    context["asked"].append(question)
    row = _require_client().table("resume_interview_sessions").insert({"id": session_id, "user_id": user_id, "resume_id": data.resume_id, "state": context, "status": "active"}).execute().data[0]
    return {"session_id": row["id"], "question": question, "question_number": 1, "question_count": data.question_count}


def _next_question(state: dict, first=False) -> str:
    focus = {"Project Deep-Dive Interview": "Ask about one actual listed project: architecture, technology choice, implementation, challenge, or trade-off.",
            "Technical Skills Interview": "Ask about a technical skill explicitly listed in the resume.",
            "HR and Behavioral Interview": "Ask a behavioral question grounded in the listed experience or projects.",
            "Resume + Job Description Interview": "Ask about a listed resume fact relevant to the target job requirements.",
            "Resume Interview": "Ask a question grounded in a specific resume fact."}.get(state["mode"], "Ask a question grounded in a specific resume fact.")
    messages = [{"role":"system","content":"You are an adaptive interviewer. Ask exactly one concise question. Use only facts in the supplied resume. Never invent achievements, projects, skills or experience. Do not repeat prior questions. " + focus},
                {"role":"user","content":json.dumps({"resume":state["profile"],"role":state["role"],"job_description":state["job_description"],"difficulty":state["difficulty"],"asked":state["asked"],"turns":state["turns"],"first":first})}]
    response = Groq(api_key=os.getenv("GROQ_API_KEY")).chat.completions.create(model="openai/gpt-oss-20b", messages=messages)
    question = (response.choices[0].message.content or "").strip()
    if len(question) < 8: raise ValueError("The interviewer could not generate a grounded question.")
    return question


def answer_session(user_id: str, session_id: str, answer: str) -> dict:
    client = _require_client()
    rows = client.table("resume_interview_sessions").select("*").eq("id", session_id).eq("user_id", user_id).eq("status", "active").limit(1).execute().data or []
    if not rows: raise LookupError("Active resume interview was not found.")
    row = rows[0]; state = row["state"]; question = state["asked"][-1]
    prompt = {"resume":state["profile"],"question":question,"answer":answer,"prior_turns":state["turns"],"job_description":state["job_description"]}
    agent = InterviewAgent.from_state(state["agent_state"])
    agent_result, _ = agent.assess_answer(question, answer, followup_count=state.get("followup_count", 0),
        previous_answers=[turn["answer"] for turn in state["turns"]], concepts_tested=[turn.get("topic", "") for turn in state["turns"]])
    result = {"score": agent_result["score"], "correctness_score": agent_result["correctness_score"],
              "depth_score": agent_result["depth_score"], "clarity_score": agent_result["clarity_score"],
              "practical_score": agent_result["practical_score"], "claim_supported": agent_result["claim_supported"],
              "feedback": agent_result["evaluation"], "strengths": agent_result["strengths"],
              "missing_concepts": agent_result["missing_concepts"], "classification": agent_result["classification"]}
    state["turns"].append({"question":question,"answer":answer,"evaluation":result,"topic":agent_result.get("topic")})
    state["followup_count"] = state.get("followup_count", 0) + 1 if agent_result.get("action") == "FOLLOW_UP" else 0
    state["agent_state"] = agent.export_state()
    done = len(state["turns"]) >= state["limit"]
    next_question = None
    if not done:
        next_question = agent_result["next_question"]
        state["asked"].append(next_question)
        if len(state["turns"]) > 0 and result.get("score", 0) >= 8: state["difficulty"] = "Hard" if state["difficulty"] == "Medium" else state["difficulty"]
        elif result.get("score", 10) < 5: state["difficulty"] = "Easy"
    report = None
    if done:
        scores = [max(0, min(10, float(t["evaluation"].get("score", 0)))) for t in state["turns"]]
        avg = round(sum(scores)/len(scores), 1)
        report = {"overall_score":avg,"technical_knowledge_score":round(sum(float(t["evaluation"].get("correctness_score",0)) for t in state["turns"])/len(scores),1),
                  "communication_score":round(sum(float(t["evaluation"].get("clarity_score",0)) for t in state["turns"])/len(scores),1),
                  "problem_solving_score":round(sum(float(t["evaluation"].get("practical_score",0)) for t in state["turns"])/len(scores),1),
                  "resume_credibility":round(sum(10 if t["evaluation"].get("claim_supported") else 5 for t in state["turns"])/len(scores),1),
                  "question_evaluations":state["turns"],"strengths":list(dict.fromkeys(s for t in state["turns"] for s in t["evaluation"].get("strengths",[]))),
                  "areas_to_improve":list(dict.fromkeys(s for t in state["turns"] for s in t["evaluation"].get("missing_concepts",[]))),
                  "unsupported_claims":[t["question"] for t in state["turns"] if not t["evaluation"].get("claim_supported")],"job_alignment":None}
        report["personalized_recommendations"] = [f"Review {topic} and explain it with a concrete example." for topic in report["areas_to_improve"][:8]]
        if state["job_description"]:
            report["job_alignment"] = match_job(state["profile"], state["job_description"])
            report["areas_to_improve"] = list(dict.fromkeys(report["areas_to_improve"] + report["job_alignment"]["missing_skills"] + report["job_alignment"]["partially_matching_skills"]))
            report["personalized_recommendations"] = [f"Prepare {skill} because it is part of the target role requirements." for skill in report["job_alignment"]["missing_skills"][:8]] + report["personalized_recommendations"]
        client.table("resume_interview_sessions").update({"state":state,"status":"completed","report":report,"completed_at":datetime.now(timezone.utc).isoformat()}).eq("id",session_id).eq("user_id",user_id).execute()
        try:
            from backend.services.learning_service import sync_resume_interview
            sync_resume_interview(user_id)
        except Exception:
            import logging
            logging.getLogger(__name__).exception("Could not sync resume interview into the learning roadmap")
    else:
        client.table("resume_interview_sessions").update({"state":state}).eq("id",session_id).eq("user_id",user_id).execute()
    return {"completed":done,"evaluation":result,"question":next_question,"report":report,"question_number":len(state["turns"])+1}
