# Discord YouTube + Moderation Bot 🛡️📺

A Discord bot that **tracks YouTube channels** (posts new uploads to your server) **and** does full server moderation, all controllable from a modern web dashboard.

![Python](https://img.shields.io/badge/Python-3.10+-3776AB?logo=python&logoColor=white)
![discord.py](https://img.shields.io/badge/discord.py-2.4+-5865F2?logo=discord&logoColor=white)
![YouTube](https://img.shields.io/badge/YouTube_Data_API-v3-FF0000?logo=youtube&logoColor=white)

---

## ✨ Features

### 📺 YouTube tracking
- `/yt subscribe <channel> [post_to]` — subscribe a Discord channel to a YouTube channel; the bot polls every 5 min and posts a rich embed whenever there's a new upload.
- `/yt unsubscribe <channel>` — remove a subscription.
- `/yt list` — show every tracked YouTube channel for the current server.
- `/yt stats <channel>` — show subscriber count, total views, video count, and latest upload.
- Channel input accepts URL (`youtube.com/@MrBeast`), handle (`@MrBeast`), or channel ID (`UC...`).
- Tracked-channel count is shown in the bot's rotating presence: `📺 5 YT channels`.

### 🛡️ Moderation (slash commands)
`/kick` · `/ban` · `/unban` · `/timeout` · `/untimeout` · `/warn` · `/warnings` · `/clearwarns` · `/purge` · `/slowmode` · `/lock` · `/unlock` · `/nick` · `/addrole` · `/removerole`

All actions are logged to the configured mod-log channel as rich embeds and to the dashboard audit feed. Warnings are persisted to disk and survive restarts.

### 🤖 Auto-moderation
- Anti-spam: 5+ messages in 6 s → 5-minute auto-timeout.
- Message-delete log forwarded to the mod-log channel.

### 📊 Info & fun
- `/stats` `/userinfo` `/avatar` `/servericon` `/ping` `/uptime` `/help`
- `/roll` `/flip` `/8ball` `/rps` `/poll`

### 🖥️ Web dashboard
- Live stats (servers, members, uptime, latency, YouTube subs, warnings)
- **YouTube panel**: subscribe / unsubscribe channels, view tracked list, see recent uploads posted
- Moderation panel: issue warn/kick/ban/timeout from the browser, view warnings per server, audit log
- Broadcast: send plain or embed messages to any channel
- Presence: customize status text/activity with dynamic variables
- Configuration: edit prefix, channel IDs, YouTube API key, admin password
- Live logs

---

## 🏗️ Architecture

```
bot.py                    # entry point
config.py                 # env + runtime config
core/
  state.py                # in-process log/audit buffers
  storage.py              # warnings.json, youtube_subs.json
youtube/
  api.py                  # async YouTube Data API client
  poller.py               # background upload-check loop
discord_bot/
  client.py               # bot factory + slash sync
  events.py               # joins/leaves/deletes/anti-spam
  presence.py             # rotating status
  cogs/                   # moderation, info, fun, youtube_cog
web/
  app.py                  # Flask factory + keep_alive thread
  auth.py                 # bearer-token decorator
  routes/                 # dashboard, mod, broadcast, youtube_routes, config_routes
templates/index.html      # SPA dashboard
data/                     # auto-created; holds warnings.json + youtube_subs.json
```

---

## 🚀 Quick start

```bash
git clone https://github.com/MacroMaster101/discord-youtube-status-bot.git
cd discord-youtube-status-bot
pip install -r requirements.txt
```

Create `.env`:

```env
DISCORD_TOKEN=your_discord_bot_token
ADMIN_PASSWORD=change_me
YOUTUBE_API_KEY=your_youtube_data_api_v3_key
PREFIX=$
WELCOME_CHANNEL_ID=
MOD_LOG_CHANNEL_ID=
MUTED_ROLE_NAME=Muted
YOUTUBE_POLL_INTERVAL=300
PORT=8080
```

| Variable | Required | Notes |
|---|---|---|
| `DISCORD_TOKEN` | ✅ | From the [Discord Developer Portal](https://discord.com/developers/applications) |
| `ADMIN_PASSWORD` | ✅ | Password for the dashboard (default `admin123` — change it) |
| `YOUTUBE_API_KEY` | ⚠️ | Required for `/yt` commands and upload polling. Get one from [Google Cloud Console](https://console.cloud.google.com/) → enable **YouTube Data API v3** → create an API key (free; ~10k quota/day is plenty) |
| `PREFIX` | ❌ | Legacy prefix; slash commands are the primary interface now |
| `WELCOME_CHANNEL_ID` | ❌ | Falls back to system channel |
| `MOD_LOG_CHANNEL_ID` | ❌ | Where mod actions get embedded |
| `MUTED_ROLE_NAME` | ❌ | Reserved for future role-based muting |
| `YOUTUBE_POLL_INTERVAL` | ❌ | Seconds between upload checks (default 300) |
| `PORT` | ❌ | Dashboard port (default 8080) |

### Discord intents
In the Developer Portal → Bot → **Privileged Gateway Intents**, enable:
- ✅ Message Content
- ✅ Server Members
- ✅ Presence

### Run

```bash
python bot.py
```

Dashboard: <http://localhost:8080> · log in with `ADMIN_PASSWORD`.

---

## 🤖 Bot invite permissions

Required: Send Messages, Embed Links, Add Reactions, Read Message History, **Kick Members**, **Ban Members**, **Moderate Members**, **Manage Messages**, **Manage Channels**, **Manage Nicknames**, **Manage Roles**.

When inviting the bot, also include the `applications.commands` scope so slash commands register.

---

## 💾 Data persistence

JSON files in `data/`:
- `warnings.json` — moderation warnings
- `youtube_subs.json` — tracked YouTube channels per server, with last-seen video IDs

On Fly.io, mount a volume at `/app/data` to persist across deploys.

---

## ☁️ Deploy to Fly.io

```bash
flyctl launch
flyctl secrets set DISCORD_TOKEN=xxx ADMIN_PASSWORD=xxx YOUTUBE_API_KEY=xxx
flyctl deploy
```

---

## 📦 Dependencies

| Package | Purpose |
|---|---|
| `discord.py` | Discord API + slash commands |
| `aiohttp` | Async YouTube Data API requests |
| `flask` | Dashboard + health checks |
| `python-dotenv` | Local `.env` loader |

---

## 📄 License

MIT.
