import csv
import io
import pandas as pd
import streamlit as st


# =========================
# Fixed Values
# =========================
FIXED_BASE_BACKGROUND_CLOTHING_PROMPT = "gray background, white t-shirt"

BODY_PROMPT_PLACEHOLDER = (
    "Example: white shirt, beige shorts, white socks, black shoes, "
    "full-body, standing pose, front view, clean gray background"
)

SKIN_DEFAULTS = {
    "natural_skin": 0.74,
    "bare_face": 0.75,
    "washed_face": 0.0,
    "dried_face": 0.0,
    "skin_details": 0.3,
    "skin_pores": 0.1,
    "dimples": 0.0,
    "wrinkles": 0.0,
    "freckles": 0.0,
    "moles": 0.0,
    "skin_imperfections": 0.0,
    "skin_acne": 0.0,
    "tanned_skin": 0.0,
    "eyes_details": 1.01,
    "iris_details": 0.0,
    "circular_iris": 0.0,
    "circular_pupil": 0.0,
}

BASE_CHARACTER_CHECK_DEFAULTS = {
    "androgynous": 1.0,
    "ugly": 1.0,
    "ordinary_face": 0.25,
    "facial_asymmetry": 1.0,
    "disheveled": 1.0,
}


# =========================
# Helper Functions
# =========================
def decode_uploaded_file(uploaded_file):
    raw = uploaded_file.getvalue()

    for encoding in ["utf-8-sig", "utf-8", "cp949"]:
        try:
            return raw.decode(encoding)
        except Exception:
            pass

    return raw.decode("utf-8", errors="ignore")


def extract_shot_ids_from_csv(csv_text):
    if not csv_text.strip():
        return []

    shot_ids = []
    reader = csv.reader(io.StringIO(csv_text.strip()))

    for row in reader:
        if not row:
            continue

        first_value = row[0].strip()

        if not first_value:
            continue

        if first_value.lower() in {"shot", "shot_id", "shot id", "id"}:
            continue

        if first_value not in shot_ids:
            shot_ids.append(first_value)

    return shot_ids


def read_csv_as_dataframe(csv_text):
    if not csv_text.strip():
        return pd.DataFrame()

    try:
        return pd.read_csv(io.StringIO(csv_text))
    except Exception:
        return pd.DataFrame()


def get_shot_id_column(df):
    if df.empty:
        return None

    candidates = [
        "shot",
        "shot_id",
        "shot id",
        "id",
        "Shot",
        "Shot ID",
        "Shot_ID",
    ]

    for col in df.columns:
        if str(col).strip() in candidates:
            return col

    return df.columns[0]


def get_selected_shot_dataframe():
    csv_text = st.session_state.get("csv_text", "")
    df = read_csv_as_dataframe(csv_text)

    if df.empty:
        return pd.DataFrame()

    shot_col = get_shot_id_column(df)

    if shot_col is None:
        return df

    shot_filter_mode = st.session_state.get("shot_filter_mode", "ALL")
    custom_shots = st.session_state.get("custom_shots", [])

    if shot_filter_mode == "ALL":
        return df

    if not custom_shots:
        return pd.DataFrame()

    return df[df[shot_col].astype(str).isin([str(x) for x in custom_shots])]


def character_label_to_value(label):
    mapping = {
        "Image 1 - Boy": "C1",
        "Image 2 - Girl": "C2",
    }
    return mapping.get(label, "C2")


def body_character_label_to_value(label):
    mapping = {
        "Image 1 - Boy": "C1",
        "Image 2 - Girl": "C2",
    }
    return mapping.get(label, "C1")


def get_checkbox_value(key, on_value):
    return on_value if st.session_state.get(key, False) else 0.0


def initialize_body_prompts():
    if "body_prompt_c1" not in st.session_state:
        st.session_state["body_prompt_c1"] = ""

    if "body_prompt_c2" not in st.session_state:
        st.session_state["body_prompt_c2"] = ""


def get_scene_shot_filter_config():
    shot_filter_mode = st.session_state.get("shot_filter_mode", "ALL")
    custom_shots = st.session_state.get("custom_shots", [])

    if shot_filter_mode == "ALL":
        return "ALL", ""

    return "CUSTOM", ", ".join(custom_shots)


def get_body_reference_candidates(character_code):
    """
    character_code: 'c1' or 'c2'

    Step3에서 여러 body 후보를 저장해둔 경우:
    st.session_state["body_candidates_c1"] = [
        {"label": "Boy Body 1", "image": ..., "filename": "..."},
        {"label": "Boy Body 2", "image": ..., "filename": "..."},
    ]

    후보 리스트가 없으면 body_result_image_c1 / body_result_image_c2를 단일 후보로 fallback.
    """

    candidates_key = f"body_candidates_{character_code}"
    candidates = st.session_state.get(candidates_key, [])

    normalized = []

    for i, item in enumerate(candidates, start=1):
        if not isinstance(item, dict):
            continue

        normalized.append(
            {
                "label": item.get(
                    "label",
                    f"{'Boy' if character_code == 'c1' else 'Girl'} Body {i}",
                ),
                "image": item.get("image"),
                "filename": item.get("filename", ""),
            }
        )

    fallback_image = st.session_state.get(f"body_result_image_{character_code}")
    fallback_filename = st.session_state.get(
        f"body_result_filename_{character_code}",
        "",
    )

    if not normalized and fallback_image is not None:
        normalized.append(
            {
                "label": f"{'Boy' if character_code == 'c1' else 'Girl'} Body 1",
                "image": fallback_image,
                "filename": fallback_filename,
            }
        )

    return normalized


def sync_scene_reference_selection(session_key, candidates):
    labels = [item["label"] for item in candidates]

    if not labels:
        st.session_state[session_key] = ""
        return

    if st.session_state.get(session_key) not in labels:
        st.session_state[session_key] = labels[0]


def get_selected_candidate(candidates, selected_label):
    for item in candidates:
        if item["label"] == selected_label:
            return item

    return None


def build_face_ui_config():
    shot_filter_mode = st.session_state.get("shot_filter_mode", "ALL")
    custom_shots = st.session_state.get("custom_shots", [])

    if shot_filter_mode == "ALL":
        shot_filter = "ALL"
        custom_shot_ids = ""
    else:
        shot_filter = "CUSTOM"
        custom_shot_ids = ", ".join(custom_shots)

    return {
        "csvstoryboardparser": {
            "input_mode": "text",
            "csv_file": "CUSTOM",
            "csv_text": st.session_state.get("csv_text", ""),
            "shot_filter": shot_filter,
            "custom_shot_ids": custom_shot_ids,
        },
        "character_registry_parser": {
            "character_filter": character_label_to_value(
                st.session_state.get("character_filter_label", "Image 2 - Girl")
            ),
            "custom_character_id": "",
            "age": st.session_state.get("age", 9),
            "include_character_id": "false",
        },
        "base_background_clothing_prompt": {
            "text": FIXED_BASE_BACKGROUND_CLOTHING_PROMPT,
        },
        "portrait_master_base_character": {
            "shot": "Head and shoulders portrait",
            "shot_weight": 2,
            "gender": "Woman",
            "age": "-",
            "nationality_1": st.session_state.get("nationality", "South Korean"),
            "nationality_2": "-",
            "nationality_mix": 0,
            "body_type": st.session_state.get("body_type", "Slim"),
            "body_type_weight": 0,
            "breast_size": "-",
            "breast_size_weight": 0,
            "butt_size": "-",
            "butt_size_weight": 0,
            "eyes_color": st.session_state.get("eyes_color", "Brown"),
            "eyes_shape": st.session_state.get(
                "eyes_shape",
                "Double Eyelid Eyes Shape",
            ),
            "lips_color": st.session_state.get("lips_color", "Peach Lips"),
            "lips_shape": st.session_state.get("lips_shape", "Thin Lips"),
            "facial_expression": st.session_state.get(
                "facial_expression",
                "Curious",
            ),
            "facial_expression_weight": 0,
            "face_shape": st.session_state.get("face_shape", "Square with Soft Jaw"),
            "face_shape_weight": 0,
            "hair_style": st.session_state.get("hair_style", "Bob"),
            "hair_color": st.session_state.get("hair_color", "Chestnut"),
            "hair_length": st.session_state.get("hair_length", "-"),
            "androgynous": 0,
            "ugly": 0,
            "ordinary_face": 0.25,
            "facial_asymmetry": 0,
            "disheveled": 0,
            "beard": "-",
            "beard_color": "-",
        },
        "portrait_master_skin_details": {
            key: default_value
            if st.session_state.get(f"skin_{key}", False)
            else 0.0
            for key, default_value in SKIN_DEFAULTS.items()
        },
    }


def build_body_ui_config():
    character_filter_label = st.session_state.get(
        "body_character_filter_label",
        "Image 1 - Boy",
    )
    character_filter = body_character_label_to_value(character_filter_label)

    if character_filter == "C1":
        body_prompt = st.session_state.get("body_prompt_c1", "")
        label = "Image 1 - Boy"
    else:
        body_prompt = st.session_state.get("body_prompt_c2", "")
        label = "Image 2 - Girl"

    return {
        "body_generation": {
            "character_filter": character_filter,
            "label": label,
            "body_prompt": body_prompt,
        }
    }


