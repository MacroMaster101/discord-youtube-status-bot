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
    if n >= 1_000_000:
        return f"{n/1_000_000:.1f}M".replace(".0M", "M")
    if n >= 1_000:
        return f"{n/1_000:.1f}K".replace(".0K", "K")
    return str(n)


def _build_activity(activity_type: str, text: str, url: str | None):
    text = (text or "")[:128]
    if activity_type == "streaming":
        return discord.Streaming(name=text or "YouTube", url=url or "https://www.youtube.com", platform="YouTube")
    return discord.Activity(type=_ACT_MAP.get(activity_type, discord.ActivityType.watching), name=text)


def _pick():
    """Return (activity, preview_dict) for the next rotation tick."""
    cache = state.YT_CHANNEL_CACHE

    # 1. Live streams take top priority.
    live = [(cid, info) for cid, info in cache.items() if info.get("live_url")]
    if live:
        if not hasattr(_pick, "_live_idx"):
            _pick._live_idx = 0
        idx = _pick._live_idx % len(live)
        _pick._live_idx += 1
        _, info = live[idx]
        text = f"🔴 LIVE: {info['title']}"
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
        return (_build_activity(e["activity_type"], e["text"], e.get("url")),
                {"activity_type": e["activity_type"], "text": e["text"], "url": e.get("url")})

    # 3. YT channel rotation.
    if cache:
        items = list(cache.items())
        if not hasattr(_pick, "_idx"):
            _pick._idx = 0
        idx = _pick._idx % (len(items) + 1)
        _pick._idx += 1
        if idx < len(items):
            _, info = items[idx]
            subs = "" if info.get("hidden_subs") else f" · {_format_subs(info['subscriber_count'])} subs"
            text = f"📺 {info['title']}{subs}"
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
        activity, preview = _pick()
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
    act = _build_activity(activity_type, text, None)
    try:
        await bot.change_presence(status=ds, activity=act)
        state.CURRENT_PRESENCE = {"activity_type": activity_type, "text": text, "url": None}
    except Exception as e:
        state.add_log(f"force_presence failed: {e}", "error")

