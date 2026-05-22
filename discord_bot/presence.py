"""Rotating bot presence — YouTube-focused.
If any tracked channel is LIVE, show a Streaming activity linking to the stream.
Otherwise rotate through each tracked channel with subscriber count, linking to
the channel page. Falls back to a hint if no channels are tracked yet."""
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


def _pick_activity():
    """Return a (discord.Activity, used_streaming_flag) for the next rotation tick."""
    cache = state.YT_CHANNEL_CACHE

    # Priority 1: any channel currently live → Streaming activity with stream URL.
    live = [(cid, info) for cid, info in cache.items() if info.get("live_url")]
    if live:
        # Rotate among live channels if there are multiple.
        if not hasattr(_pick_activity, "_live_idx"):
            _pick_activity._live_idx = 0
        idx = _pick_activity._live_idx % len(live)
        _pick_activity._live_idx += 1
        cid, info = live[idx]
        name = f"🔴 LIVE: {info['title']}"[:128]
        return discord.Streaming(name=name, url=info["live_url"], platform="YouTube",
                                 details=info.get("live_title")), True

    # Priority 2: rotate through tracked channels with sub counts.
    if cache:
        items = list(cache.items())
        if not hasattr(_pick_activity, "_idx"):
            _pick_activity._idx = 0
        idx = _pick_activity._idx % (len(items) + 1)
        _pick_activity._idx += 1
        if idx < len(items):
            cid, info = items[idx]
            subs = "" if info.get("hidden_subs") else f" · {_format_subs(info['subscriber_count'])} subs"
            name = f"📺 {info['title']}{subs}"[:128]
            # Streaming activity gives the clickable channel link in user's profile.
            return discord.Streaming(name=name, url=info["url"], platform="YouTube"), True
        # Every Nth tick, show a summary instead.
        total = len(items)
        name = f"📺 {total} YT channel{'s' if total != 1 else ''}"
        return discord.Activity(type=discord.ActivityType.watching, name=name), False

    # Priority 3: nothing tracked yet.
    return discord.Activity(type=discord.ActivityType.watching, name="📺 /yt subscribe to start"), False


def start_presence(client: discord.Client):
    @tasks.loop(seconds=20)
    async def rotate():
        if not state.PRESENCE_ROTATION_ENABLED:
            return
        activity, _ = _pick_activity()
        status = _STATUS_MAP.get(state.CUSTOM_PRESENCE_STATUS, discord.Status.online)
        try:
            await client.change_presence(status=status, activity=activity)
        except Exception as e:
            state.add_log(f"presence change failed: {e}", "error")

    @rotate.before_loop
    async def before():
        await client.wait_until_ready()

    if not rotate.is_running():
        rotate.start()
    client._rotate_task = rotate


async def force_presence(client: discord.Client, status: str, activity: str, text: str, prefix: str):
    act_type = _ACT_MAP.get(activity, discord.ActivityType.watching)
    server_count = len(client.guilds)
    yt_subs = storage.yt_total_subscriptions()
    formatted = text.format(
        server_count=server_count,
        yt_subs=yt_subs,
        prefix=prefix,
    ) if text else "📺 YouTube tracker"
    activity_obj = discord.Activity(type=act_type, name=formatted[:128])
    await client.change_presence(
        status=_STATUS_MAP.get(status, discord.Status.online),
        activity=activity_obj,
    )
