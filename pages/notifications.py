"""Notification center page."""
from __future__ import annotations

import streamlit as st
from sqlalchemy.orm import Session

from services.notification_service import list_notifications, mark_as_read


def render(db: Session, user_id: int) -> None:
    """Render notifications and read-state actions."""
    st.title("🔔 Bildirim Merkezi")
    st.caption("Mevcut bildirim sistemi korunarak popup ve e-posta desteğiyle genişletildi.")
    items = list_notifications(db, user_id)
    if not items:
        st.info("Bildirim bulunmuyor.")
        return
    for item in items:
        icon = "🟢" if item.read else "🔴"
        with st.container(border=True):
            st.write(f"{icon} **{item.title}**")
            st.write(item.message)
            st.caption(f"Kanal: {item.channel} · E-posta: {'gönderildi' if item.emailed else 'gönderilmedi'} · {item.created_at:%d.%m.%Y %H:%M}")
            if not item.read and st.button("Okundu işaretle", key=f"read_{item.id}"):
                mark_as_read(db, item.id, user_id)
                st.rerun()
