"""Dashboard endpoints: login, stats, logs, servers."""
import threading
import discord
from flask import Blueprint, request, jsonify, current_app
from config import Config
from core import state, storage
from web.auth import require_auth

bp = Blueprint("dashboard", __name__, url_prefix="/api")


def _bot() -> discord.Client:
    return current_app.config["BOT"]


@bp.route("/login", methods=["POST"])
def login():
    data = request.get_json() or {}
    if data.get("password") == Config.ADMIN_PASSWORD:
        return jsonify({"token": Config.ADMIN_PASSWORD}), 200
    return jsonify({"message": "Invalid password"}), 401


@bp.route("/stats")
@require_auth
def stats():
    bot = _bot()
    uptime = state.uptime_seconds()
    h, r = divmod(uptime, 3600)
    m, s = divmod(r, 60)
    uptime_str = f"{h}h {m}m {s}s" if uptime else "N/A"

    ready = bot.is_ready()
    latency_ms = round(bot.latency * 1000) if ready else 0
    server_count = len(bot.guilds) if ready else 0
    total_members = sum(g.member_count for g in bot.guilds) if ready else 0
    online_members = sum(
        1 for g in bot.guilds for m in g.members
        if m.status != discord.Status.offline and not m.bot
    ) if ready else 0
    text_channels = sum(len(g.text_channels) for g in bot.guilds) if ready else 0
    voice_channels = sum(len(g.voice_channels) for g in bot.guilds) if ready else 0

    bot_user = None
    if bot.user:
        bot_user = {
            "name": bot.user.name,
            "discriminator": bot.user.discriminator,
            "avatar": bot.user.display_avatar.url if bot.user.avatar else None,
        }

    return jsonify({
        "status": state.CUSTOM_PRESENCE_STATUS,
        "uptime": uptime_str,
        "uptime_seconds": uptime,
        "latency": latency_ms,
        "server_count": server_count,
        "total_members": total_members,
        "online_members": online_members,
        "text_channels": text_channels,
        "voice_channels": voice_channels,
        "bot_user": bot_user,
        "youtube": {
            "tracked_channels": storage.yt_total_subscriptions(),
            "recent_events": len(state.get_yt_events()),
            "api_configured": bool(Config.YOUTUBE_API_KEY),
        },
        "system": {"threads": threading.active_count()},
    })


@bp.route("/logs")
@require_auth
def logs():
    return jsonify(state.get_logs())


@bp.route("/servers")
@require_auth
def servers():
    bot = _bot()
    if not bot.is_ready():
        return jsonify([])
    result = []
    for guild in bot.guilds:
        channels = [
            {"id": str(ch.id), "name": ch.name}
            for ch in guild.text_channels
            if ch.permissions_for(guild.me).send_messages
        ]
        result.append({
            "id": str(guild.id),
            "name": guild.name,
            "member_count": guild.member_count,
            "icon": guild.icon.url if guild.icon else None,
            "channels": channels,
        })
    return jsonify(result)
