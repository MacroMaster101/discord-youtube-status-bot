# Contributing

Thanks for helping out! Bug reports, ideas and pull requests are all welcome.

## Branches

```
feature/*  →  dev  →  main
```

- **`main`** is what runs in production. Every merge into it deploys automatically. It only accepts pull requests from `dev`.
- **`dev`** is where work comes together. Open your pull request against `dev`.
- **`feature/<short-name>`**: create one from `dev` for each change.

## Local setup

```bash
git clone https://github.com/MacroMaster101/discord-youtube-status-bot.git
cd discord-youtube-status-bot
python -m venv .venv
pip install -r requirements.txt -r requirements-dev.txt
cp .env.example .env   # then fill in your own values
python bot.py
```

The dashboard runs at http://localhost:8080.

## Before opening a pull request

Run the same checks CI runs:

```bash
ruff check .
pytest
```

- Keep pull requests focused on one change.
- Describe what changed and how you tested it.
- Never include tokens, API keys, passwords or files from `data/`.

## Reporting bugs

Open an issue with the **Bug report** template. For security problems, follow [SECURITY.md](SECURITY.md) instead of opening a public issue.
