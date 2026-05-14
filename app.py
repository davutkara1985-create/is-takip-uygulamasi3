import streamlit as st
import streamlit.components.v1 as components

# Streamlit sayfasını tam ekran yap
st.set_page_config(layout="wide", page_title="İş Yönetim Sistemi")

# HTML dosyasını oku
with open("index.html", "r", encoding="utf-8") as f:
    html_kodu = f.read()

# HTML'i Streamlit bileşeni olarak ekranda göster
components.html(
    html_kodu,
    height=800,
    scrolling=True
)
<style>
html, body {
    height: auto;
    margin: 0;
}
</style>
