from pathlib import Path
import os

from dotenv import load_dotenv

BACKEND_DIR = Path(__file__).resolve().parent
load_dotenv(BACKEND_DIR / ".env")


def cors_origins() -> list[str]:
    """Return the allowed browser origins for the frontend."""
    configured = os.getenv("CORS_ORIGINS", "http://127.0.0.1:5173,http://localhost:5173")
    return [origin.strip().rstrip("/") for origin in configured.split(",") if origin.strip()]
