"""Keep the suite independent of whoever is running it.

config.py calls load_dotenv() when imported, so a developer's real .env lands in
os.environ as soon as the tests import anything. That made results depend on the
machine: with DASHBOARD_ALLOWED_USERS set locally the guild-rule tests failed,
while CI passed because there is no .env there. A test that passes in CI and
fails on your laptop teaches people to distrust the suite.

Every variable the application reads is cleared before each test. A test that
cares about one sets it explicitly with monkeypatch, which still works -- this
only removes the ambient value.
"""
import pytest

# Mirrors os.getenv() calls across config.py, web/oauth.py and web/access.py.
APP_ENV_VARS = (
    "DISCORD_TOKEN",
    "ADMIN_PASSWORD",
    "YOUTUBE_API_KEY",
    "YOUTUBE_CHANNEL_ID",
    "YOUTUBE_NOTIFY_CHANNEL_ID",
    "YOUTUBE_LAST_VIDEO_ID",
    "YOUTUBE_POLL_INTERVAL",
    "PREFIX",
    "PORT",
    "FLASK_SECRET_KEY",
    "DISCORD_CLIENT_ID",
    "DISCORD_CLIENT_SECRET",
    "OAUTH_REDIRECT_URI",
    "DASHBOARD_ALLOWED_USERS",
    "CF_ACCESS_TEAM_DOMAIN",
    "CF_ACCESS_AUD",
)


@pytest.fixture(autouse=True)
def _no_ambient_env(monkeypatch):
    for name in APP_ENV_VARS:
        monkeypatch.delenv(name, raising=False)
