import base64
import json

from fastapi import FastAPI, Request, Response
from fastapi.testclient import TestClient
from slowapi.errors import RateLimitExceeded

from backend.rate_limit import limiter, rate_limit_exceeded_handler, rate_limit_key


def _request(headers=(), client=("203.0.113.10", 1234)):
    return Request({
        "type": "http",
        "http_version": "1.1",
        "method": "GET",
        "scheme": "http",
        "path": "/",
        "raw_path": b"/",
        "query_string": b"",
        "headers": list(headers),
        "client": client,
        "server": ("testserver", 80),
    })


def _token(subject):
    header = base64.urlsafe_b64encode(b'{"alg":"none"}').decode().rstrip("=")
    body = base64.urlsafe_b64encode(json.dumps({"sub": subject}).encode()).decode().rstrip("=")
    return f"{header}.{body}.signature"


def test_authenticated_user_is_the_rate_limit_key():
    request = _request([(b"authorization", f"Bearer {_token('user-123')}".encode())])
    assert rate_limit_key(request) == "user:user-123"


def test_unauthenticated_request_uses_ip_address():
    assert rate_limit_key(_request()) == "203.0.113.10"


def test_rate_limit_returns_frontend_friendly_429():
    app = FastAPI()
    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, rate_limit_exceeded_handler)

    @app.get("/rate-limit-test")
    @limiter.limit("1/minute")
    def limited_endpoint(request: Request, response: Response):
        return {"ok": True}

    client = TestClient(app)
    assert client.get("/rate-limit-test").status_code == 200
    response = client.get("/rate-limit-test")
    assert response.status_code == 429
    assert response.json()["detail"] == "Too many interview requests. Please wait a minute and try again."
    assert response.headers["retry-after"] == "60"
