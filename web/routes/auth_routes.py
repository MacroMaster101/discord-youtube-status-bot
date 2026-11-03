"""Discord OAuth2 sign-in routes.

These are browser redirects, not API calls, so the resulting session token is
handed back in an HttpOnly cookie rather than a JSON body: there is no
JavaScript running on the round trip from Discord to pick a token out of a
response, and putting one in the redirect URL would leak it into browser history,
the Referer header and any logs along the way.
"""
from flask import Blueprint, current_app, redirect, request, session

from core import state
from web import oauth
from web.auth import SESSION_COOKIE, create_session, revoke_session, bearer_token

bp = Blueprint("auth_routes", __name__, url_prefix="/auth")

_STATE_KEY = "oauth_state"


def _bot_guild_ids():
    bot = current_app.config.get("BOT")
    try:
        return [g.id for g in getattr(bot, "guilds", []) or []]
    except Exception:
        return []


def _is_https() -> bool:
    """Whether the browser reached us over HTTPS.

    Behind the Cloudflare Tunnel the origin is plain HTTP and only
    X-Forwarded-Proto says otherwise. Trusting it here can only make the cookie
    stricter: a spoofed "https" means the browser then refuses to send the cookie
    back over plain HTTP, which fails the sign-in rather than weakening it.
    """
    if request.is_secure:
        return True
    return request.headers.get("X-Forwarded-Proto", "").split(",")[0].strip() == "https"


def _fail(reason: str, detail: str = ""):
    state.add_log(f"Discord sign-in failed: {reason}{(' - ' + detail) if detail else ''}", "warning")
    # Back to the console, not the public landing page: that is where the
    # login card lives and where the error has somewhere to be shown.
    return redirect(f"/dashboard?auth_error={reason}")


@bp.route("/discord")
def discord_start():
    if not oauth.is_configured():
        return _fail("not_configured")
    value = oauth.new_state()
    session[_STATE_KEY] = value
    return redirect(oauth.authorize_url(value))


@bp.route("/discord/callback")
def discord_callback():
    if not oauth.is_configured():
        return _fail("not_configured")

    # Pop first: a state is single-use whether or not the rest succeeds, so a
    # replayed callback cannot reuse it.
    expected = session.pop(_STATE_KEY, None)
    supplied = request.args.get("state", "")
    if not expected or not supplied or not _constant_eq(expected, supplied):
        return _fail("bad_state")

    if request.args.get("error"):
        return _fail("denied", request.args.get("error", ""))

    code = request.args.get("code", "")
    if not code:
        return _fail("no_code")

    try:
        token = oauth.exchange_code(code)
        user = oauth.fetch_user(token)
        guilds = oauth.fetch_guilds(token)
    except oauth.OAuthError as e:
        return _fail("discord_error", str(e))

    if not oauth.may_sign_in(guilds, _bot_guild_ids()):
        state.add_log(
            f"Discord sign-in refused for {user['username']}: not an admin of a server this bot is in.",
            "warning",
        )
        return _fail("not_authorised")

    dash_token = create_session(via="discord", who=user["username"])
    state.add_log(f"Discord sign-in: {user['username']}", "success")

    response = redirect("/dashboard")
    response.set_cookie(
        SESSION_COOKIE, dash_token,
        httponly=True, samesite="Lax", secure=_is_https(), max_age=12 * 60 * 60, path="/",
    )
    return response


@bp.route("/logout")
def logout():
    revoke_session(bearer_token())
    session.pop(_STATE_KEY, None)
    response = redirect("/")
    response.delete_cookie(SESSION_COOKIE, path="/")
    return response


def _constant_eq(a: str, b: str) -> bool:
    import hmac
    return hmac.compare_digest(str(a), str(b))
