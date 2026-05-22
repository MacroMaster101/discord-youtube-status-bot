"""Moderation endpoints: warnings list, action runner, audit feed."""
import asyncio
import datetime
import discord
from flask import Blueprint, request, jsonify, current_app
from core import state, storage
from web.auth import require_auth

bp = Blueprint("mod", __name__, url_prefix="/api/mod")


def _bot() -> discord.Client:
    return current_app.config["BOT"]


@bp.route("/actions")
@require_auth
def actions():
    return jsonify(state.get_mod_actions())


@bp.route("/warnings")
@require_auth
def warnings():
    guild_id = request.args.get("guild_id")
    if not guild_id:
        return jsonify({"message": "guild_id required"}), 400
    bot = _bot()
    if not bot.is_ready():
        return jsonify({"warnings": []})
    guild = bot.get_guild(int(guild_id))
    if guild is None:
        return jsonify({"warnings": []})
    raw = storage.all_warnings_for_guild(guild_id)
    out = []
    for uid, entries in raw.items():
        member = guild.get_member(int(uid))
        out.append({
            "user_id": uid,
            "user_name": str(member) if member else f"Unknown ({uid})",
            "avatar": member.display_avatar.url if member else None,
            "count": len(entries),
            "warnings": entries,
        })
    out.sort(key=lambda x: x["count"], reverse=True)
    return jsonify({"warnings": out})


@bp.route("/action", methods=["POST"])
@require_auth
def action():
    data = request.get_json() or {}
    act = data.get("action")
    guild_id = data.get("guild_id")
    user_id = data.get("user_id")
    reason = data.get("reason", "Issued from dashboard")
    duration = data.get("duration")
    if not (act and guild_id and user_id):
        return jsonify({"message": "action, guild_id, user_id required"}), 400

    bot = _bot()
    if not bot.is_ready():
        return jsonify({"message": "Bot not ready"}), 503
    guild = bot.get_guild(int(guild_id))
    if guild is None:
        return jsonify({"message": "Guild not found"}), 404

    async def run():
        try:
            if act == "ban":
                await guild.ban(discord.Object(id=int(user_id)),
                                reason=f"[Dashboard] {reason}", delete_message_seconds=0)
                state.add_mod_action("ban", "Dashboard", user_id, reason, guild.name)
                return True, "Banned"
            if act == "unban":
                await guild.unban(discord.Object(id=int(user_id)), reason=f"[Dashboard] {reason}")
                state.add_mod_action("unban", "Dashboard", user_id, reason, guild.name)
                return True, "Unbanned"

            member = guild.get_member(int(user_id))
            if member is None:
                return False, "Member not found"
            if act == "kick":
                await member.kick(reason=f"[Dashboard] {reason}")
                state.add_mod_action("kick", "Dashboard", member, reason, guild.name)
                return True, "Kicked"
            if act == "timeout":
                mins = int(duration) if duration else 10
                until = datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(minutes=mins)
                await member.timeout(until, reason=f"[Dashboard] {reason}")
                state.add_mod_action("timeout", "Dashboard", member, f"{reason} ({mins}m)", guild.name)
                return True, f"Timed out for {mins}m"
            if act == "untimeout":
                await member.timeout(None, reason=f"[Dashboard] {reason}")
                state.add_mod_action("untimeout", "Dashboard", member, reason, guild.name)
                return True, "Timeout removed"
            if act == "warn":
                count = storage.add_warning(guild_id, user_id, "Dashboard", reason)
                state.add_mod_action("warn", "Dashboard", member, f"{reason} (total: {count})", guild.name)
                return True, f"Warned (total: {count})"
            if act == "clear_warnings":
                count = storage.clear_warnings(guild_id, user_id)
                state.add_mod_action("clear_warnings", "Dashboard", member, f"Cleared {count}", guild.name)
                return True, f"Cleared {count} warnings"
            return False, f"Unknown action: {act}"
        except discord.Forbidden:
            return False, "Bot lacks permissions"
        except discord.HTTPException as e:
            return False, f"Discord error: {e}"
        except Exception as e:
            return False, str(e)

    fut = asyncio.run_coroutine_threadsafe(run(), bot.loop)
    try:
        ok, msg = fut.result(timeout=15)
    except Exception as e:
        return jsonify({"message": str(e)}), 500
    if not ok:
        return jsonify({"message": msg}), 400
    return jsonify({"status": "success", "message": msg})
