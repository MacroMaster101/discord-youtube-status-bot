# Discord YouTube Tracker Bot 📺

A premium, modern Discord companion that keeps your community actively updated with real-time YouTube uploads and channel stats, powered by an elegant web dashboard.

![Python](https://img.shields.io/badge/Python-3.10+-3776AB?logo=python&logoColor=white)
![discord.py](https://img.shields.io/badge/discord.py-2.4+-5865F2?logo=discord&logoColor=white)
![YouTube](https://img.shields.io/badge/YouTube_Data_API-v3-FF0000?logo=youtube&logoColor=white)
![AWS](https://img.shields.io/badge/AWS-%23FF9900.svg?logo=amazon-aws&logoColor=white)
![Amazon EC2](https://img.shields.io/badge/Amazon_EC2-FF9900?logo=amazonec2&logoColor=white)
![Docker](https://img.shields.io/badge/Docker-2496ED?logo=docker&logoColor=white)
![GitHub Actions](https://img.shields.io/badge/GitHub_Actions-2088FF?logo=github-actions&logoColor=white)

---

## ✨ Features

### 📺 Smart YouTube Monitoring
- **Automatic Upload Alerts** — Subscribes any server channel to a YouTube channel; polls the API in the background and posts rich embeds for new uploads.
- **Dynamic Status Presence** — Displays live stats in the bot's status rotation (e.g. `📺 5 YT channels`).
- **Interactive Slash Commands**:
  - `/yt subscribe <channel> [channel]` — Link a Discord channel to your YouTube creator stream.
  - `/yt unsubscribe <channel>` — Remove subscription mapping.
  - `/yt list` — List all monitored YouTube channels.
  - `/yt stats <channel>` — Display real-time subscribers, view counts, and latest videos.

### 📊 Community Fun & Utilities
- **Activity & Info** — `/stats`, `/userinfo`, `/avatar`, `/servericon`, `/ping`, `/uptime`, `/help`.
- **Engagement Tools** — `/roll`, `/flip`, `/8ball`, `/rps`, `/poll`.
- **QoL Interactions** — Auto-responds with friendly GG reactions (`GG`, `GG WP`, `good game`).

### 🖥️ Web Control Panel
- **Real-Time Statistics** — Live tracking of servers, active members, connection latency, and YouTube feed statuses.
- **YouTube Hub** — Manage active tracking lists, channel subscriptions, and recent uploads feed directly from the UI.
- **Announcement Dispatcher** — Broadcast raw messages or styled embeds directly to any selected server channel.
- **Presence Controller** — Customize your bot's Discord activity status, presence color, and rotation playlist.
- **Security & Logs** — Full live operational operations logger and protected administrator dashboard credentials.

---

## 🏗️ Architecture

```
bot.py                    # Application Entry Point
config.py                 # Central configurations & dotenv parser
core/
  state.py                # Volatile logs + event state buffers
  storage.py              # Persistent subscribers manager (youtube_subs.json)
youtube/
  api.py                  # Async Google YouTube Data v3 client
  poller.py               # Background feed poller
discord_bot/
  client.py               # Gateway initialization & Slash syncing
  events.py               # Message interceptors & GG reactions
  presence.py             # Status rotator
  cogs/                   # Bot slash commands cogs
web/
  app.py                  # Flask web-server initialization
  auth.py                 # Protected decorator handlers
  routes/                 # Configuration and statistics API endpoints
templates/index.html      # Responsive Single Page dashboard
data/                     # Auto-created directory for JSON storage
```

---

## 💾 Storage & Volumes

All persistent databases (subscriptions, logs, custom presences) are written to the `./data` folder. Under our Docker architecture, this folder is mounted as a volume `./data:/app/data`, securing your data across rebuilds and server reboots.

---

## ☁️ Production Deployment (AWS EC2)

This repository is optimized for deployment to an AWS EC2 instance running Ubuntu Server and Docker.

### 1. Security Group Setup
Before deploying, log into your AWS Management Console and add an **Inbound Rule** to your security group (e.g. `launch-wizard-1`):
- **Type**: `Custom TCP`
- **Port Range**: `8081`
- **Source**: `Anywhere-IPv4` (`0.0.0.0/0`) or `My IP` for security.

### 2. Manual Host Initialization
SSH into your Singapore AWS EC2 instance from the directory containing your key:
```bash
ssh -i "bot-key.pem" ubuntu@13.212.35.227
```

In your home directory, clone this repository:
```bash
git clone https://github.com/MacroMaster101/discord-youtube-status-bot.git
cd discord-youtube-status-bot
```

Create your production environment file:
```bash
nano .env
```
Paste and fill in the following configurations:
```env
DISCORD_TOKEN=your_token_here
ADMIN_PASSWORD=your_dashboard_password_here
YOUTUBE_API_KEY=your_youtube_api_key_here
PREFIX=$
YOUTUBE_POLL_INTERVAL=300
PORT=8080
```
*(Press `Ctrl+O` -> `Enter` to save, and `Ctrl+X` to exit nano)*

Create the persistence folder:
```bash
mkdir -p data
```

Start the bot container:
```bash
docker compose up -d --build
```

Your premium dashboard is now accessible at: `http://13.212.35.227:8081`

### 3. Automated Git Deployments (CI/CD)
The project includes a pre-configured GitHub Actions workflow at `.github/workflows/deploy.yml` that automatically pulls new changes and rebuilds the container on pushes to `main`.

To enable this, add the following **GitHub Secrets** under **Settings -> Secrets and variables -> Actions**:
- `EC2_HOST`: `13.212.35.227`
- `EC2_USERNAME`: `ubuntu`
- `EC2_SSH_KEY`: (Contents of your `bot-key.pem` SSH key file)

---

## 🚀 Local Development

For quick testing or local configuration:

1. Clone the repository and install requirements:
   ```bash
   pip install -r requirements.txt
   ```
2. Set up local configurations in your `.env` file.
3. Run the development daemon:
   ```bash
   python bot.py
   ```
4. Access local dashboard at: `http://localhost:8080`
