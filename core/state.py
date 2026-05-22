"""Shared in-process state: log buffer, mod-action audit feed, presence settings."""
import sys
import threading
import datetime
import collections

LOGS_BUFFER = collections.deque(maxlen=300)
MOD_ACTIONS_BUFFER = collections.deque(maxlen=300)
YT_EVENTS_BUFFER = collections.deque(maxlen=100)

PRESENCE_ROTATION_ENABLED = True
CUSTOM_PRESENCE_STATUS = "online"
CUSTOM_PRESENCE_ACTIVITY = "watching"
CUSTOM_PRESENCE_TEXT = ""

BOT_START_TIME: datetime.datetime | None = None

_log_lock = threading.Lock()


def add_log(message: str, level: str = "info"):
    timestamp = datetime.datetime.now().strftime("%H:%M:%S")
    entry = {"timestamp": timestamp, "message": message, "level": level}
    with _log_lock:
        LOGS_BUFFER.append(entry)
    sys.stdout.write(f"[{timestamp}] [{level.upper()}] {message}\n")
    sys.stdout.flush()


def add_mod_action(action: str, moderator, target, reason: str, guild_name: str):
    entry = {
        "timestamp": datetime.datetime.utcnow().isoformat() + "Z",
        "time": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "action": action,
        "moderator": str(moderator),
        "target": str(target),
        "reason": reason or "No reason provided",
        "guild": guild_name,
    }
    with _log_lock:
        MOD_ACTIONS_BUFFER.append(entry)
    add_log(f"MOD: {action} {target} by {moderator} in {guild_name} — {reason or 'no reason'}", "warning")


def add_yt_event(channel_title: str, video_title: str, video_url: str, guild_name: str):
    entry = {
        "time": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "channel": channel_title,
        "video": video_title,
        "url": video_url,
        "guild": guild_name,
    }
    with _log_lock:
        YT_EVENTS_BUFFER.append(entry)
    add_log(f"YT: new upload from {channel_title} → {video_title} (posted to {guild_name})", "success")


def get_logs():
    with _log_lock:
        return list(LOGS_BUFFER)


def get_mod_actions():
    with _log_lock:
        return list(MOD_ACTIONS_BUFFER)


def get_yt_events():
    with _log_lock:
        return list(YT_EVENTS_BUFFER)


def set_start_time():
    global BOT_START_TIME
    BOT_START_TIME = datetime.datetime.utcnow()


def uptime_seconds() -> int:
    if not BOT_START_TIME:
        return 0
    return int((datetime.datetime.utcnow() - BOT_START_TIME).total_seconds())
