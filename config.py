"""Central configuration. All env vars loaded here, all mutable runtime config exposed via Config.
Settings changed from the dashboard are saved to data/config.json so they survive restarts and redeploys.
"""
import os
import json
from dotenv import load_dotenv
from core.passwords import hash_password

load_dotenv()


class Config:
    DATA_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "data"))
    os.makedirs(DATA_DIR, exist_ok=True)
    PERSISTENT_CONFIG_FILE = os.path.join(DATA_DIR, "config.json")

    # Initial default values from environment variables
    DISCORD_TOKEN = os.getenv("DISCORD_TOKEN", "")
    PREFIX = os.getenv("PREFIX", "$")
    # No default: the dashboard refuses logins until a strong password is set (see web/auth.py).
    ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "")
    # Set when the password is changed from the dashboard; it then replaces ADMIN_PASSWORD.
    # Only this salted hash is saved (in data/config.json), never the password itself.
    ADMIN_PASSWORD_HASH = ""
    YOUTUBE_API_KEY = os.getenv("YOUTUBE_API_KEY", "")
    YOUTUBE_CHANNEL_ID = os.getenv("YOUTUBE_CHANNEL_ID", "")
    YOUTUBE_NOTIFY_CHANNEL_ID = os.getenv("YOUTUBE_NOTIFY_CHANNEL_ID", "")
    YOUTUBE_LAST_VIDEO_ID = os.getenv("YOUTUBE_LAST_VIDEO_ID", "")
    YOUTUBE_POLL_INTERVAL = int(os.getenv("YOUTUBE_POLL_INTERVAL", "300"))
    PORT = int(os.getenv("PORT", "8080"))

    CUSTOM_PRESENCE_FILE = os.path.join(DATA_DIR, "custom_presence.json")

    @classmethod
    def _read_persistent(cls) -> dict:
        if not os.path.exists(cls.PERSISTENT_CONFIG_FILE):
            return {}
        try:
            with open(cls.PERSISTENT_CONFIG_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {}

    @classmethod
    def _write_persistent(cls, data: dict):
        try:
            with open(cls.PERSISTENT_CONFIG_FILE, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=4)
        except Exception as e:
            print(f"Failed to save persistent config: {e}")

    @classmethod
    def load_persistent(cls):
        """Load settings saved from the dashboard (data/config.json)."""
        data = cls._read_persistent()
        # Older versions saved the dashboard password in plain text: replace it with a hash.
        legacy = data.pop("ADMIN_PASSWORD", None)
        if legacy:
            data["ADMIN_PASSWORD_HASH"] = hash_password(str(legacy))
            cls._write_persistent(data)
        for k, v in data.items():
            if hasattr(cls, k):
                current_val = getattr(cls, k)
                # Do not overwrite a non-empty environment/dotenv value with an empty one
                if current_val and not v:
                    continue

                if k in ("YOUTUBE_POLL_INTERVAL", "PORT"):
                    setattr(cls, k, int(v))
                else:
                    setattr(cls, k, str(v))

    @classmethod
    def set_admin_password(cls, new_password: str):
        """Save only a salted hash of a dashboard-chosen password (not written to .env)."""
        cls.ADMIN_PASSWORD_HASH = hash_password(new_password)
        data = cls._read_persistent()
        data.pop("ADMIN_PASSWORD", None)
        data["ADMIN_PASSWORD_HASH"] = cls.ADMIN_PASSWORD_HASH
        cls._write_persistent(data)

    @classmethod
    def update_env(cls, key: str, value: str):
        """Update the configuration value in memory, persist it to config.json, and write to .env for fallback compatibility."""
        # 1. Update in memory
        setattr(cls, key, value)

        # 2. Persist to data/config.json (mounted as a Docker volume)
        persistent_data = cls._read_persistent()
        persistent_data[key] = value
        cls._write_persistent(persistent_data)

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
