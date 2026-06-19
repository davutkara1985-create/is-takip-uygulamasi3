"""Reusable card/metric components."""
from __future__ import annotations

import streamlit as st


def kpi_card(label: str, value: int | str, help_text: str = "") -> None:
    """Render a Streamlit metric with consistent labels."""
    st.metric(label=label, value=value, help=help_text or None)


def info_card(title: str, body: str, icon: str = "ℹ️") -> None:
    """Render a small HTML info card."""
    st.markdown(
        f"""
        <div class="turkak-card">
          <strong>{icon} {title}</strong>
          <p style="margin-bottom:0">{body}</p>
        </div>
        """,
        unsafe_allow_html=True,
    )
