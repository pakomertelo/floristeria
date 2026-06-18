from __future__ import annotations
import base64, hashlib, hmac, os, secrets, time
from http.cookies import SimpleCookie
from . import config

COOKIE_NAME = "mlj_session"

def hash_password(password: str, salt: bytes | None = None) -> str:
    salt = salt or os.urandom(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, 180_000)
    return "pbkdf2_sha256$180000$%s$%s" % (base64.b64encode(salt).decode(), base64.b64encode(digest).decode())

def verify_password(password: str, encoded: str) -> bool:
    try:
        algo, iterations, salt_b64, digest_b64 = encoded.split("$", 3)
        if algo != "pbkdf2_sha256": return False
        salt = base64.b64decode(salt_b64)
        expected = base64.b64decode(digest_b64)
        actual = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, int(iterations))
        return hmac.compare_digest(actual, expected)
    except Exception:
        return False

def sign(value: str) -> str:
    sig = hmac.new(config.SESSION_SECRET.encode(), value.encode(), hashlib.sha256).hexdigest()
    return f"{value}.{sig}"

def unsign(signed: str) -> str | None:
    if not signed or "." not in signed: return None
    value, sig = signed.rsplit(".", 1)
    expected = hmac.new(config.SESSION_SECRET.encode(), value.encode(), hashlib.sha256).hexdigest()
    return value if hmac.compare_digest(sig, expected) else None

def make_session(user_id: int) -> str:
    payload = f"{user_id}:{int(time.time())}:{secrets.token_urlsafe(16)}"
    return sign(base64.urlsafe_b64encode(payload.encode()).decode())

def read_session(cookie_header: str | None) -> int | None:
    if not cookie_header: return None
    cookie = SimpleCookie(cookie_header)
    morsel = cookie.get(COOKIE_NAME)
    if not morsel: return None
    raw = unsign(morsel.value)
    if not raw: return None
    try:
        payload = base64.urlsafe_b64decode(raw.encode()).decode()
        return int(payload.split(":", 1)[0])
    except Exception:
        return None

def csrf_token() -> str:
    return secrets.token_urlsafe(32)

def constant_time_equal(a: str, b: str) -> bool:
    return hmac.compare_digest(a or "", b or "")
