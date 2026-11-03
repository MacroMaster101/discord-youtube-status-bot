<p align="center">
  <img src="assets/logo.png" alt="Discord YouTube Status Bot logo" width="160">
</p>

<h1 align="center">Discord YouTube Status Bot</h1>

<p align="center">
  A Discord bot that follows a YouTube channel: it posts new uploads and live streams to your server,<br>
  shows the channel's live stats in the bot's status, and comes with a web dashboard to control everything.
</p>

<p align="center">
  <a href="https://github.com/MacroMaster101/discord-youtube-status-bot/actions/workflows/ci.yml"><img src="https://github.com/MacroMaster101/discord-youtube-status-bot/actions/workflows/ci.yml/badge.svg?branch=dev" alt="CI"></a>
  <a href="https://github.com/MacroMaster101/discord-youtube-status-bot/actions/workflows/deploy.yml"><img src="https://github.com/MacroMaster101/discord-youtube-status-bot/actions/workflows/deploy.yml/badge.svg?branch=main" alt="Deploy"></a>
  <img src="https://img.shields.io/badge/Python-3.14-3776AB?logo=python&logoColor=white" alt="Python 3.14">
  <img src="https://img.shields.io/badge/discord.py-2.7+-5865F2?logo=discord&logoColor=white" alt="discord.py 2.7+">
  <img src="https://img.shields.io/badge/YouTube_Data_API-v3-FF0000?logo=youtube&logoColor=white" alt="YouTube Data API v3">
  <img src="https://img.shields.io/badge/Docker-2496ED?logo=docker&logoColor=white" alt="Docker">
  <a href="LICENSE"><img src="https://img.shields.io/badge/License-MIT-green.svg" alt="License: MIT"></a>
</p>

<p align="center">
  <a href="#-features">Features</a> ·
  <a href="#-quick-start-local">Quick start</a> ·
  <a href="#-docker">Docker</a> ·
  <a href="#-deploying-to-a-server-ubuntu--docker">Deploy</a> ·
  <a href="#-signing-in">Signing in</a> ·
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

### 🌐 Public page
`/` is a public landing page: channel avatar, subscriber, view and video counts, a live badge while the channel is streaming, and links to the current stream, the next scheduled one and the newest upload. It takes no sign-in and shows nothing that is not already on the channel itself — a hidden subscriber count stays hidden. It reads the poller's cache, so it never spends YouTube API quota no matter how much traffic it gets. `robots.txt` keeps crawlers off everything else.