def build_scene_ui_config():
    shot_filter, custom_shot_ids = get_scene_shot_filter_config()

    boy_candidates = get_body_reference_candidates("c1")
    girl_candidates = get_body_reference_candidates("c2")

    selected_boy = get_selected_candidate(
        boy_candidates,
        st.session_state.get("scene_boy_reference_label", ""),
    )
    selected_girl = get_selected_candidate(
        girl_candidates,
        st.session_state.get("scene_girl_reference_label", ""),
    )

    selected_shot_df = get_selected_shot_dataframe()

    return {
        "scene_generation": {
            "shot_filter": shot_filter,
            "custom_shot_ids": custom_shot_ids,
            "selected_shot_count": len(selected_shot_df),
            "selected_shot_data": selected_shot_df.to_dict(orient="records"),
            "reference_images": {
                "image_1_boy_body": {
                    "label": selected_boy["label"] if selected_boy else "",
                    "filename": selected_boy.get("filename", "") if selected_boy else "",
                },
                "image_2_girl_body": {
                    "label": selected_girl["label"] if selected_girl else "",
                    "filename": selected_girl.get("filename", "") if selected_girl else "",
                },
            },
        }
    }


def get_scene_result_candidates():
    """
    Step4에서 생성된 scene 후보를 Step5 입력 이미지로 사용하기 위한 helper.

    st.session_state["scene_candidates"] = [
        {"label": "Scene 1", "image": ..., "filename": "..."},
        {"label": "Scene 2", "image": ..., "filename": "..."},
    ]

    후보 리스트가 없으면 scene_result_image를 단일 후보로 fallback.
    """

    candidates = st.session_state.get("scene_candidates", [])
    normalized = []

    for i, item in enumerate(candidates, start=1):
        if not isinstance(item, dict):
            continue

        normalized.append(
            {
                "label": item.get("label", f"Scene {i}"),
                "image": item.get("image"),
                "filename": item.get("filename", ""),
            }
        )

    fallback_image = st.session_state.get("scene_result_image")
    fallback_filename = st.session_state.get("scene_result_filename", "")

    if not normalized and fallback_image is not None:
        normalized.append(
            {
                "label": "Scene 1",
                "image": fallback_image,
                "filename": fallback_filename,
            }
        )

    return normalized



# def build_camera_refinement_ui_config():
#     scene_candidates = get_scene_result_candidates()
#     selected_scene = get_selected_candidate(
#         scene_candidates,
#         st.session_state.get("camera_input_scene_label", ""),
#     )

#     selected_shot_df = get_selected_shot_dataframe()
#     prompt_source = st.session_state.get(
#         "camera_prompt_source",
#         "Qwen Multi-Angle Prompt",
#     )

#     switch_setting = 1 if prompt_source == "Structured Scene Prompt" else 2

#     return {
#         "camera_angle_refinement": {
#             "input_scene": {
#                 "label": selected_scene["label"] if selected_scene else "",
#                 "filename": selected_scene.get("filename", "") if selected_scene else "",
#             },
#             "selected_shot_count": len(selected_shot_df),
#             "selected_shot_data": selected_shot_df.to_dict(orient="records"),
#             "camera_control": {
#                 "horizontal_angle": st.session_state.get("camera_horizontal_angle", 0),
#                 "vertical_angle": st.session_state.get("camera_vertical_angle", 0),
#                 "zoom": st.session_state.get("camera_zoom", 5),
#                 "default_prompts": st.session_state.get("camera_default_prompts", True),
#                 "camera_view": st.session_state.get("camera_view", False),
#             },
#             "prompt_source": {
#                 "mode": prompt_source,
#                 "two_way_switch_selection": switch_setting,
#             },
#         }
#     }

def build_camera_refinement_ui_config():
    scene_candidates = get_scene_result_candidates()
    selected_scene = get_selected_candidate(
        scene_candidates,
        st.session_state.get("camera_input_scene_label", ""),
    )

    selected_shot_df = get_selected_shot_dataframe()
    prompt_source = st.session_state.get(
        "camera_prompt_source",
        "Use Camera Angle Prompt",
    )

    switch_setting = 1 if prompt_source == "Preserve Original Scene Prompt" else 2

    return {
        "camera_angle_refinement": {
            "input_scene": {
                "label": selected_scene["label"] if selected_scene else "",
                "filename": selected_scene.get("filename", "") if selected_scene else "",
            },
            "selected_shot_count": len(selected_shot_df),
            "selected_shot_data": selected_shot_df.to_dict(orient="records"),
            "camera_control": {
                "horizontal_angle": st.session_state.get("camera_horizontal_angle", 0),
                "vertical_angle": st.session_state.get("camera_vertical_angle", 0),
                "zoom": st.session_state.get("camera_zoom", 5),
                "default_prompts": st.session_state.get("camera_default_prompts", True),
                "camera_view": st.session_state.get("camera_view", False),
            },
            "prompt_source": {
                "mode": prompt_source,
                "two_way_switch_selection": switch_setting,
            },
        }
    }


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


# =========================
# Page Config
# =========================
st.set_page_config(
    page_title="AI Storyboard Pipeline",
    page_icon="🎬",
    layout="wide",
)

st.title("🎬 AI Storyboard Generation Pipeline")
st.caption("A ComfyUI-based multi-stage generation system for character-consistent cinematic storyboard creation")


# =========================
# Tabs
# =========================
tab1, tab2, tab3, tab4, tab5 = st.tabs(
    [
        "Step 1. Storyboard Data",
        "Step 2. Character Identity",
        "Step 3. Body Reference",
        "Step 4. Scene Generation",
        "Step 5. Camera Refinement",
    ]
)


# =========================
# Step 1. Storyboard Data Parsing
# =========================
with tab1:
    st.header("Step 1. Storyboard Data Parsing")

    uploaded_csv = st.file_uploader(
        "Upload Storyboard CSV",
        type=["csv"],
        help="CSV 파일을 업로드하면 내부적으로 텍스트로 읽어서 workflow에 전달합니다.",
    )

    if uploaded_csv is not None:
        csv_text = decode_uploaded_file(uploaded_csv)
        st.session_state["csv_text"] = csv_text
        st.success(f"업로드 완료: {uploaded_csv.name}")
    else:
        csv_text = st.session_state.get("csv_text", "")

    if csv_text:
        preview_col, filter_col = st.columns([1.55, 1.0], gap="large")

        with preview_col:
            with st.expander("Parsed Storyboard Data Preview", expanded=True):
                try:
                    preview_df = pd.read_csv(io.StringIO(csv_text))

                    st.dataframe(
                        preview_df,
                        use_container_width=True,
                        hide_index=True,
                    )

                except Exception:
                    st.warning("CSV를 표 형태로 읽지 못했습니다. 원본 텍스트로 표시합니다.")
                    st.code(csv_text)

        with filter_col:
            st.subheader("Shot Selection Control")

            shot_ids = extract_shot_ids_from_csv(csv_text)

            st.radio(
                "shot_filter",
                options=["ALL", "CUSTOM"],
                horizontal=True,
                key="shot_filter_mode",
                help="ALL은 전체 shot을 사용하고, CUSTOM은 선택한 shot만 사용합니다.",
            )

            if st.session_state.get("shot_filter_mode", "ALL") == "CUSTOM":
                if shot_ids:
                    st.multiselect(
                        "Select Storyboard Shots",
                        options=shot_ids,
                        default=[],
                        key="custom_shots",
                        help="CUSTOM일 때만 shot을 선택합니다.",
                    )
                else:
                    st.warning("CSV에서 추출된 shot id가 없습니다.")
    else:
        st.info("CSV 파일을 업로드하면 Parsed Storyboard Data Preview와 Shot Selection Control이 표시됩니다.")


