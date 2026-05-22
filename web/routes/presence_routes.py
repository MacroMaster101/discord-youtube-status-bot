"""Custom presence management endpoints: list, add, remove, current preview."""
from flask import Blueprint, request, jsonify
from core import state, storage
from web.auth import require_auth

bp = Blueprint("presence", __name__, url_prefix="/api/presence")


@bp.route("/current")
@require_auth
def current():
    """What the bot is currently displaying as its Discord presence."""
    return jsonify(state.CURRENT_PRESENCE)


@bp.route("/entries")
@require_auth
def entries():
    return jsonify(storage.presence_list())


@bp.route("/entries", methods=["POST"])
@require_auth
def add_entry():
    data = request.get_json() or {}
    activity_type = data.get("activity_type", "watching")
    text = data.get("text", "").strip()
    url = data.get("url", "").strip()
    if not text:
        return jsonify({"message": "Text is required"}), 400
    entry = storage.presence_add(activity_type, text, url)
    state.add_log(f"Custom presence added: {activity_type} — {text}", "success")
    return jsonify(entry), 201


@bp.route("/entries/<int:entry_id>", methods=["DELETE"])
@require_auth
def remove_entry(entry_id):
    removed = storage.presence_remove(entry_id)
    if not removed:
        return jsonify({"message": "Entry not found"}), 404
    state.add_log(f"Custom presence removed (id={entry_id})", "info")
    return jsonify({"status": "success"})


@bp.route("/entries/clear", methods=["POST"])
@require_auth
def clear_entries():
    storage.presence_clear()
    state.add_log("All custom presence entries cleared", "info")
    return jsonify({"status": "success"})
