import streamlit as st
import streamlit.components.v1 as components

# Streamlit sayfasını geniş ekran yap
st.set_page_config(
    page_title="İş Yönetim Sistemi",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# Streamlit'in kendi boşluklarını ve üst/alt alanlarını kaldır
st.markdown("""
<style>
/* Sayfanın genel boşluklarını sıfırla */
html, body, [data-testid="stAppViewContainer"] {
    margin: 14 !important;
    padding: 14 !important;
    overflow: hidden !important;
}

/* Streamlit ana içerik kapsayıcısının boşluklarını kaldır */
.block-container {
    padding-top: 0rem !important;
    padding-bottom: 0rem !important;
    padding-left: 0rem !important;
    padding-right: 0rem !important;
    margin: 0 !important;
    max-width: 100% !important;
}

/* Streamlit üst barını gizle */
[data-testid="stHeader"] {
    display: none !important;
}

/* Streamlit toolbar alanını gizle */
[data-testid="stToolbar"] {
    display: none !important;
}

/* Streamlit footer alanını gizle */
footer {
    display: none !important;
}

/* iframe çevresindeki boşlukları kaldır */
iframe {
    display: block !important;
    width: 100vw !important;
    min-width: 100vw !important;
    height: 100vh !important;
    min-height: 100vh !important;
    border: none !important;
    margin: 0 !important;
    padding: 0 !important;
}
</style>
""", unsafe_allow_html=True)

# HTML dosyasını oku
with open("index.html", "r", encoding="utf-8") as f:
    html_kodu = f.read()
ai_proxy_url = st.secrets.get("AI_PROXY_URL", "http://127.0.0.1:8000/ai-content")
st.write("AI_PROXY_URL:", ai_proxy_url)
html_kodu = html_kodu.replace("__AI_PROXY_URL__", ai_proxy_url)

# HTML'i Streamlit bileşeni olarak tam ekrana yakın göster
components.html(
    html_kodu,
    height=1100,
    scrolling=False
)
