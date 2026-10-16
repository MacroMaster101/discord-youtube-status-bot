"""JSON-file persistence for custom presence entries."""
import os
import json
import threading
import datetime
from config import Config


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


def yt_total_subscriptions() -> int:
    """Number of tracked YouTube channels (the bot follows one main channel)."""
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
