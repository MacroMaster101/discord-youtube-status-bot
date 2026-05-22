"""Rotating bot presence — YouTube-focused. Cycles through tracked YT channel names
and a few static YT-themed statuses. No member/presence intents needed."""
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


def _build_statuses():
    """Build the rotation: tracked YT channels first, then a few static fillers."""
    statuses = []
    seen = set()
    for subs in storage.yt_list_all().values():
        for s in subs:
            title = s.get("yt_channel_title")
            if title and title not in seen:
                seen.add(title)
                statuses.append((discord.ActivityType.watching, f"📺 {title}"))

    total = len(seen)
    if total:
        statuses.append((discord.ActivityType.watching, f"📺 {total} YT channel{'s' if total != 1 else ''}"))
    else:
        statuses.append((discord.ActivityType.watching, "📺 /yt subscribe to start"))

    statuses.append((discord.ActivityType.playing, "/help · YouTube tracker"))
    return statuses


def start_presence(client: discord.Client):
    @tasks.loop(seconds=20)
    async def rotate():
        if not state.PRESENCE_ROTATION_ENABLED:
            return
        statuses = _build_statuses()
        if not hasattr(rotate, "_index"):
            rotate._index = 0
        idx = rotate._index % len(statuses)
        rotate._index += 1
        activity_type, text = statuses[idx]
        activity = discord.Activity(type=activity_type, name=text[:128])
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
