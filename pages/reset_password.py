"""Forgot-password and reset-token page."""
from __future__ import annotations

import streamlit as st
from sqlalchemy.orm import Session

from services.auth_service import complete_password_reset, safe_request_password_reset


def render(db: Session) -> None:
    """Render request-reset or complete-reset form depending on token query param."""
    st.title("🔐 Şifremi Unuttum")
    token = st.query_params.get("token")

    if token:
        with st.form("complete_reset_form"):
            st.write("Yeni şifrenizi belirleyin.")
            p1 = st.text_input("Yeni şifre", type="password")
            p2 = st.text_input("Yeni şifre tekrar", type="password")
            submitted = st.form_submit_button("Şifreyi güncelle", type="primary")
            if submitted:
                if p1 != p2:
                    st.error("Şifreler eşleşmiyor.")
                    return
                try:
                    complete_password_reset(db, token, p1)
                    st.success("Şifre güncellendi. Giriş ekranından oturum açabilirsiniz.")
                except ValueError as exc:
                    st.error(str(exc))
        return

    with st.form("request_reset_form"):
        email = st.text_input("E-posta adresiniz")
        base_url = st.text_input("Uygulama adresi", value=st.secrets.get("APP_BASE_URL", "http://localhost:8501"))
        submitted = st.form_submit_button("Sıfırlama bağlantısı gönder", type="primary")
        if submitted:
            try:
                st.info(safe_request_password_reset(db, email, base_url))
            except ValueError as exc:
                st.error(str(exc))
