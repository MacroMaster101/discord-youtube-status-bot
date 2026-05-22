"""Broadcast message + restart endpoints."""
import asyncio
import datetime
import os
import time
import threading
import discord
from flask import Blueprint, request, jsonify, current_app
from core import state
from web.auth import require_auth

bp = Blueprint("broadcast", __name__, url_prefix="/api")


def _bot() -> discord.Client:
    return current_app.config["BOT"]


@bp.route("/send-message", methods=["POST"])
@require_auth
def send_message():
    bot = _bot()
    data = request.get_json() or {}
    channel_id = data.get("channel_id")
    content = data.get("content")
    use_embed = data.get("embed", False)
    if not (channel_id and content):
        return jsonify({"message": "Missing channel ID or content"}), 400
    channel = bot.get_channel(int(channel_id))
    if not channel:
        return jsonify({"message": "Channel not found"}), 404
    try:
        if use_embed:
            embed = discord.Embed(
                title="📢 Broadcast Announcement", description=content,
                color=0x5865F2, timestamp=datetime.datetime.utcnow(),
            )
            embed.set_footer(text="Sent via Bot Dashboard",
                             icon_url=bot.user.display_avatar.url if bot.user.avatar else None)
            fut = asyncio.run_coroutine_threadsafe(channel.send(embed=embed), bot.loop)
        else:
            fut = asyncio.run_coroutine_threadsafe(channel.send(content), bot.loop)
        fut.result()
        state.add_log(f"Broadcast sent to #{channel.name} in {channel.guild.name}", "success")
        return jsonify({"status": "success"})
    except Exception as e:
        state.add_log(f"Broadcast failed: {e}", "error")
        return jsonify({"message": str(e)}), 500


@bp.route("/restart", methods=["POST"])
@require_auth
def restart():
    state.add_log("Service reboot requested. Exiting...", "warning")

    def schedule_exit():
        time.sleep(1)
        os._exit(0)
    threading.Thread(target=schedule_exit, daemon=True).start()
    return jsonify({"status": "success"})
