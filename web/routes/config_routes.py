"""Config get/set + presence control + API key test."""
import asyncio
import discord
import urllib.request
import urllib.error
import json as _json
from flask import Blueprint, request, jsonify, current_app
from config import Config
from core import state
from discord_bot.presence import force_presence
from web.auth import require_auth

bp = Blueprint("config", __name__, url_prefix="/api")


@bp.route("/test-yt-key", methods=["POST"])
@require_auth
def test_yt_key():
    """Test a YouTube API key by making a lightweight channels.list call."""
    data = request.get_json() or {}
    key = data.get("key", "").strip()
    if not key:
        key = Config.YOUTUBE_API_KEY
    if not key:
        return jsonify({"ok": False, "message": "No API key provided or saved"}), 400
    try:
        url = (
            "https://www.googleapis.com/youtube/v3/channels"
            f"?part=id&id=UC_x5XG1OV2P6uZZ5FSM9Ttw&key={key}"
        )
        req = urllib.request.Request(url, headers={"Accept": "application/json"})
        with urllib.request.urlopen(req, timeout=10) as resp:
            body = _json.loads(resp.read())
        if body.get("items"):
            return jsonify({"ok": True, "message": "API key is valid ✓"})
        return jsonify({"ok": False, "message": "Unexpected response — key may be invalid"})
    except urllib.error.HTTPError as e:
        msg = f"HTTP {e.code}"
        try:
            err_body = _json.loads(e.read())
            msg = err_body.get("error", {}).get("message", msg)
        except Exception:
            pass
        return jsonify({"ok": False, "message": msg}), 400
    except Exception as e:
        return jsonify({"ok": False, "message": str(e)}), 500


def _bot() -> discord.Client:
    return current_app.config["BOT"]


@bp.route("/config", methods=["GET"])
@require_auth
def get_config():
    return jsonify({
        "PREFIX": Config.PREFIX,
        "WELCOME_CHANNEL_ID": Config.WELCOME_CHANNEL_ID or "",
        "YOUTUBE_API_KEY_SET": bool(Config.YOUTUBE_API_KEY),
        "YOUTUBE_CHANNEL_ID": Config.YOUTUBE_CHANNEL_ID or "",
        "YOUTUBE_NOTIFY_CHANNEL_ID": Config.YOUTUBE_NOTIFY_CHANNEL_ID or "",
        "YOUTUBE_POLL_INTERVAL": Config.YOUTUBE_POLL_INTERVAL,
    })


@bp.route("/config", methods=["POST"])
@require_auth
def set_config():
    data = request.get_json() or {}
    try:
        for key in ("PREFIX", "WELCOME_CHANNEL_ID", "YOUTUBE_NOTIFY_CHANNEL_ID"):
            if key in data:
                Config.update_env(key, str(data[key]))
        if data.get("ADMIN_PASSWORD"):
            Config.update_env("ADMIN_PASSWORD", str(data["ADMIN_PASSWORD"]))
        if "YOUTUBE_API_KEY" in data and data["YOUTUBE_API_KEY"]:
            Config.update_env("YOUTUBE_API_KEY", str(data["YOUTUBE_API_KEY"]))
        if "YOUTUBE_CHANNEL_ID" in data:
            Config.update_env("YOUTUBE_CHANNEL_ID", str(data["YOUTUBE_CHANNEL_ID"]))
        state.add_log(f"Configuration updated", "success")
        return jsonify({"status": "success", "token": Config.ADMIN_PASSWORD})
    except Exception as e:
        state.add_log(f"Config save failed: {e}", "error")
        return jsonify({"message": str(e)}), 500


@bp.route("/presence", methods=["GET", "POST"])
@require_auth
def presence():
    bot = _bot()
    if request.method == "GET":
        return jsonify({
            "status": state.CUSTOM_PRESENCE_STATUS,
            "activity": state.CUSTOM_PRESENCE_ACTIVITY,
            "text": state.CUSTOM_PRESENCE_TEXT,
            "rotation": state.PRESENCE_ROTATION_ENABLED
        })

    data = request.get_json() or {}
    status = data.get("status", "online")
    activity = data.get("activity", "watching")
    text = data.get("text", "")
    rotation = data.get("rotation", True)

    state.CUSTOM_PRESENCE_STATUS = status
    state.CUSTOM_PRESENCE_ACTIVITY = activity
    state.CUSTOM_PRESENCE_TEXT = text
    state.PRESENCE_ROTATION_ENABLED = rotation
    state.add_log(f"Presence updated: status={status}, activity={activity}, rotation={rotation}", "info")

    if not rotation:
        asyncio.run_coroutine_threadsafe(
            force_presence(bot, status, activity, text, Config.PREFIX), bot.loop
        )
    return jsonify({"status": "success"})
