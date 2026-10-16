"""Dashboard auth and presence formatting."""
import secrets

from config import Config
from discord_bot import presence
from web.auth import check_password


def test_check_password(monkeypatch):
    # Random per run, so no password-looking literal lives in the repo.
    expected = secrets.token_hex(8)
    monkeypatch.setattr(Config, "ADMIN_PASSWORD", expected)
    assert check_password(expected)
    assert not check_password(expected + "x")
    assert not check_password(None)
    assert not check_password("")


def test_format_counts():
    assert presence._format_subs(230) == "230"
    assert presence._format_subs(1500) == "1.5K"
    assert presence._format_subs(2_000_000) == "2M"
    assert presence._format_views(3_400_000_000) == "3.4B"
    assert presence._format_subs("bad") == "0"


def test_presence_entries_roundtrip(tmp_path, monkeypatch):
    from core import storage

    monkeypatch.setattr(Config, "CUSTOM_PRESENCE_FILE", str(tmp_path / "presence.json"))
    assert storage.presence_list() == []
    entry = storage.presence_add("watching", "{subs} subs")
    assert storage.presence_list() == [entry]
    assert storage.presence_remove(entry["id"])
    assert storage.presence_list() == []
