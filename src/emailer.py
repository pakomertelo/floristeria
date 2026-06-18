from __future__ import annotations
import datetime, smtplib
from email.message import EmailMessage
from . import config

class EmailError(Exception): pass

def send_contact_email(data: dict) -> None:
    sent_at = datetime.datetime.now(datetime.UTC).replace(microsecond=0).isoformat()
    body = f"""Nuevo mensaje desde la web de Floristería Mi Lindo Jardín

Nombre: {data['name']}
Email: {data['email']}
Teléfono: {data.get('phone') or 'No indicado'}
Asunto: {data['subject']}
Fecha: {sent_at}

Mensaje:
{data['message']}
"""
    if not config.MAIL_HOST:
        outbox = config.BASE_DIR / "data" / "mail_outbox.log"
        outbox.parent.mkdir(parents=True, exist_ok=True)
        with outbox.open("a", encoding="utf-8") as fh:
            fh.write("\n--- EMAIL DE DESARROLLO ---\n" + body)
        return
    msg = EmailMessage()
    msg["Subject"] = f"Contacto web: {data['subject']}"
    msg["From"] = config.MAIL_FROM
    msg["To"] = config.CONTACT_TO_EMAIL
    msg["Reply-To"] = data["email"]
    msg.set_content(body)
    try:
        if config.MAIL_SECURE:
            server = smtplib.SMTP_SSL(config.MAIL_HOST, config.MAIL_PORT, timeout=15)
        else:
            server = smtplib.SMTP(config.MAIL_HOST, config.MAIL_PORT, timeout=15)
            server.starttls()
        with server:
            if config.MAIL_USER:
                server.login(config.MAIL_USER, config.MAIL_PASS)
            server.send_message(msg)
    except Exception as exc:
        raise EmailError("No se pudo enviar el email") from exc
