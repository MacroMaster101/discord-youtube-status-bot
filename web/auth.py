"""Bearer-token auth decorator for dashboard API routes."""
from functools import wraps
from flask import request, jsonify
from config import Config


def require_auth(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        auth_header = request.headers.get("Authorization", "")
        if not auth_header.startswith("Bearer "):
            return jsonify({"message": "Unauthorized"}), 401
        token = auth_header.split(" ", 1)[1]
        if token != Config.ADMIN_PASSWORD:
            return jsonify({"message": "Unauthorized"}), 401
        return f(*args, **kwargs)
    return decorated
