"""Content idea pool with CRUD and AI generation."""
from __future__ import annotations

import streamlit as st
from sqlalchemy.orm import Session

from database.models import ContentIdea
from services.ai_service import AIServiceError, generate_idea_content
from utils.constants import IDEA_STATUSES


def _create_form(db: Session, user_id: int) -> None:
    """Create a new content idea."""
    with st.form("idea_create", clear_on_submit=True):
        st.subheader("Yeni fikir")
        title = st.text_input("Başlık")
        description = st.text_area("Açıklama")
        status = st.selectbox("Durum", IDEA_STATUSES)
        submitted = st.form_submit_button("Fikri kaydet", type="primary")
        if submitted:
            if not title:
                st.error("Başlık zorunludur.")
                return
            db.add(ContentIdea(title=title.strip(), description=description.strip(), status=status, owner_id=user_id))
            st.success("Fikir kaydedildi.")


def render(db: Session, user_id: int) -> None:
    """Render content idea pool with update/delete and AI buttons."""
    st.title("💡 İçerik Fikir Havuzu")
    st.caption("Fikir → araştırılıyor → hazır akışıyla içerik üretimi")
    _create_form(db, user_id)
    st.divider()

    status_filter = st.selectbox("Duruma göre filtrele", ["Tümü"] + IDEA_STATUSES)
    q = st.text_input("Arama", placeholder="Başlık veya açıklama içinde ara")
    query = db.query(ContentIdea)
    if status_filter != "Tümü":
        query = query.filter(ContentIdea.status == status_filter)
    ideas = query.order_by(ContentIdea.updated_at.desc()).all()
    if q:
        ideas = [i for i in ideas if q.lower() in f"{i.title} {i.description}".lower()]

    if not ideas:
        st.info("Fikir bulunmuyor.")
        return

    for idea in ideas:
        with st.expander(f"{idea.title} · {idea.status}", expanded=False):
            idea.title = st.text_input("Başlık", value=idea.title, key=f"idea_title_{idea.id}")
            idea.description = st.text_area("Açıklama", value=idea.description, key=f"idea_desc_{idea.id}")
            idea.status = st.selectbox(
                "Durum",
                IDEA_STATUSES,
                index=IDEA_STATUSES.index(idea.status) if idea.status in IDEA_STATUSES else 0,
                key=f"idea_status_{idea.id}",
            )
            c1, c2, c3 = st.columns(3)
            with c1:
                if st.button("Güncelle", key=f"idea_save_{idea.id}"):
                    st.success("Fikir güncellendi.")
            with c2:
                if st.button("İçerik oluştur", key=f"idea_ai_{idea.id}"):
                    try:
                        result = generate_idea_content(idea.title, idea.description)
                        idea.generated_text = str(result.get("text", ""))
                        idea.image_prompt = str(result.get("image_prompt", ""))
                        st.success("Metin ve görsel prompt üretildi.")
                    except AIServiceError as exc:
                        st.error(str(exc))
            with c3:
                if st.button("Sil", key=f"idea_delete_{idea.id}"):
                    db.delete(idea)
                    st.success("Fikir silindi.")
                    st.rerun()
            if idea.generated_text:
                st.text_area("Üretilen metin", value=idea.generated_text, height=160, key=f"idea_text_{idea.id}")
            if idea.image_prompt:
                st.text_area("Görsel prompt", value=idea.image_prompt, height=120, key=f"idea_img_{idea.id}")
