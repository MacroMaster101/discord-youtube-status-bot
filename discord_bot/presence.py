"""Rotating bot presence.

Priority order:
1. If any tracked YouTube channel is LIVE → Streaming activity with stream URL.
2. If user has added custom presence entries via the dashboard → rotate those.
3. Otherwise rotate through tracked YT channels (name + sub count) as Streaming.
4. Fallback: help hint.

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

# Module-level client reference set by start_presence()
_client: discord.Client | None = None
_rotation_index = 0


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


def _build_rotation_items(channel_info: dict | None) -> list:
    items = []

    if channel_info:
        items.append({"activity_type": "streaming", "text": "📺 {title} · {subs} subs", "url": channel_info["url"], "channel_info": channel_info})
        items.append({"activity_type": "streaming", "text": "📺 {title} · {views} views", "url": channel_info["url"], "channel_info": channel_info})
        items.append({"activity_type": "streaming", "text": "📺 {title} · {videos} videos", "url": channel_info["url"], "channel_info": channel_info})
        if channel_info.get("upcoming_title"):
            items.append({"activity_type": "streaming", "text": "📅 Upcoming: {upcoming_title}", "url": channel_info["upcoming_url"], "channel_info": channel_info})
        if channel_info.get("latest_video_title"):
            items.append({"activity_type": "streaming", "text": "🆕 New: {latest_video_title}", "url": channel_info["latest_video_url"], "channel_info": channel_info})

    items.append({"activity_type": "watching", "text": "💡 Type {prefix}help for commands", "url": None, "channel_info": channel_info})

    for e in storage.presence_list():
        items.append({"activity_type": e["activity_type"], "text": e["text"], "url": e.get("url"), "channel_info": channel_info})

    return items


def _pick(advance: bool = True) -> tuple:
    """Return (activity, preview_dict) for the current rotation position."""
    global _rotation_index, _client

    client = _client
    cache = state.YT_CHANNEL_CACHE
    from config import Config

    channel_info = None
    if Config.YOUTUBE_CHANNEL_ID:
        channel_info = cache.get(Config.YOUTUBE_CHANNEL_ID)
    if not channel_info and cache:
        channel_info = list(cache.values())[0]

    # Pin live status
    if channel_info and channel_info.get("live_url"):
        text = "🔴 LIVE: {live_title}"
        formatted = _format_status_text(text, client, channel_info)
        url = channel_info["live_url"]
        activity = _build_activity("streaming", formatted, url)
        preview = {"activity_type": "streaming", "text": formatted, "url": url}
        return activity, preview

    rotation_items = _build_rotation_items(channel_info)

    if not rotation_items:
        status_text = "📺 Setup YouTube Bot in Dashboard"
        return (_build_activity("watching", status_text, None),
                {"activity_type": "watching", "text": status_text, "url": None})

    idx = _rotation_index % len(rotation_items)
    if advance:
        _rotation_index += 1

    item = rotation_items[idx]
    formatted = _format_status_text(item["text"], client, item["channel_info"])

    url = item.get("url")
    if item["activity_type"] == "streaming" and not url:
        url = "https://www.youtube.com"

    return (_build_activity(item["activity_type"], formatted, url),
            {"activity_type": item["activity_type"], "text": formatted, "url": url})


def _peek() -> tuple:
    """Return current presence without advancing the rotation index."""
    return _pick(advance=False)


# Module-level loop — defined once, safe to check .is_running() across reconnects
@tasks.loop(seconds=15)
async def _rotate():
    if not state.PRESENCE_ROTATION_ENABLED or _client is None:
        return
    activity, preview = _pick(advance=True)
    status = _STATUS_MAP.get(state.CUSTOM_PRESENCE_STATUS, discord.Status.online)
    try:
        await _client.change_presence(status=status, activity=activity)
        state.CURRENT_PRESENCE = preview
    except Exception as e:
        state.add_log(f"presence change failed: {e}", "error")


@_rotate.before_loop
async def _before_rotate():
    if _client is not None:
        await _client.wait_until_ready()


def start_presence(client: discord.Client):
    global _client
    _client = client
    if not _rotate.is_running():
        _rotate.start()


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
