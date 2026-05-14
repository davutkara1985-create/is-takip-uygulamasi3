import streamlit as st
import streamlit.components.v1 as components

# Streamlit sayfasını tam ekran yap
st.set_page_config(layout="wide", page_title="İş Takip Sistemi")

# HTML dosyasını oku
with open("index.html", "r", encoding="utf-8") as f:
    html_kodu = f.read()

# HTML'i Streamlit bileşeni olarak ekranda göster
components.html(html_kodu, height=900, scrolling=True)
