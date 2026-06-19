"""Custom timeline UI page."""
from __future__ import annotations

import streamlit as st
from sqlalchemy.orm import Session

from database.models import TimelineEvent
from utils.constants import TIMELINE_TYPES


def _event_form(db: Session, user_id: int) -> None:
    """Create a timeline event."""
    with st.expander("➕ Zaman tüneline olay ekle", expanded=False):
        with st.form("timeline_event_form", clear_on_submit=True):
            title = st.text_input("Başlık")
            description = st.text_area("Açıklama")
            event_date = st.date_input("Tarih")
            event_type = st.selectbox("Tür", TIMELINE_TYPES)
            if st.form_submit_button("Ekle", type="primary"):
                if not title:
                    st.error("Başlık zorunludur.")
                    return
                db.add(
                    TimelineEvent(
                        title=title.strip(),
                        description=description.strip(),
                        event_date=event_date,
                        event_type=event_type,
                        created_by=user_id,
                    )
                )
                st.success("Olay eklendi.")


def render(db: Session, user_id: int) -> None:
    """Render st.timeline-like custom vertical timeline."""
    st.title("🕘 Zaman Tüneli")
    st.caption("Kurumsal iletişim faaliyetlerinin tarihsel görünümü")
    _event_form(db, user_id)

    items = db.query(TimelineEvent).order_by(TimelineEvent.event_date.desc()).all()
    if not items:
        st.info("Zaman tüneli kaydı yok.")
        return

    for item in items:
        st.markdown(
            f"""
            <div class="timeline-item">
              <strong>{item.event_date:%d.%m.%Y} · {item.event_type}</strong>
              <h4 style="margin:.3rem 0">{item.title}</h4>
              <p style="margin-bottom:0">{item.description}</p>
            </div>
            """,
            unsafe_allow_html=True,
        )
