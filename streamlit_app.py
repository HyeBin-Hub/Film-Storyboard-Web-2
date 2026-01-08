# app.py
import streamlit as st
from typing import Any, Dict, List, Optional

from backend import generate_faces, generate_full_body, generate_scene


# -----------------------------
# Page / Session init
# -----------------------------
st.set_page_config(page_title="AI Storyboard Demo", layout="wide")

if "busy" not in st.session_state:
    st.session_state.busy = False

if "step" not in st.session_state:
    st.session_state.step = 1

if "generated_faces" not in st.session_state:
    st.session_state.generated_faces: List[str] = []

if "selected_face_url" not in st.session_state:
    st.session_state.selected_face_url: Optional[str] = None

if "generated_fullbody" not in st.session_state:
    st.session_state.generated_fullbody: List[str] = []

if "selected_fullbody_url" not in st.session_state:
    st.session_state.selected_fullbody_url: Optional[str] = None

if "scene_results" not in st.session_state:
    st.session_state.scene_results: List[str] = []

if "last_error" not in st.session_state:
    st.session_state.last_error: Optional[str] = None


def set_error(msg: str) -> None:
    st.session_state.last_error = msg


def clear_error() -> None:
    st.session_state.last_error = None


def set_busy(v: bool) -> None:
    st.session_state.busy = v


# -----------------------------
# Sidebar: credentials / settings
# -----------------------------
with st.sidebar:
    st.markdown("## RunComfy Settings")

    api_key = st.text_input("RunComfy API Key", type="password")
    deployment_id = st.text_input("Deployment ID")

    st.markdown("---")
    st.markdown("## Generation Settings")

    width = st.selectbox("Width", [512, 768, 896, 1024], index=2)
    height = st.selectbox("Height", [768, 896, 1152, 1024], index=2)
    batch_size = st.selectbox("Batch Size", [1, 2, 4], index=2)

    st.markdown("---")
    st.markdown("## PortraitMaster Options (minimum)")
    pm_options: Dict[str, Any] = {
        "Gender": st.selectbox("Gender", ["-", "male", "female"], index=0),
        "age": st.selectbox("Age", ["-", "child", "teen", "adult"], index=0),
        "Nationality": st.selectbox("Nationality", ["Korean", "-", "Japanese", "Chinese"], index=0),
        "Hair Style": st.text_input("Hair Style", value="-"),
        "Body Type": st.selectbox("Body Type", ["-", "slim", "average", "athletic"], index=0),
    }

    st.markdown("---")
    if st.button("Reset Session", disabled=st.session_state.busy):
        st.session_state.step = 1
        st.session_state.generated_faces = []
        st.session_state.selected_face_url = None
        st.session_state.generated_fullbody = []
        st.session_state.selected_fullbody_url = None
        st.session_state.scene_results = []
        clear_error()
        st.rerun()


# -----------------------------
# Header / Error panel
# -----------------------------
st.markdown("# AI Storyboard Demo")

if st.session_state.last_error:
    st.error("❌ Generate failed.")
    with st.expander("See error details", expanded=False):
        st.code(st.session_state.last_error)


# -----------------------------
# Layout
# -----------------------------
col_left, col_right = st.columns([1.1, 1.0], gap="large")


# =============================
# LEFT: Inputs
# =============================
with col_left:
    st.markdown("## Inputs")

    base_prompt = st.text_area(
        "Step1 - Base Portrait Prompt",
        value="Grey background, a 12-year-old Korean boy, white t-shirt, Buzz cut hair, documentary photograph, cinematic still frame,",
        height=110,
        disabled=st.session_state.busy,
    )

    outfit_prompt = st.text_area(
        "Step2 - Outfit Keywords (for Groq)",
        value="white background, white t-shirt, black pants, yellow sneakers",
        height=80,
        disabled=st.session_state.busy,
    )

    story_prompt = st.text_area(
        "Step3 - Scene Description (Korean OK, GoogleTranslate node will translate)",
        value="소년과 소녀가 카메라 오른쪽 방향으로 나란히 걸어가고 있습니다.",
        height=80,
        disabled=st.session_state.busy,
    )

    # Background URL: Step3에서는 bg_url이 필요.
    # 외부 URL은 403이 날 수 있으니, 사용자는 "RunComfy가 반환한 url"을 넣는 게 안전.
    bg_url = st.text_input(
        "Step3 - Background Image URL (recommended: RunComfy output url)",
        value="",
        disabled=st.session_state.busy,
        help="외부 위키/구글 이미지 링크는 RunComfy 서버에서 403으로 막힐 수 있습니다. RunComfy 결과 url을 쓰는 것이 가장 안전합니다.",
    )


