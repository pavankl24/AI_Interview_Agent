from fastapi.middleware.cors import CORSMiddleware

from .config import cors_origins
from .routers.interview import router as interview_router
from api import app

web_mount = next((route for route in app.router.routes if getattr(route, "name", "") == "web"), None)
if web_mount is not None:
    app.router.routes.remove(web_mount)

app.include_router(interview_router)

app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins(),
    allow_credentials=True,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type"],
)


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/api/health")
def api_health():
    return {"status": "ok"}


if web_mount is not None:
    app.router.routes.append(web_mount)
