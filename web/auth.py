"""Dashboard auth: admin password check plus random session tokens.

Logging in with the admin password returns a random session token. The password itself is never
sent back or stored in the browser. Sessions live in memory, so a restart logs everyone out.
"""
import hmac
import secrets
import threading
import time
from functools import wraps
from flask import request, jsonify
from config import Config

SESSION_TTL_SECONDS = 12 * 60 * 60
MIN_PASSWORD_LENGTH = 8
DEFAULT_PASSWORDS = {"admin123", "change_me", "your_dashboard_password_here", "your_admin_password_here"}

_sessions: dict[str, float] = {}  # token -> expiry (epoch seconds)
_lock = threading.Lock()


def password_problem(password) -> str | None:
    """Return why a password is unsafe to use for the dashboard, or None if it's fine."""
    password = str(password or "")
    if not password:
        return "ADMIN_PASSWORD is not set"
    if password in DEFAULT_PASSWORDS:
        return "ADMIN_PASSWORD is still a default value"
    if len(password) < MIN_PASSWORD_LENGTH:
        return f"ADMIN_PASSWORD must be at least {MIN_PASSWORD_LENGTH} characters"
    return None


def check_password(candidate: str) -> bool:
    """Constant-time comparison against the admin password."""
    return hmac.compare_digest(str(candidate or "").encode(), str(Config.ADMIN_PASSWORD).encode())


def create_session() -> str:
    token = secrets.token_urlsafe(32)
    now = time.time()
    with _lock:
        # Drop expired sessions while we're here
        for t in [t for t, exp in _sessions.items() if exp <= now]:
            del _sessions[t]
        _sessions[token] = now + SESSION_TTL_SECONDS
    return token


def session_valid(token: str) -> bool:
    if not token:
        return False
    with _lock:
        exp = _sessions.get(token)
        if exp is None:
            return False
        if exp <= time.time():
            del _sessions[token]
            return False
        return True


def revoke_session(token: str):
    with _lock:
        _sessions.pop(token, None)


def revoke_all_sessions():
    with _lock:
        _sessions.clear()


def bearer_token() -> str:
    auth_header = request.headers.get("Authorization", "")
    if not auth_header.startswith("Bearer "):
        return ""
    return auth_header.split(" ", 1)[1].strip()


def require_auth(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not session_valid(bearer_token()):
            return jsonify({"message": "Unauthorized"}), 401
        return f(*args, **kwargs)
    return decorated
