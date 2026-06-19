"""Reusable Streamlit helpers: state defaults, CSS and filtering."""
from __future__ import annotations

from datetime import date
from pathlib import Path
from typing import Iterable

import streamlit as st

from utils.constants import FONT_SIZE_OPTIONS, THEME_OPTIONS


def init_session_defaults() -> None:
    """Initialize application-level session state values."""
    st.session_state.setdefault("accessibility_theme", THEME_OPTIONS[0])
    st.session_state.setdefault("font_size", "Normal")
    st.session_state.setdefault("chat_messages", [])
    st.session_state.setdefault("active_page", "dashboard")


def inject_global_css() -> None:
    """Inject responsive, accessible CSS based on session settings."""
    font_size = FONT_SIZE_OPTIONS.get(st.session_state.get("font_size", "Normal"), "16px")
    dark = st.session_state.get("accessibility_theme") == "Koyu"
    bg = "#111827" if dark else "#ffffff"
    fg = "#f9fafb" if dark else "#1f2937"
    panel_bg = "#1f2937" if dark else "#ffffff"
    line = "#374151" if dark else "#e5e7eb"

    st.markdown(
        f"""
        <style>
        html, body, [data-testid="stAppViewContainer"] {{
            font-size: {font_size};
            background: {bg};
            color: {fg};
        }}
        .block-container {{
            max-width: 1280px;
            padding-top: 1.2rem;
            padding-left: 1rem;
            padding-right: 1rem;
        }}
        [data-testid="stSidebar"] {{ min-width: 280px; }}
        .turkak-card {{
            border: 1px solid {line};
            border-radius: 18px;
            padding: 1rem;
            background: {panel_bg};
            box-shadow: 0 8px 24px rgba(31, 41, 55, .08);
            margin-bottom: .8rem;
        }}
        .timeline-item {{
            border-left: 4px solid #c8102e;
            padding: .8rem 1rem;
            margin: .6rem 0;
            background: {panel_bg};
            border-radius: 0 14px 14px 0;
            border-top: 1px solid {line};
            border-right: 1px solid {line};
            border-bottom: 1px solid {line};
        }}
        @media (max-width: 820px) {{
            .block-container {{ padding-left: .5rem; padding-right: .5rem; }}
            [data-testid="column"] {{ width: 100% !important; flex: 1 1 100% !important; }}
            [data-testid="stMetric"] {{ padding: .3rem 0; }}
            .turkak-card {{ padding: .8rem; }}
            button {{ min-height: 42px; }}
        }}
        </style>
        """,
        unsafe_allow_html=True,
    )


def save_uploaded_file(uploaded_file, target_dir: Path) -> Path:
    """Persist a Streamlit UploadedFile to target directory and return its path."""
    target_dir.mkdir(parents=True, exist_ok=True)
    safe_name = Path(uploaded_file.name).name.replace(" ", "_")
    target_path = target_dir / safe_name
    suffix = 1
    while target_path.exists():
        target_path = target_dir / f"{Path(safe_name).stem}_{suffix}{Path(safe_name).suffix}"
        suffix += 1
    target_path.write_bytes(uploaded_file.getbuffer())
    return target_path


def contains_text(record_values: Iterable[str], query: str) -> bool:
    """Case-insensitive Turkish-friendly filtering helper."""
    if not query:
        return True
    haystack = " ".join(str(v or "") for v in record_values).lower()
    return query.lower() in haystack


def date_in_range(value: date | None, start: date | None, end: date | None) -> bool:
    """Return True when a date is inside optional start/end boundaries."""
    if value is None:
        return not start and not end
    if start and value < start:
        return False
    if end and value > end:
        return False
    return True
