"""Rotating bot presence.

Priority order:
1. If any tracked YouTube channel is LIVE → Streaming activity with stream URL.
2. If user has added custom presence entries via the dashboard → rotate those.
3. Otherwise rotate through tracked YT channels (name + sub count) as Streaming.
4. Fallback: '/yt subscribe to start' hint.

Also writes the active activity to state.CURRENT_PRESENCE so the dashboard
can show a live preview.
"""
import discord
from discord.ext import tasks
from core import state, storage

_STATUS_MAP = {
    "online": discord.Status.online,
    "idle": discord.Status.idle,
    "dnd": discord.Status.dnd,
    "invisible": discord.Status.invisible,
}

_ACT_MAP = {
    "playing": discord.ActivityType.playing,
    "watching": discord.ActivityType.watching,
    "listening": discord.ActivityType.listening,
    "streaming": discord.ActivityType.streaming,
}


def _format_subs(n: int) -> str:
    try:
        n = int(n)
    except (ValueError, TypeError):
        return "0"
    if n >= 1_000_000:
        return f"{n/1_000_000:.1f}M".replace(".0M", "M")
    if n >= 1_000:
        return f"{n/1_000:.1f}K".replace(".0K", "K")
    return str(n)


def _format_views(n: int) -> str:
    try:
        n = int(n)
    except (ValueError, TypeError):
        return "0"
    if n >= 1_000_000_000:
        return f"{n/1_000_000_000:.1f}B".replace(".0B", "B")
    if n >= 1_000_000:
        return f"{n/1_000_000:.1f}M".replace(".0M", "M")
    if n >= 1_000:
        return f"{n/1_000:.1f}K".replace(".0K", "K")
    return str(n)


def _format_status_text(text: str, client: discord.Client, channel_info: dict | None = None) -> str:
    if not text:
        return ""

    cache = state.YT_CHANNEL_CACHE

    # Fallback to the first cached channel's statistics when single-channel variables are queried globally
    if not channel_info and cache:
        channel_info = list(cache.values())[0]

    server_count = len(client.guilds) if hasattr(client, "guilds") else 0
    yt_subs = storage.yt_total_subscriptions()
    from config import Config
    prefix = Config.PREFIX or "$"

    total_subs_val = sum(info.get("subscriber_count", 0) for info in cache.values())
    total_views_val = sum(info.get("view_count", 0) for info in cache.values())
    total_videos_val = sum(info.get("video_count", 0) for info in cache.values())

    kwargs = {
        "server_count": server_count,
        "yt_subs": yt_subs,
        "prefix": prefix,
        "total_subs": _format_subs(total_subs_val),
        "total_views": _format_views(total_views_val),
        "total_videos": f"{total_videos_val:,}",
        "title": "",
        "channel_title": "",
        "subs": "",
        "views": "",
        "videos": "",
        "live_title": "",
        "live_url": "",
        "upcoming_title": "",
        "upcoming_url": "",
        "latest_video_title": "",
        "latest_video_url": "",
    }

    if channel_info:
        kwargs.update({
            "title": channel_info["title"],
            "channel_title": channel_info["title"],
            "subs": "hidden" if channel_info.get("hidden_subs") else _format_subs(channel_info["subscriber_count"]),
            "views": _format_views(channel_info.get("view_count", 0)),
            "videos": f"{channel_info.get('video_count', 0):,}",
            "live_title": channel_info.get("live_title") or "",
            "live_url": channel_info.get("live_url") or "",
            "upcoming_title": channel_info.get("upcoming_title") or "",
            "upcoming_url": channel_info.get("upcoming_url") or "",
            "latest_video_title": channel_info.get("latest_video_title") or "",
            "latest_video_url": channel_info.get("latest_video_url") or "",
        })

    try:
        return text.format(**kwargs)
    except Exception:
        return text


def _build_activity(activity_type: str, text: str, url: str | None):
    text = (text or "")[:128]
    if activity_type == "streaming":
        return discord.Streaming(name=text or "YouTube", url=url or "https://www.youtube.com", platform="YouTube")
    return discord.Activity(type=_ACT_MAP.get(activity_type, discord.ActivityType.watching), name=text)


