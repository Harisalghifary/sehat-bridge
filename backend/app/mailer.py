"""Plain-text transactional email through the configured SMTP relay.

Local development and CI use Mailpit (`localhost:1025`). A delivery failure is
logged and swallowed: a signup or reset request must not reveal whether the
address exists or whether the mail server is down.
"""

from __future__ import annotations

import asyncio
import logging
import smtplib
from email.message import EmailMessage

from app.config import get_settings

logger = logging.getLogger(__name__)


async def send_email(*, to: str, subject: str, text: str) -> bool:
    settings = get_settings()
    message = EmailMessage()
    message["From"] = settings.smtp_from
    message["To"] = to
    message["Subject"] = subject
    message.set_content(text)

    def _send() -> None:
        with smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=3) as smtp:
            smtp.send_message(message)

    try:
        await asyncio.to_thread(_send)
        return True
    except Exception:
        logger.warning("email delivery failed", exc_info=True)
        return False


def verification_email(link: str) -> tuple[str, str]:
    return (
        "Verifikasi email Sehat Bridge",
        "Selamat datang di Sehat Bridge.\n\n"
        f"Verifikasi email Anda dengan membuka tautan berikut:\n{link}\n\n"
        "Tautan berlaku selama 24 jam. Abaikan email ini bila Anda tidak "
        "mendaftar.\n",
    )


def password_reset_email(link: str) -> tuple[str, str]:
    return (
        "Atur ulang kata sandi Sehat Bridge",
        "Kami menerima permintaan mengatur ulang kata sandi akun Anda.\n\n"
        f"Buka tautan berikut untuk membuat kata sandi baru:\n{link}\n\n"
        "Tautan berlaku selama 60 menit dan hanya dapat dipakai sekali. Bila "
        "Anda tidak meminta ini, abaikan email ini.\n",
    )
