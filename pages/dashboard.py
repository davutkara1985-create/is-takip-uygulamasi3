"""Dashboard page with metrics and daily AI assistant summary."""
from __future__ import annotations

from datetime import date, timedelta

import streamlit as st
from sqlalchemy.orm import Session

from components.cards import info_card, kpi_card
from database.models import BrandAsset, ContentIdea, Notification, TimelineEvent, WorkItem
from services.ai_service import AIServiceError, generate_daily_summary


def _dashboard_context(db: Session, user_id: int) -> dict:
    """Collect current dashboard metrics used by the AI summary."""
    today = date.today()
    week_end = today + timedelta(days=7)
    open_items = db.query(WorkItem).filter(WorkItem.status != "Tamamlandı").count()
    due_week = (
        db.query(WorkItem)
        .filter(WorkItem.due_date.is_not(None), WorkItem.due_date >= today, WorkItem.due_date <= week_end)
        .count()
    )
    overdue = db.query(WorkItem).filter(WorkItem.due_date.is_not(None), WorkItem.due_date < today).count()
    return {
        "open_work_items": open_items,
        "due_this_week": due_week,
        "overdue": overdue,
        "content_ideas": db.query(ContentIdea).count(),
        "ready_ideas": db.query(ContentIdea).filter(ContentIdea.status == "hazır").count(),
        "library_assets": db.query(BrandAsset).count(),
        "timeline_events": db.query(TimelineEvent).count(),
        "unread_notifications": db.query(Notification).filter(Notification.user_id == user_id, Notification.read.is_(False)).count(),
    }


def render(db: Session, user_id: int) -> None:
    """Render dashboard metrics, AI assistant and compact action summary."""
    st.title("🏠 Anasayfa")
    st.caption("Günün özeti, aktif işler, içerik fikirleri ve bildirim durumu")

    ctx = _dashboard_context(db, user_id)
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        kpi_card("Açık İş", ctx["open_work_items"], "Tamamlanmamış işler")
    with col2:
        kpi_card("Bu Hafta", ctx["due_this_week"], "7 gün içinde hedef tarihi olan işler")
    with col3:
        kpi_card("Geciken", ctx["overdue"], "Hedef tarihi geçmiş işler")
    with col4:
        kpi_card("Bildirim", ctx["unread_notifications"], "Okunmamış bildirimler")

    st.divider()
    st.subheader("🧠 Günlük AI Asistan")
    st.info("Kullanıcı verileri özetlenerek günlük odak önerisi üretilebilir.")
    if st.button("Günün AI özetini üret", type="primary"):
        try:
            summary = generate_daily_summary(ctx)
            st.success("Özet üretildi")
            st.write(summary)
        except AIServiceError as exc:
            st.error(str(exc))

    left, right = st.columns([1, 1])
    with left:
        info_card("İçerik Fikir Havuzu", f"Toplam {ctx['content_ideas']} fikir, {ctx['ready_ideas']} hazır fikir var.", "💡")
    with right:
        info_card("Kurumsal Hafıza", f"Kütüphanede {ctx['library_assets']} dosya, zaman tünelinde {ctx['timeline_events']} olay var.", "📚")
