import base64
import json
import os

from fastapi import Request
from fastapi.responses import JSONResponse
from slowapi import Limiter
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address


def rate_limit_key(request: Request) -> str:
    authorization = request.headers.get("authorization", "")
    if authorization.lower().startswith("bearer "):
        parts = authorization[7:].strip().split(".")
        if len(parts) == 3:
            try:
                payload = parts[1] + "=" * (-len(parts[1]) % 4)
                user_id = json.loads(base64.urlsafe_b64decode(payload)).get("sub")
                if user_id:
                    return f"user:{user_id}"
            except (ValueError, TypeError, json.JSONDecodeError):
                pass
    return get_remote_address(request)


limiter = Limiter(
    key_func=rate_limit_key,
    storage_uri=os.getenv("RATE_LIMIT_STORAGE_URI", "memory://"),
    headers_enabled=True,
)


async def rate_limit_exceeded_handler(_request: Request, _error: RateLimitExceeded):
    return JSONResponse(
        status_code=429,
        content={"detail": "Too many interview requests. Please wait a minute and try again."},
        headers={"Retry-After": "60"},
    )