# =========================
# Step 2. Character Identity Generation
# =========================
with tab2:
    st.header("Step 2. Character Identity Generation")

    preview_col, settings_col = st.columns([1.45, 1.25], gap="large")

    with preview_col:
        st.subheader("Character Identity Preview")

        face_preview_col1, face_preview_col2 = st.columns(2, gap="medium")

        with face_preview_col1:
            st.markdown("#### Image 1 - Boy")

            if "face_result_image_c1" in st.session_state:
                st.image(
                    st.session_state["face_result_image_c1"],
                    caption="Image 1 - Boy Face Reference",
                    use_container_width=True,
                )
            else:
                render_empty_preview_box(
                    "Image 1 - Boy face reference will appear here.",
                    520,
                )

        with face_preview_col2:
            st.markdown("#### Image 2 - Girl")

            if "face_result_image_c2" in st.session_state:
                st.image(
                    st.session_state["face_result_image_c2"],
                    caption="Image 2 - Girl Face Reference",
                    use_container_width=True,
                )
            else:
                render_empty_preview_box(
                    "Image 2 - Girl face reference will appear here.",
                    520,
                )

    with settings_col:
        st.subheader("Target Character Control")

        st.radio(
            "character_filter",
            options=["Image 1 - Boy", "Image 2 - Girl"],
            index=1,
            horizontal=True,
            key="character_filter_label",
            help="UI에서는 Image 1 / Image 2로 표시하고, workflow에는 C1 / C2로 전달합니다.",
        )

        with st.expander("Identity Attribute Controls", expanded=True):
            with st.container(border=True):
                st.markdown("###### Core Identity")

                basic_col1, basic_col2 = st.columns(2)

                with basic_col1:
                    st.slider(
                        "Age",
                        min_value=1,
                        max_value=100,
                        value=9,
                        step=1,
                        key="age",
                    )

                with basic_col2:
                    st.selectbox(
                        "Nationality",
                        options=[
                            "South Korean",
                            "Korean",
                            "East Asian",
                            "Japanese",
                            "Chinese",
                        ],
                        index=0,
                        key="nationality",
                    )

            with st.container(border=True):
                st.markdown("###### Face")

                face_col1, face_col2, face_col3 = st.columns(3)

                with face_col1:
                    st.selectbox(
                        "Body Type",
                        options=["Slim", "Average", "Athletic", "Curvy", "Heavy"],
                        index=0,
                        key="body_type",
                    )

                with face_col2:
                    st.selectbox(
                        "Face Shape",
                        options=[
                            "Oval",
                            "Round",
                            "Square",
                            "Square with Soft Jaw",
                            "Heart",
                            "Long",
                            "Diamond",
                        ],
                        index=3,
                        key="face_shape",
                    )

                with face_col3:
                    st.selectbox(
                        "Expression",
                        options=[
                            "Neutral",
                            "Curious",
                            "Gentle Smile",
                            "Serious",
                            "Sad",
                            "Surprised",
                            "Calm",
                        ],
                        index=1,
                        key="facial_expression",
                    )

            with st.container(border=True):
                st.markdown("###### Eyes / Lips")

                eye_col1, eye_col2 = st.columns(2)

                with eye_col1:
                    st.selectbox(
                        "Eyes Color",
                        options=[
                            "Brown",
                            "Dark Brown",
                            "Black",
                            "Hazel",
                            "Blue",
                            "Green",
                        ],
                        index=0,
                        key="eyes_color",
                    )

                    st.selectbox(
                        "Eyes Shape",
                        options=[
                            "Double Eyelid Eyes Shape",
                            "Monolid Eyes Shape",
                            "Almond Eyes",
                            "Round Eyes",
                            "Sharp Eyes",
                        ],
                        index=0,
                        key="eyes_shape",
                    )

                with eye_col2:
                    st.selectbox(
                        "Lips Color",
                        options=[
                            "Peach Lips",
                            "Pink Lips",
                            "Natural Lips",
                            "Pale Lips",
                            "Rose Lips",
                        ],
                        index=0,
                        key="lips_color",
                    )

                    st.selectbox(
                        "Lips Shape",
                        options=["Thin Lips", "Full Lips", "Small Lips", "Soft Lips"],
                        index=0,
                        key="lips_shape",
                    )

            with st.container(border=True):
                st.markdown("###### Hair")

                hair_col1, hair_col2, hair_col3 = st.columns(3)

                with hair_col1:
                    st.selectbox(
                        "Hair Style",
                        options=[
                            "Bob",
                            "Straight",
                            "Wavy",
                            "Braided Pigtails",
                            "Ponytail",
                            "Short Hair",
                            "Long Hair",
                        ],
                        index=0,
                        key="hair_style",
                    )

                with hair_col2:
                    st.selectbox(
                        "Hair Color",
                        options=[
                            "Chestnut",
                            "Black",
                            "Dark Brown",
                            "Brown",
                            "Blonde",
                            "Auburn",
                        ],
                        index=0,
                        key="hair_color",
                    )

                with hair_col3:
                    st.selectbox(
                        "Hair Length",
                        options=["-", "Short", "Medium", "Long", "Shoulder Length"],
                        index=0,
                        key="hair_length",
                    )

        with st.expander("Fine-Grained Appearance Attributes", expanded=False):
            skin_keys = list(SKIN_DEFAULTS.keys())
            skin_cols = st.columns(3)

            for i, key in enumerate(skin_keys):
                with skin_cols[i % 3]:
                    default_checked = SKIN_DEFAULTS[key] > 0

                    st.checkbox(
                        key,
                        value=default_checked,
                        key=f"skin_{key}",
                    )

        st.divider()

        generate_clicked = st.button(
            "Generate Character Identity",
            type="primary",
            use_container_width=True,
        )

        if generate_clicked:
            csv_text = st.session_state.get("csv_text", "")

            if not csv_text.strip():
                st.error("먼저 Step 1에서 CSV 파일을 업로드해야 합니다.")

            elif (
                st.session_state.get("shot_filter_mode", "ALL") == "CUSTOM"
                and len(st.session_state.get("custom_shots", [])) == 0
            ):
                st.error("shot_filter가 CUSTOM이면 최소 1개 이상의 shot을 선택해야 합니다.")

            else:
                config = build_face_ui_config()

                st.success("Face branch UI 입력값이 정상적으로 수집되었습니다.")
                st.subheader("Collected Character Identity Config")
                st.json(config)


# =========================
# Step 3. Full-Body Reference Generation
# =========================
with tab3:
    st.header("Step 3. Full-Body Reference Generation")

    initialize_body_prompts()

    preview_col, settings_col = st.columns([1.45, 1.25], gap="large")

    with preview_col:
        st.subheader("Full-Body Reference Preview")

        body_preview_col1, body_preview_col2 = st.columns(2, gap="medium")

        with body_preview_col1:
            st.markdown("#### Image 1 - Boy")

            if "body_result_image_c1" in st.session_state:
                st.image(
                    st.session_state["body_result_image_c1"],
                    caption="Image 1 - Boy Body Reference",
                    use_container_width=True,
                )
            else:
                render_empty_preview_box(
                    "Image 1 - Boy body reference will appear here.",
                    520,
                )

        with body_preview_col2:
            st.markdown("#### Image 2 - Girl")

            if "body_result_image_c2" in st.session_state:
                st.image(
                    st.session_state["body_result_image_c2"],
                    caption="Image 2 - Girl Body Reference",
                    use_container_width=True,
                )
            else:
                render_empty_preview_box(
                    "Image 2 - Girl body reference will appear here.",
                    520,
                )

    with settings_col:
        st.subheader("Reference Generation Control")

        st.radio(
            "body_character_filter",
            options=["Image 1 - Boy", "Image 2 - Girl"],
            index=0,
            horizontal=True,
            key="body_character_filter_label",
            help="UI에서는 Image 1 / Image 2로 표시하고, workflow에는 C1 / C2로 전달합니다.",
        )

        st.divider()

        st.markdown("### Full-Body Prompt Editor")

        selected_body_target = st.session_state.get(
            "body_character_filter_label",
            "Image 1 - Boy",
        )

        if selected_body_target == "Image 1 - Boy":
            st.text_area(
                "Image 1 - Boy Body Prompt",
                key="body_prompt_c1",
                height=260,
                placeholder=BODY_PROMPT_PLACEHOLDER,
                help="Image 1 - Boy의 전신 reference 생성을 위한 프롬프트입니다. 사용자가 직접 수정할 수 있습니다.",
            )

        else:
            st.text_area(
                "Image 2 - Girl Body Prompt",
                key="body_prompt_c2",
                height=260,
                placeholder=BODY_PROMPT_PLACEHOLDER,
                help="Image 2 - Girl의 전신 reference 생성을 위한 프롬프트입니다. 사용자가 직접 수정할 수 있습니다.",
            )

        with st.expander("Reference Prompt Guidelines", expanded=False):
            st.markdown(
                """
                - 얼굴 reference와 같은 인물로 보이도록 identity 유지 문장을 포함하는 것이 좋습니다.
                - 전신이 모두 보이도록 `full-body`, `head to toe`, `entire body visible` 표현을 포함하세요.
                - 의상은 상의, 하의, 양말, 신발까지 구체적으로 작성하는 것이 좋습니다.
                - 이후 Scene Generation에서 reference로 쓰기 좋게 `clean background`를 유지하는 것이 좋습니다.
                - 복잡한 포즈나 강한 카메라 앵글은 전신 reference 생성 단계에서는 피하는 것이 좋습니다.
                """
            )

        st.divider()

        generate_body_clicked = st.button(
            "Generate Full-Body Reference",
            type="primary",
            use_container_width=True,
        )

        if generate_body_clicked:
            csv_text = st.session_state.get("csv_text", "")

            if not csv_text.strip():
                st.error("먼저 Step 1에서 CSV 파일을 업로드해야 합니다.")

            elif (
                st.session_state.get("shot_filter_mode", "ALL") == "CUSTOM"
                and len(st.session_state.get("custom_shots", [])) == 0
            ):
                st.error("shot_filter가 CUSTOM이면 최소 1개 이상의 shot을 선택해야 합니다.")

            else:
                body_config = build_body_ui_config()

                st.success("Body branch UI 입력값이 정상적으로 수집되었습니다.")
                st.subheader("Collected Full-Body Reference Config")
                st.json(body_config)


