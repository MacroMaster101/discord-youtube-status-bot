"""Discord OAuth sign-in rules, Cloudflare Access trust, and how they reach require_auth."""
import pytest

from config import Config
from web import access, auth, oauth
from web.app import create_app


@pytest.fixture(autouse=True)
def isolated(tmp_path, monkeypatch):
    monkeypatch.setattr(Config, "PERSISTENT_CONFIG_FILE", str(tmp_path / "config.json"))
    monkeypatch.setattr(Config, "ADMIN_PASSWORD_HASH", "")
    monkeypatch.setattr(Config, "update_env", classmethod(lambda cls, k, v: setattr(cls, k, v)))
    auth.revoke_all_sessions()
    access.reset_for_tests()
    yield
    access.reset_for_tests()


@pytest.fixture
def client():
    return create_app(bot=None).test_client()


# --- who may sign in with Discord -------------------------------------------------

ADMIN = str(oauth.ADMINISTRATOR)
MANAGE = str(oauth.MANAGE_GUILD)


def test_admin_of_a_guild_the_bot_is_in_may_sign_in():
    guilds = [{"id": "1", "permissions": ADMIN}]
    assert oauth.may_sign_in(guilds, ["1"]) is True


def test_manage_guild_is_enough():
    guilds = [{"id": "1", "permissions": MANAGE}]
    assert oauth.may_sign_in(guilds, ["1"]) is True


def test_owner_flag_is_enough_without_permission_bits():
    guilds = [{"id": "1", "permissions": "0", "owner": True}]
    assert oauth.may_sign_in(guilds, ["1"]) is True


def test_admin_of_an_unrelated_guild_may_not_sign_in():
    """Running some other server says nothing about this bot."""
    guilds = [{"id": "999", "permissions": ADMIN}]
    assert oauth.may_sign_in(guilds, ["1"]) is False


def test_ordinary_member_of_the_bots_guild_may_not_sign_in():
    """Being in the server is not authority over it."""
    guilds = [{"id": "1", "permissions": "0"}]
    assert oauth.may_sign_in(guilds, ["1"]) is False


def test_no_guilds_at_all_may_not_sign_in():
    assert oauth.may_sign_in([], ["1"]) is False


def test_garbled_permissions_do_not_grant_access():
    guilds = [{"id": "1", "permissions": "not-a-number"}]
    assert oauth.may_sign_in(guilds, ["1"]) is False


# --- Cloudflare Access ------------------------------------------------------------

def test_access_is_disabled_without_configuration(monkeypatch):
    monkeypatch.delenv("CF_ACCESS_TEAM_DOMAIN", raising=False)
    monkeypatch.delenv("CF_ACCESS_AUD", raising=False)
    assert access.is_configured() is False


def test_email_header_alone_never_authenticates(client, monkeypatch):
    """The header is attacker-supplied; only the signed JWT counts.

    This is the whole reason web/access.py refuses to read the email header, so
    it is worth a test that would fail loudly if that ever changed.
    """
    monkeypatch.delenv("CF_ACCESS_TEAM_DOMAIN", raising=False)
    monkeypatch.delenv("CF_ACCESS_AUD", raising=False)
    r = client.get("/api/stats", headers={
        "Cf-Access-Authenticated-User-Email": "attacker@example.com",
        "Cf-Access-Jwt-Assertion": "not.a.real.jwt",
    })
    assert r.status_code == 401


def test_unverifiable_assertion_is_refused(client, monkeypatch):
    """Configured but the token does not verify -> still unauthorised."""
    monkeypatch.setenv("CF_ACCESS_TEAM_DOMAIN", "example.cloudflareaccess.com")
    monkeypatch.setenv("CF_ACCESS_AUD", "a" * 64)
    access.reset_for_tests()
    r = client.get("/api/stats", headers={"Cf-Access-Jwt-Assertion": "garbage"})
    assert r.status_code == 401


# --- sessions and the cookie ------------------------------------------------------

def test_oauth_cookie_authenticates(client):
    token = auth.create_session(via="discord", who="someone")
    client.set_cookie("dash_session", token)
    assert client.get("/api/stats").status_code != 401


def test_empty_bearer_header_does_not_mask_the_cookie(client):
    """The dashboard always sends "Bearer " + whatever it has, often nothing."""
    token = auth.create_session(via="discord", who="someone")
    client.set_cookie("dash_session", token)
    r = client.get("/api/stats", headers={"Authorization": "Bearer "})
    assert r.status_code != 401


