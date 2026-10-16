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

- Set a strong `ADMIN_PASSWORD` in `.env`. The dashboard has full control of the bot.
- Never commit `.env` or anything in `data/`. Both are already in `.gitignore`.
- The dashboard serves plain HTTP. Limit its port to your own IP in your firewall or cloud security group, or put it behind HTTPS (for example a Cloudflare Tunnel or a reverse proxy).
- If a Discord token or YouTube API key leaks, regenerate it right away in the Discord Developer Portal or Google Cloud Console.
