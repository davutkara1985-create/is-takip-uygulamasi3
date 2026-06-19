"""Modal abstraction built on Streamlit dialog."""
from __future__ import annotations

import streamlit as st


def show_asset_dialog(asset) -> None:
    """Open a modal-like dialog for a library asset."""
    @st.dialog(asset.title)
    def _dialog() -> None:
        left, right = st.columns([1, 2])
        with left:
            st.subheader(asset.title)
            st.write(asset.description or "Açıklama girilmemiş.")
            st.caption(f"Dosya: {asset.file_name}")
        with right:
            if str(asset.mime_type).startswith("image"):
                st.image(asset.file_path, use_container_width=True)
            else:
                with open(asset.file_path, "rb") as fh:
                    st.download_button("Dosyayı indir", data=fh, file_name=asset.file_name)
    _dialog()
