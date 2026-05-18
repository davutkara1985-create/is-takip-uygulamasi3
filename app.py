import streamlit as st
st.set_page_config(
    page_title="TÜRKAK İş Yönetim Sistemi",
    page_icon="turkak.png",
    layout="wide",
    initial_sidebar_state="collapsed"
)
import streamlit.components.v1 as components

# Streamlit sayfasını tam ekran yap
st.set_page_config(layout="wide", page_title="İş Yönetim Sistemi")
st.markdown("""
<style>
    .block-container {
        max-width: 100% !important;
        padding-top: 0rem !important;
        padding-right: 0rem !important;
        padding-left: 0rem !important;
        padding-bottom: 0rem !important;
    }

    [data-testid="stAppViewContainer"] {
        padding: 0 !important;
    }

    [data-testid="stHeader"] {
        background: transparent;
        height: 0rem;
    }

    [data-testid="stToolbar"] {
        display: none;
    }

    footer {
        visibility: hidden;
    }

    iframe {
        width: 100vw !important;
        min-height: 100vh !important;
        border: none !important;
    }
</style>
""", unsafe_allow_html=True)
# HTML dosyasını oku
with open("index.html", "r", encoding="utf-8") as f:
    html_kodu = f.read()

# HTML'i Streamlit bileşeni olarak ekranda göster
components.html(
    html_code,
    height=1100,
    scrolling=True
)
