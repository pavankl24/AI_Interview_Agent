import logging

from fastapi import APIRouter, File, Header, HTTPException, Request, UploadFile

from backend.rate_limit import limiter
from backend.schemas_resume import AnswerSubmission, InterviewStart, MatchRequest, ProfileUpdate
from backend.services import resume_service as service
from database import verify_access_token

router = APIRouter(prefix="/api/resumes", tags=["Resume interviews"])
logger = logging.getLogger(__name__)


def user_id(authorization: str | None) -> str:
    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(status_code=401, detail="Sign in to manage your resumes.")
    uid = verify_access_token(authorization[7:].strip())
    if not uid: raise HTTPException(status_code=401, detail="Your sign-in session is invalid or expired.")
    return uid


def invoke(fn, *args):
    try: return fn(*args)
    except LookupError as error: raise HTTPException(status_code=404, detail=str(error)) from error
    except ValueError as error: raise HTTPException(status_code=422, detail=str(error)) from error
    except HTTPException: raise
    except Exception as error:
        logger.exception("Resume interview request failed")
        raise HTTPException(status_code=503, detail="Resume service is unavailable. Check Supabase and Groq configuration.") from error


@router.get("")
def resumes(authorization: str | None = Header(default=None)):
    return invoke(service.list_resumes, user_id(authorization))


@router.post("")
@limiter.limit("5/hour")
async def upload_resume(request: Request, file: UploadFile = File(...), authorization: str | None = Header(default=None)):
    content = await file.read(service.MAX_UPLOAD + 1)
    return invoke(service.create_resume, user_id(authorization), file.filename or "resume", file.content_type or "", content)


@router.patch("/{resume_id}")
def edit_resume(resume_id: str, data: ProfileUpdate, authorization: str | None = Header(default=None)):
    return invoke(service.update_resume, user_id(authorization), resume_id, data.profile.model_dump())


@router.delete("/{resume_id}")
def remove_resume(resume_id: str, authorization: str | None = Header(default=None)):
    invoke(service.delete_resume, user_id(authorization), resume_id)
    return {"deleted": True}


@router.post("/{resume_id}/match")
@limiter.limit("10/hour")
def match(request: Request, resume_id: str, data: MatchRequest, authorization: str | None = Header(default=None)):
    profile = invoke(service.get_resume, user_id(authorization), resume_id)["profile"]
    return invoke(service.match_job, profile, data.job_description)


@router.post("/interviews")
@limiter.limit("10/hour")
def start(request: Request, data: InterviewStart, authorization: str | None = Header(default=None)):
    return invoke(service.start_session, user_id(authorization), data)


@router.post("/interviews/{session_id}/answer")
@limiter.limit("30/hour")
def answer(request: Request, session_id: str, data: AnswerSubmission, authorization: str | None = Header(default=None)):
    return invoke(service.answer_session, user_id(authorization), session_id, data.answer)


@router.get("/interviews/{session_id}")
def get_report(session_id: str, authorization: str | None = Header(default=None)):
    uid = user_id(authorization)
    rows = service._require_client().table("resume_interview_sessions").select("id,status,report,created_at,completed_at").eq("id", session_id).eq("user_id", uid).limit(1).execute().data or []
    if not rows: raise HTTPException(status_code=404, detail="Interview report was not found.")
    return rows[0]
