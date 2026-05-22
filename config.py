"""Central configuration. All env vars loaded here, all mutable runtime config exposed via Config."""
import os
from dotenv import load_dotenv

load_dotenv()


class Config:
    DISCORD_TOKEN = os.getenv("DISCORD_TOKEN", "")
    PREFIX = os.getenv("PREFIX", "$")
    WELCOME_CHANNEL_ID = os.getenv("WELCOME_CHANNEL_ID", "")
    ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "admin123")
    YOUTUBE_API_KEY = os.getenv("YOUTUBE_API_KEY", "")
    YOUTUBE_CHANNEL_ID = os.getenv("YOUTUBE_CHANNEL_ID", "")
    YOUTUBE_POLL_INTERVAL = int(os.getenv("YOUTUBE_POLL_INTERVAL", "300"))
    PORT = int(os.getenv("PORT", "8080"))

    DATA_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "data"))
    YOUTUBE_SUBS_FILE = os.path.join(DATA_DIR, "youtube_subs.json")
    CUSTOM_PRESENCE_FILE = os.path.join(DATA_DIR, "custom_presence.json")

    @classmethod
    def update_env(cls, key: str, value: str):
        env_path = ".env"
        lines = []
        if os.path.exists(env_path):
            with open(env_path, "r", encoding="utf-8") as f:
                lines = f.readlines()
        new_line = f"{key}={value}\n"
        for i, line in enumerate(lines):
            if line.strip().startswith(f"{key}="):
                lines[i] = new_line
                break
        else:
            lines.append(new_line)
        with open(env_path, "w", encoding="utf-8") as f:
            f.writelines(lines)
        setattr(cls, key, value)


os.makedirs(Config.DATA_DIR, exist_ok=True)
