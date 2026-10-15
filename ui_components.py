"""Reusable Streamlit image preview components."""

import streamlit as st


# =============================================================================================================================
# Image Preview UI
# =============================================================================================================================

def render_empty_preview_box(message, height=520):
    
    st.markdown(
        f"""
        <div style="
            border: 1px dashed #999;
            border-radius: 12px;
            height: {height}px;
            display: flex;
            align-items: center;
            justify-content: center;
            color: #777;
            font-size: 15px;
            text-align: center;
            padding: 20px;
        ">
            {message}
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_image_preview_box(image_url, caption="", height=400):
    
    max_img_height = height - 55

    html = (
        f'<div style="'
        f'border: 1px dashed #999;'
        f'border-radius: 12px;'
        f'height: {height}px;'
        f'display: flex;'
        f'flex-direction: column;'
        f'align-items: center;'
        f'justify-content: center;'
        f'color: #777;'
        f'font-size: 14px;'
        f'text-align: center;'
        f'padding: 12px;'
        f'">'
        f'<img src="{image_url}" style="'
        f'max-width: 100%;'
        f'max-height: {max_img_height}px;'
        f'object-fit: contain;'
        f'border-radius: 8px;'
        f'">'
        f'<div style="margin-top: 8px;">{caption}</div>'
        f'</div>'
    )

    st.markdown(html, unsafe_allow_html=True)
