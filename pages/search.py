"""Advanced search page with date and content filters."""
from __future__ import annotations

from datetime import date

import pandas as pd
import streamlit as st
from sqlalchemy.orm import Session

from database.models import BrandAsset, ContentIdea, TimelineEvent, WorkItem
from utils.helpers import contains_text, date_in_range


def _rows(db: Session) -> list[dict]:
    """Collect searchable rows from selected modules."""
    rows: list[dict] = []
    for item in db.query(WorkItem).all():
        rows.append({"modül": "İş", "başlık": item.title, "içerik": item.content, "tarih": item.due_date, "durum": item.status})
    for item in db.query(ContentIdea).all():
        rows.append({"modül": "Fikir", "başlık": item.title, "içerik": item.description, "tarih": item.created_at.date(), "durum": item.status})
    for item in db.query(TimelineEvent).all():
        rows.append({"modül": "Zaman Tüneli", "başlık": item.title, "içerik": item.description, "tarih": item.event_date, "durum": item.event_type})
    for item in db.query(BrandAsset).all():
        rows.append({"modül": "Kütüphane", "başlık": item.title, "içerik": item.description, "tarih": item.created_at.date(), "durum": item.mime_type})
    return rows


def render(db: Session, user_id: int) -> None:
    """Render content/date advanced search."""
    st.title("🔎 Gelişmiş Arama")
    st.caption("Tarih ve içerik filtresiyle modüller arası arama")
    c1, c2, c3 = st.columns([2, 1, 1])
    with c1:
        q = st.text_input("İçerik araması", placeholder="Başlık, açıklama veya içerik")
    with c2:
        start = st.date_input("Başlangıç", value=None)
    with c3:
        end = st.date_input("Bitiş", value=None)

    rows = [
        row
        for row in _rows(db)
        if contains_text([row["başlık"], row["içerik"], row["durum"], row["modül"]], q)
        and date_in_range(row["tarih"], start, end)
    ]
    if not rows:
        st.info("Filtrelere uygun kayıt bulunamadı.")
        return
    st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)
