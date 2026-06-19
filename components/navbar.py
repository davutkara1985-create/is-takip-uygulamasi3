"""Sidebar navigation component."""
from __future__ import annotations

import streamlit as st

from services.auth_service import is_admin


def render_nav(unread_count: int = 0) -> str:
    """Render sidebar menu and return selected page key."""
    st.sidebar.markdown("### TÜRKAK\nİş Yönetim Sistemi")
    labels = {
        "dashboard": "🏠 Anasayfa",
        "admin": "⚙️ Admin",
        "library": "🎨 Kurumsal Kimlik Kütüphanesi",
        "notifications": f"🔔 Bildirim Merkezi ({unread_count})",
        "ideas": "💡 İçerik Fikir Havuzu",
        "timeline": "🕘 Zaman Tüneli",
        "search": "🔎 Gelişmiş Arama",
    }
    options = ["dashboard", "library", "notifications", "ideas", "timeline", "search"]
    if is_admin():
        options.insert(1, "admin")
    current = st.session_state.get("active_page", "dashboard")
    selected = st.sidebar.radio(
        "Menü",
        options,
        format_func=lambda key: labels[key],
        index=options.index(current) if current in options else 0,
        label_visibility="collapsed",
    )
    st.session_state["active_page"] = selected
    return selected
