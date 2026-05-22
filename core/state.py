"""Shared in-process state: log buffer, YouTube event feed, presence settings."""
import sys
import threading
import datetime
import collections

LOGS_BUFFER = collections.deque(maxlen=300)
YT_EVENTS_BUFFER = collections.deque(maxlen=100)

# Cache of per-channel metadata refreshed by the poller.
# Shape: { yt_channel_id: {"title": str, "subscriber_count": int, "hidden_subs": bool,
#                           "live_url": str|None, "live_title": str|None,
#                           "url": str} }
YT_CHANNEL_CACHE: dict = {}

# What the bot is currently showing (live preview for the dashboard).
# Shape: {"activity_type": str, "text": str, "url": str|None}
CURRENT_PRESENCE: dict = {"activity_type": "watching", "text": "starting...", "url": None}

PRESENCE_ROTATION_ENABLED = True
CUSTOM_PRESENCE_STATUS = "online"
CUSTOM_PRESENCE_ACTIVITY = "watching"
CUSTOM_PRESENCE_TEXT = ""

BOT_START_TIME: datetime.datetime | None = None

_log_lock = threading.Lock()


def add_log(message: str, level: str = "info"):
    now_utc = datetime.datetime.utcnow()
    timestamp_iso = now_utc.isoformat() + "Z"
    console_ts = now_utc.strftime("%H:%M:%S") + " UTC"
    entry = {"timestamp": timestamp_iso, "message": message, "level": level}
    with _log_lock:
        LOGS_BUFFER.append(entry)
    sys.stdout.write(f"[{console_ts}] [{level.upper()}] {message}\n")
    sys.stdout.flush()


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