# =========================
# Step 4. Reference-Guided Scene Generation
# =========================
with tab4:
    st.header("Step 4. Reference-Guided Scene Generation")

    boy_candidates = get_body_reference_candidates("c1")
    girl_candidates = get_body_reference_candidates("c2")

    sync_scene_reference_selection("scene_boy_reference_label", boy_candidates)
    sync_scene_reference_selection("scene_girl_reference_label", girl_candidates)

    preview_col, settings_col = st.columns([1.45, 1.25], gap="large")

    with preview_col:
        st.subheader("Generated Storyboard Preview")

        selected_shot_df = get_selected_shot_dataframe()

        if selected_shot_df.empty:
            st.caption("Selected Storyboard Context: None")
        else:
            st.caption(f"Selected Scene Count: {len(selected_shot_df)}")

        if "scene_result_image" in st.session_state:
            st.image(
                st.session_state["scene_result_image"],
                caption="Generated Storyboard Scene",
                use_container_width=True,
            )
        else:
            render_empty_preview_box(
                "Generated storyboard scene will appear here.",
                560,
            )

    with settings_col:
        st.subheader("Scene Generation Control")

        with st.container(border=True):
            st.markdown("###### Selected Storyboard Context")

            selected_shot_df = get_selected_shot_dataframe()
            shot_filter_mode = st.session_state.get("shot_filter_mode", "ALL")
            custom_shots = st.session_state.get("custom_shots", [])

            if selected_shot_df.empty:
                st.warning("표시할 scene 정보가 없습니다. Step 1에서 CSV와 shot 선택을 확인하세요.")
            else:
                if shot_filter_mode == "ALL":
                    st.caption(f"Shot Filter: ALL / {len(selected_shot_df)} scene(s)")
                elif custom_shots:
                    st.caption(f"Shot Filter: CUSTOM / {', '.join(custom_shots)}")
                else:
                    st.caption("Shot Filter: CUSTOM / No shot selected")

                st.dataframe(
                    selected_shot_df,
                    use_container_width=True,
                    hide_index=True,
                )

        st.divider()

        st.markdown("### Character Reference Inputs")

        st.markdown("##### Image 1 - Boy Body Reference")

        if boy_candidates:
            st.selectbox(
                "Select Image 1 - Boy Body Reference",
                options=[item["label"] for item in boy_candidates],
                key="scene_boy_reference_label",
                label_visibility="collapsed",
            )

            selected_boy = get_selected_candidate(
                boy_candidates,
                st.session_state.get("scene_boy_reference_label", ""),
            )

            if selected_boy and selected_boy.get("image") is not None:
                st.image(
                    selected_boy["image"],
                    caption=selected_boy["label"],
                    use_container_width=True,
                )
            else:
                render_empty_preview_box(
                    "Selected boy body reference preview is not available.",
                    220,
                )

        else:
            st.warning("Step 3에서 Image 1 - Boy body reference를 먼저 생성해야 합니다.")

        st.divider()

        st.markdown("##### Image 2 - Girl Body Reference")

        if girl_candidates:
            st.selectbox(
                "Select Image 2 - Girl Body Reference",
                options=[item["label"] for item in girl_candidates],
                key="scene_girl_reference_label",
                label_visibility="collapsed",
            )

            selected_girl = get_selected_candidate(
                girl_candidates,
                st.session_state.get("scene_girl_reference_label", ""),
            )

            if selected_girl and selected_girl.get("image") is not None:
                st.image(
                    selected_girl["image"],
                    caption=selected_girl["label"],
                    use_container_width=True,
                )
            else:
                render_empty_preview_box(
                    "Selected girl body reference preview is not available.",
                    220,
                )

        else:
            st.warning("Step 3에서 Image 2 - Girl body reference를 먼저 생성해야 합니다.")

        st.divider()

        generate_scene_clicked = st.button(
            "Generate Storyboard Scene",
            type="primary",
            use_container_width=True,
        )

        if generate_scene_clicked:
            csv_text = st.session_state.get("csv_text", "")

            if not csv_text.strip():
                st.error("먼저 Step 1에서 CSV 파일을 업로드해야 합니다.")

            elif (
                st.session_state.get("shot_filter_mode", "ALL") == "CUSTOM"
                and len(st.session_state.get("custom_shots", [])) == 0
            ):
                st.error("shot_filter가 CUSTOM이면 최소 1개 이상의 shot을 선택해야 합니다.")

            elif not boy_candidates:
                st.error("Image 1 - Boy body reference 후보가 없습니다. 먼저 Step 3을 진행하세요.")

            elif not girl_candidates:
                st.error("Image 2 - Girl body reference 후보가 없습니다. 먼저 Step 3을 진행하세요.")

            else:
                scene_config = build_scene_ui_config()

                st.success("Scene branch UI 입력값이 정상적으로 수집되었습니다.")
                st.subheader("Collected Scene Generation Config")
                st.json(scene_config)

# # =========================
# # Step 5. Camera Angle Refinement
# # =========================
# with tab5:
#     st.header("Step 5. Camera Angle Refinement")

#     scene_candidates = get_scene_result_candidates()
#     sync_scene_reference_selection("camera_input_scene_label", scene_candidates)

#     preview_col, settings_col = st.columns([1.45, 1.25], gap="large")

#     with preview_col:
#         st.subheader("Camera Refinement Preview")

#         source_col, refined_col = st.columns(2, gap="medium")

#         with source_col:
#             st.markdown("#### Input Scene")

#             selected_input_scene = get_selected_candidate(
#                 scene_candidates,
#                 st.session_state.get("camera_input_scene_label", ""),
#             )

#             if selected_input_scene and selected_input_scene.get("image") is not None:
#                 st.image(
#                     selected_input_scene["image"],
#                     caption=selected_input_scene["label"],
#                     use_container_width=True,
#                 )
#             else:
#                 render_empty_preview_box(
#                     "A generated scene from Step 4 will appear here.",
#                     520,
#                 )

#         with refined_col:
#             st.markdown("#### Refined Scene")

#             if "camera_refined_result_image" in st.session_state:
#                 st.image(
#                     st.session_state["camera_refined_result_image"],
#                     caption="Camera-Refined Storyboard Scene",
#                     use_container_width=True,
#                 )
#             else:
#                 render_empty_preview_box(
#                     "The camera-refined scene will appear here.",
#                     520,
#                 )

#     with settings_col:
#         st.subheader("Camera Refinement Control")

#         with st.container(border=True):
#             st.markdown("###### Source Scene Input")

#             if scene_candidates:
#                 st.selectbox(
#                     "Select Input Scene",
#                     options=[item["label"] for item in scene_candidates],
#                     key="camera_input_scene_label",
#                 )

#                 selected_input_scene = get_selected_candidate(
#                     scene_candidates,
#                     st.session_state.get("camera_input_scene_label", ""),
#                 )

#                 if selected_input_scene:
#                     filename = selected_input_scene.get("filename", "")
#                     if filename:
#                         st.caption(f"Selected File: {filename}")
#             else:
#                 st.warning("Step 4에서 생성된 scene 이미지가 없습니다. 먼저 Scene Generation을 진행하세요.")

#         st.divider()

#         with st.container(border=True):
#             st.markdown("###### Camera Angle Control")

#             angle_col1, angle_col2 = st.columns(2)

#             with angle_col1:
#                 st.slider(
#                     "Horizontal Angle",
#                     min_value=-180,
#                     max_value=180,
#                     value=0,
#                     step=1,
#                     key="camera_horizontal_angle",
#                     help="좌우 시점 변화를 제어합니다.",
#                 )

#                 st.slider(
#                     "Vertical Angle",
#                     min_value=-90,
#                     max_value=90,
#                     value=0,
#                     step=1,
#                     key="camera_vertical_angle",
#                     help="상하 시점 변화를 제어합니다.",
#                 )

#             with angle_col2:
#                 st.slider(
#                     "Zoom",
#                     min_value=0,
#                     max_value=10,
#                     value=5,
#                     step=1,
#                     key="camera_zoom",
#                     help="카메라 줌 강도를 제어합니다.",
#                 )

#                 st.checkbox(
#                     "Use Default Angle Prompts",
#                     value=True,
#                     key="camera_default_prompts",
#                     help="Qwen Multi-Angle Camera의 기본 프롬프트를 사용합니다.",
#                 )

#                 st.checkbox(
#                     "Enable Camera View Mode",
#                     value=False,
#                     key="camera_view",
#                     help="카메라 관점 중심의 view 해석을 활성화합니다.",
#                 )

#         st.divider()

#         with st.container(border=True):
#             st.markdown("###### Prompt Source Control")

#             st.radio(
#                 "Prompt Source",
#                 options=["Structured Scene Prompt", "Qwen Multi-Angle Prompt"],
#                 index=1,
#                 key="camera_prompt_source",
#                 help=(
#                     "Structured Scene Prompt는 기존 scene description을 사용하고, "
#                     "Qwen Multi-Angle Prompt는 앵글 제어에 맞춰 생성된 프롬프트를 사용합니다."
#                 ),
#             )

#             if st.session_state.get("camera_prompt_source") == "Structured Scene Prompt":
#                 st.caption("TwoWaySwitch Selection: 1 (ScenePromptBuilder output)")
#             else:
#                 st.caption("TwoWaySwitch Selection: 2 (Qwen Multi-Angle Camera output)")

#         with st.expander("Camera Refinement Guide", expanded=False):
#             st.markdown(
#                 """
#                 - Step 5는 Step 4에서 생성된 장면을 입력으로 받아 카메라 앵글만 다시 조정하는 단계입니다.
#                 - Horizontal Angle은 좌/우 시점 변화를, Vertical Angle은 상/하 시점 변화를 의미합니다.
#                 - Zoom은 인물 및 장면의 프레이밍 강도를 조정합니다.
#                 - Prompt Source를 Qwen Multi-Angle Prompt로 두면, 앵글 제어에 최적화된 프롬프트를 사용할 수 있습니다.
#                 - Structured Scene Prompt는 기존 shot description의 의미를 최대한 유지하고 싶을 때 적합합니다.
#                 """
#             )

#         st.divider()

#         generate_camera_clicked = st.button(
#             "Generate Camera-Refined Scene",
#             type="primary",
#             use_container_width=True,
#         )

#         if generate_camera_clicked:
#             if not scene_candidates:
#                 st.error("Step 4 결과 이미지가 없습니다. 먼저 Scene Generation을 진행하세요.")

