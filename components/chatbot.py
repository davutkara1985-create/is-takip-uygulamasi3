"""Sidebar chatbot component using the AI service."""
from __future__ import annotations

import streamlit as st
from sqlalchemy.orm import Session

from database.models import BrandAsset, ContentIdea, Notification, TimelineEvent, WorkItem
from services.ai_service import AIServiceError, chatbot_reply


def _context(db: Session, user_id: int) -> dict:
    """Collect compact app context for chatbot answers."""
    return {
        "user_id": user_id,
        "work_items": db.query(WorkItem).count(),
        "content_ideas": db.query(ContentIdea).count(),
        "library_assets": db.query(BrandAsset).count(),
        "timeline_events": db.query(TimelineEvent).count(),
        "unread_notifications": db.query(Notification).filter(Notification.user_id == user_id, Notification.read.is_(False)).count(),
    }


def render_sidebar_chatbot(db: Session, user_id: int) -> None:
    """Render a compact context-aware chatbot in the sidebar."""
    with st.sidebar.expander("🤖 Kurumsal Asistan", expanded=False):
        for msg in st.session_state.get("chat_messages", [])[-4:]:
            st.chat_message(msg["role"]).write(msg["content"])
        question = st.chat_input("Uygulama hakkında sorun", key="sidebar_chat_input")
        if question:
            st.session_state.chat_messages.append({"role": "user", "content": question})
            try:
                answer = chatbot_reply(question, _context(db, user_id))
            except AIServiceError as exc:
                answer = f"AI yanıtı alınamadı: {exc}"
            st.session_state.chat_messages.append({"role": "assistant", "content": answer})
            st.rerun()
