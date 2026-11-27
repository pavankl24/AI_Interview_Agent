import logging

from fastapi import APIRouter, Header, HTTPException, Request
from pydantic import ValidationError

from backend.schemas_learning import GoalRequest, TaskUpdate, HintRequest, ReassessmentRequest, ExerciseSubmission
from backend.services.learning_service import create_learning, get_learning, hint_for_task, update_task, reassess, submit_exercise
from backend.rate_limit import limiter
from database import verify_access_token

router = APIRouter(prefix="/learning", tags=["Learning roadmap"])
logger = logging.getLogger(__name__)


def user_id(authorization: str | None) -> str:
    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(status_code=401, detail="Sign in to access your learning roadmap.")
    result = verify_access_token(authorization[7:].strip())
    if not result: raise HTTPException(status_code=401, detail="Your sign-in session is invalid or expired.")
    return result


@router.get("")
def read_learning(authorization: str | None = Header(default=None)):
    try: return get_learning(user_id(authorization))
    except HTTPException: raise
    except Exception as error:
        logger.exception("Could not load learning roadmap")
        raise HTTPException(status_code=503, detail="Could not load your learning roadmap. Apply the learning migrations and try again.") from error


@router.post("")
@limiter.limit("3/hour")
def start_learning(request: Request, data: GoalRequest, authorization: str | None = Header(default=None)):
    try: return create_learning(user_id(authorization), data.goal.strip() if data.goal else None)
    except HTTPException: raise
    except ValueError as error: raise HTTPException(status_code=422, detail=str(error)) from error
    except Exception as error:
        logger.exception("Could not create learning roadmap")
        error_code = str(getattr(error, "code", ""))
        error_module = type(error).__module__.lower()
        error_name = type(error).__name__.lower()
        if error_code in {"42P01", "PGRST205"}:
            detail = "Learning tables are missing in Supabase. Run supabase/migrations/004_learning_roadmaps.sql in the SQL Editor."
        elif error_code == "42501":
            detail = "Supabase denied access to learning storage. Verify the server uses the Supabase secret or service-role key and that migration 004 was applied."
        elif "groq" in error_module or "groq" in error_name:
            detail = "Groq could not generate the roadmap. Check GROQ_API_KEY and the Groq API response in the backend terminal."
        else:
            detail = f"Roadmap request failed ({type(error).__name__}). See the backend terminal traceback for details."
        raise HTTPException(status_code=502, detail=detail) from error


@router.patch("/tasks/{task_id}")
def patch_task(task_id: str, data: TaskUpdate, authorization: str | None = Header(default=None)):
    try: return update_task(user_id(authorization), task_id, data.status)
    except HTTPException: raise
    except LookupError as error: raise HTTPException(status_code=404, detail=str(error)) from error
    except Exception as error:
        logger.exception("Could not update learning task")
        raise HTTPException(status_code=503, detail="Could not update learning progress.") from error


@router.post("/tasks/{task_id}/hint")
def task_hint(task_id: str, data: HintRequest, authorization: str | None = Header(default=None)):
    try: return {"hint": hint_for_task(user_id(authorization), task_id, data.exercise_id)}
    except HTTPException: raise
    except LookupError as error: raise HTTPException(status_code=404, detail=str(error)) from error
    except Exception as error:
        logger.exception("Could not generate exercise hint")
        raise HTTPException(status_code=502, detail="Could not generate a hint right now.") from error


@router.post("/tasks/{task_id}/reassess")
@limiter.limit("10/hour")
def reassess_task(request: Request, task_id: str, data: ReassessmentRequest, authorization: str | None = Header(default=None)):
    try: return reassess(user_id(authorization), task_id, data.question, data.answer)
    except HTTPException: raise
    except LookupError as error: raise HTTPException(status_code=404, detail=str(error)) from error
    except ValueError as error: raise HTTPException(status_code=422, detail=str(error)) from error
    except Exception as error:
        logger.exception("Could not reassess learning task")
        raise HTTPException(status_code=502, detail="Could not complete the topic assessment.") from error


@router.post("/tasks/{task_id}/exercises/submit")
@limiter.limit("20/hour")
async def submit_task_exercise(request: Request, task_id: str, data: ExerciseSubmission, authorization: str | None = Header(default=None)):
    try: return await submit_exercise(user_id(authorization), task_id, data.exercise_id, data.language_id, data.source_code)
    except HTTPException: raise
    except LookupError as error: raise HTTPException(status_code=404, detail=str(error)) from error
    except ValueError as error: raise HTTPException(status_code=422, detail=str(error)) from error
    except TimeoutError as error: raise HTTPException(status_code=504, detail=str(error)) from error
    except Exception as error:
        logger.exception("Could not execute learning exercise")
        raise HTTPException(status_code=503, detail="Could not validate the exercise with Judge0.") from error
