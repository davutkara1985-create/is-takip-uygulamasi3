"""Notification center service: in-app records, toast rendering and optional email."""
from __future__ import annotations

from sqlalchemy.orm import Session
import streamlit as st

from database.models import Notification, User
from services.email_service import EmailNotConfiguredError, send_email


def create_notification(
    db: Session,
    *,
    user_id: int,
    title: str,
    message: str,
    channel: str = "app",
    entity_type: str | None = None,
    entity_id: int | None = None,
) -> Notification:
    """Create an in-app notification and optionally send it by email."""
    item = Notification(
        user_id=user_id,
        title=title,
        message=message,
        channel=channel,
        entity_type=entity_type,
        entity_id=entity_id,
    )
    db.add(item)
    db.flush()

    if "email" in channel:
        user = db.get(User, user_id)
        if user and user.email:
            try:
                send_email(user.email, title, message)
                item.emailed = True
            except EmailNotConfiguredError:
                item.emailed = False
            except Exception:
                item.emailed = False
    return item


def unread_count(db: Session, user_id: int) -> int:
    """Return unread notification count for a user."""
    return db.query(Notification).filter(Notification.user_id == user_id, Notification.read.is_(False)).count()


def list_notifications(db: Session, user_id: int, limit: int = 50) -> list[Notification]:
    """Return latest notifications for a user."""
    return (
        db.query(Notification)
        .filter(Notification.user_id == user_id)
        .order_by(Notification.created_at.desc())
        .limit(limit)
        .all()
    )


def mark_as_read(db: Session, notification_id: int, user_id: int) -> None:
    """Mark a notification as read for the owner user."""
    item = (
        db.query(Notification)
        .filter(Notification.id == notification_id, Notification.user_id == user_id)
        .one_or_none()
    )
    if item:
        item.read = True


def render_unread_toasts(db: Session, user_id: int) -> None:
    """Show unread notifications once per Streamlit session with st.toast."""
    rendered_key = "rendered_notification_toasts"
    rendered = set(st.session_state.get(rendered_key, []))
    items = (
        db.query(Notification)
        .filter(Notification.user_id == user_id, Notification.read.is_(False))
        .order_by(Notification.created_at.desc())
        .limit(5)
        .all()
    )
    for item in items:
        if item.id in rendered:
            continue
        st.toast(f"{item.title}: {item.message}", icon="🔔")
        rendered.add(item.id)
    st.session_state[rendered_key] = list(rendered)
