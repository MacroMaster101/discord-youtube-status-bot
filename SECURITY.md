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

- Set a strong `ADMIN_PASSWORD` (8+ characters) in `.env`. The dashboard has full control of the bot, and it refuses logins while the password is empty or a known default.
- Never commit `.env` or anything in `data/`. Both are already in `.gitignore`.
- The dashboard serves plain HTTP. Use the built-in Cloudflare Tunnel option (`COMPOSE_PROFILES=tunnel`, see the README) with `DASHBOARD_BIND_ADDRESS=127.0.0.1`, or limit port 8081 to your own IP in your firewall or cloud security group.
- Logging in returns a random session token (valid for 12 hours). The password itself is never stored in the browser.
- If a Discord token or YouTube API key leaks, regenerate it right away in the Discord Developer Portal or Google Cloud Console.
