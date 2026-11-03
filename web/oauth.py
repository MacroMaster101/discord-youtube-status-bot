"""Discord OAuth2 sign-in for the dashboard.

The dashboard controls the whole bot, so the bar for getting in is "you already
run a server this bot is in": the signed-in account must have Manage Server or
Administrator on at least one guild the bot is a member of. Being able to see a
guild is not enough, and losing the bot from that guild revokes access on the
next sign-in.

Deliberately dependency-free (urllib, not requests) and synchronous: Flask's
routes run on their own thread while discord.py owns the event loop, so nothing
here may await or touch the loop.
"""
import json
import os
import secrets
import urllib.error
import urllib.parse
import urllib.request

API = "https://discord.com/api/v10"
AUTHORIZE = "https://discord.com/oauth2/authorize"
SCOPES = "identify guilds"

# Discord fronts its API with Cloudflare, which rejects clients by signature.
# urllib's default "Python-urllib/3.x" is refused with HTTP 403 and "error code:
# 1010" before the request reaches the API, so every call identifies itself the
# way Discord documents.
USER_AGENT = ("DiscordBot (https://github.com/MacroMaster101/"
              "discord-youtube-status-bot, 1.0)")

# Discord permission bits. Either of these means "runs this server".
MANAGE_GUILD = 1 << 5
ADMINISTRATOR = 1 << 3


class OAuthError(RuntimeError):
    """Anything that went wrong talking to Discord."""


def client_id() -> str:
    return os.getenv("DISCORD_CLIENT_ID", "").strip()


def client_secret() -> str:
    return os.getenv("DISCORD_CLIENT_SECRET", "").strip()


def redirect_uri() -> str:
    return os.getenv("OAUTH_REDIRECT_URI", "").strip()


def is_configured() -> bool:
    return bool(client_id() and client_secret() and redirect_uri())


def new_state() -> str:
    return secrets.token_urlsafe(24)


def authorize_url(state: str) -> str:
    """Where to send the browser to start the flow."""
    query = urllib.parse.urlencode({
        "client_id": client_id(),
        "redirect_uri": redirect_uri(),
        "response_type": "code",
        "scope": SCOPES,
        "state": state,
    })
    return f"{AUTHORIZE}?{query}"


def _request(url, *, data=None, headers=None, timeout=10):
    body = urllib.parse.urlencode(data).encode() if data else None
    sent = {"User-Agent": USER_AGENT, "Accept": "application/json"}
    sent.update(headers or {})
    request = urllib.request.Request(url, data=body, headers=sent)
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        detail = e.read().decode("utf-8", "replace")[:200]
        raise OAuthError(f"discord returned {e.code}: {detail}") from e
    except (urllib.error.URLError, OSError, ValueError) as e:
        raise OAuthError(f"could not reach discord: {e}") from e


def exchange_code(code: str) -> str:
    """Trade the one-time code for an access token."""
    payload = _request(API + "/oauth2/token", data={
        "client_id": client_id(),
        "client_secret": client_secret(),
        "grant_type": "authorization_code",
        "code": code,
        "redirect_uri": redirect_uri(),
    }, headers={"Content-Type": "application/x-www-form-urlencoded"})
    token = payload.get("access_token")
    if not token:
        raise OAuthError("no access token in the response")
    return token


def _bearer(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


def fetch_user(token: str) -> dict:
    me = _request(API + "/users/@me", headers=_bearer(token))
    return {
        "id": str(me.get("id", "")),
        "username": me.get("global_name") or me.get("username") or "unknown",
        "avatar": me.get("avatar"),
    }


def fetch_guilds(token: str) -> list:
    guilds = _request(API + "/users/@me/guilds", headers=_bearer(token))
    return guilds if isinstance(guilds, list) else []


def runs_guild(guild: dict) -> bool:
    """Does this membership carry enough authority to configure the bot?"""
    try:
        permissions = int(guild.get("permissions", 0))
    except (TypeError, ValueError):
        return False
    if guild.get("owner"):
        return True
    return bool(permissions & (MANAGE_GUILD | ADMINISTRATOR))


def allowed_user_ids() -> frozenset:
    """Discord user ids explicitly permitted to sign in, if the list is in use.

    Empty means "not in use", which leaves the guild rule as the only gate.
    """
    raw = os.getenv("DASHBOARD_ALLOWED_USERS", "")
    return frozenset(part.strip() for part in raw.replace(";", ",").split(",") if part.strip())


def may_sign_in(user_guilds: list, bot_guild_ids, user_id=None) -> bool:
    """True when this account may open the dashboard.

    The guild rule on its own is broader than it looks: it admits anyone holding
    Manage Server or Administrator on a server the bot is in, so promoting a
    moderator in Discord would hand them the dashboard -- which can broadcast as
    the bot, rewrite its tokens and restart it. Setting DASHBOARD_ALLOWED_USERS
    adds a second gate so that only named accounts get in.

    Both gates must pass. Keeping the guild rule means access still disappears
    when someone is demoted, rather than resting on the list alone, and an id
    left behind on the list after a demotion does not stay privileged.
    """
    allowed = allowed_user_ids()
    if allowed and str(user_id or "") not in allowed:
        return False

    present = {str(g) for g in bot_guild_ids}
    return any(
        str(guild.get("id", "")) in present and runs_guild(guild)
        for guild in user_guilds
    )
