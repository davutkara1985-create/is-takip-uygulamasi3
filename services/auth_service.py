"""Authentication, session and password-reset services."""
from __future__ import annotations

import hashlib
import secrets
from datetime import datetime, timedelta
from typing import Optional

import bcrypt
import streamlit as st
from sqlalchemy.orm import Session

from database.models import User
from services.email_service import EmailNotConfiguredError, send_email
from utils.constants import ROLE_ADMIN


def hash_password(password: str) -> str:
    """Return a secure bcrypt hash for a plaintext password."""
    if len(password) < 8:
        raise ValueError("Şifre en az 8 karakter olmalıdır.")
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt(rounds=12)).decode("utf-8")


def verify_password(password: str, password_hash: str) -> bool:
    """Verify a plaintext password against a bcrypt hash."""
    try:
        return bcrypt.checkpw(password.encode("utf-8"), password_hash.encode("utf-8"))
    except ValueError:
        return False


def token_digest(token: str) -> str:
    """Create a deterministic SHA-256 digest for reset token storage."""
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def authenticate_user(db: Session, username: str, password: str) -> Optional[User]:
    """Authenticate an active user by username and password."""
    user = db.query(User).filter(User.username == username.strip().lower()).one_or_none()
    if not user or not user.active:
        return None
    if not verify_password(password, user.password_hash):
        return None
    return user


def login_user(user: User) -> None:
    """Store the authenticated user in Streamlit session state."""
    st.session_state["auth_user_id"] = user.id
    st.session_state["auth_username"] = user.username
    st.session_state["auth_role"] = user.role
    st.session_state["auth_full_name"] = user.full_name
    st.session_state["logged_in"] = True


def logout_user() -> None:
    """Clear the Streamlit login state."""
    for key in ["auth_user_id", "auth_username", "auth_role", "auth_full_name", "logged_in"]:
        st.session_state.pop(key, None)


def require_login() -> bool:
    """Return True when a user is logged in."""
    return bool(st.session_state.get("logged_in") and st.session_state.get("auth_user_id"))


def current_user_id() -> int | None:
    """Return the logged-in user id from session state."""
    user_id = st.session_state.get("auth_user_id")
    return int(user_id) if user_id else None


def is_admin() -> bool:
    """Check whether the current session belongs to an admin."""
    return st.session_state.get("auth_role") == ROLE_ADMIN


def reset_user_password_by_admin(db: Session, user_id: int, new_password: str) -> User:
    """Reset a user's password as admin using bcrypt and force password change."""
    user = db.get(User, user_id)
    if not user:
        raise ValueError("Kullanıcı bulunamadı.")
    user.password_hash = hash_password(new_password)
    user.must_change_password = True
    return user


def change_own_password(db: Session, user_id: int, old_password: str, new_password: str) -> None:
    """Change a user's own password after validating the current password."""
    user = db.get(User, user_id)
    if not user:
        raise ValueError("Kullanıcı bulunamadı.")
    if not verify_password(old_password, user.password_hash):
        raise ValueError("Mevcut şifre hatalı.")
    user.password_hash = hash_password(new_password)
    user.must_change_password = False


def create_password_reset_token(db: Session, email: str) -> str:
    """Create and persist a one-time password-reset token for a user email."""
    user = db.query(User).filter(User.email == email.strip().lower(), User.active.is_(True)).one_or_none()
    if not user:
        raise ValueError("Bu e-posta adresiyle aktif kullanıcı bulunamadı.")
    token = secrets.token_urlsafe(36)
    user.reset_token_hash = token_digest(token)
    user.reset_token_expires_at = datetime.utcnow() + timedelta(minutes=30)
    return token


def send_password_reset_email(email: str, token: str, base_url: str) -> None:
    """Send a reset link using SMTP. The caller controls the public base URL."""
    reset_link = f"{base_url.rstrip('/')}?page=reset_password&token={token}"
    body = (
        "Merhaba,\n\n"
        "TÜRKAK İş Yönetim Sistemi şifre sıfırlama bağlantınız aşağıdadır. "
        "Bağlantı 30 dakika geçerlidir.\n\n"
        f"{reset_link}\n\n"
        "Bu talep size ait değilse bu e-postayı yok sayabilirsiniz."
    )
    send_email(email, "TÜRKAK İş Yönetim Sistemi - Şifre Sıfırlama", body)


def complete_password_reset(db: Session, token: str, new_password: str) -> None:
    """Validate a reset token and set a new password."""
    digest = token_digest(token)
    user = db.query(User).filter(User.reset_token_hash == digest).one_or_none()
    if not user or not user.reset_token_expires_at or user.reset_token_expires_at < datetime.utcnow():
        raise ValueError("Şifre sıfırlama bağlantısı geçersiz veya süresi dolmuş.")
    user.password_hash = hash_password(new_password)
    user.must_change_password = False
    user.reset_token_hash = None
    user.reset_token_expires_at = None


def safe_request_password_reset(db: Session, email: str, base_url: str) -> str:
    """Create token and send email; returns a user-facing status message."""
    token = create_password_reset_token(db, email)
    try:
        send_password_reset_email(email, token, base_url)
        return "Şifre sıfırlama bağlantısı e-posta adresine gönderildi."
    except EmailNotConfiguredError:
        return "SMTP ayarı eksik. Token üretildi; geliştirici ortamında link konsola/loga alınmalıdır."
