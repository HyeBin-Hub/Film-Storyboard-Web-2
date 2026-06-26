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
                "eyes_shape", "Double Eyelid Eyes Shape"
            ),
            "lips_color": st.session_state.get("lips_color", "Peach Lips"),
            "lips_shape": st.session_state.get("lips_shape", "Thin Lips"),
            "facial_expression": st.session_state.get(
                "facial_expression", "Curious"
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

SCENE_PROMPT_PLACEHOLDER = (
    "Example: Image 1 - Boy and Image 2 - Girl are walking through an empty red sorghum field. "
    "Image 1 is on the left and Image 2 is on the right. "
    "Use a long shot, eye-level camera, full-body framing, cinematic vintage tone, cloudy and windy atmosphere."
)


def initialize_scene_prompt():
    if "scene_prompt" not in st.session_state:
        st.session_state["scene_prompt"] = ""


def build_scene_ui_config():
    shot_filter_mode = st.session_state.get("shot_filter_mode", "ALL")
    custom_shots = st.session_state.get("custom_shots", [])

    if shot_filter_mode == "ALL":
        shot_filter = "ALL"
        custom_shot_ids = ""
    else:
        shot_filter = "CUSTOM"
        custom_shot_ids = ", ".join(custom_shots)

    return {
        "scene_generation": {
            "shot_filter": shot_filter,
            "custom_shot_ids": custom_shot_ids,
            "scene_prompt": st.session_state.get("scene_prompt", ""),
            "reference_images": {
                "image_1": "Image 1 - Boy Body Reference",
                "image_2": "Image 2 - Girl Body Reference",
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
    같은 형태를 읽는다.

    후보 리스트가 없으면 body_result_image_c1 / c2 를 단일 후보로 fallback 한다.
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

    # fallback: Step3에서 단일 결과만 저장되어 있는 경우
    fallback_image = st.session_state.get(f"body_result_image_{character_code}")
    fallback_filename = st.session_state.get(f"body_result_filename_{character_code}", "")

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

    return {
        "scene_generation": {
            "shot_filter": shot_filter,
            "custom_shot_ids": custom_shot_ids,
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


# =========================
# Page Config
# =========================
st.set_page_config(
    page_title="Storyboard Generator",
    page_icon="🎬",
    layout="wide",
)

st.title("🎬 Storyboard Generator")
st.caption("Face / Body Generation Branch UI Test")


# =========================
# Tabs
# =========================
tab1, tab2, tab3, tab4 = st.tabs(
    [
        "Step 1. CSV",
        "Step 2. Face Settings",
        "Step 3. Body Settings",
        "Step 4. Scene Settings",
    ]
)

# =========================
# Step 1. CSV Upload
# =========================
with tab1:
    st.header("Step 1. CSV file upload")

    uploaded_csv = st.file_uploader(
        "Upload CSV file",
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
        with st.expander("Preview uploaded CSV", expanded=True):
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

        shot_ids = extract_shot_ids_from_csv(csv_text)

        st.subheader("Shot Filter")

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
                    "Select shots",
                    options=shot_ids,
                    default=[],
                    key="custom_shots",
                    help="CUSTOM일 때만 shot을 선택합니다.",
                )
            else:
                st.warning("CSV에서 추출된 shot id가 없습니다.")


# =========================
# Step 2. Face Settings
# =========================
with tab2:
    st.header("Step 2. Face Generation Branch")

    preview_col, settings_col = st.columns([1.45, 1.25], gap="large")

    with preview_col:
        st.subheader("Generated Face Preview")
    
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
        st.subheader("Character Target")

        st.radio(
            "character_filter",
            options=["Image 1 - Boy", "Image 2 - Girl"],
            index=1,
            horizontal=True,
            key="character_filter_label",
            help="UI에서는 Image 1 / Image 2로 표시하고, workflow에는 C1 / C2로 전달합니다.",
        )

        with st.expander("Main Character Appearance", expanded=True):
            with st.container(border=True):
                st.markdown("###### Basic Identity")

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

        with st.expander("Advanced Skin Details", expanded=False):
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
            "Generate Face",
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
                st.subheader("Collected Face Branch Config")
                st.json(config)


# =========================
# Step 3. Body Settings
# =========================
with tab3:
    st.header("Step 3. Body Reference Generation")

    initialize_body_prompts()

    preview_col, settings_col = st.columns([1.45, 1.25], gap="large")

    with preview_col:
        st.subheader("Generated Body Preview")

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
        st.subheader("Body Generation Settings")

        st.radio(
            "body_character_filter",
            options=["Image 1 - Boy", "Image 2 - Girl"],
            index=0,
            horizontal=True,
            key="body_character_filter_label",
            help="UI에서는 Image 1 / Image 2로 표시하고, workflow에는 C1 / C2로 전달합니다.",
        )

        st.divider()

        st.markdown("### Body Prompt Editor")

        selected_body_target = st.session_state.get(
            "body_character_filter_label",
            "Image 1 - Boy",
        )

        if selected_body_target == "Image 1 - Boy":
            st.text_area(
                "Image 1 - Boy Body Prompt",
                key="body_prompt_c1",
                height=150,
                placeholder=BODY_PROMPT_PLACEHOLDER,
                help="Image 1 - Boy의 전신 reference 생성을 위한 프롬프트입니다. 사용자가 직접 수정할 수 있습니다.",
            )

        else:
            st.text_area(
                "Image 2 - Girl Body Prompt",
                key="body_prompt_c2",
                height=150,
                placeholder=BODY_PROMPT_PLACEHOLDER,
                help="Image 2 - Girl의 전신 reference 생성을 위한 프롬프트입니다. 사용자가 직접 수정할 수 있습니다.",
            )


        with st.expander("Body Prompt Guide", expanded=False):
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
            "Generate Body Reference",
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
                st.subheader("Collected Body Branch Config")
                st.json(body_config)
                
# =========================
# Step 4. Scene Settings
# =========================
with tab4:
    st.header("Step 4. Scene Generation")

    boy_candidates = get_body_reference_candidates("c1")
    girl_candidates = get_body_reference_candidates("c2")

    sync_scene_reference_selection("scene_boy_reference_label", boy_candidates)
    sync_scene_reference_selection("scene_girl_reference_label", girl_candidates)

    preview_col, settings_col = st.columns([1.45, 1.25], gap="large")

    with preview_col:
        st.subheader("Generated Scene Preview")

        shot_filter_mode = st.session_state.get("shot_filter_mode", "ALL")
        custom_shots = st.session_state.get("custom_shots", [])

        if shot_filter_mode == "ALL":
            st.caption("Selected Shots: ALL")
        elif custom_shots:
            st.caption(f"Selected Shots: {', '.join(custom_shots)}")
        else:
            st.caption("Selected Shots: CUSTOM / No shot selected")

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
        st.subheader("Scene Generation Settings")

        with st.container(border=True):
            st.markdown("###### Selected Shot Filter")

            shot_filter_mode = st.session_state.get("shot_filter_mode", "ALL")
            custom_shots = st.session_state.get("custom_shots", [])

            if shot_filter_mode == "ALL":
                st.write("ALL")
            elif custom_shots:
                st.write(", ".join(custom_shots))
            else:
                st.warning("Step 1에서 CUSTOM shot을 선택해야 합니다.")

        st.divider()

        st.markdown("### Reference Images")

        # Boy reference selection
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

        # Girl reference selection
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
            "Generate Scene",
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
                st.subheader("Collected Scene Branch Config")
                st.json(scene_config)
