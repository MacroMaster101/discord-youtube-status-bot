"""YouTube API parsing and poller posting logic. No network or Discord connection is used."""
import asyncio

import pytest

from config import Config
from core import state
from youtube import api, poller


def _video(vid, status):
    return {
        "id": vid, "title": f"Video {vid}", "thumbnail": None, "channel_title": "Channel",
        "published_at": "", "url": f"https://www.youtube.com/watch?v={vid}", "status": status,
    }


def test_uploads_playlist_id():
    assert api._uploads_playlist_id("UCcCp0B0bypJE4EJjwq8u2lQ") == "UUcCp0B0bypJE4EJjwq8u2lQ"


def test_recent_uploads_parses_and_keeps_playlist_order(monkeypatch):
    async def fake_get(session, path, params):
        if path == "playlistItems":
            return {"items": [{"contentDetails": {"videoId": v}} for v in ("A", "GONE", "B")]}
        assert path == "videos"
        return {"items": [  # API order differs from playlist order; "GONE" is private/deleted
            {"id": "B", "snippet": {"title": "b", "liveBroadcastContent": "none", "thumbnails": {"high": {"url": "hb"}}}},
            {"id": "A", "snippet": {"title": "a", "liveBroadcastContent": "live",
                                    "thumbnails": {"high": {"url": "ha"}, "maxres": {"url": "ma"}}}},
        ]}

    monkeypatch.setattr(api, "_get", fake_get)
    uploads = asyncio.run(api.recent_uploads("UC" + "x" * 22))
    assert [v["id"] for v in uploads] == ["A", "B"]
    assert uploads[0]["status"] == "live"
    assert uploads[0]["thumbnail"] == "ma"  # prefers maxres
    assert uploads[1]["thumbnail"] == "hb"


@pytest.mark.parametrize("uploads, expected", [
    ([], (None, None, None)),
    ([_video("S", "upcoming"), _video("V", "none")], (None, "S", "V")),
    ([_video("L", "live"), _video("V", "none")], ("L", None, "L")),
])
def test_channel_activity_picks_live_upcoming_latest(monkeypatch, uploads, expected):
    async def fake_recent(_):
        return uploads

    monkeypatch.setattr(api, "recent_uploads", fake_recent)
    live, upcoming, latest = asyncio.run(api.channel_activity("UC" + "x" * 22))
    assert tuple(v and v["id"] for v in (live, upcoming, latest)) == expected


class _Channel:
    name = "youtube-feed"

    def __init__(self, sent):
        self.sent = sent

    async def send(self, content=None, embed=None):
        self.sent.append(content)


class _Guild:
    name = "guild"

    def __init__(self, sent):
        self.sent = sent

    def get_channel(self, cid):
        return _Channel(self.sent) if cid == 123 else None


class _Client:
    def __init__(self, sent):
        self.guilds = [_Guild(sent)]

    async def change_presence(self, **kwargs):
        pass

    async def wait_until_ready(self):
        pass


def test_poller_posts_once_when_stream_goes_live_and_once_per_upload(monkeypatch):
    monkeypatch.setattr(Config, "update_env", classmethod(lambda cls, k, v: setattr(cls, k, v)))
    monkeypatch.setattr(Config, "YOUTUBE_API_KEY", "fake")
    monkeypatch.setattr(Config, "YOUTUBE_CHANNEL_ID", "UC" + "x" * 22)
    monkeypatch.setattr(Config, "YOUTUBE_NOTIFY_CHANNEL_ID", "123")
    monkeypatch.setattr(Config, "YOUTUBE_LAST_VIDEO_ID", "OLD")
    monkeypatch.setattr(state, "YT_CHANNEL_CACHE", {})

    async def fake_info(_):
        return {"id": Config.YOUTUBE_CHANNEL_ID, "title": "Channel", "subscriber_count": 1}

    monkeypatch.setattr(api, "resolve_channel", fake_info)

    steps = [
        ((None, _video("S", "upcoming"), _video("OLD", "none")), 0),  # scheduled: not posted yet
        ((_video("S", "live"), None, _video("S", "live")), 1),        # goes live: posted
        ((_video("S", "live"), None, _video("S", "live")), 0),        # still live
        ((None, None, _video("S", "none")), 0),                       # ended, VOD has same id
        ((None, None, _video("V", "none")), 1),                       # normal upload
    ]
    sent = []
    loop = poller.setup_poller(_Client(sent))
    for result, expected_posts in steps:
        async def fake_activity(_, r=result):
            return r

        monkeypatch.setattr(api, "channel_activity", fake_activity)
        before = len(sent)
        asyncio.run(loop.coro())
        assert len(sent) - before == expected_posts

    assert "is live now" in sent[0]
    assert "uploaded a new video" in sent[1]
    assert Config.YOUTUBE_LAST_VIDEO_ID == "V"