#             elif (
#                 st.session_state.get("camera_prompt_source") == "Structured Scene Prompt"
#                 and get_selected_shot_dataframe().empty
#             ):
#                 st.error("Structured Scene Prompt를 사용하려면 Step 1의 shot 데이터가 필요합니다.")

#             else:
#                 camera_config = build_camera_refinement_ui_config()

#                 st.success("Camera refinement UI 입력값이 정상적으로 수집되었습니다.")
#                 st.subheader("Collected Camera Refinement Config")
#                 st.json(camera_config)

# =========================
# Step 5. Camera Angle Refinement
# =========================
with tab5:
    st.header("Step 5. Camera Angle Refinement")

    scene_candidates = get_scene_result_candidates()
    sync_scene_reference_selection("camera_input_scene_label", scene_candidates)

    preview_col, settings_col = st.columns([1.45, 1.25], gap="large")

    with preview_col:
        st.subheader("Camera Refinement Preview")

        source_col, refined_col = st.columns(2, gap="medium")

        with source_col:
            st.markdown("#### Input Scene")

            selected_input_scene = get_selected_candidate(
                scene_candidates,
                st.session_state.get("camera_input_scene_label", ""),
            )

            if selected_input_scene and selected_input_scene.get("image") is not None:
                st.image(
                    selected_input_scene["image"],
                    caption=selected_input_scene["label"],
                    use_container_width=True,
                )
            else:
                render_empty_preview_box(
                    "A generated scene from Step 4 will appear here.",
                    520,
                )

        with refined_col:
            st.markdown("#### Refined Scene")

            if "camera_refined_result_image" in st.session_state:
                st.image(
                    st.session_state["camera_refined_result_image"],
                    caption="Camera-Refined Storyboard Scene",
                    use_container_width=True,
                )
            else:
                render_empty_preview_box(
                    "The camera-refined scene will appear here.",
                    520,
                )

    with settings_col:
        st.subheader("Camera Refinement Control")

        with st.container(border=True):
            st.markdown("###### Source Scene Input")

            if scene_candidates:
                st.selectbox(
                    "Select Input Scene",
                    options=[item["label"] for item in scene_candidates],
                    key="camera_input_scene_label",
                )

                selected_input_scene = get_selected_candidate(
                    scene_candidates,
                    st.session_state.get("camera_input_scene_label", ""),
                )

                if selected_input_scene:
                    filename = selected_input_scene.get("filename", "")
                    if filename:
                        st.caption(f"Selected File: {filename}")
            else:
                st.warning("Step 4에서 생성된 scene 이미지가 없습니다. 먼저 Scene Generation을 진행하세요.")

        st.divider()

        with st.container(border=True):
            st.markdown("###### Prompt Source Control")

            st.radio(
                "Prompt Source",
                options=[
                    "Preserve Original Scene Prompt",
                    "Use Camera Angle Prompt",
                ],
                index=1,
                key="camera_prompt_source",
                help=(
                    "Preserve Original Scene Prompt는 기존 scene description을 유지하고, "
                    "Use Camera Angle Prompt는 Qwen Multi-Angle Camera의 앵글 제어 프롬프트를 사용합니다."
                ),
            )

            if st.session_state.get("camera_prompt_source") == "Preserve Original Scene Prompt":
                st.caption("TwoWaySwitch Selection: 1 (ScenePromptBuilder output)")
            else:
                st.caption("TwoWaySwitch Selection: 2 (Qwen Multi-Angle Camera output)")

        if st.session_state.get("camera_prompt_source") == "Use Camera Angle Prompt":
            st.divider()

            with st.container(border=True):
                st.markdown("###### Camera Angle Control")

                angle_col1, angle_col2 = st.columns(2)

                with angle_col1:
                    st.slider(
                        "Horizontal Angle",
                        min_value=-180,
                        max_value=180,
                        value=0,
                        step=1,
                        key="camera_horizontal_angle",
                        help="좌우 시점 변화를 제어합니다.",
                    )

                    st.slider(
                        "Vertical Angle",
                        min_value=-90,
                        max_value=90,
                        value=0,
                        step=1,
                        key="camera_vertical_angle",
                        help="상하 시점 변화를 제어합니다.",
                    )

                with angle_col2:
                    st.slider(
                        "Zoom",
                        min_value=0,
                        max_value=10,
                        value=5,
                        step=1,
                        key="camera_zoom",
                        help="카메라 줌 강도를 제어합니다.",
                    )

                    st.checkbox(
                        "Use Default Angle Prompts",
                        value=True,
                        key="camera_default_prompts",
                        help="Qwen Multi-Angle Camera의 기본 프롬프트를 사용합니다.",
                    )

                    st.checkbox(
                        "Enable Camera View Mode",
                        value=False,
                        key="camera_view",
                        help="카메라 관점 중심의 view 해석을 활성화합니다.",
                    )

        else:
            st.info(
                "Camera Angle Control is available only when "
                "'Use Camera Angle Prompt' is selected."
            )

        with st.expander("Camera Refinement Guide", expanded=False):
            st.markdown(
                """
                - Step 5는 Step 4에서 생성된 장면을 입력으로 받아 카메라 앵글을 다시 조정하는 단계입니다.
                - Preserve Original Scene Prompt는 기존 storyboard scene description을 유지하는 모드입니다.
                - Use Camera Angle Prompt는 Qwen Multi-Angle Camera가 생성한 앵글 제어 프롬프트를 사용하는 모드입니다.
                - Horizontal Angle은 좌/우 시점 변화를, Vertical Angle은 상/하 시점 변화를 의미합니다.
                - Zoom은 인물 및 장면의 프레이밍 강도를 조정합니다.
                """
            )

        st.divider()

        generate_camera_clicked = st.button(
            "Generate Camera-Refined Scene",
            type="primary",
            use_container_width=True,
        )

        if generate_camera_clicked:
            if not scene_candidates:
                st.error("Step 4 결과 이미지가 없습니다. 먼저 Scene Generation을 진행하세요.")

            elif (
                st.session_state.get("camera_prompt_source") == "Preserve Original Scene Prompt"
                and get_selected_shot_dataframe().empty
            ):
                st.error("Preserve Original Scene Prompt를 사용하려면 Step 1의 shot 데이터가 필요합니다.")

            else:
                camera_config = build_camera_refinement_ui_config()

                st.success("Camera refinement UI 입력값이 정상적으로 수집되었습니다.")
                st.subheader("Collected Camera Refinement Config")
                st.json(camera_config)




# import csv
# import io
# import pandas as pd
# import streamlit as st


# # =========================
# # Fixed Values
# # =========================
# FIXED_BASE_BACKGROUND_CLOTHING_PROMPT = "gray background, white t-shirt"

# BODY_PROMPT_PLACEHOLDER = (
#     "Example: white shirt, beige shorts, white socks, black shoes, "
#     "full-body, standing pose, front view, clean gray background"
# )

# SKIN_DEFAULTS = {
#     "natural_skin": 0.74,
#     "bare_face": 0.75,
#     "washed_face": 0.0,
#     "dried_face": 0.0,
#     "skin_details": 0.3,
#     "skin_pores": 0.1,
#     "dimples": 0.0,
#     "wrinkles": 0.0,
#     "freckles": 0.0,
#     "moles": 0.0,
#     "skin_imperfections": 0.0,
#     "skin_acne": 0.0,
#     "tanned_skin": 0.0,
#     "eyes_details": 1.01,
#     "iris_details": 0.0,
#     "circular_iris": 0.0,
#     "circular_pupil": 0.0,
# }

# BASE_CHARACTER_CHECK_DEFAULTS = {
#     "androgynous": 1.0,
#     "ugly": 1.0,
#     "ordinary_face": 0.25,
#     "facial_asymmetry": 1.0,
#     "disheveled": 1.0,
# }


# # =========================
# # Helper Functions
# # =========================
# def decode_uploaded_file(uploaded_file):
#     raw = uploaded_file.getvalue()

#     for encoding in ["utf-8-sig", "utf-8", "cp949"]:
#         try:
#             return raw.decode(encoding)
#         except Exception:
#             pass

#     return raw.decode("utf-8", errors="ignore")


# def extract_shot_ids_from_csv(csv_text):
#     if not csv_text.strip():
#         return []

#     shot_ids = []
#     reader = csv.reader(io.StringIO(csv_text.strip()))

#     for row in reader:
#         if not row:
#             continue

#         first_value = row[0].strip()

#         if not first_value:
#             continue

#         if first_value.lower() in {"shot", "shot_id", "shot id", "id"}:
#             continue

#         if first_value not in shot_ids:
#             shot_ids.append(first_value)

#     return shot_ids


# def read_csv_as_dataframe(csv_text):
#     if not csv_text.strip():
#         return pd.DataFrame()

#     try:
#         return pd.read_csv(io.StringIO(csv_text))
#     except Exception:
#         return pd.DataFrame()


# def get_shot_id_column(df):
#     if df.empty:
#         return None

#     candidates = [
#         "shot",
#         "shot_id",
#         "shot id",
#         "id",
#         "Shot",
#         "Shot ID",
#         "Shot_ID",
#     ]

#     for col in df.columns:
#         if str(col).strip() in candidates:
#             return col

#     return df.columns[0]


# def get_selected_shot_dataframe():
#     csv_text = st.session_state.get("csv_text", "")
#     df = read_csv_as_dataframe(csv_text)