def _pick(client: discord.Client):
    """Return (activity, preview_dict) for the next rotation tick."""
    cache = state.YT_CHANNEL_CACHE
    from config import Config

    channel_info = None
    if Config.YOUTUBE_CHANNEL_ID:
        channel_info = cache.get(Config.YOUTUBE_CHANNEL_ID)
    if not channel_info and cache:
        channel_info = list(cache.values())[0]

    # If channel is live, pin the live status — don't rotate away from it
    if channel_info and channel_info.get("live_url"):
        text = "🔴 LIVE: {live_title}"
        formatted = _format_status_text(text, client, channel_info)
        url = channel_info["live_url"]
        activity = _build_activity("streaming", formatted, url)
        preview = {"activity_type": "streaming", "text": formatted, "url": url}
        return activity, preview

    # Build rotation items
    rotation_items = []

    if channel_info:
        rotation_items.append({
            "activity_type": "streaming",
            "text": "📺 {title} · {subs} subs",
            "url": channel_info["url"],
            "channel_info": channel_info
        })
        rotation_items.append({
            "activity_type": "streaming",
            "text": "📺 {title} · {views} views",
            "url": channel_info["url"],
            "channel_info": channel_info
        })
        rotation_items.append({
            "activity_type": "streaming",
            "text": "📺 {title} · {videos} videos",
            "url": channel_info["url"],
            "channel_info": channel_info
        })
        if channel_info.get("upcoming_title"):
            rotation_items.append({
                "activity_type": "streaming",
                "text": "📅 Upcoming: {upcoming_title}",
                "url": channel_info["upcoming_url"],
                "channel_info": channel_info
            })
        if channel_info.get("latest_video_title"):
            rotation_items.append({
                "activity_type": "streaming",
                "text": "🆕 New: {latest_video_title}",
                "url": channel_info["latest_video_url"],
                "channel_info": channel_info
            })

    # Add help command reminder to rotation (always present)
    rotation_items.append({
        "activity_type": "watching",
        "text": "💡 Type {prefix}help for commands",
        "url": None,
        "channel_info": channel_info
    })

    # Custom entries from the dashboard
    custom = storage.presence_list()
    for e in custom:
        rotation_items.append({
            "activity_type": e["activity_type"],
            "text": e["text"],
            "url": e.get("url"),
            "channel_info": channel_info
        })

    # Empty fallback
    if not rotation_items:
        status_text = "📺 Setup YouTube Bot in Dashboard"
        return (_build_activity("watching", status_text, None),
                {"activity_type": "watching", "text": status_text, "url": None})

    # Cycle through the rotation items
    if not hasattr(_pick, "_idx"):
        _pick._idx = 0
    idx = _pick._idx % len(rotation_items)
    if getattr(_pick, "_advance", True):
        _pick._idx += 1

    item = rotation_items[idx]
    formatted = _format_status_text(item["text"], client, item["channel_info"])

    url = item.get("url")
    if item["activity_type"] == "streaming" and not url:
        url = "https://www.youtube.com"

    return (_build_activity(item["activity_type"], formatted, url),
            {"activity_type": item["activity_type"], "text": formatted, "url": url})


def _peek(client: discord.Client):
    """Return current presence without advancing the rotation index."""
    _pick._advance = False
    try:
        return _pick(client)
    finally:
        _pick._advance = True


def start_presence(client: discord.Client):
    # Guard against on_ready firing multiple times (reconnects) spawning duplicate loops
    if getattr(client, "_rotate_task", None) and client._rotate_task.is_running():
        return

    @tasks.loop(seconds=30)
    async def rotate():
        if not state.PRESENCE_ROTATION_ENABLED:
            return
        activity, preview = _pick(client)
        status = _STATUS_MAP.get(state.CUSTOM_PRESENCE_STATUS, discord.Status.online)
        try:
            await client.change_presence(status=status, activity=activity)
            state.CURRENT_PRESENCE = preview
        except Exception as e:
            state.add_log(f"presence change failed: {e}", "error")

    @rotate.before_loop
    async def before():
        await client.wait_until_ready()

    rotate.start()
    client._rotate_task = rotate


async def force_presence(bot, status: str, activity_type: str, text: str, prefix: str = ""):
    """One-shot presence change used by the dashboard when rotation is disabled."""
    ds = _STATUS_MAP.get(status, discord.Status.online)
    formatted = _format_status_text(text, bot)

    act = _build_activity(activity_type, formatted, None)
    try:
        await bot.change_presence(status=ds, activity=act)
        state.CURRENT_PRESENCE = {"activity_type": activity_type, "text": formatted, "url": None}
    except Exception as e:
        state.add_log(f"force_presence failed: {e}", "error")


