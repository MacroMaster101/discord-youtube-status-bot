"""JSON-file persistence for warnings and YouTube subscriptions."""
import os
import json
import time
import threading
import datetime
from config import Config

_warn_lock = threading.Lock()
_yt_lock = threading.Lock()


def _load(path: str) -> dict:
    if not os.path.exists(path):
        return {}
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def _save(path: str, data: dict):
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)
    os.replace(tmp, path)


# -------- Warnings --------

def add_warning(guild_id, user_id, moderator_id, reason) -> int:
    with _warn_lock:
        data = _load(Config.WARNINGS_FILE)
        gkey, ukey = str(guild_id), str(user_id)
        data.setdefault(gkey, {}).setdefault(ukey, [])
        data[gkey][ukey].append({
            "id": int(time.time() * 1000),
            "moderator": str(moderator_id),
            "reason": reason or "No reason provided",
            "time": datetime.datetime.utcnow().isoformat() + "Z",
        })
        _save(Config.WARNINGS_FILE, data)
        return len(data[gkey][ukey])


def get_warnings(guild_id, user_id) -> list:
    with _warn_lock:
        data = _load(Config.WARNINGS_FILE)
        return data.get(str(guild_id), {}).get(str(user_id), [])


def clear_warnings(guild_id, user_id) -> int:
    with _warn_lock:
        data = _load(Config.WARNINGS_FILE)
        gkey, ukey = str(guild_id), str(user_id)
        if gkey in data and ukey in data[gkey]:
            count = len(data[gkey][ukey])
            del data[gkey][ukey]
            _save(Config.WARNINGS_FILE, data)
            return count
        return 0


def all_warnings_for_guild(guild_id) -> dict:
    with _warn_lock:
        return _load(Config.WARNINGS_FILE).get(str(guild_id), {})


def total_warnings() -> int:
    with _warn_lock:
        data = _load(Config.WARNINGS_FILE)
    return sum(len(u) for g in data.values() for u in g.values())


# -------- YouTube subscriptions --------
# Shape: { guild_id: { channel_id: { yt_channel_id, yt_channel_title, last_video_id } } }
# guild_id+discord_channel_id is the post target; one Discord channel can subscribe to multiple YT channels via a list.
# To keep things simple we use composite key "guild_id:discord_channel_id:yt_channel_id" inside a flat list per guild.

def yt_list_all() -> dict:
    with _yt_lock:
        return _load(Config.YOUTUBE_SUBS_FILE)


def yt_list_for_guild(guild_id) -> list:
    return yt_list_all().get(str(guild_id), [])


def yt_add(guild_id, discord_channel_id, yt_channel_id, yt_channel_title) -> bool:
    with _yt_lock:
        data = _load(Config.YOUTUBE_SUBS_FILE)
        subs = data.setdefault(str(guild_id), [])
        for s in subs:
            if s["yt_channel_id"] == yt_channel_id and str(s["discord_channel_id"]) == str(discord_channel_id):
                return False
        subs.append({
            "discord_channel_id": str(discord_channel_id),
            "yt_channel_id": yt_channel_id,
            "yt_channel_title": yt_channel_title,
            "last_video_id": None,
            "added_at": datetime.datetime.utcnow().isoformat() + "Z",
        })
        _save(Config.YOUTUBE_SUBS_FILE, data)
        return True


def yt_remove(guild_id, discord_channel_id, yt_channel_id) -> bool:
    with _yt_lock:
        data = _load(Config.YOUTUBE_SUBS_FILE)
        subs = data.get(str(guild_id), [])
        before = len(subs)
        subs = [s for s in subs if not (s["yt_channel_id"] == yt_channel_id and str(s["discord_channel_id"]) == str(discord_channel_id))]
        data[str(guild_id)] = subs
        _save(Config.YOUTUBE_SUBS_FILE, data)
        return len(subs) < before


def yt_update_last_video(guild_id, discord_channel_id, yt_channel_id, video_id):
    with _yt_lock:
        data = _load(Config.YOUTUBE_SUBS_FILE)
        for s in data.get(str(guild_id), []):
            if s["yt_channel_id"] == yt_channel_id and str(s["discord_channel_id"]) == str(discord_channel_id):
                s["last_video_id"] = video_id
                break
        _save(Config.YOUTUBE_SUBS_FILE, data)


def yt_total_subscriptions() -> int:
    return sum(len(v) for v in yt_list_all().values())