#     if df.empty:
#         return pd.DataFrame()

#     shot_col = get_shot_id_column(df)

#     if shot_col is None:
#         return df

#     shot_filter_mode = st.session_state.get("shot_filter_mode", "ALL")
#     custom_shots = st.session_state.get("custom_shots", [])

#     if shot_filter_mode == "ALL":
#         return df

#     if not custom_shots:
#         return pd.DataFrame()

#     return df[df[shot_col].astype(str).isin([str(x) for x in custom_shots])]


# def character_label_to_value(label):
#     mapping = {
#         "Image 1 - Boy": "C1",
#         "Image 2 - Girl": "C2",
#     }
#     return mapping.get(label, "C2")


# def body_character_label_to_value(label):
#     mapping = {
#         "Image 1 - Boy": "C1",
#         "Image 2 - Girl": "C2",
#     }
#     return mapping.get(label, "C1")


# def get_checkbox_value(key, on_value):
#     return on_value if st.session_state.get(key, False) else 0.0


# def initialize_body_prompts():
#     if "body_prompt_c1" not in st.session_state:
#         st.session_state["body_prompt_c1"] = ""

#     if "body_prompt_c2" not in st.session_state:
#         st.session_state["body_prompt_c2"] = ""


# def get_scene_shot_filter_config():
#     shot_filter_mode = st.session_state.get("shot_filter_mode", "ALL")
#     custom_shots = st.session_state.get("custom_shots", [])

#     if shot_filter_mode == "ALL":
#         return "ALL", ""

#     return "CUSTOM", ", ".join(custom_shots)


# def get_body_reference_candidates(character_code):
#     """
#     character_code: 'c1' or 'c2'

#     Step3에서 여러 body 후보를 저장해둔 경우:
#     st.session_state["body_candidates_c1"] = [
#         {"label": "Boy Body 1", "image": ..., "filename": "..."},
#         {"label": "Boy Body 2", "image": ..., "filename": "..."},
#     ]

#     후보 리스트가 없으면 body_result_image_c1 / body_result_image_c2를 단일 후보로 fallback.
#     """

#     candidates_key = f"body_candidates_{character_code}"
#     candidates = st.session_state.get(candidates_key, [])

#     normalized = []

#     for i, item in enumerate(candidates, start=1):
#         if not isinstance(item, dict):
#             continue

#         normalized.append(
#             {
#                 "label": item.get(
#                     "label",
#                     f"{'Boy' if character_code == 'c1' else 'Girl'} Body {i}",
#                 ),
#                 "image": item.get("image"),
#                 "filename": item.get("filename", ""),
#             }
#         )

#     fallback_image = st.session_state.get(f"body_result_image_{character_code}")
#     fallback_filename = st.session_state.get(
#         f"body_result_filename_{character_code}",
#         "",
#     )

#     if not normalized and fallback_image is not None:
#         normalized.append(
#             {
#                 "label": f"{'Boy' if character_code == 'c1' else 'Girl'} Body 1",
#                 "image": fallback_image,
#                 "filename": fallback_filename,
#             }
#         )

#     return normalized


# def sync_scene_reference_selection(session_key, candidates):
#     labels = [item["label"] for item in candidates]

#     if not labels:
#         st.session_state[session_key] = ""
#         return

#     if st.session_state.get(session_key) not in labels:
#         st.session_state[session_key] = labels[0]


# def get_selected_candidate(candidates, selected_label):
#     for item in candidates:
#         if item["label"] == selected_label:
#             return item

#     return None


# def build_face_ui_config():
#     shot_filter_mode = st.session_state.get("shot_filter_mode", "ALL")
#     custom_shots = st.session_state.get("custom_shots", [])

#     if shot_filter_mode == "ALL":
#         shot_filter = "ALL"
#         custom_shot_ids = ""
#     else:
#         shot_filter = "CUSTOM"
#         custom_shot_ids = ", ".join(custom_shots)

#     return {
#         "csvstoryboardparser": {
#             "input_mode": "text",
#             "csv_file": "CUSTOM",
#             "csv_text": st.session_state.get("csv_text", ""),
#             "shot_filter": shot_filter,
#             "custom_shot_ids": custom_shot_ids,
#         },
#         "character_registry_parser": {
#             "character_filter": character_label_to_value(
#                 st.session_state.get("character_filter_label", "Image 2 - Girl")
#             ),
#             "custom_character_id": "",
#             "age": st.session_state.get("age", 9),
#             "include_character_id": "false",
#         },
#         "base_background_clothing_prompt": {
#             "text": FIXED_BASE_BACKGROUND_CLOTHING_PROMPT,
#         },
#         "portrait_master_base_character": {
#             "shot": "Head and shoulders portrait",
#             "shot_weight": 2,
#             "gender": "Woman",
#             "age": "-",
#             "nationality_1": st.session_state.get("nationality", "South Korean"),
#             "nationality_2": "-",
#             "nationality_mix": 0,
#             "body_type": st.session_state.get("body_type", "Slim"),
#             "body_type_weight": 0,
#             "breast_size": "-",
#             "breast_size_weight": 0,
#             "butt_size": "-",
#             "butt_size_weight": 0,
#             "eyes_color": st.session_state.get("eyes_color", "Brown"),
#             "eyes_shape": st.session_state.get(
#                 "eyes_shape",
#                 "Double Eyelid Eyes Shape",
#             ),
#             "lips_color": st.session_state.get("lips_color", "Peach Lips"),
#             "lips_shape": st.session_state.get("lips_shape", "Thin Lips"),
#             "facial_expression": st.session_state.get(
#                 "facial_expression",
#                 "Curious",
#             ),
#             "facial_expression_weight": 0,
#             "face_shape": st.session_state.get("face_shape", "Square with Soft Jaw"),
#             "face_shape_weight": 0,
#             "hair_style": st.session_state.get("hair_style", "Bob"),
#             "hair_color": st.session_state.get("hair_color", "Chestnut"),
#             "hair_length": st.session_state.get("hair_length", "-"),
#             "androgynous": 0,
#             "ugly": 0,
#             "ordinary_face": 0.25,
#             "facial_asymmetry": 0,
#             "disheveled": 0,
#             "beard": "-",
#             "beard_color": "-",
#         },
#         "portrait_master_skin_details": {
#             key: default_value
#             if st.session_state.get(f"skin_{key}", False)
#             else 0.0
#             for key, default_value in SKIN_DEFAULTS.items()
#         },
#     }


# def build_body_ui_config():
#     character_filter_label = st.session_state.get(
#         "body_character_filter_label",
#         "Image 1 - Boy",
#     )
#     character_filter = body_character_label_to_value(character_filter_label)

#     if character_filter == "C1":
#         body_prompt = st.session_state.get("body_prompt_c1", "")
#         label = "Image 1 - Boy"
#     else:
#         body_prompt = st.session_state.get("body_prompt_c2", "")
#         label = "Image 2 - Girl"

#     return {
#         "body_generation": {
#             "character_filter": character_filter,
#             "label": label,
#             "body_prompt": body_prompt,
#         }
#     }


# def build_scene_ui_config():
#     shot_filter, custom_shot_ids = get_scene_shot_filter_config()

#     boy_candidates = get_body_reference_candidates("c1")
#     girl_candidates = get_body_reference_candidates("c2")

#     selected_boy = get_selected_candidate(
#         boy_candidates,
#         st.session_state.get("scene_boy_reference_label", ""),
#     )
#     selected_girl = get_selected_candidate(
#         girl_candidates,
#         st.session_state.get("scene_girl_reference_label", ""),
#     )

#     selected_shot_df = get_selected_shot_dataframe()

#     return {
#         "scene_generation": {
#             "shot_filter": shot_filter,
#             "custom_shot_ids": custom_shot_ids,
#             "selected_shot_count": len(selected_shot_df),
#             "selected_shot_data": selected_shot_df.to_dict(orient="records"),
#             "reference_images": {
#                 "image_1_boy_body": {
#                     "label": selected_boy["label"] if selected_boy else "",
#                     "filename": selected_boy.get("filename", "") if selected_boy else "",
#                 },
#                 "image_2_girl_body": {
#                     "label": selected_girl["label"] if selected_girl else "",
#                     "filename": selected_girl.get("filename", "") if selected_girl else "",
#                 },
#             },
#         }
#     }


# def render_empty_preview_box(message, height=520):
#     st.markdown(
#         f"""
#         <div style="
#             border: 1px dashed #999;
#             border-radius: 12px;
#             height: {height}px;
#             display: flex;
#             align-items: center;
#             justify-content: center;
#             color: #777;
#             font-size: 15px;
#             text-align: center;
#             padding: 20px;
#         ">
#             {message}
#         </div>
#         """,
#         unsafe_allow_html=True,
#     )


# # =========================
# # Page Config
# # =========================
# st.set_page_config(
#     page_title="AI Storyboard Pipeline",
#     page_icon="🎬",
#     layout="wide",
# )

# st.title("🎬 AI Storyboard Generation Pipeline")
# st.caption("A ComfyUI-based multi-stage generation system for character-consistent cinematic storyboard creation")


# # =========================
# # Tabs
# # =========================
# tab1, tab2, tab3, tab4 = st.tabs(
#     [
#         "Step 1. Storyboard Data",
#         "Step 2. Character Identity",
#         "Step 3. Body Reference",
#         "Step 4. Reference-Guided Scene Generation",
#     ]
# )


