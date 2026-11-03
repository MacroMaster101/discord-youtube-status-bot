"""The public landing page and its stats endpoint, which take no credentials."""
import pytest

from config import Config
from core import state
from web import auth
from web.app import create_app

CHANNEL = {
    "title": "JustForFun",
    "description": "unused",
    "thumbnail": "https://example.invalid/avatar.jpg",
    "subscriber_count": 12345,
    "view_count": 678901,
    "video_count": 42,
    "hidden_subs": False,
    "url": "https://www.youtube.com/channel/UCxxxx",
    "live_url": None,
    "live_title": None,
    "upcoming_title": None,
    "upcoming_url": None,
    "latest_video_title": "A new video",
    "latest_video_url": "https://youtu.be/abc123",
}


@pytest.fixture(autouse=True)
def isolated(tmp_path, monkeypatch):
    monkeypatch.setattr(Config, "PERSISTENT_CONFIG_FILE", str(tmp_path / "config.json"))
    monkeypatch.setattr(Config, "YOUTUBE_CHANNEL_ID", "UCxxxx")
    auth.revoke_all_sessions()
    state.YT_CHANNEL_CACHE.clear()
    yield
    state.YT_CHANNEL_CACHE.clear()


@pytest.fixture
def client():
    return create_app(bot=None).test_client()


@pytest.fixture
def populated():
    state.YT_CHANNEL_CACHE["UCxxxx"] = dict(CHANNEL)


def test_stats_need_no_credentials(client, populated):
    r = client.get("/api/public/stats")
    assert r.status_code == 200
    assert r.get_json()["channel"]["title"] == "JustForFun"


def test_stats_publish_only_public_channel_facts(client, populated):
    """Anything a stranger could not read off the channel page must not appear."""
    channel = client.get("/api/public/stats").get_json()["channel"]
    assert set(channel) == {
        "title", "thumbnail", "url", "subscribers", "views", "videos",
        "live", "upcoming", "latest",
    }


def test_stats_never_expose_internals(client, populated, monkeypatch):
    monkeypatch.setattr(Config, "YOUTUBE_API_KEY", "SECRET-API-KEY")
    monkeypatch.setattr(Config, "DISCORD_TOKEN", "SECRET-TOKEN")
    monkeypatch.setattr(Config, "ADMIN_PASSWORD", "SECRET-PASSWORD")
    state.add_log("a private log line", "info")
    body = client.get("/api/public/stats").get_data(as_text=True)
    for secret in ("SECRET-API-KEY", "SECRET-TOKEN", "SECRET-PASSWORD", "private log line"):
        assert secret not in body


def test_hidden_subscriber_count_stays_hidden(client):
    hidden = dict(CHANNEL, hidden_subs=True)
    state.YT_CHANNEL_CACHE["UCxxxx"] = hidden
    channel = client.get("/api/public/stats").get_json()["channel"]
    assert channel["subscribers"] is None
    # The other figures are still public.
    assert channel["views"] == 678901


def test_stats_survive_an_empty_cache(client):
    """Before the first poll there is nothing to show, and that is not an error."""
    body = client.get("/api/public/stats").get_json()
    assert body["channel"] is None
    assert body["bot"]["online"] is False


def test_live_stream_is_surfaced(client):
    state.YT_CHANNEL_CACHE["UCxxxx"] = dict(
        CHANNEL, live_title="Streaming now", live_url="https://youtu.be/live1"
    )
    live = client.get("/api/public/stats").get_json()["channel"]["live"]
    assert live == {"title": "Streaming now", "url": "https://youtu.be/live1"}


def test_a_half_filled_link_is_dropped(client):
    """A title with no url would render an anchor pointing nowhere."""
    state.YT_CHANNEL_CACHE["UCxxxx"] = dict(CHANNEL, latest_video_url=None)
    assert client.get("/api/public/stats").get_json()["channel"]["latest"] is None


# --- routing ---------------------------------------------------------------------

def test_root_serves_the_public_page_not_the_console(client):
    body = client.get("/").get_data(as_text=True)
    assert "loginPassword" not in body
    assert "/api/public/stats" in body


def test_dashboard_serves_the_console(client):
    body = client.get("/dashboard").get_data(as_text=True)
    assert "loginPassword" in body


def test_robots_keeps_crawlers_out_of_the_private_surface(client):
    body = client.get("/robots.txt").get_data(as_text=True)
    assert "Disallow: /dashboard" in body
    assert "Disallow: /api/" in body
    assert "Disallow: /auth/" in body
