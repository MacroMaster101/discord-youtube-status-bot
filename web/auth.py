"""Bearer-token auth decorator for dashboard API routes."""
import hmac
from functools import wraps
from flask import request, jsonify
from config import Config


def check_password(candidate: str) -> bool:
    """Constant-time comparison against the admin password."""
    return hmac.compare_digest(str(candidate or "").encode(), str(Config.ADMIN_PASSWORD).encode())


def require_auth(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        auth_header = request.headers.get("Authorization", "")
        if not auth_header.startswith("Bearer "):
            return jsonify({"message": "Unauthorized"}), 401
        token = auth_header.split(" ", 1)[1]
        if not check_password(token):
            return jsonify({"message": "Unauthorized"}), 401
        return f(*args, **kwargs)
    return decorated
