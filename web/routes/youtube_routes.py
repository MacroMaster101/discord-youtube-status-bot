"""YouTube subscription management endpoints + recent upload feed."""
import asyncio
import discord
from flask import Blueprint, request, jsonify, current_app
from core import state, storage
from youtube import api as yt_api
from web.auth import require_auth

bp = Blueprint("youtube", __name__, url_prefix="/api/youtube")


def _bot() -> discord.Client:
    return current_app.config["BOT"]


@bp.route("/subscriptions")
@require_auth
def subscriptions():
    """All YT subs across all guilds, enriched with guild & channel names."""
    bot = _bot()
    out = []
    for guild_id, subs in storage.yt_list_all().items():
        guild = bot.get_guild(int(guild_id)) if bot.is_ready() else None
        for s in subs:
            ch = guild.get_channel(int(s["discord_channel_id"])) if guild else None
            out.append({
                "guild_id": guild_id,
                "guild_name": guild.name if guild else f"Unknown ({guild_id})",
                "discord_channel_id": s["discord_channel_id"],
                "discord_channel_name": ch.name if ch else "(missing)",
                "yt_channel_id": s["yt_channel_id"],
                "yt_channel_title": s["yt_channel_title"],
                "last_video_id": s.get("last_video_id"),
                "added_at": s.get("added_at"),
            })
    return jsonify({"subscriptions": out})


@bp.route("/events")
@require_auth
def events():
    return jsonify(state.get_yt_events())


@bp.route("/subscribe", methods=["POST"])
@require_auth
def subscribe():
    bot = _bot()
    data = request.get_json() or {}
    guild_id = data.get("guild_id")
    channel_id = data.get("discord_channel_id")
    query = data.get("query")
    if not (guild_id and channel_id and query):
        return jsonify({"message": "guild_id, discord_channel_id, query required"}), 400

    fut = asyncio.run_coroutine_threadsafe(yt_api.resolve_channel(query), bot.loop)
    try:
        info = fut.result(timeout=15)
    except yt_api.YouTubeError as e:
        return jsonify({"message": str(e)}), 400
    except Exception as e:
        return jsonify({"message": str(e)}), 500
    if not info:
        return jsonify({"message": "Channel not found"}), 404

    added = storage.yt_add(guild_id, channel_id, info["id"], info["title"])
    if not added:
        return jsonify({"message": "Already subscribed"}), 409
    state.add_log(f"YT subscribe (dashboard): {info['title']}", "success")
    return jsonify({"status": "success", "channel": info})


@bp.route("/unsubscribe", methods=["POST"])
@require_auth
def unsubscribe():
    data = request.get_json() or {}
    guild_id = data.get("guild_id")
    channel_id = data.get("discord_channel_id")
    yt_channel_id = data.get("yt_channel_id")
    if not (guild_id and channel_id and yt_channel_id):
        return jsonify({"message": "guild_id, discord_channel_id, yt_channel_id required"}), 400
    removed = storage.yt_remove(guild_id, channel_id, yt_channel_id)
    if not removed:
        return jsonify({"message": "Subscription not found"}), 404
    state.add_log(f"YT unsubscribe (dashboard): {yt_channel_id}", "info")
    return jsonify({"status": "success"})


@bp.route("/lookup", methods=["POST"])
@require_auth
def lookup():
    """Resolve a channel query → channel info, used by the dashboard preview."""
    bot = _bot()
    data = request.get_json() or {}
    query = data.get("query")
    if not query:
        return jsonify({"message": "query required"}), 400
    fut = asyncio.run_coroutine_threadsafe(yt_api.resolve_channel(query), bot.loop)
    try:
        info = fut.result(timeout=15)
    except yt_api.YouTubeError as e:
        return jsonify({"message": str(e)}), 400
    except Exception as e:
        return jsonify({"message": str(e)}), 500
    if not info:
        return jsonify({"message": "Not found"}), 404
    return jsonify(info)
