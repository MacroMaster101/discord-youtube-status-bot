"""Config get/set + presence control."""
import asyncio
import discord
from flask import Blueprint, request, jsonify, current_app
from config import Config
from core import state
from discord_bot.presence import force_presence
from web.auth import require_auth

bp = Blueprint("config", __name__, url_prefix="/api")


def _bot() -> discord.Client:
    return current_app.config["BOT"]


@bp.route("/config", methods=["GET"])
@require_auth
def get_config():
    return jsonify({
        "PREFIX": Config.PREFIX,
        "WELCOME_CHANNEL_ID": Config.WELCOME_CHANNEL_ID or "",
        "MOD_LOG_CHANNEL_ID": Config.MOD_LOG_CHANNEL_ID or "",
        "MUTED_ROLE_NAME": Config.MUTED_ROLE_NAME or "",
        "YOUTUBE_API_KEY_SET": bool(Config.YOUTUBE_API_KEY),
        "YOUTUBE_POLL_INTERVAL": Config.YOUTUBE_POLL_INTERVAL,
    })


@bp.route("/config", methods=["POST"])
@require_auth
def set_config():
    data = request.get_json() or {}
    try:
        for key in ("PREFIX", "WELCOME_CHANNEL_ID", "MOD_LOG_CHANNEL_ID", "MUTED_ROLE_NAME"):
            if key in data:
                Config.update_env(key, str(data[key]))
        if data.get("ADMIN_PASSWORD"):
            Config.update_env("ADMIN_PASSWORD", str(data["ADMIN_PASSWORD"]))
        if "YOUTUBE_API_KEY" in data and data["YOUTUBE_API_KEY"]:
            Config.update_env("YOUTUBE_API_KEY", str(data["YOUTUBE_API_KEY"]))
        state.add_log(f"Configuration updated", "success")
        return jsonify({"status": "success", "token": Config.ADMIN_PASSWORD})
    except Exception as e:
        state.add_log(f"Config save failed: {e}", "error")
        return jsonify({"message": str(e)}), 500


@bp.route("/presence", methods=["POST"])
@require_auth
def presence():
    bot = _bot()
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