def test_revoked_session_cookie_stops_working(client):
    token = auth.create_session(via="discord", who="someone")
    client.set_cookie("dash_session", token)
    auth.revoke_session(token)
    assert client.get("/api/stats").status_code == 401


def test_session_endpoint_reports_unauthenticated_without_credentials(client):
    body = client.get("/api/session").get_json()
    assert body["authenticated"] is False
    assert body["via"] is None


def test_session_endpoint_reports_how_we_signed_in(client):
    token = auth.create_session(via="discord", who="someone")
    client.set_cookie("dash_session", token)
    body = client.get("/api/session").get_json()
    assert body["authenticated"] is True
    assert body["via"] == "discord"
    assert body["who"] == "someone"


def test_logout_clears_the_cookie(client):
    token = auth.create_session(via="discord", who="someone")
    client.set_cookie("dash_session", token)
    client.post("/api/logout")
    assert auth.session_valid(token) is False


# --- the OAuth routes themselves ---------------------------------------------------

def test_start_refuses_when_oauth_is_not_configured(client, monkeypatch):
    for key in ("DISCORD_CLIENT_ID", "DISCORD_CLIENT_SECRET", "OAUTH_REDIRECT_URI"):
        monkeypatch.delenv(key, raising=False)
    r = client.get("/auth/discord")
    assert r.status_code == 302
    assert "auth_error=not_configured" in r.headers["Location"]


def test_callback_rejects_a_mismatched_state(client, monkeypatch):
    monkeypatch.setenv("DISCORD_CLIENT_ID", "id")
    monkeypatch.setenv("DISCORD_CLIENT_SECRET", "secret")
    monkeypatch.setenv("OAUTH_REDIRECT_URI", "https://example.com/auth/discord/callback")
    r = client.get("/auth/discord/callback?code=x&state=forged")
    assert r.status_code == 302
    assert "auth_error=bad_state" in r.headers["Location"]


# --- the explicit user allowlist ---------------------------------------------------

ADMIN_OF_OURS = [{"id": "1", "permissions": ADMIN}]


def test_without_an_allowlist_the_guild_rule_still_governs(monkeypatch):
    monkeypatch.delenv("DASHBOARD_ALLOWED_USERS", raising=False)
    assert oauth.may_sign_in(ADMIN_OF_OURS, ["1"], "999") is True


def test_a_listed_admin_may_sign_in(monkeypatch):
    monkeypatch.setenv("DASHBOARD_ALLOWED_USERS", "42")
    assert oauth.may_sign_in(ADMIN_OF_OURS, ["1"], "42") is True


def test_an_unlisted_admin_is_refused(monkeypatch):
    """The whole point: being a server admin is no longer enough on its own."""
    monkeypatch.setenv("DASHBOARD_ALLOWED_USERS", "42")
    assert oauth.may_sign_in(ADMIN_OF_OURS, ["1"], "999") is False


def test_a_listed_non_admin_is_still_refused(monkeypatch):
    """Both gates apply, so a demotion revokes access even while listed."""
    monkeypatch.setenv("DASHBOARD_ALLOWED_USERS", "42")
    member_only = [{"id": "1", "permissions": "0"}]
    assert oauth.may_sign_in(member_only, ["1"], "42") is False


def test_a_missing_user_id_is_refused_when_the_list_is_in_use(monkeypatch):
    monkeypatch.setenv("DASHBOARD_ALLOWED_USERS", "42")
    assert oauth.may_sign_in(ADMIN_OF_OURS, ["1"], None) is False


def test_the_list_tolerates_spaces_and_separators(monkeypatch):
    monkeypatch.setenv("DASHBOARD_ALLOWED_USERS", " 7 , 42 ; 99 ")
    assert oauth.allowed_user_ids() == frozenset({"7", "42", "99"})
    assert oauth.may_sign_in(ADMIN_OF_OURS, ["1"], "42") is True


def test_an_empty_list_is_treated_as_not_in_use(monkeypatch):
    monkeypatch.setenv("DASHBOARD_ALLOWED_USERS", "   ")
    assert oauth.allowed_user_ids() == frozenset()
    assert oauth.may_sign_in(ADMIN_OF_OURS, ["1"], "999") is True


def test_ids_are_compared_as_strings_not_numbers(monkeypatch):
    """Discord ids exceed 2^53, so they travel as strings throughout."""
    monkeypatch.setenv("DASHBOARD_ALLOWED_USERS", "1507300707613806694")
    assert oauth.may_sign_in(ADMIN_OF_OURS, ["1"], 1507300707613806694) is True
