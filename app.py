
import streamlit as st

st.set_page_config(layout="wide", page_title="İş Yönetim Sistemi")

with open("index.html", "r", encoding="utf-8") as f:
    html_kodu = f.read()

st.markdown(html_kodu, unsafe_allow_html=True)
