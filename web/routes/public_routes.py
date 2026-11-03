"""The parts of the bot anyone may see.

Everything here is unauthenticated, so the rule is simple: only publish what is
already public on the YouTube channel itself, plus whether the bot is up. No
logs, no configuration, no Discord server details, no counts of anything
internal. If a field would tell a stranger something they could not learn by
opening the channel in a browser, it does not belong in this file.

Nothing here calls the YouTube API. It reads the cache the poller already
maintains, so a burst of traffic costs nothing in quota.
"""
from flask import Blueprint, Response, current_app, jsonify

from config import Config
from core import state

bp = Blueprint("public", __name__)


def _channel():
    cache = state.YT_CHANNEL_CACHE
    if Config.YOUTUBE_CHANNEL_ID and Config.YOUTUBE_CHANNEL_ID in cache:
        return cache[Config.YOUTUBE_CHANNEL_ID]
    return next(iter(cache.values()), None)


def _link(title, url):
    return {"title": title, "url": url} if title and url else None


@bp.route("/api/public/stats")
def public_stats():
    bot = current_app.config.get("BOT")
    try:
        online = bool(bot and bot.is_ready())
    except Exception:
        online = False

    info = _channel()
    channel = None
    if info:
        channel = {
            "title": info.get("title"),
            "thumbnail": info.get("thumbnail"),
            "url": info.get("url"),
            # Hidden subscriber counts stay hidden: the channel owner chose that.
            "subscribers": None if info.get("hidden_subs") else info.get("subscriber_count"),
            "views": info.get("view_count"),
            "videos": info.get("video_count"),
            "live": _link(info.get("live_title"), info.get("live_url")),
            "upcoming": _link(info.get("upcoming_title"), info.get("upcoming_url")),
            "latest": _link(info.get("latest_video_title"), info.get("latest_video_url")),
        }

    return jsonify({"bot": {"online": online}, "channel": channel})


@bp.route("/robots.txt")
def robots():
    # The landing page is fine to index. Everything that takes a credential, or
    # answers differently once you have one, is not.
    body = (
        "User-agent: *\n"
        "Disallow: /dashboard\n"
        "Disallow: /api/\n"
        "Disallow: /auth/\n"
        "Allow: /api/public/\n"
    )
    return Response(body, mimetype="text/plain")
