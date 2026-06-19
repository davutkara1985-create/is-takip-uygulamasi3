"""Admin page: user CRUD-lite and secure password reset."""
from __future__ import annotations

import streamlit as st
from sqlalchemy.orm import Session

from database.models import User
from services.auth_service import hash_password, is_admin, reset_user_password_by_admin
from utils.constants import ROLES, ROLE_LABELS


def _create_user_form(db: Session) -> None:
    """Render the admin create-user form."""
    with st.form("create_user_form", clear_on_submit=True):
        st.subheader("Yeni kullanıcı")
        username = st.text_input("Kullanıcı adı")
        full_name = st.text_input("Ad Soyad")
        email = st.text_input("E-posta")
        role = st.selectbox("Rol", ROLES, format_func=lambda r: ROLE_LABELS.get(r, r))
        password = st.text_input("Geçici şifre", type="password")
        submitted = st.form_submit_button("Kullanıcı oluştur", type="primary")
        if submitted:
            if not username or not full_name or not email or not password:
                st.error("Tüm alanlar zorunludur.")
                return
            exists = db.query(User).filter((User.username == username.strip().lower()) | (User.email == email.strip().lower())).first()
            if exists:
                st.error("Bu kullanıcı adı veya e-posta zaten kullanılıyor.")
                return
            db.add(
                User(
                    username=username.strip().lower(),
                    full_name=full_name.strip(),
                    email=email.strip().lower(),
                    role=role,
                    password_hash=hash_password(password),
                    active=True,
                    must_change_password=True,
                )
            )
            st.success("Kullanıcı oluşturuldu.")


def _user_table(db: Session) -> None:
    """Render existing users with active/role update and password reset."""
    st.subheader("Kullanıcılar")
    users = db.query(User).order_by(User.created_at.desc()).all()
    for user in users:
        with st.expander(f"{user.full_name} · {user.username}", expanded=False):
            c1, c2, c3 = st.columns([2, 1, 1])
            with c1:
                user.full_name = st.text_input("Ad Soyad", value=user.full_name, key=f"name_{user.id}")
                user.email = st.text_input("E-posta", value=user.email, key=f"email_{user.id}")
            with c2:
                user.role = st.selectbox(
                    "Rol",
                    ROLES,
                    index=ROLES.index(user.role) if user.role in ROLES else 0,
                    format_func=lambda r: ROLE_LABELS.get(r, r),
                    key=f"role_{user.id}",
                )
                user.active = st.checkbox("Aktif", value=user.active, key=f"active_{user.id}")
            with c3:
                new_password = st.text_input("Yeni şifre", type="password", key=f"reset_{user.id}")
                if st.button("Şifreyi sıfırla", key=f"reset_btn_{user.id}"):
                    try:
                        reset_user_password_by_admin(db, user.id, new_password)
                        st.success("Şifre bcrypt ile sıfırlandı; kullanıcıdan değiştirmesi istenecek.")
                    except ValueError as exc:
                        st.error(str(exc))
                if st.button("Kullanıcıyı kaydet", key=f"save_{user.id}"):
                    st.success("Kullanıcı güncellendi.")


def render(db: Session, user_id: int) -> None:
    """Render admin module."""
    if not is_admin():
        st.warning("Bu ekran sadece admin kullanıcılar içindir.")
        return
    st.title("⚙️ Admin")
    st.caption("Kullanıcı yönetimi ve güvenli şifre reset")
    _create_user_form(db)
    st.divider()
    _user_table(db)
