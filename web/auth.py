"""Dashboard auth: three ways in, one session.

A request is authorised if it carries any of:

1. a session token minted by the password login (`/api/login`),
2. a session token minted by Discord OAuth sign-in (`/auth/discord`), or
3. a signed, verified Cloudflare Access JWT (see web/access.py).

The first two are the same kind of random token, so everything downstream of
`require_auth` is identical regardless of how the person signed in. Sessions live
in memory, so a restart logs everyone out. The password itself is never sent back
or stored in the browser.
"""
import hmac
import secrets
import threading
import time
from functools import wraps
from flask import request, jsonify
from config import Config
from core.passwords import verify_password
from web import access

SESSION_TTL_SECONDS = 12 * 60 * 60
MIN_PASSWORD_LENGTH = 8
DEFAULT_PASSWORDS = {"admin123", "change_me", "your_dashboard_password_here", "your_admin_password_here"}

# Set on the OAuth round trip, where there is no JavaScript to carry a header.
# HttpOnly so a cross-site script cannot read it; SameSite=Lax so it still
# arrives on the top-level redirect back from Discord.
SESSION_COOKIE = "dash_session"

# token -> {"exp": float, "via": str, "who": str}
_sessions: dict[str, dict] = {}
_lock = threading.Lock()


def strength_issue(value) -> str | None:
    """Return why a candidate dashboard password is unsafe, or None if it's fine."""
    value = str(value or "")
    if not value:
        return "it is empty"
    if value in DEFAULT_PASSWORDS:
        return "it is a default value"
    if len(value) < MIN_PASSWORD_LENGTH:
        return f"it must be at least {MIN_PASSWORD_LENGTH} characters"
    return None


def login_block_reason() -> str | None:
    """Why password login is disabled right now, or None when it's allowed."""
    if Config.ADMIN_PASSWORD_HASH:
        return None  # set from the dashboard, already checked by strength_issue()
    issue = strength_issue(Config.ADMIN_PASSWORD)
    return f"ADMIN_PASSWORD is not safe ({issue})" if issue else None


def check_password(candidate: str) -> bool:
    """Check a login attempt against the dashboard password (hash first, then .env value)."""
    if Config.ADMIN_PASSWORD_HASH:
        return verify_password(str(candidate or ""), Config.ADMIN_PASSWORD_HASH)
    return hmac.compare_digest(str(candidate or "").encode(), str(Config.ADMIN_PASSWORD).encode())


def create_session(via: str = "password", who: str = "") -> str:
    token = secrets.token_urlsafe(32)
    now = time.time()
    with _lock:
        # Drop expired sessions while we're here
        for t in [t for t, s in _sessions.items() if s["exp"] <= now]:
            del _sessions[t]
        _sessions[token] = {"exp": now + SESSION_TTL_SECONDS, "via": via, "who": who}
    return token


def session_info(token: str) -> dict | None:
    if not token:
        return None
    with _lock:
        entry = _sessions.get(token)
        if entry is None:
            return None
        if entry["exp"] <= time.time():
            del _sessions[token]
            return None
        return dict(entry)


def session_valid(token: str) -> bool:
    return session_info(token) is not None


def revoke_session(token: str):
    with _lock:
        _sessions.pop(token, None)


def revoke_all_sessions():
    with _lock:
        _sessions.clear()


def bearer_token() -> str:
    """The session token for this request, from the header or the OAuth cookie.

    A non-empty header wins, so an explicit token is never silently overridden by
    a stale cookie. An empty one does not: the dashboard's fetch helper always
    sends "Bearer " with whatever it has, which is the empty string after an
    OAuth sign-in, and that must not mask the cookie that actually carries the
    session.
    """
    auth_header = request.headers.get("Authorization", "")
    if auth_header.startswith("Bearer "):
        supplied = auth_header.split(" ", 1)[1].strip()
        if supplied:
            return supplied
    return request.cookies.get(SESSION_COOKIE, "").strip()


def current_identity() -> dict | None:
    """How this request is authenticated, or None if it isn't.

    Cloudflare Access is checked first: it is proof carried by the request
    itself, so it stays valid even when the in-memory sessions were cleared by a
    restart.
    """
    email = access.identity()
    if email:
        return {"via": "cloudflare", "who": email}
    entry = session_info(bearer_token())
    if entry:
        return {"via": entry["via"], "who": entry["who"]}
    return None


def require_auth(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if current_identity() is None:
            return jsonify({"message": "Unauthorized"}), 401
        return f(*args, **kwargs)
    return decorated
