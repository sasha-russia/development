"""Settings come from environment variables (see .env.example)."""

import os
from pathlib import Path
from zoneinfo import ZoneInfo


def _int(name: str, default: int) -> int:
    value = os.getenv(name, "").strip()
    return int(value) if value else default


DATA_DIR = Path(os.getenv("DATA_DIR", Path(__file__).resolve().parent.parent / "data"))
DATA_DIR.mkdir(parents=True, exist_ok=True)
DATABASE_URL = os.getenv("DATABASE_URL", f"sqlite:///{DATA_DIR / 'social.db'}")

BASE_URL = os.getenv("BASE_URL", "http://localhost:8000").rstrip("/")
SECRET_KEY = os.getenv("SECRET_KEY", "dev-secret-change-me")
ADMIN_LOGIN = os.getenv("ADMIN_LOGIN", "admin")
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "")

TZ = ZoneInfo(os.getenv("TIMEZONE", "Europe/Moscow"))
# The daily report covers the previous day from this hour to this hour.
DAY_START_HOUR = _int("DAY_START_HOUR", 8)

# Telegram: an ordinary user account (MTProto). Bots cannot read other people's channels.
TG_API_ID = _int("TG_API_ID", 0)
TG_API_HASH = os.getenv("TG_API_HASH", "")

# VK: the service key of a VK application (Settings -> Сервисный ключ доступа).
VK_TOKEN = os.getenv("VK_TOKEN", "")
VK_API_VERSION = "5.199"

# Classification. Without a key the rule-based classifier is used.
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")
CLAUDE_MODEL = os.getenv("CLAUDE_MODEL", "claude-opus-5-5")
CLASSIFY_BATCH = _int("CLASSIFY_BATCH", 25)

# MAX bot that sends reports.
MAX_BOT_TOKEN = os.getenv("MAX_BOT_TOKEN", "")
MAX_CHAT_ID = os.getenv("MAX_CHAT_ID", "")
MAX_USER_ID = os.getenv("MAX_USER_ID", "")
MAX_API = "https://platform-api2.max.ru"

# Collection.
POLL_MINUTES = _int("POLL_MINUTES", 10)
PRIORITY_POLL_MINUTES = _int("PRIORITY_POLL_MINUTES", 5)
BACKFILL_DAYS = _int("BACKFILL_DAYS", 3)
COMMENT_WINDOW_DAYS = _int("COMMENT_WINDOW_DAYS", 3)
PRIORITY_COMMENT_WINDOW_DAYS = _int("PRIORITY_COMMENT_WINDOW_DAYS", 7)
DISABLE_SCHEDULER = os.getenv("DISABLE_SCHEDULER", "") == "1"

# Geocoding (OpenStreetMap Nominatim, 1 request per second).
NOMINATIM_URL = os.getenv("NOMINATIM_URL", "https://nominatim.openstreetmap.org/search")
NOMINATIM_EMAIL = os.getenv("NOMINATIM_EMAIL", "")
# Mytishchi urban district: south, west, north, east.
AREA_BBOX = (55.86, 37.50, 56.13, 37.95)
CITY_CENTER = (55.9105, 37.7363)
