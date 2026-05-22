"""Flask app factory + keep_alive thread launcher. Routes are split into modules under web/routes/."""
import os
import threading
import discord
from flask import Flask, render_template
from config import Config
from web.routes import dashboard, broadcast, youtube_routes, config_routes


def create_app(bot: discord.Client) -> Flask:
    template_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "templates"))
    app = Flask(__name__, template_folder=template_dir)
    app.config["BOT"] = bot

    @app.route("/")
    def home():
        return render_template("index.html")

    @app.route("/health")
    def health():
        return "OK", 200

    app.register_blueprint(dashboard.bp)
    app.register_blueprint(broadcast.bp)
    app.register_blueprint(youtube_routes.bp)
    app.register_blueprint(config_routes.bp)
    return app


def keep_alive(bot: discord.Client):
    app = create_app(bot)

    def run():
        app.run(host="0.0.0.0", port=Config.PORT, use_reloader=False)

    threading.Thread(target=run, daemon=True).start()