### 🖥️ Web dashboard
At `/dashboard`. Sign in with a password, Discord or Cloudflare Access (see [Signing in](#-signing-in)):
- Bot stats: servers, members, latency
- Live log viewer
- YouTube hub: channel stats, live status and recent alerts
- Broadcast a message or embed to any channel
- Presence controller: status, rotation entries and a live preview
- Settings: API key (with a test button), channel, alert channel, prefix, password, restart

---

## 🚀 Quick start (local)

**You need:** Python 3.12+, a [Discord bot token](https://discord.com/developers/applications) with the **Message Content**, **Server Members** and **Presence** intents enabled, and a [YouTube Data API v3 key](https://console.cloud.google.com/apis/library/youtube.googleapis.com).

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
| `ADMIN_PASSWORD` | ✅ | Dashboard password, 8+ characters. Optional once Discord or Cloudflare sign-in works, but keep it: it is the only one that works over the SSH tunnel. Login stays disabled while it's empty or a default like `admin123`. |
| `YOUTUBE_API_KEY` | ✅ | YouTube Data API v3 key |
| `YOUTUBE_CHANNEL_ID` | ✅ | `@handle`, channel URL or `UC…` ID |
| `YOUTUBE_NOTIFY_CHANNEL_ID` | | Discord channel ID for alerts (can be set in the dashboard) |
| `YOUTUBE_POLL_INTERVAL` | | Seconds between checks (default `300`) |
| `PREFIX` | | Command prefix (default `$`) |
| `PORT` | | Dashboard port (default `8080`) |
| `YOUTUBE_LAST_VIDEO_ID` | | Written by the bot; carry it over when moving host or the newest video is re-announced |
| `DASHBOARD_BIND_ADDRESS` | | Docker only: host address the dashboard is published on (default `127.0.0.1`, which keeps it off the public internet). Set `0.0.0.0` only to expose it deliberately |
| `COMPOSE_PROFILES` / `TUNNEL_TOKEN` | | Docker only: set `COMPOSE_PROFILES=tunnel` and a Cloudflare Tunnel token for HTTPS access |
| `APP_UID` / `APP_GID` | | Docker only: uid/gid the container runs as; must own `.env` and `data/` (default `1001`) |
| `DASHBOARD_ALLOWED_USERS` | | Discord user ids allowed to sign in. Unset means any admin of a server the bot is in |
| `DISCORD_CLIENT_ID` / `DISCORD_CLIENT_SECRET` | | Discord OAuth sign-in; see [Signing in](#-signing-in) |
| `OAUTH_REDIRECT_URI` | | Must match the redirect set on the Discord application exactly |
| `FLASK_SECRET_KEY` | | Signs the short-lived OAuth state cookie; generated per start if unset |
| `CF_ACCESS_TEAM_DOMAIN` / `CF_ACCESS_AUD` | | Cloudflare Access sign-in; both are needed or it stays off |

Run it:

```bash
python bot.py
```

The public page is at http://localhost:8080 and the dashboard at http://localhost:8080/dashboard. If the Discord token is missing or wrong, the dashboard still starts so you can read the logs.

---

## 🐳 Docker

```bash
mkdir -p data
docker compose up -d --build
```

- The dashboard is published on host port **8081**.
- `./data` is mounted into the container, so dashboard settings, custom presence entries and the last-posted video survive rebuilds.

---

## ☁️ Deploying to a server (Ubuntu + Docker)

1. On an Ubuntu server with Docker installed:
   ```bash
   git clone https://github.com/MacroMaster101/discord-youtube-status-bot.git
   cd discord-youtube-status-bot
   nano .env          # same variables as above
   mkdir -p data
   docker compose up -d --build
   ```
2. Choose how to reach the dashboard. It serves plain HTTP, so don't leave it open to everyone:
   - **HTTPS with Cloudflare Tunnel (recommended):** create a tunnel in Cloudflare Zero Trust → Networks → Tunnels and point its public hostname at `http://bot:8080`. Then add to `.env`:
     ```env
     COMPOSE_PROFILES=tunnel
     TUNNEL_TOKEN=<your tunnel token>
     ```
     Run `docker compose up -d` and open your tunnel's `https://` address for the public page, or `/dashboard` for the console. Port 8081 can stay closed.
   - **SSH tunnel (no ports opened):** run `docker compose up -d` -- the dashboard is on loopback by default -- then from your own machine:
     ```bash
     ssh -i /path/to/key -L 8081:127.0.0.1:8081 user@your-server
     ```
     Leave it running and open `http://localhost:8081/dashboard`. Only port 22 needs to be reachable.
   - **Direct:** add `DASHBOARD_BIND_ADDRESS=0.0.0.0` to `.env`, then open port **8081** in your cloud security group **to your own IP only** and visit `http://<your-server-ip>:8081/dashboard`. A `ufw` rule will not restrict it -- Docker's iptables chain is evaluated first, so the security group is what actually limits access.

Dashboard sessions are random tokens that expire after 12 hours. Logging out, restarting the bot or changing the password ends them. A password changed from the dashboard is stored only as a hash and overrides the one in `.env` (see [SECURITY.md](SECURITY.md) to reset it).

### Automatic deploys

[`.github/workflows/deploy.yml`](.github/workflows/deploy.yml) deploys on every push to `main`: it SSHes into the server, runs `git pull origin main`, then `docker compose up -d --build`. A run takes roughly 25 seconds, nearly all of it the container restart. The **Deploy** badge at the top of this page shows the result of the most recent run.

Add these repository secrets under **Settings → Secrets and variables → Actions**:

| Secret | Value |
|---|---|
| `EC2_HOST` | The server's public IP or hostname |
| `EC2_USERNAME` | The SSH user, e.g. `ubuntu` |
| `EC2_SSH_KEY` | Contents of the private SSH key for that user |

> The `EC2_*` names are historical, from the original AWS deployment. They are only secret names: the workflow deploys to any server reachable over SSH.

#### How a change reaches the server

[`branch-flow.yml`](.github/workflows/branch-flow.yml) enforces `feature/* -> dev -> main`, so deploying is the last step of that flow:

1. Branch off `dev` as `feature/<name>` and open a PR into `dev`. CI runs lint, tests, a Docker build and CodeQL.
2. Merge into `dev`. Nothing deploys — `dev` is the staging branch.
3. Open a PR from `dev` into `main`. Only `dev` may merge into `main`.
4. Merge it. That push to `main` is what triggers the deploy.

Dependabot branches may merge straight into `dev`.

#### Watching and verifying a deploy

From the **Actions** tab, or on the command line:

```bash
gh run watch "$(gh run list --workflow=deploy.yml --limit 1 --json databaseId --jq '.[0].databaseId')" --exit-status
```

A green run means the commands exited 0, not that the bot came back up. Confirm that separately:

```bash
ssh -i /path/to/key user@your-server \
  'cd ~/discord-youtube-status-bot && git log --oneline -1 && docker compose ps && docker compose logs --since 2m bot | tail -5'
```

The bot logs `Logged in as ...` once it reaches Discord.

#### First deploy on a new server

The workflow pulls into an existing checkout, so create one before the first automated deploy:

```bash
git clone https://github.com/MacroMaster101/discord-youtube-status-bot.git ~/discord-youtube-status-bot
cd ~/discord-youtube-status-bot
nano .env && chmod 600 .env    # variables as in the table above
docker compose up -d --build
```

If the workflow was disabled, re-enable it with `gh workflow enable deploy.yml`.

---

## 🔐 Signing in

The dashboard has three doors. Any one of them is enough, and they can be used together.

| Door | Set up with | Good for |
|---|---|---|
| Admin password | `ADMIN_PASSWORD` | Local access over the SSH tunnel; the fallback that always works |
| Discord OAuth | `DISCORD_CLIENT_ID` / `_SECRET` / `OAUTH_REDIRECT_URI` | Signing in as yourself, no shared secret |
| Cloudflare Access | `CF_ACCESS_TEAM_DOMAIN` / `CF_ACCESS_AUD` | A public hostname where you never see a login form |

Keep `ADMIN_PASSWORD` set even after adding the other two. If Cloudflare is down or the OAuth app is misconfigured, it is the only way back in — and over the SSH tunnel there is no Access header and no public redirect URI, so it is the *only* door that works there.

### Discord OAuth

Anyone who holds **Manage Server** or **Administrator** on a server this bot is in may sign in. Both halves are checked: administering some unrelated server is not enough, and being an ordinary member of this one is not either.

That is broader than it first sounds. The dashboard can broadcast as the bot, rewrite its tokens and restart it, so anyone you grant Manage Server to in Discord — a common thing to give a moderator — gets all of that too. To restrict it to named accounts, set `DASHBOARD_ALLOWED_USERS` to a comma-separated list of Discord user ids (enable Developer Mode in Discord, then right-click a user → Copy User ID). Both checks then apply, so a listed account that is later demoted still loses access.

1. Open the [Discord Developer Portal](https://discord.com/developers/applications) and pick the application this bot already uses.
2. Under **OAuth2**, copy the **Client ID** and **Client Secret**.
3. Add a redirect: `https://<your-hostname>/auth/discord/callback`. It must match `OAUTH_REDIRECT_URI` exactly, including the scheme and any trailing path.
4. Put all three in `.env`, plus a `FLASK_SECRET_KEY` (any long random string — `openssl rand -base64 32`). Without it the key is regenerated on every restart, which interrupts sign-ins that are mid-flight.

### Cloudflare Tunnel

The tunnel gives the dashboard an HTTPS hostname without opening a single inbound port — the connection is made outward from the server.

1. In **Cloudflare Zero Trust → Networks → Tunnels**, create a tunnel and choose **Docker** as the connector. Copy the token out of the command it shows you (the long string after `--token`).
2. Add a **public hostname** to the tunnel: pick the hostname you want, and point its service at `http://bot:8080`. That is the bot's address *on the compose network*, which is why no host port has to be published.
3. In `.env`:
   ```env
   COMPOSE_PROFILES=tunnel
   TUNNEL_TOKEN=<the token from step 1>
   ```
4. `docker compose up -d`. The `cloudflared` container only starts when `COMPOSE_PROFILES=tunnel` is set, so until then nothing changes.

Port 8081 can stay bound to loopback throughout: the tunnel does not use it.

### Cloudflare Access

Access puts Cloudflare's own sign-in in front of the hostname, so unauthenticated requests never reach the bot.

1. In **Zero Trust → Access → Applications**, add a **Self-hosted** application for the hostname from the previous step.
2. Add a policy — for a personal dashboard, *Allow* with an **Emails** rule listing your own address.
3. Open the application's **Overview** and copy the **Application Audience (AUD) Tag**.
4. In `.env`:
   ```env
   CF_ACCESS_TEAM_DOMAIN=yourteam.cloudflareaccess.com
   CF_ACCESS_AUD=<the AUD tag>
   ```
5. Restart the bot.

Every request then has to carry a `Cf-Access-Jwt-Assertion` that verifies against your team's public keys. The `Cf-Access-Authenticated-User-Email` header is deliberately ignored: any client can send it, and it is only meaningful on requests that actually came through Access. If either variable is missing, Access sign-in stays off rather than half-trusting that header.

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
  auth.py               Who is signed in: password, Discord or Cloudflare Access
  oauth.py              Discord OAuth2 sign-in (urllib only, no event loop)
  access.py             Cloudflare Access JWT verification
  routes/               Dashboard API endpoints, OAuth redirects and the public stats
templates/
  public.html           Public landing page: channel stats, no sign-in
  index.html            Single-page dashboard
tests/                  pytest suite
```

---

## 🤝 Contributing

Work flows `feature/*` → `dev` → `main`, and every merge into `main` deploys. See [CONTRIBUTING.md](CONTRIBUTING.md). CI runs lint (`ruff`), tests (`pytest`) and a Docker build on every push to `dev` and every pull request.

Found a security issue? Please report it privately; see [SECURITY.md](SECURITY.md).

## 📄 License

[MIT](LICENSE)
