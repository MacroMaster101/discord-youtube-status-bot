"""YouTube channel hub management endpoints."""
import asyncio
import discord
from flask import Blueprint, jsonify, current_app
from core import state
from config import Config
from web.auth import require_auth

bp = Blueprint("youtube", __name__, url_prefix="/api/youtube")


def _bot() -> discord.Client:
    return current_app.config["BOT"]


@bp.route("/channel-hub")
@require_auth
def channel_hub():
    """Get the primary channel stats and live status, recent events, and configuration."""
    bot = _bot()
    cache = state.YT_CHANNEL_CACHE
    channel_info = None
    if Config.YOUTUBE_CHANNEL_ID:
        channel_info = cache.get(Config.YOUTUBE_CHANNEL_ID)
    if not channel_info and cache:
        channel_info = list(cache.values())[0]

    return jsonify({
        "channel": channel_info,
        "configured_id": Config.YOUTUBE_CHANNEL_ID,
        "api_configured": bool(Config.YOUTUBE_API_KEY),
        "notify_channel_id": Config.YOUTUBE_NOTIFY_CHANNEL_ID,
        "welcome_channel_id": Config.WELCOME_CHANNEL_ID,
        "events": state.get_yt_events(),
    })


@bp.route("/subscriptions")
@require_auth
def subscriptions():
    """Fallback stub to support legacy calls if any."""
    bot = _bot()
    cache = state.YT_CHANNEL_CACHE
    channel_info = None
    if Config.YOUTUBE_CHANNEL_ID:
        channel_info = cache.get(Config.YOUTUBE_CHANNEL_ID)
    if not channel_info and cache:
        channel_info = list(cache.values())[0]
        
    out = []
    if channel_info:
        out.append({
            "guild_id": "all",
            "guild_name": "Primary Channel",
            "discord_channel_id": Config.YOUTUBE_NOTIFY_CHANNEL_ID or Config.WELCOME_CHANNEL_ID or "N/A",
            "discord_channel_name": "Notify Channel",
            "yt_channel_id": Config.YOUTUBE_CHANNEL_ID,
            "yt_channel_title": channel_info["title"],
            "last_video_id": Config.YOUTUBE_LAST_VIDEO_ID,
            "added_at": "Setup",
        })
    return jsonify({"subscriptions": out})


@bp.route("/events")
@require_auth
def events():
    return jsonify(state.get_yt_events())
