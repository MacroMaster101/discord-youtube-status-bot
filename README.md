<p align="center">
  <img src="assets/logo.svg" alt="Discord YouTube Status Bot logo" width="140">
</p>

<h1 align="center">Discord YouTube Status Bot</h1>

<p align="center">
  A Discord bot that follows a YouTube channel: it posts new uploads and live streams to your server,<br>
  shows the channel's live stats in the bot's status, and comes with a web dashboard to control everything.
</p>

<p align="center">
  <a href="https://github.com/MacroMaster101/discord-youtube-status-bot/actions/workflows/ci.yml"><img src="https://github.com/MacroMaster101/discord-youtube-status-bot/actions/workflows/ci.yml/badge.svg?branch=dev" alt="CI"></a>
  <img src="https://img.shields.io/badge/Python-3.12-3776AB?logo=python&logoColor=white" alt="Python 3.12">
  <img src="https://img.shields.io/badge/discord.py-2.4+-5865F2?logo=discord&logoColor=white" alt="discord.py 2.4+">
  <img src="https://img.shields.io/badge/YouTube_Data_API-v3-FF0000?logo=youtube&logoColor=white" alt="YouTube Data API v3">
  <img src="https://img.shields.io/badge/Docker-2496ED?logo=docker&logoColor=white" alt="Docker">
  <a href="LICENSE"><img src="https://img.shields.io/badge/License-MIT-green.svg" alt="License: MIT"></a>
</p>

<p align="center">
  <a href="#-features">Features</a> ·
  <a href="#-quick-start-local">Quick start</a> ·
  <a href="#-docker">Docker</a> ·
  <a href="#-contributing">Contributing</a>
</p>

---

## ✨ Features

### 📺 YouTube alerts
- Posts an embed to your chosen Discord channel when the channel **uploads a video** or **goes live** ("🔴 is live now!").
- Scheduled streams aren't posted until they actually start, and a finished stream isn't posted a second time.
- Uses only cheap API calls (about 3 quota units per check), so the free 10,000-unit daily quota lasts all day even with frequent checks.

### 🟢 Live bot status
The bot's Discord status rotates every 15 seconds through the channel's subscribers, views, video count, upcoming stream and newest upload. While the channel is live, it's pinned to `🔴 LIVE: <title>` with a Streaming badge linking to the stream. You can add your own rotation entries with placeholders like `{subs}`, `{views}` and `{latest_video_title}`.

### 💬 Commands
Commands use a prefix (default `$`, changeable from the dashboard).

| Command | What it does |
|---|---|
| `$yt stats [channel]` | Subscribers, views, video count and latest video. Uses the main channel if none is given. |
| `$yt link` | Link to the main YouTube channel |
| `$stats` | Server statistics |
| `$userinfo [@user]` | Info about a member |
| `$avatar [@user]` | A member's avatar |
| `$servericon` | The server's icon |
| `$ping` / `$uptime` | Bot latency / how long it's been online |
| `$help` | Full command list |

The bot also replies to "gg", "gg wp" or "good game" with a GG and a 🏆 reaction.

### 🖥️ Web dashboard
Password-protected control panel:
- Bot stats: servers, members, latency
- Live log viewer
- YouTube hub: channel stats, live status and recent alerts
- Broadcast a message or embed to any channel
- Presence controller: status, rotation entries and a live preview
- Settings: API key (with a test button), channel, alert channel, prefix, password, restart

---

## 🚀 Quick start (local)

**You need:** Python 3.12, a [Discord bot token](https://discord.com/developers/applications) with the **Message Content**, **Server Members** and **Presence** intents enabled, and a [YouTube Data API v3 key](https://console.cloud.google.com/apis/library/youtube.googleapis.com).

```bash
git clone https://github.com/MacroMaster101/discord-youtube-status-bot.git
cd discord-youtube-status-bot
pip install -r requirements.txt
cp .env.example .env
```

Fill in `.env`:

| Variable | Required | Description |
|---|---|---|
| `DISCORD_TOKEN` | ✅ | Your bot token |
| `ADMIN_PASSWORD` | ✅ | Dashboard password. Use a strong one. |
| `YOUTUBE_API_KEY` | ✅ | YouTube Data API v3 key |
| `YOUTUBE_CHANNEL_ID` | ✅ | `@handle`, channel URL or `UC…` ID |
| `YOUTUBE_NOTIFY_CHANNEL_ID` | | Discord channel ID for alerts (can be set in the dashboard) |
| `YOUTUBE_POLL_INTERVAL` | | Seconds between checks (default `300`) |
| `PREFIX` | | Command prefix (default `$`) |
| `PORT` | | Dashboard port (default `8080`) |

Run it:

```bash
python bot.py
```

The dashboard is at http://localhost:8080. If the Discord token is missing or wrong, the dashboard still starts so you can read the logs.

---

## 🐳 Docker

```bash
mkdir -p data
docker compose up -d --build
```

- The dashboard is published on host port **8081**.
- `./data` is mounted into the container, so dashboard settings, custom presence entries and the last-posted video survive rebuilds.

---

## ☁️ Deploying to a server (e.g. AWS EC2)

1. On an Ubuntu server with Docker installed:
   ```bash
   git clone https://github.com/MacroMaster101/discord-youtube-status-bot.git
   cd discord-youtube-status-bot
   nano .env          # same variables as above
   mkdir -p data
   docker compose up -d --build
   ```
2. Open port **8081** in your firewall or security group, ideally **only to your own IP**. The dashboard uses plain HTTP.
3. Visit `http://<your-server-ip>:8081`.

### Automatic deploys
[`.github/workflows/deploy.yml`](.github/workflows/deploy.yml) SSHes into the server on every push to `main`, pulls the code and rebuilds the container. Add these repository secrets under **Settings → Secrets and variables → Actions**:

| Secret | Value |
|---|---|
| `EC2_HOST` | Your server's public IP |
| `EC2_USERNAME` | e.g. `ubuntu` |
| `EC2_SSH_KEY` | Contents of the server's private SSH key (`.pem`) |

---

## 🏗️ Project structure

```
bot.py                  Entry point: starts the dashboard and the bot
config.py               Settings from .env, plus dashboard changes saved to data/config.json
core/
  state.py              In-memory logs, alert history and presence state
  storage.py            JSON storage for custom presence entries
youtube/
  api.py                Async YouTube Data API v3 client (uploads playlist, quota-friendly)
  poller.py             Background checks: stats cache, live status, new upload/live alerts
discord_bot/
  client.py             Bot setup and startup
  events.py             GG auto-reply
  presence.py           Rotating status
  cogs/                 Commands (info, youtube)
web/
  app.py                Flask app (runs in a background thread)
  auth.py               Dashboard password check
  routes/               Dashboard API endpoints
templates/index.html    Single-page dashboard
tests/                  pytest suite
```

---

## 🤝 Contributing

Work flows `feature/*` → `dev` → `main`, and every merge into `main` deploys. See [CONTRIBUTING.md](CONTRIBUTING.md). CI runs lint (`ruff`), tests (`pytest`) and a Docker build on every push to `dev` and every pull request.

Found a security issue? Please report it privately; see [SECURITY.md](SECURITY.md).

## 📄 License

[MIT](LICENSE)
