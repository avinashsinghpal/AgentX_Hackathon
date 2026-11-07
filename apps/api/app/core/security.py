import base64
import hashlib
import hmac
import json
import secrets
import time
from typing import Any

from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError

from app.core.config import settings

# Argon2id password hasher with production-grade security parameters
_ph = PasswordHasher(
    time_cost=3,
    memory_cost=65536,
    parallelism=4,
    hash_len=32,
)


def hash_password(password: str) -> str:
    """Hash a password using Argon2id."""
    return _ph.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a plain password against an Argon2id hash."""
    try:
        return _ph.verify(hashed_password, plain_password)
    except (VerifyMismatchError, Exception):
        return False


def _sign(data_bytes: bytes, secret: str) -> str:
    sig = hmac.new(secret.encode("utf-8"), data_bytes, hashlib.sha256).digest()
    return base64.urlsafe_b64encode(sig).decode("utf-8").rstrip("=")


def create_session_token(user_id: str, role: str, expires_in_seconds: int = 86400 * 7) -> str:
    """
    Creates an HMAC-SHA256 signed session token containing user_id, role, and expiry timestamp.
    Format: base64(payload_json).signature
    """
    payload = {
        "sub": user_id,
        "role": role,
        "exp": int(time.time()) + expires_in_seconds,
        "iat": int(time.time()),
        "nonce": secrets.token_hex(8),
    }
    payload_json = json.dumps(payload, separators=(",", ":")).encode("utf-8")
    payload_b64 = base64.urlsafe_b64encode(payload_json).decode("utf-8").rstrip("=")
    signature = _sign(payload_b64.encode("utf-8"), settings.SECRET_KEY)
    return f"{payload_b64}.{signature}"


def decode_session_token(token: str) -> dict[str, Any] | None:
    """
    Validates signature and expiry of a session token and returns the decoded payload.
    """
    try:
        parts = token.split(".")
        if len(parts) != 2:
            return None
        payload_b64, signature = parts

        # Verify HMAC signature
        expected_sig = _sign(payload_b64.encode("utf-8"), settings.SECRET_KEY)
        if not hmac.compare_digest(signature, expected_sig):
            return None

        # Add base64 padding if needed
        padding = 4 - (len(payload_b64) % 4)
        if padding != 4:
            payload_b64 += "=" * padding

        payload_bytes = base64.urlsafe_b64decode(payload_b64.encode("utf-8"))
        payload: dict[str, Any] = json.loads(payload_bytes.decode("utf-8"))

        # Check expiration
        if payload.get("exp", 0) < int(time.time()):
            return None

        return payload
    except Exception:
        return None


def generate_csrf_token() -> str:
    """Generate a cryptographically secure CSRF token."""
    return secrets.token_urlsafe(32)


def verify_csrf_token(cookie_csrf: str | None, header_csrf: str | None) -> bool:
    """
    Verify CSRF token match using constant-time comparison.
    """
    if not cookie_csrf or not header_csrf:
        return False
    return hmac.compare_digest(cookie_csrf, header_csrf)