# =============================
# RIGHT: Actions / Outputs
# =============================
with col_right:
    st.markdown("## Actions")

    if not api_key or not deployment_id:
        st.info("Enter API Key + Deployment ID in the sidebar.")
    else:
        # -------------------------
        # Step 1: Generate Faces
        # -------------------------
        st.markdown("### Step 1) Portrait")
        c1, c2 = st.columns([1, 1])
        with c1:
            if st.button("Generate Portraits", disabled=st.session_state.busy):
                clear_error()
                set_busy(True)
                try:
                    urls = generate_faces(
                        api_key=api_key,
                        deployment_id=deployment_id,
                        width=width,
                        height=height,
                        batch_size=batch_size,
                        pm_options=pm_options,
                        base_prompt=base_prompt,
                    )
                    st.session_state.generated_faces = urls
                    st.session_state.selected_face_url = None
                    st.session_state.step = 1
                except Exception as e:
                    set_error(str(e))
                finally:
                    set_busy(False)
                    st.rerun()

        with c2:
            if st.button("Clear Portraits", disabled=st.session_state.busy):
                st.session_state.generated_faces = []
                st.session_state.selected_face_url = None
                st.rerun()

        if st.session_state.generated_faces:
            st.markdown("#### Portrait Results")
            cols = st.columns(min(len(st.session_state.generated_faces), 4))
            for i, url in enumerate(st.session_state.generated_faces):
                with cols[i % len(cols)]:
                    border = "3px solid #FFD700" if url == st.session_state.selected_face_url else "1px solid #333"
                    st.markdown(f"<div style='border:{border}; padding:4px; border-radius:8px;'>", unsafe_allow_html=True)
                    st.image(url, use_container_width=True)
                    st.markdown("</div>", unsafe_allow_html=True)

                    if st.button(f"Select Portrait #{i+1}", key=f"sel_face_{i}", disabled=st.session_state.busy):
                        st.session_state.selected_face_url = url
                        st.session_state.step = 2
                        st.rerun()

        st.markdown("---")

        # -------------------------
        # Step 2: Generate Full body
        # -------------------------
        st.markdown("### Step 2) Full Body")
        if not st.session_state.selected_face_url:
            st.info("Select a portrait from Step 1 to proceed.")
        else:
            st.caption("Selected portrait URL:")
            st.code(st.session_state.selected_face_url)

            if st.button("Generate Full Body", disabled=st.session_state.busy):
                clear_error()
                set_busy(True)
                try:
                    urls = generate_full_body(
                        face_url=st.session_state.selected_face_url,
                        outfit_prompt=outfit_prompt,
                        api_key=api_key,
                        deployment_id=deployment_id,
                    )
                    st.session_state.generated_fullbody = urls
                    st.session_state.selected_fullbody_url = None
                    st.session_state.step = 2
                except Exception as e:
                    set_error(str(e))
                finally:
                    set_busy(False)
                    st.rerun()

            if st.session_state.generated_fullbody:
                st.markdown("#### Full Body Results")
                cols = st.columns(min(len(st.session_state.generated_fullbody), 4))
                for i, url in enumerate(st.session_state.generated_fullbody):
                    with cols[i % len(cols)]:
                        border = "3px solid #00E5FF" if url == st.session_state.selected_fullbody_url else "1px solid #333"
                        st.markdown(f"<div style='border:{border}; padding:4px; border-radius:8px;'>", unsafe_allow_html=True)
                        st.image(url, use_container_width=True)
                        st.markdown("</div>", unsafe_allow_html=True)

                        if st.button(f"Select FullBody #{i+1}", key=f"sel_body_{i}", disabled=st.session_state.busy):
                            st.session_state.selected_fullbody_url = url
                            st.session_state.step = 3
                            st.rerun()

        st.markdown("---")

        # -------------------------
        # Step 3: Generate Scene
        # -------------------------
        st.markdown("### Step 3) Scene")
        if not st.session_state.selected_fullbody_url:
            st.info("Select a full-body image from Step 2 to proceed.")
        elif not bg_url:
            st.warning("Provide a Background Image URL for Step 3 (preferably a RunComfy output url).")
        else:
            st.caption("Selected character (image1) URL:")
            st.code(st.session_state.selected_fullbody_url)
            st.caption("Background (image3) URL:")
            st.code(bg_url)

            if st.button("Generate Scene", disabled=st.session_state.busy):
                clear_error()
                set_busy(True)
                try:
                    urls = generate_scene(
                        char1_url=st.session_state.selected_fullbody_url,
                        char2_url=None,   # 필요하면 확장 가능
                        bg_url=bg_url,
                        story_prompt=story_prompt,
                        api_key=api_key,
                        deployment_id=deployment_id,
                    )
                    st.session_state.scene_results = urls
                    st.session_state.step = 3
                except Exception as e:
                    set_error(str(e))
                finally:
                    set_busy(False)
                    st.rerun()

            if st.session_state.scene_results:
                st.markdown("#### Scene Results")
                for url in st.session_state.scene_results:
                    st.image(url, use_container_width=True)
