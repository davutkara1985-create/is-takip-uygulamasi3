"""TÜRKAK İş Yönetim Sistemi - modular Streamlit entrypoint."""
from __future__ import annotations

import streamlit as st

from components.chatbot import render_sidebar_chatbot
from components.navbar import render_nav
from database.db import get_session, init_db
from database.models import User
from pages import admin, dashboard, ideas, library, notifications, reset_password, search, timeline
from services.auth_service import authenticate_user, change_own_password, current_user_id, login_user, logout_user, require_login
from services.notification_service import render_unread_toasts, unread_count
from utils.constants import APP_ICON, APP_TITLE, FONT_SIZE_OPTIONS, THEME_OPTIONS
from utils.helpers import init_session_defaults, inject_global_css


def render_login(db) -> None:
    """Render login and forgot-password access."""
    st.title("TÜRKAK İş Yönetim Sistemi")
    st.caption("Kurumsal iletişim süreçleri için modüler yönetim paneli")

    with st.form("login_form"):
        username = st.text_input("Kullanıcı adı")
        password = st.text_input("Şifre", type="password")
        submitted = st.form_submit_button("Giriş Yap", type="primary")
        if submitted:
            user = authenticate_user(db, username, password)
            if not user:
                st.error("Kullanıcı adı veya şifre hatalı.")
                return
            login_user(user)
            st.success("Giriş başarılı.")
            st.rerun()

    if st.button("Şifremi Unuttum"):
        st.query_params["page"] = "reset_password"
        st.rerun()


def render_accessibility_settings() -> None:
    """Render session-state based accessibility settings in sidebar."""
    with st.sidebar.expander("♿ Erişilebilirlik", expanded=False):
        st.session_state["accessibility_theme"] = st.selectbox(
            "Tema",
            THEME_OPTIONS,
            index=THEME_OPTIONS.index(st.session_state.get("accessibility_theme", THEME_OPTIONS[0])),
        )
        st.session_state["font_size"] = st.selectbox(
            "Yazı boyutu",
            list(FONT_SIZE_OPTIONS.keys()),
            index=list(FONT_SIZE_OPTIONS.keys()).index(st.session_state.get("font_size", "Normal")),
        )


def render_profile(db, user: User) -> None:
    """Render profile/password update form."""
    with st.sidebar.expander("👤 Profil / Şifre", expanded=False):
        st.write(f"**{user.full_name}**")
        st.caption(user.email)
        with st.form("change_password_form"):
            old = st.text_input("Mevcut şifre", type="password")
            new = st.text_input("Yeni şifre", type="password")
            new2 = st.text_input("Yeni şifre tekrar", type="password")
            submitted = st.form_submit_button("Şifreyi değiştir")
            if submitted:
                if new != new2:
                    st.error("Yeni şifreler eşleşmiyor.")
                    return
                try:
                    change_own_password(db, user.id, old, new)
                    st.success("Şifre güncellendi.")
                except ValueError as exc:
                    st.error(str(exc))
        if st.button("Çıkış Yap"):
            logout_user()
            st.rerun()


def route_page(page_key: str, db, user_id: int) -> None:
    """Route selected sidebar page to its module render function."""
    if page_key == "dashboard":
        dashboard.render(db, user_id)
    elif page_key == "admin":
        admin.render(db, user_id)
    elif page_key == "library":
        library.render(db, user_id)
    elif page_key == "notifications":
        notifications.render(db, user_id)
    elif page_key == "ideas":
        ideas.render(db, user_id)
    elif page_key == "timeline":
        timeline.render(db, user_id)
    elif page_key == "search":
        search.render(db, user_id)
    else:
        dashboard.render(db, user_id)


def main() -> None:
    """Configure Streamlit, initialize DB and render the application."""
    st.set_page_config(page_title=APP_TITLE, page_icon=APP_ICON, layout="wide", initial_sidebar_state="expanded")
    init_session_defaults()
    inject_global_css()
    init_db()

    with get_session() as db:
        if st.query_params.get("page") == "reset_password":
            reset_password.render(db)
            return

        if not require_login():
            render_login(db)
            return

        user_id = current_user_id()
        user = db.get(User, user_id) if user_id else None
        if not user or not user.active:
            logout_user()
            st.warning("Oturum sonlandırıldı. Lütfen tekrar giriş yapın.")
            return

        render_accessibility_settings()
        render_profile(db, user)
        unread = unread_count(db, user.id)
        page_key = render_nav(unread)
        render_sidebar_chatbot(db, user.id)
        render_unread_toasts(db, user.id)
        route_page(page_key, db, user.id)


if __name__ == "__main__":
    main()
