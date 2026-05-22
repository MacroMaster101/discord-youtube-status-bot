"""Central configuration. All env vars loaded here, all mutable runtime config exposed via Config.
Supports saving/loading configurations from a persistent config.json inside the mounted Fly volume to survive restarts.
"""
import os
import json
from dotenv import load_dotenv

load_dotenv()


class Config:
    DATA_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "data"))
    os.makedirs(DATA_DIR, exist_ok=True)
    PERSISTENT_CONFIG_FILE = os.path.join(DATA_DIR, "config.json")

    # Initial default values from environment variables
    DISCORD_TOKEN = os.getenv("DISCORD_TOKEN", "")
    PREFIX = os.getenv("PREFIX", "$")
    WELCOME_CHANNEL_ID = os.getenv("WELCOME_CHANNEL_ID", "")
    ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "admin123")
    YOUTUBE_API_KEY = os.getenv("YOUTUBE_API_KEY", "")
    YOUTUBE_CHANNEL_ID = os.getenv("YOUTUBE_CHANNEL_ID", "")
    YOUTUBE_NOTIFY_CHANNEL_ID = os.getenv("YOUTUBE_NOTIFY_CHANNEL_ID", "")
    YOUTUBE_LAST_VIDEO_ID = os.getenv("YOUTUBE_LAST_VIDEO_ID", "")
    YOUTUBE_POLL_INTERVAL = int(os.getenv("YOUTUBE_POLL_INTERVAL", "300"))
    PORT = int(os.getenv("PORT", "8080"))

    YOUTUBE_SUBS_FILE = os.path.join(DATA_DIR, "youtube_subs.json")
    CUSTOM_PRESENCE_FILE = os.path.join(DATA_DIR, "custom_presence.json")

    @classmethod
    def load_persistent(cls):
        """Load persistent configurations from config.json (persisted across Fly deploys/restarts)"""
        if os.path.exists(cls.PERSISTENT_CONFIG_FILE):
            try:
                with open(cls.PERSISTENT_CONFIG_FILE, "r", encoding="utf-8") as f:
                    data = json.load(f)
                for k, v in data.items():
                    if hasattr(cls, k):
                        current_val = getattr(cls, k)
                        # Do not overwrite a non-empty environment/dotenv value with an empty one
                        if current_val and not v:
                            continue
                        # Prioritize environment variables/secrets if they are set in the actual environment
                        if k in ("DISCORD_TOKEN", "YOUTUBE_API_KEY") and os.getenv(k):
                            continue

                        if k in ("YOUTUBE_POLL_INTERVAL", "PORT"):
                            setattr(cls, k, int(v))
                        else:
                            setattr(cls, k, str(v))
            except Exception as e:
                print(f"Failed to load persistent config: {e}")

    @classmethod
    def update_env(cls, key: str, value: str):
        """Update the configuration value in memory, persist it to config.json, and write to .env for fallback compatibility."""
        # 1. Update in memory
        setattr(cls, key, value)

        # 2. Persist to persistent config.json (mounted in Fly volume)
        persistent_data = {}
        if os.path.exists(cls.PERSISTENT_CONFIG_FILE):
            try:
                with open(cls.PERSISTENT_CONFIG_FILE, "r", encoding="utf-8") as f:
                    persistent_data = json.load(f)
            except Exception:
                pass
        persistent_data[key] = value
        try:
            with open(cls.PERSISTENT_CONFIG_FILE, "w", encoding="utf-8") as f:
                json.dump(persistent_data, f, indent=4)
        except Exception as e:
            print(f"Failed to save persistent config: {e}")

        # 3. Write to .env for local fallback
        env_path = ".env"
        lines = []
        if os.path.exists(env_path):
            try:
                with open(env_path, "r", encoding="utf-8") as f:
                    lines = f.readlines()
            except Exception:
                pass
        new_line = f"{key}={value}\n"
        for i, line in enumerate(lines):
            if line.strip().startswith(f"{key}="):
                lines[i] = new_line
                break
        else:
            lines.append(new_line)
        try:
            with open(env_path, "w", encoding="utf-8") as f:
                f.writelines(lines)
        except Exception:
            pass


# Load persistent configuration on module import
Config.load_persistent()
