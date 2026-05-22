"""Rotating bot presence. Cycles between server stats and YouTube subscription count."""
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


def start_presence(client: discord.Client):
    @tasks.loop(seconds=20)
    async def rotate():
        if not state.PRESENCE_ROTATION_ENABLED:
            return
        total_members = sum(g.member_count for g in client.guilds)
        total_online = sum(
            1 for g in client.guilds for m in g.members
            if m.status != discord.Status.offline and not m.bot
        )
        server_count = len(client.guilds)
        yt_subs = storage.yt_total_subscriptions()

        statuses = [
            (discord.ActivityType.watching, f"👥 {total_members:,} members"),
            (discord.ActivityType.watching, f"🟢 {total_online:,} online"),
            (discord.ActivityType.watching, f"🌐 {server_count} server{'s' if server_count != 1 else ''}"),
        ]
        if yt_subs:
            statuses.append((discord.ActivityType.watching, f"📺 {yt_subs} YT channel{'s' if yt_subs != 1 else ''}"))
        statuses.append((discord.ActivityType.playing, "/help | Moderating 🛡️"))

        if not hasattr(rotate, "_index"):
            rotate._index = 0
        idx = rotate._index % len(statuses)
        rotate._index += 1
        activity_type, text = statuses[idx]
        activity = discord.Activity(type=activity_type, name=text)
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
    # Expose for manual triggers from the web API
    client._rotate_task = rotate


async def force_presence(client: discord.Client, status: str, activity: str, text: str, prefix: str):
    act_type = _ACT_MAP.get(activity, discord.ActivityType.watching)
    total_members = sum(g.member_count for g in client.guilds) if client.guilds else 0
    online_members = sum(
        1 for g in client.guilds for m in g.members
        if m.status != discord.Status.offline and not m.bot
    )
    server_count = len(client.guilds)
    formatted = text.format(
        total_members=f"{total_members:,}",
        online_members=f"{online_members:,}",
        server_count=server_count,
        prefix=prefix,
    ) if text else "/help"
    activity_obj = discord.Activity(type=act_type, name=formatted)
    await client.change_presence(
        status=_STATUS_MAP.get(status, discord.Status.online),
        activity=activity_obj,
    )
