from fastapi.testclient import TestClient

from app.core.security import verify_csrf_token


def test_csrf_token_validation_logic() -> None:
    token = "secure-random-csrf-token-12345"
    assert verify_csrf_token(token, token) is True
    assert verify_csrf_token(token, "wrong-token") is False
    assert verify_csrf_token(None, token) is False
    assert verify_csrf_token(token, None) is False


def test_rate_limiter_registered(client: TestClient) -> None:
    # Multiple rapid requests to healthz should succeed within default 120/min limit
    for _ in range(5):
        res = client.get("/healthz")
        assert res.status_code == 200
