from __future__ import annotations
import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
IS_VERCEL = bool(os.getenv("VERCEL"))

def load_env(path: Path | None = None) -> None:
    env_path = path or BASE_DIR / ".env"
    if not env_path.exists():
        return
    for raw in env_path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))

load_env()

PORT = int(os.getenv("PORT", "3000"))
APP_URL = os.getenv("APP_URL", f"http://localhost:{PORT}")
DEFAULT_DATABASE_PATH = Path("/tmp/floristeria.sqlite") if IS_VERCEL else BASE_DIR / "data" / "floristeria.sqlite"
DEFAULT_UPLOAD_DIR = Path("/tmp/uploads") if IS_VERCEL else BASE_DIR / "public" / "uploads"
DATABASE_PATH = Path(os.getenv("DATABASE_PATH", str(DEFAULT_DATABASE_PATH)))
SESSION_SECRET = os.getenv("SESSION_SECRET", "dev-secret-change-me")
ADMIN_EMAIL = os.getenv("ADMIN_EMAIL", "admin@milindojardin.local")
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "Admin123!")
CONTACT_TO_EMAIL = os.getenv("CONTACT_TO_EMAIL", "dueno@milindojardin.local")
MAIL_HOST = os.getenv("MAIL_HOST", "")
MAIL_PORT = int(os.getenv("MAIL_PORT", "587"))
MAIL_SECURE = os.getenv("MAIL_SECURE", "false").lower() in {"1", "true", "yes"}
MAIL_USER = os.getenv("MAIL_USER", "")
MAIL_PASS = os.getenv("MAIL_PASS", "")
MAIL_FROM = os.getenv("MAIL_FROM", "Floristería Mi Lindo Jardín <no-reply@milindojardin.local>")
MAX_IMAGE_BYTES = 2 * 1024 * 1024
UPLOAD_DIR = Path(os.getenv("UPLOAD_DIR", str(DEFAULT_UPLOAD_DIR)))
PUBLIC_DIR = BASE_DIR / "public"
