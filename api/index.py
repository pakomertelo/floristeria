from __future__ import annotations

import io
import os
from email.message import Message
from http import HTTPStatus
from src import config
from src.db import init_db
from src.server import App

# Vercel exposes the app over HTTPS, so production cookies should be secure.
os.environ.setdefault("NODE_ENV", "production")
config.UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
init_db()

class _Body(io.BytesIO):
    def __init__(self) -> None:
        super().__init__()
        self.chunks: list[bytes] = []

    def write(self, data: bytes) -> int:  # type: ignore[override]
        self.chunks.append(data)
        return len(data)

class VercelHandler(App):
    def __init__(self, environ: dict) -> None:
        self.environ = environ
        self.command = environ.get("REQUEST_METHOD", "GET").upper()
        query = environ.get("QUERY_STRING", "")
        self.path = environ.get("PATH_INFO", "/") + (f"?{query}" if query else "")
        self.client_address = (environ.get("HTTP_X_FORWARDED_FOR", "127.0.0.1").split(",")[0].strip(), 0)
        self.headers = Message()
        for key, value in environ.items():
            if key.startswith("HTTP_"):
                name = key[5:].replace("_", "-").title()
                self.headers[name] = value
        if environ.get("CONTENT_TYPE"):
            self.headers["Content-Type"] = environ["CONTENT_TYPE"]
        if environ.get("CONTENT_LENGTH"):
            self.headers["Content-Length"] = environ["CONTENT_LENGTH"]
        self.rfile = environ.get("wsgi.input", io.BytesIO())
        self.wfile = _Body()
        self._status = "200 OK"
        self._headers: list[tuple[str, str]] = []

    def send_response(self, code, message=None):
        phrase = message or HTTPStatus(code).phrase
        self._status = f"{code} {phrase}"

    def send_header(self, keyword, value):
        self._headers.append((keyword, str(value)))

    def end_headers(self):
        return None

    def response(self):
        if self.command == "GET":
            self.do_GET()
        elif self.command == "POST":
            self.do_POST()
        else:
            self.send_error(405)
        return self._status, self._headers, b"".join(self.wfile.chunks)

def app(environ, start_response):
    handler = VercelHandler(environ)
    status, headers, body = handler.response()
    start_response(status, headers)
    return [body]
