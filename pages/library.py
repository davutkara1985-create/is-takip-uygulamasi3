"""Corporate identity library page."""
from __future__ import annotations

from pathlib import Path

import streamlit as st
from sqlalchemy.orm import Session

from components.modal import show_asset_dialog
from database.models import BrandAsset
from services.auth_service import is_admin
from utils.helpers import save_uploaded_file

UPLOAD_DIR = Path(__file__).resolve().parents[1] / "data" / "uploads" / "library"


def _upload_form(db: Session, user_id: int) -> None:
    """Admin upload form for corporate identity assets."""
    if not is_admin():
        return
    with st.expander("➕ Yeni kurumsal kimlik dosyası yükle", expanded=False):
        with st.form("library_upload_form", clear_on_submit=True):
            title = st.text_input("Başlık")
            description = st.text_area("Açıklama")
            uploaded = st.file_uploader("Görsel / dosya yükle", type=["png", "jpg", "jpeg", "webp", "svg", "pdf"])
            submitted = st.form_submit_button("Kütüphaneye ekle", type="primary")
            if submitted:
                if not title or uploaded is None:
                    st.error("Başlık ve dosya zorunludur.")
                    return
                path = save_uploaded_file(uploaded, UPLOAD_DIR)
                db.add(
                    BrandAsset(
                        title=title.strip(),
                        description=description.strip(),
                        file_name=uploaded.name,
                        file_path=str(path),
                        mime_type=uploaded.type or "application/octet-stream",
                        uploaded_by=user_id,
                    )
                )
                st.success("Dosya kütüphaneye eklendi.")


def render(db: Session, user_id: int) -> None:
    """Render corporate identity library for admins and users."""
    st.title("🎨 Kurumsal Kimlik Kütüphanesi")
    st.caption("Logo, görsel, şablon ve kurumsal kimlik materyalleri")
    _upload_form(db, user_id)

    assets = db.query(BrandAsset).order_by(BrandAsset.created_at.desc()).all()
    if not assets:
        st.info("Henüz kütüphane kaydı bulunmuyor.")
        return

    for asset in assets:
        left, right = st.columns([1, 2])
        with left:
            st.markdown(f"### {asset.title}")
            st.write(asset.description or "Açıklama girilmemiş.")
            if st.button("Detay / önizleme", key=f"asset_{asset.id}"):
                show_asset_dialog(asset)
        with right:
            if str(asset.mime_type).startswith("image") and Path(asset.file_path).exists():
                st.image(asset.file_path, use_container_width=True)
            elif Path(asset.file_path).exists():
                with open(asset.file_path, "rb") as fh:
                    st.download_button("Dosyayı indir", data=fh, file_name=asset.file_name, key=f"download_{asset.id}")
            else:
                st.warning("Dosya yolu bulunamadı.")
        st.divider()
