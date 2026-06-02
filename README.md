# Discord YouTube Tracker Bot 📺

A Discord bot that tracks YouTube channels and posts new uploads to your server, controllable from a modern web dashboard.

![Python](https://img.shields.io/badge/Python-3.10+-3776AB?logo=python&logoColor=white)
![discord.py](https://img.shields.io/badge/discord.py-2.4+-5865F2?logo=discord&logoColor=white)
![YouTube](https://img.shields.io/badge/YouTube_Data_API-v3-FF0000?logo=youtube&logoColor=white)

---

## ✨ Features

### 📺 YouTube tracking
- `/yt subscribe <channel> [post_to]` — subscribe a Discord channel to a YouTube channel; the bot polls every 5 min and posts a rich embed whenever there's a new upload.
- `/yt unsubscribe <channel>` — remove a subscription.
- `/yt list` — show every tracked YouTube channel for the current server.
- `/yt stats <channel>` — show subscriber count, total views, video count, latest upload.
- Channel input accepts URL (`youtube.com/@MrBeast`), handle (`@MrBeast`), or channel ID (`UC...`).
- Tracked-channel count is shown in the bot's rotating presence: `📺 5 YT channels`.

### 📊 Info & fun
- `/stats` `/userinfo` `/avatar` `/servericon` `/ping` `/uptime` `/help`
- `/roll` `/flip` `/8ball` `/rps` `/poll`

### 🤝 Quality of life
- Friendly GG reactions

### 🖥️ Web dashboard
- Live stats (servers, members, uptime, latency, YouTube subs, recent uploads)
- **YouTube panel**: subscribe / unsubscribe channels, view tracked list, see recent uploads posted
- Broadcast: send plain or embed messages to any channel
- Presence: customize bot status with dynamic variables
- Configuration: edit prefix, YouTube API key, admin password
- Live logs

---

## 🏗️ Architecture

```
bot.py                    # entry point
config.py                 # env + runtime config
core/
  state.py                # log + YT-event buffers
  storage.py              # youtube_subs.json
youtube/
  api.py                  # async YouTube Data API v3 client
  poller.py               # background upload-check loop
discord_bot/
  client.py               # bot factory + slash sync
  events.py               # GG response
  presence.py             # rotating status
  cogs/                   # info, fun, youtube_cog
web/
  app.py                  # Flask factory + keep_alive thread
  auth.py                 # bearer-token decorator
  routes/                 # dashboard, broadcast, youtube_routes, config_routes
templates/index.html      # SPA dashboard
data/                     # auto-created; holds youtube_subs.json
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
YOUTUBE_POLL_INTERVAL=300
PORT=8080
```

| Variable | Required | Notes |
|---|---|---|
| `DISCORD_TOKEN` | ✅ | From the [Discord Developer Portal](https://discord.com/developers/applications) |
| `ADMIN_PASSWORD` | ✅ | Dashboard password (default `admin123` — change it) |
| `YOUTUBE_API_KEY` | ✅ | Required for `/yt` and the upload poller. Get one from [Google Cloud Console](https://console.cloud.google.com/) → enable **YouTube Data API v3** → create an API key |
| `PREFIX` | ❌ | Editable from dashboard. Default `$` (legacy commands only — primary interface is slash) |
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

When inviting the bot, include the `applications.commands` scope so slash commands register.

---

## 💾 Data persistence

`data/youtube_subs.json` — tracked YouTube channels per server, with last-seen video IDs.

We map a local directory `./data` to `/app/data` inside the Docker container to ensure data is preserved across container updates and system restarts.

---

## ☁️ Deploy to AWS EC2 (Docker Compose & GitHub Actions)

This repository is configured to deploy to an AWS EC2 instance running Docker and Docker Compose.

### 1. Initial Host Setup
Connect to your EC2 instance via SSH:
```bash
ssh -i /path/to/bot-key.pem ubuntu@13.212.35.227
```

In the user's home directory, clone this repository:
```bash
git clone https://github.com/MacroMaster101/discord-youtube-status-bot.git
cd discord-youtube-status-bot
```

Create a local `.env` file containing your configurations:
```env
DISCORD_TOKEN=your_token_here
ADMIN_PASSWORD=your_admin_password_here
YOUTUBE_API_KEY=your_youtube_api_key_here
PORT=8080
```

Start the container manually for the first time:
```bash
docker compose up -d --build
```

The web dashboard will be accessible externally on port **8081** (mapped to the internal container port **8080**). Ensure that you open port **8081** in your AWS Security Group.

### 2. Automated CI/CD Setup with GitHub Actions
Pushing to the `main` branch triggers an automated deployment via GitHub Actions.

Configure the following **GitHub Secrets** under your repository's **Settings -> Secrets and variables -> Actions**:
- `EC2_HOST`: `13.212.35.227`
- `EC2_USERNAME`: `ubuntu`
- `EC2_SSH_KEY`: The complete contents of your `bot-key.pem` SSH key file.

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