# # =========================
# # Step 1. Storyboard Data Parsing
# # =========================
# with tab1:
#     st.header("Step 1. Storyboard Data Parsing")

#     uploaded_csv = st.file_uploader(
#         "Upload Storyboard CSV",
#         type=["csv"],
#         help="CSV 파일을 업로드하면 내부적으로 텍스트로 읽어서 workflow에 전달합니다.",
#     )

#     if uploaded_csv is not None:
#         csv_text = decode_uploaded_file(uploaded_csv)
#         st.session_state["csv_text"] = csv_text
#         st.success(f"업로드 완료: {uploaded_csv.name}")
#     else:
#         csv_text = st.session_state.get("csv_text", "")

#     if csv_text:
#         preview_col, filter_col = st.columns([1.55, 1.0], gap="large")

#         with preview_col:
#             with st.expander("Parsed Storyboard Data Preview", expanded=True):
#                 try:
#                     preview_df = pd.read_csv(io.StringIO(csv_text))

#                     st.dataframe(
#                         preview_df,
#                         use_container_width=True,
#                         hide_index=True,
#                     )

#                 except Exception:
#                     st.warning("CSV를 표 형태로 읽지 못했습니다. 원본 텍스트로 표시합니다.")
#                     st.code(csv_text)

#         with filter_col:
#             st.subheader("Shot Selection Control")

#             shot_ids = extract_shot_ids_from_csv(csv_text)

#             st.radio(
#                 "shot_filter",
#                 options=["ALL", "CUSTOM"],
#                 horizontal=True,
#                 key="shot_filter_mode",
#                 help="ALL은 전체 shot을 사용하고, CUSTOM은 선택한 shot만 사용합니다.",
#             )

#             if st.session_state.get("shot_filter_mode", "ALL") == "CUSTOM":
#                 if shot_ids:
#                     st.multiselect(
#                         "Select Storyboard Shots",
#                         options=shot_ids,
#                         default=[],
#                         key="custom_shots",
#                         help="CUSTOM일 때만 shot을 선택합니다.",
#                     )
#                 else:
#                     st.warning("CSV에서 추출된 shot id가 없습니다.")
#     else:
#         st.info("CSV 파일을 업로드하면 Parsed Storyboard Data Preview와 Shot Selection Control이 표시됩니다.")


# # =========================
# # Step 2. Character Identity Generation
# # =========================
# with tab2:
#     st.header("Step 2. Character Identity Generation")

#     preview_col, settings_col = st.columns([1.45, 1.25], gap="large")

#     with preview_col:
#         st.subheader("Character Identity Preview")

#         face_preview_col1, face_preview_col2 = st.columns(2, gap="medium")

#         with face_preview_col1:
#             st.markdown("#### Image 1 - Boy")

#             if "face_result_image_c1" in st.session_state:
#                 st.image(
#                     st.session_state["face_result_image_c1"],
#                     caption="Image 1 - Boy Face Reference",
#                     use_container_width=True,
#                 )
#             else:
#                 render_empty_preview_box(
#                     "Image 1 - Boy face reference will appear here.",
#                     520,
#                 )

#         with face_preview_col2:
#             st.markdown("#### Image 2 - Girl")

#             if "face_result_image_c2" in st.session_state:
#                 st.image(
#                     st.session_state["face_result_image_c2"],
#                     caption="Image 2 - Girl Face Reference",
#                     use_container_width=True,
#                 )
#             else:
#                 render_empty_preview_box(
#                     "Image 2 - Girl face reference will appear here.",
#                     520,
#                 )

#     with settings_col:
#         st.subheader("Target Character Control")

#         st.radio(
#             "character_filter",
#             options=["Image 1 - Boy", "Image 2 - Girl"],
#             index=1,
#             horizontal=True,
#             key="character_filter_label",
#             help="UI에서는 Image 1 / Image 2로 표시하고, workflow에는 C1 / C2로 전달합니다.",
#         )

#         with st.expander("Identity Attribute Controls", expanded=True):
#             with st.container(border=True):
#                 st.markdown("###### Core Identity")

#                 basic_col1, basic_col2 = st.columns(2)

#                 with basic_col1:
#                     st.slider(
#                         "Age",
#                         min_value=1,
#                         max_value=100,
#                         value=9,
#                         step=1,
#                         key="age",
#                     )

#                 with basic_col2:
#                     st.selectbox(
#                         "Nationality",
#                         options=[
#                             "South Korean",
#                             "Korean",
#                             "East Asian",
#                             "Japanese",
#                             "Chinese",
#                         ],
#                         index=0,
#                         key="nationality",
#                     )

#             with st.container(border=True):
#                 st.markdown("###### Face")

#                 face_col1, face_col2, face_col3 = st.columns(3)

#                 with face_col1:
#                     st.selectbox(
#                         "Body Type",
#                         options=["Slim", "Average", "Athletic", "Curvy", "Heavy"],
#                         index=0,
#                         key="body_type",
#                     )

#                 with face_col2:
#                     st.selectbox(
#                         "Face Shape",
#                         options=[
#                             "Oval",
#                             "Round",
#                             "Square",
#                             "Square with Soft Jaw",
#                             "Heart",
#                             "Long",
#                             "Diamond",
#                         ],
#                         index=3,
#                         key="face_shape",
#                     )

#                 with face_col3:
#                     st.selectbox(
#                         "Expression",
#                         options=[
#                             "Neutral",
#                             "Curious",
#                             "Gentle Smile",
#                             "Serious",
#                             "Sad",
#                             "Surprised",
#                             "Calm",
#                         ],
#                         index=1,
#                         key="facial_expression",
#                     )

#             with st.container(border=True):
#                 st.markdown("###### Eyes / Lips")

#                 eye_col1, eye_col2 = st.columns(2)

#                 with eye_col1:
#                     st.selectbox(
#                         "Eyes Color",
#                         options=[
#                             "Brown",
#                             "Dark Brown",
#                             "Black",
#                             "Hazel",
#                             "Blue",
#                             "Green",
#                         ],
#                         index=0,
#                         key="eyes_color",
#                     )

#                     st.selectbox(
#                         "Eyes Shape",
#                         options=[
#                             "Double Eyelid Eyes Shape",
#                             "Monolid Eyes Shape",
#                             "Almond Eyes",
#                             "Round Eyes",
#                             "Sharp Eyes",
#                         ],
#                         index=0,
#                         key="eyes_shape",
#                     )

#                 with eye_col2:
#                     st.selectbox(
#                         "Lips Color",
#                         options=[
#                             "Peach Lips",
#                             "Pink Lips",
#                             "Natural Lips",
#                             "Pale Lips",
#                             "Rose Lips",
#                         ],
#                         index=0,
#                         key="lips_color",
#                     )

#                     st.selectbox(
#                         "Lips Shape",
#                         options=["Thin Lips", "Full Lips", "Small Lips", "Soft Lips"],
#                         index=0,
#                         key="lips_shape",
#                     )

#             with st.container(border=True):
#                 st.markdown("###### Hair")

#                 hair_col1, hair_col2, hair_col3 = st.columns(3)

#                 with hair_col1:
#                     st.selectbox(
#                         "Hair Style",
#                         options=[
#                             "Bob",
#                             "Straight",
#                             "Wavy",
#                             "Braided Pigtails",
#                             "Ponytail",
#                             "Short Hair",
#                             "Long Hair",
#                         ],
#                         index=0,
#                         key="hair_style",
#                     )

#                 with hair_col2:
#                     st.selectbox(
#                         "Hair Color",
#                         options=[
#                             "Chestnut",
#                             "Black",
#                             "Dark Brown",
#                             "Brown",
#                             "Blonde",
#                             "Auburn",
#                         ],
#                         index=0,
#                         key="hair_color",
#                     )

#                 with hair_col3:
#                     st.selectbox(
#                         "Hair Length",
#                         options=["-", "Short", "Medium", "Long", "Shoulder Length"],
#                         index=0,
#                         key="hair_length",
#                     )

#         with st.expander("Fine-Grained Appearance Attributes", expanded=False):
#             skin_keys = list(SKIN_DEFAULTS.keys())
#             skin_cols = st.columns(3)

#             for i, key in enumerate(skin_keys):
#                 with skin_cols[i % 3]:
#                     default_checked = SKIN_DEFAULTS[key] > 0

#                     st.checkbox(
#                         key,
#                         value=default_checked,
#                         key=f"skin_{key}",
#                     )

#         st.divider()

#         generate_clicked = st.button(
#             "Generate Character Identity",
#             type="primary",
#             use_container_width=True,
#         )

#         if generate_clicked:
#             csv_text = st.session_state.get("csv_text", "")

#             if not csv_text.strip():
#                 st.error("먼저 Step 1에서 CSV 파일을 업로드해야 합니다.")

#             elif (
#                 st.session_state.get("shot_filter_mode", "ALL") == "CUSTOM"
#                 and len(st.session_state.get("custom_shots", [])) == 0
#             ):
#                 st.error("shot_filter가 CUSTOM이면 최소 1개 이상의 shot을 선택해야 합니다.")

#             else:
#                 config = build_face_ui_config()

#                 st.success("Face branch UI 입력값이 정상적으로 수집되었습니다.")
#                 st.subheader("Collected Character Identity Config")
#                 st.json(config)


# # =========================
# # Step 3. Full-Body Reference Generation
# # =========================
# with tab3:
#     st.header("Step 3. Full-Body Reference Generation")

#     initialize_body_prompts()

