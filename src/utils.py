from __future__ import annotations
import html, json, re, uuid
from pathlib import Path
from urllib.parse import parse_qs
from . import config

EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
ALLOWED_IMAGE_TYPES = {"image/jpeg": ".jpg", "image/png": ".png", "image/webp": ".webp", "image/gif": ".gif"}

def esc(value) -> str:
    return html.escape(str(value or ""), quote=True)

def clean(value: str, limit: int = 2000) -> str:
    value = (value or "").replace("\x00", "").strip()
    return value[:limit]

def is_email(value: str) -> bool:
    return bool(EMAIL_RE.match(value or ""))

def parse_urlencoded(body: bytes) -> dict[str, str]:
    parsed = parse_qs(body.decode("utf-8", errors="replace"), keep_blank_values=True)
    return {k: v[-1] if v else "" for k, v in parsed.items()}

def parse_multipart(body: bytes, content_type: str) -> tuple[dict[str, str], dict[str, dict]]:
    marker = "boundary="
    if marker not in content_type:
        return {}, {}
    boundary = content_type.split(marker, 1)[1].strip().strip('"')
    delimiter = ("--" + boundary).encode()
    fields: dict[str, str] = {}
    files: dict[str, dict] = {}
    for part in body.split(delimiter):
        part = part.strip(b"\r\n")
        if not part or part == b"--" or b"\r\n\r\n" not in part:
            continue
        header_blob, data = part.split(b"\r\n\r\n", 1)
        headers = header_blob.decode("utf-8", errors="replace").split("\r\n")
        disposition = next((h for h in headers if h.lower().startswith("content-disposition:")), "")
        ctype = next((h.split(":",1)[1].strip() for h in headers if h.lower().startswith("content-type:")), "application/octet-stream")
        name_match = re.search(r'name="([^"]+)"', disposition)
        if not name_match:
            continue
        name = name_match.group(1)
        filename_match = re.search(r'filename="([^"]*)"', disposition)
        data = data.rstrip(b"\r\n")
        if filename_match and filename_match.group(1):
            files[name] = {"filename": filename_match.group(1), "content_type": ctype, "data": data}
        else:
            fields[name] = data.decode("utf-8", errors="replace")
    return fields, files

def save_image(fileinfo: dict | None) -> tuple[str, str | None]:
    if not fileinfo or not fileinfo.get("data"):
        return "", None
    content_type = fileinfo.get("content_type", "")
    data = fileinfo.get("data", b"")
    if content_type not in ALLOWED_IMAGE_TYPES:
        return "", "Solo se permiten imágenes JPG, PNG, WEBP o GIF."
    if len(data) > config.MAX_IMAGE_BYTES:
        return "", "La imagen supera el tamaño máximo de 2 MB."
    config.UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    filename = f"{uuid.uuid4().hex}{ALLOWED_IMAGE_TYPES[content_type]}"
    path = config.UPLOAD_DIR / filename
    path.write_bytes(data)
    return f"/uploads/{filename}", None

def image_src(path: str, category: str = "") -> str:
    if path:
        return path
    return "/img/default"
