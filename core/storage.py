"""JSON-file persistence for YouTube subscriptions."""
import os
import json
import threading
import datetime
from config import Config

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


# Shape: { guild_id: [ {discord_channel_id, yt_channel_id, yt_channel_title, last_video_id, added_at} ] }

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
    return 1 if Config.YOUTUBE_CHANNEL_ID else 0


# -------- Custom presence rotation entries --------
# Shape: [ {id, activity_type, text, url?} ]

_pres_lock = threading.Lock()


def presence_list() -> list:
    with _pres_lock:
        return _load(Config.CUSTOM_PRESENCE_FILE).get("entries", [])


def presence_add(activity_type: str, text: str, url: str = "") -> dict:
    entry = {
        "id": int(datetime.datetime.utcnow().timestamp() * 1000),
        "activity_type": activity_type,
        "text": text,
        "url": url or None,
    }
    with _pres_lock:
        data = _load(Config.CUSTOM_PRESENCE_FILE)
        entries = data.setdefault("entries", [])
        entries.append(entry)
        _save(Config.CUSTOM_PRESENCE_FILE, data)
    return entry


def presence_remove(entry_id: int) -> bool:
    with _pres_lock:
        data = _load(Config.CUSTOM_PRESENCE_FILE)
        entries = data.get("entries", [])
        before = len(entries)
        data["entries"] = [e for e in entries if e["id"] != entry_id]
        _save(Config.CUSTOM_PRESENCE_FILE, data)
        return len(data["entries"]) < before


def presence_clear():
    with _pres_lock:
        _save(Config.CUSTOM_PRESENCE_FILE, {"entries": []})
