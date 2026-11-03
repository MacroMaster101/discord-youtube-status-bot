"""Flask app factory + keep_alive thread launcher. Routes are split into modules under web/routes/."""
import os
import secrets
import threading
import discord
from flask import Flask, render_template
from config import Config
from web.routes import (
    dashboard, broadcast, youtube_routes, config_routes, presence_routes, auth_routes,
    public_routes,
)


def _secret_key() -> str:
    """Key for the signed session cookie that carries the OAuth state.

    A generated key is fine for a single process -- the cookie only has to
    survive the round trip to Discord -- but it changes on every restart, so set
    FLASK_SECRET_KEY in .env to stop sign-ins being interrupted by a redeploy.
    """
    configured = os.getenv("FLASK_SECRET_KEY", "").strip()
    if configured:
        return configured
    return secrets.token_urlsafe(32)


def create_app(bot: discord.Client) -> Flask:
    template_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "templates"))
    app = Flask(__name__, template_folder=template_dir)
    app.config["BOT"] = bot
    app.secret_key = _secret_key()
    app.config.update(SESSION_COOKIE_HTTPONLY=True, SESSION_COOKIE_SAMESITE="Lax")

    @app.route("/")
    def home():
        """The public landing page. Shows only what the channel already shows."""
        return render_template("public.html")

    @app.route("/dashboard")
    @app.route("/dashboard/")
    def console():
        """The control centre. The page is served to anyone; everything it then
        calls is behind require_auth, and it shows a login card until one of
        those calls succeeds."""
        return render_template("index.html")

    @app.route("/health")
    def health():
        return "OK", 200

    app.register_blueprint(public_routes.bp)
    app.register_blueprint(auth_routes.bp)
    app.register_blueprint(dashboard.bp)
    app.register_blueprint(broadcast.bp)
    app.register_blueprint(youtube_routes.bp)
    app.register_blueprint(config_routes.bp)
    app.register_blueprint(presence_routes.bp)
    return app


def keep_alive(bot: discord.Client):
    app = create_app(bot)

    def run():
        app.run(host="0.0.0.0", port=Config.PORT, use_reloader=False)

    threading.Thread(target=run, daemon=True).start()
