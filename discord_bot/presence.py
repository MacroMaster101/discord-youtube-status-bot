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

    # 1. Live streams take top priority. Show channel and stream title: 🔴 LIVE: {title} — {live_title}
    live = [(cid, info) for cid, info in cache.items() if info.get("live_url")]
    if live:
        if not hasattr(_pick, "_live_idx"):
            _pick._live_idx = 0
        idx = _pick._live_idx % len(live)
        _pick._live_idx += 1
        _, info = live[idx]
        text = _format_status_text("🔴 LIVE: {title} — {live_title}", client, info)
        return (_build_activity("streaming", text, info["live_url"]),
                {"activity_type": "streaming", "text": text, "url": info["live_url"]})

    # 2. Custom entries from the dashboard.
    custom = storage.presence_list()
    if custom:
        if not hasattr(_pick, "_cust_idx"):
            _pick._cust_idx = 0
        idx = _pick._cust_idx % len(custom)
        _pick._cust_idx += 1
        e = custom[idx]
        text = e["text"] or ""

        # Select active rotating channel for context, cycling through them
        channel_info = None
        if cache:
            items = list(cache.values())
            if not hasattr(_pick, "_cust_chan_idx"):
                _pick._cust_chan_idx = 0
            chan_idx = _pick._cust_chan_idx % len(items)
            _pick._cust_chan_idx += 1
            channel_info = items[chan_idx]

        formatted = _format_status_text(text, client, channel_info)
        return (_build_activity(e["activity_type"], formatted, e.get("url")),
                {"activity_type": e["activity_type"], "text": formatted, "url": e.get("url")})

    # 3. YT channel rotation. Cycles through 3 variants per channel + 1 global summary at the end.
    if cache:
        items = list(cache.items())
        if not hasattr(_pick, "_idx"):
            _pick._idx = 0
        total_variants = len(items) * 3
        idx = _pick._idx % (total_variants + 1)
        _pick._idx += 1

        if idx < total_variants:
            channel_idx = idx // 3
            variant_idx = idx % 3
            _, info = items[channel_idx]
            if variant_idx == 0:
                text = _format_status_text("📺 {title} · {subs} subs", client, info)
            elif variant_idx == 1:
                text = _format_status_text("📺 {title} · {views} views", client, info)
            else:
                text = _format_status_text("📺 {title} · {videos} videos", client, info)

            return (_build_activity("streaming", text, info["url"]),
                    {"activity_type": "streaming", "text": text, "url": info["url"]})

        total = len(items)
        text = f"📺 {total} YT channel{'s' if total != 1 else ''}"
        return (_build_activity("watching", text, None),
                {"activity_type": "watching", "text": text, "url": None})

    # 4. Empty fallback.
    text = "📺 /yt subscribe to start"
    return (_build_activity("watching", text, None),
            {"activity_type": "watching", "text": text, "url": None})


def start_presence(client: discord.Client):
    @tasks.loop(seconds=20)
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

    if not rotate.is_running():
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


