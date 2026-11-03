# Security Policy

## Supported versions

Only the latest code on the `main` branch is supported. Fixes are not backported.

## Reporting a vulnerability

Please **do not open a public issue** for security problems.

Report it privately through GitHub instead:
**Security** tab → **Report a vulnerability**
([direct link](https://github.com/MacroMaster101/discord-youtube-status-bot/security/advisories/new)).

Include what you found, how to reproduce it, and what an attacker could do with it. You should get a reply within 7 days.

## Running your own copy safely

- `/` and `/api/public/stats` are unauthenticated by design. They publish only what the YouTube channel already shows publicly — title, avatar, counts, live status and video links — plus whether the bot is online. A hidden subscriber count is returned as null rather than the real figure. No logs, configuration, Discord server details or bot internals are exposed there, and `tests/test_public.py` asserts the response contains exactly that set of fields so the endpoint cannot quietly grow one.
- Set a strong `ADMIN_PASSWORD` (8+ characters) in `.env`. The dashboard has full control of the bot, and it refuses logins while the password is empty or a known default.
- Never commit `.env` or anything in `data/`. Both are already in `.gitignore`.
- The dashboard serves plain HTTP, so under Docker it is published on `127.0.0.1` by default and is not reachable from the network until you change that. Use the built-in Cloudflare Tunnel option (`COMPOSE_PROFILES=tunnel`, see the README) to reach it over HTTPS, or an SSH tunnel. If you set `DASHBOARD_BIND_ADDRESS=0.0.0.0`, limit port 8081 to your own IP in your cloud security group -- a `ufw` rule will not do it, because Docker's iptables chain is evaluated first.
- Logging in returns a random session token (valid for 12 hours). The password itself is never stored in the browser.
- Two other ways in can be enabled alongside the password (see the README): Discord OAuth, which admits only accounts holding Manage Server or Administrator on a server the bot is in, and Cloudflare Access, which verifies the signed `Cf-Access-Jwt-Assertion` on every request. The `Cf-Access-Authenticated-User-Email` header is never trusted on its own: any client can send it, and it only means anything on requests that actually came through Access. Keep `ADMIN_PASSWORD` set regardless -- over the SSH tunnel there is no Access header and no public redirect URI, so it is the only door that works there.
- A Discord sign-in is handed back in an HttpOnly, SameSite=Lax cookie rather than a URL fragment, so the session token does not land in browser history, the Referer header or any proxy log.
- Changing the password from the dashboard saves only a salted scrypt hash (in `data/config.json`), which then takes priority over `ADMIN_PASSWORD` in `.env`. To go back to the `.env` password, delete `ADMIN_PASSWORD_HASH` from `data/config.json` and restart.
- If a Discord token or YouTube API key leaks, regenerate it right away in the Discord Developer Portal or Google Cloud Console.
