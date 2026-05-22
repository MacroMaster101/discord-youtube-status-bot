"""Async YouTube Data API v3 client. Only the few endpoints we need."""
import re
import aiohttp
from typing import Optional
from config import Config

BASE = "https://www.googleapis.com/youtube/v3"

_HANDLE_RE = re.compile(r"youtube\.com/@([A-Za-z0-9_\-.]+)")
_CHANNEL_RE = re.compile(r"youtube\.com/channel/(UC[A-Za-z0-9_\-]{22})")
_USER_RE = re.compile(r"youtube\.com/user/([A-Za-z0-9_\-]+)")
_C_RE = re.compile(r"youtube\.com/c/([A-Za-z0-9_\-]+)")


class YouTubeError(Exception):
    pass


def _require_key():
    if not Config.YOUTUBE_API_KEY:
        raise YouTubeError("YOUTUBE_API_KEY is not configured")


async def _get(session: aiohttp.ClientSession, path: str, params: dict) -> dict:
    _require_key()
    params = {**params, "key": Config.YOUTUBE_API_KEY}
    async with session.get(f"{BASE}/{path}", params=params, timeout=aiohttp.ClientTimeout(total=15)) as r:
        body = await r.json(content_type=None)
        if r.status != 200:
            msg = body.get("error", {}).get("message", f"HTTP {r.status}")
            raise YouTubeError(msg)
        return body


async def resolve_channel(query: str) -> Optional[dict]:
    """Resolve a channel from URL, @handle, channel ID, or search term.
    Returns {id, title, subscriber_count, view_count, thumbnail} or None.
    """
    query = query.strip()
    channel_id = None
    handle = None

    if m := _CHANNEL_RE.search(query):
        channel_id = m.group(1)
    elif m := _HANDLE_RE.search(query):
        handle = m.group(1)
    elif query.startswith("@"):
        handle = query[1:]
    elif query.startswith("UC") and len(query) == 24:
        channel_id = query
    elif m := _USER_RE.search(query):
        handle = m.group(1)
    elif m := _C_RE.search(query):
        handle = m.group(1)

    async with aiohttp.ClientSession() as session:
        if channel_id is None:
            if handle:
                data = await _get(session, "channels", {"part": "id", "forHandle": handle})
                items = data.get("items", [])
                if items:
                    channel_id = items[0]["id"]
            if channel_id is None:
                # last resort: search
                data = await _get(session, "search", {"part": "snippet", "type": "channel", "q": query, "maxResults": 1})
                items = data.get("items", [])
                if not items:
                    return None
                channel_id = items[0]["snippet"]["channelId"]

        data = await _get(session, "channels", {"part": "snippet,statistics", "id": channel_id})
        items = data.get("items", [])
        if not items:
            return None
        it = items[0]
        sn = it["snippet"]
        st = it.get("statistics", {})
        return {
            "id": it["id"],
            "title": sn["title"],
            "description": sn.get("description", ""),
            "thumbnail": sn.get("thumbnails", {}).get("high", {}).get("url"),
            "subscriber_count": int(st.get("subscriberCount", 0)),
            "view_count": int(st.get("viewCount", 0)),
            "video_count": int(st.get("videoCount", 0)),
            "hidden_subs": st.get("hiddenSubscriberCount", False),
        }


async def live_stream(yt_channel_id: str) -> Optional[dict]:
    """If the channel is currently live, return {id, title, url}. Else None."""
    async with aiohttp.ClientSession() as session:
        data = await _get(session, "search", {
            "part": "snippet", "channelId": yt_channel_id, "eventType": "live",
            "type": "video", "maxResults": 1,
        })
        items = data.get("items", [])
        if not items:
            return None
        it = items[0]
        vid = it["id"]["videoId"]
        sn = it["snippet"]
        return {
            "id": vid,
            "title": sn["title"],
            "url": f"https://www.youtube.com/watch?v={vid}",
        }


async def upcoming_stream(yt_channel_id: str) -> Optional[dict]:
    """If the channel has an upcoming scheduled live stream, return {id, title, url}. Else None."""
    async with aiohttp.ClientSession() as session:
        data = await _get(session, "search", {
            "part": "snippet", "channelId": yt_channel_id, "eventType": "upcoming",
            "type": "video", "maxResults": 1,
        })
        items = data.get("items", [])
        if not items:
            return None
        it = items[0]
        vid = it["id"]["videoId"]
        sn = it["snippet"]
        return {
            "id": vid,
            "title": sn["title"],
            "url": f"https://www.youtube.com/watch?v={vid}",
        }


async def latest_video(yt_channel_id: str) -> Optional[dict]:
    """Returns {id, title, thumbnail, published_at, url} for the most recent upload, or None."""
    async with aiohttp.ClientSession() as session:
        data = await _get(session, "search", {
            "part": "snippet", "channelId": yt_channel_id, "order": "date",
            "type": "video", "maxResults": 1,
        })
        items = data.get("items", [])
        if not items:
            return None
        it = items[0]
        vid = it["id"]["videoId"]
        sn = it["snippet"]
        return {
            "id": vid,
            "title": sn["title"],
            "thumbnail": sn.get("thumbnails", {}).get("high", {}).get("url"),
            "channel_title": sn.get("channelTitle"),
            "published_at": sn.get("publishedAt"),
            "url": f"https://www.youtube.com/watch?v={vid}",
        }
