"""Async email service — stdlib smtplib wrapped in run_in_executor.

SMTP config is read via ConfigService (DB first, then env fallback).
All send errors are logged and suppressed — email is non-critical for core flows.
"""
import asyncio
import logging
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

log = logging.getLogger(__name__)


async def send_email(
    to: str,
    subject: str,
    body_html: str,
    body_text: str | None = None,
    *,
    db=None,
) -> bool:
    """Send email asynchronously. Returns True on success, False if unconfigured or failed.

    Pass `db` to enable DB-backed config (Admin UI). Without it, falls back to env vars.
    """
    smtp_cfg = await _load_smtp_config(db)
    loop = asyncio.get_event_loop()
    try:
        return await loop.run_in_executor(
            None, _send_sync, to, subject, body_html, body_text, smtp_cfg
        )
    except Exception as exc:
        log.warning("email send failed: %s", exc)
        return False


async def _load_smtp_config(db) -> dict:
    """Read SMTP settings from ConfigService (DB → env → hardcoded default)."""
    if db is not None:
        from app.services.config_service import ConfigService
        cfg = ConfigService(db)
        return {
            "host": await cfg.get("smtp_host", ""),
            "port": int(await cfg.get("smtp_port", "587") or "587"),
            "username": await cfg.get("smtp_username", ""),
            "password": await cfg.get("smtp_password", ""),
            "from_email": await cfg.get("smtp_from_email", ""),
            "use_tls": (await cfg.get("smtp_use_tls", "true") or "true").lower()
                       not in ("false", "0", "no"),
        }

    # No db available — fall through to env vars directly
    import os
    username = os.environ.get("SMTP_USERNAME", "")
    return {
        "host": os.environ.get("SMTP_HOST", ""),
        "port": int(os.environ.get("SMTP_PORT", "587")),
        "username": username,
        "password": os.environ.get("SMTP_PASSWORD", ""),
        "from_email": os.environ.get("SMTP_FROM_EMAIL", username),
        "use_tls": os.environ.get("SMTP_USE_TLS", "true").lower() not in ("false", "0", "no"),
    }


def _send_sync(
    to: str,
    subject: str,
    body_html: str,
    body_text: str | None,
    cfg: dict,
) -> bool:
    host = cfg["host"]
    if not host:
        log.debug("SMTP_HOST not configured — skipping email to %s", to)
        return False

    from_email = cfg["from_email"] or cfg["username"]
    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = from_email
    msg["To"] = to

    if body_text:
        msg.attach(MIMEText(body_text, "plain", "utf-8"))
    msg.attach(MIMEText(body_html, "html", "utf-8"))

    try:
        with smtplib.SMTP(host, cfg["port"], timeout=15) as smtp:
            if cfg["use_tls"]:
                smtp.starttls()
            if cfg["username"] and cfg["password"]:
                smtp.login(cfg["username"], cfg["password"])
            smtp.sendmail(from_email, [to], msg.as_string())
        log.info("email sent to %s: %s", to, subject)
        return True
    except Exception as exc:
        log.error("SMTP error sending to %s: %s", to, exc)
        return False