#     preview_col, settings_col = st.columns([1.45, 1.25], gap="large")

#     with preview_col:
#         st.subheader("Full-Body Reference Preview")

#         body_preview_col1, body_preview_col2 = st.columns(2, gap="medium")

#         with body_preview_col1:
#             st.markdown("#### Image 1 - Boy")

#             if "body_result_image_c1" in st.session_state:
#                 st.image(
#                     st.session_state["body_result_image_c1"],
#                     caption="Image 1 - Boy Body Reference",
#                     use_container_width=True,
#                 )
#             else:
#                 render_empty_preview_box(
#                     "Image 1 - Boy body reference will appear here.",
#                     520,
#                 )

#         with body_preview_col2:
#             st.markdown("#### Image 2 - Girl")

#             if "body_result_image_c2" in st.session_state:
#                 st.image(
#                     st.session_state["body_result_image_c2"],
#                     caption="Image 2 - Girl Body Reference",
#                     use_container_width=True,
#                 )
#             else:
#                 render_empty_preview_box(
#                     "Image 2 - Girl body reference will appear here.",
#                     520,
#                 )

#     with settings_col:
#         st.subheader("Reference Generation Control")

#         st.radio(
#             "body_character_filter",
#             options=["Image 1 - Boy", "Image 2 - Girl"],
#             index=0,
#             horizontal=True,
#             key="body_character_filter_label",
#             help="UI에서는 Image 1 / Image 2로 표시하고, workflow에는 C1 / C2로 전달합니다.",
#         )

#         st.divider()

#         st.markdown("### Full-Body Prompt Editor")

#         selected_body_target = st.session_state.get(
#             "body_character_filter_label",
#             "Image 1 - Boy",
#         )

#         if selected_body_target == "Image 1 - Boy":
#             st.text_area(
#                 "Image 1 - Boy Body Prompt",
#                 key="body_prompt_c1",
#                 height=150,
#                 placeholder=BODY_PROMPT_PLACEHOLDER,
#                 help="Image 1 - Boy의 전신 reference 생성을 위한 프롬프트입니다. 사용자가 직접 수정할 수 있습니다.",
#             )

#         else:
#             st.text_area(
#                 "Image 2 - Girl Body Prompt",
#                 key="body_prompt_c2",
#                 height=150,
#                 placeholder=BODY_PROMPT_PLACEHOLDER,
#                 help="Image 2 - Girl의 전신 reference 생성을 위한 프롬프트입니다. 사용자가 직접 수정할 수 있습니다.",
#             )

#         with st.expander("Reference Prompt Guidelines", expanded=False):
#             st.markdown(
#                 """
#                 - 얼굴 reference와 같은 인물로 보이도록 identity 유지 문장을 포함하는 것이 좋습니다.
#                 - 전신이 모두 보이도록 `full-body`, `head to toe`, `entire body visible` 표현을 포함하세요.
#                 - 의상은 상의, 하의, 양말, 신발까지 구체적으로 작성하는 것이 좋습니다.
#                 - 이후 Scene Generation에서 reference로 쓰기 좋게 `clean background`를 유지하는 것이 좋습니다.
#                 - 복잡한 포즈나 강한 카메라 앵글은 전신 reference 생성 단계에서는 피하는 것이 좋습니다.
#                 """
#             )

#         st.divider()

#         generate_body_clicked = st.button(
#             "Generate Full-Body Reference",
#             type="primary",
#             use_container_width=True,
#         )

#         if generate_body_clicked:
#             csv_text = st.session_state.get("csv_text", "")

#             if not csv_text.strip():
#                 st.error("먼저 Step 1에서 CSV 파일을 업로드해야 합니다.")

#             elif (
#                 st.session_state.get("shot_filter_mode", "ALL") == "CUSTOM"
#                 and len(st.session_state.get("custom_shots", [])) == 0
#             ):
#                 st.error("shot_filter가 CUSTOM이면 최소 1개 이상의 shot을 선택해야 합니다.")

#             else:
#                 body_config = build_body_ui_config()

#                 st.success("Body branch UI 입력값이 정상적으로 수집되었습니다.")
#                 st.subheader("Collected Full-Body Reference Config")
#                 st.json(body_config)


# # =========================
# # Step 4. Cinematic Scene Synthesis
# # =========================
# with tab4:
#     st.header("Step 4. Reference-Guided Scene Generation")

#     boy_candidates = get_body_reference_candidates("c1")
#     girl_candidates = get_body_reference_candidates("c2")

#     sync_scene_reference_selection("scene_boy_reference_label", boy_candidates)
#     sync_scene_reference_selection("scene_girl_reference_label", girl_candidates)

#     preview_col, settings_col = st.columns([1.45, 1.25], gap="large")

#     with preview_col:
#         st.subheader("Generated Storyboard Preview")

#         selected_shot_df = get_selected_shot_dataframe()

#         if selected_shot_df.empty:
#             st.caption("Selected Storyboard Context: None")
#         else:
#             st.caption(f"Selected Storyboard Context Count: {len(selected_shot_df)}")

#         if "scene_result_image" in st.session_state:
#             st.image(
#                 st.session_state["scene_result_image"],
#                 caption="Generated Storyboard Scene",
#                 use_container_width=True,
#             )
#         else:
#             render_empty_preview_box(
#                 "Generated storyboard scene will appear here.",
#                 560,
#             )

#     with settings_col:
#         st.subheader("Scene Generation Control")

#         with st.container(border=True):
#             st.markdown("###### Selected Storyboard Context")

#             selected_shot_df = get_selected_shot_dataframe()
#             shot_filter_mode = st.session_state.get("shot_filter_mode", "ALL")
#             custom_shots = st.session_state.get("custom_shots", [])

#             if selected_shot_df.empty:
#                 st.warning("표시할 scene 정보가 없습니다. Step 1에서 CSV와 shot 선택을 확인하세요.")
#             else:
#                 if shot_filter_mode == "ALL":
#                     st.caption(f"Shot Filter: ALL / {len(selected_shot_df)} scene(s)")
#                 elif custom_shots:
#                     st.caption(f"Shot Filter: CUSTOM / {', '.join(custom_shots)}")
#                 else:
#                     st.caption("Shot Filter: CUSTOM / No shot selected")

#                 st.dataframe(
#                     selected_shot_df,
#                     use_container_width=True,
#                     hide_index=True,
#                 )

#         st.divider()

#         st.markdown("### Character Reference Inputs")

#         st.markdown("##### Image 1 - Boy Body Reference")

#         if boy_candidates:
#             st.selectbox(
#                 "Select Image 1 - Boy Body Reference",
#                 options=[item["label"] for item in boy_candidates],
#                 key="scene_boy_reference_label",
#                 label_visibility="collapsed",
#             )

#             selected_boy = get_selected_candidate(
#                 boy_candidates,
#                 st.session_state.get("scene_boy_reference_label", ""),
#             )

#             if selected_boy and selected_boy.get("image") is not None:
#                 st.image(
#                     selected_boy["image"],
#                     caption=selected_boy["label"],
#                     use_container_width=True,
#                 )
#             else:
#                 render_empty_preview_box(
#                     "Selected boy body reference preview is not available.",
#                     220,
#                 )

#         else:
#             st.warning("Step 3에서 Image 1 - Boy body reference를 먼저 생성해야 합니다.")

#         st.divider()

#         st.markdown("##### Image 2 - Girl Body Reference")

#         if girl_candidates:
#             st.selectbox(
#                 "Select Image 2 - Girl Body Reference",
#                 options=[item["label"] for item in girl_candidates],
#                 key="scene_girl_reference_label",
#                 label_visibility="collapsed",
#             )

#             selected_girl = get_selected_candidate(
#                 girl_candidates,
#                 st.session_state.get("scene_girl_reference_label", ""),
#             )

#             if selected_girl and selected_girl.get("image") is not None:
#                 st.image(
#                     selected_girl["image"],
#                     caption=selected_girl["label"],
#                     use_container_width=True,
#                 )
#             else:
#                 render_empty_preview_box(
#                     "Selected girl body reference preview is not available.",
#                     220,
#                 )

#         else:
#             st.warning("Step 3에서 Image 2 - Girl body reference를 먼저 생성해야 합니다.")

#         st.divider()

#         generate_scene_clicked = st.button(
#             "Generate Storyboard Scene",
#             type="primary",
#             use_container_width=True,
#         )

#         if generate_scene_clicked:
#             csv_text = st.session_state.get("csv_text", "")

#             if not csv_text.strip():
#                 st.error("먼저 Step 1에서 CSV 파일을 업로드해야 합니다.")

#             elif (
#                 st.session_state.get("shot_filter_mode", "ALL") == "CUSTOM"
#                 and len(st.session_state.get("custom_shots", [])) == 0
#             ):
#                 st.error("shot_filter가 CUSTOM이면 최소 1개 이상의 shot을 선택해야 합니다.")

#             elif not boy_candidates:
#                 st.error("Image 1 - Boy body reference 후보가 없습니다. 먼저 Step 3을 진행하세요.")

#             elif not girl_candidates:
#                 st.error("Image 2 - Girl body reference 후보가 없습니다. 먼저 Step 3을 진행하세요.")

#             else:
#                 scene_config = build_scene_ui_config()

#                 st.success("Scene branch UI 입력값이 정상적으로 수집되었습니다.")
#                 st.subheader("Collected Scene Synthesis Config")
#                 st.json(scene_config)

