"""SMTP email helper used by password-reset and notification flows."""
from __future__ import annotations

import smtplib
import ssl
from email.message import EmailMessage
from typing import Mapping

import streamlit as st


class EmailNotConfiguredError(RuntimeError):
    """Raised when SMTP settings are missing."""


def _smtp_settings() -> Mapping[str, str | int | bool]:
    smtp = st.secrets.get("smtp", {}) if hasattr(st, "secrets") else {}
    host = smtp.get("host")
    username = smtp.get("username")
    password = smtp.get("password")
    sender = smtp.get("sender", username)
    if not host or not username or not password or not sender:
        raise EmailNotConfiguredError("SMTP ayarları tanımlı değil.")
    return {
        "host": host,
        "port": int(smtp.get("port", 587)),
        "username": username,
        "password": password,
        "sender": sender,
        "use_tls": bool(smtp.get("use_tls", True)),
    }


def send_email(to_email: str, subject: str, body: str) -> None:
    """Send a plain-text email through configured SMTP settings."""
    settings = _smtp_settings()
    msg = EmailMessage()
    msg["From"] = str(settings["sender"])
    msg["To"] = to_email
    msg["Subject"] = subject
    msg.set_content(body)

    if settings["use_tls"]:
        context = ssl.create_default_context()
        with smtplib.SMTP(str(settings["host"]), int(settings["port"]), timeout=15) as server:
            server.starttls(context=context)
            server.login(str(settings["username"]), str(settings["password"]))
            server.send_message(msg)
    else:
        with smtplib.SMTP_SSL(str(settings["host"]), int(settings["port"]), timeout=15) as server:
            server.login(str(settings["username"]), str(settings["password"]))
            server.send_message(msg)
