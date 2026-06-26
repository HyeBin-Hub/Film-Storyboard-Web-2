import csv
import io
import pandas as pd
import streamlit as st


# =========================
# Fixed Values
# =========================
FIXED_BASE_BACKGROUND_CLOTHING_PROMPT = "gray background, white t-shirt"

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


def get_single_choice(key, empty_value="-"):
    values = st.session_state.get(key, [])

    if isinstance(values, list) and len(values) > 0:
        return values[0]

    return empty_value


def get_checkbox_value(key, on_value):
    return on_value if st.session_state.get(key, False) else 0.0


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
            "character_filter": st.session_state.get("character_filter", "C2"),
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
            "nationality_1": get_single_choice("nationality_choice"),
            "nationality_2": "-",
            "nationality_mix": 0,
            "body_type": get_single_choice("body_type_choice"),
            "body_type_weight": 0,
            "breast_size": "-",
            "breast_size_weight": 0,
            "butt_size": "-",
            "butt_size_weight": 0,
            "eyes_color": get_single_choice("eyes_color_choice"),
            "eyes_shape": get_single_choice("eyes_shape_choice"),
            "lips_color": get_single_choice("lips_color_choice"),
            "lips_shape": get_single_choice("lips_shape_choice"),
            "facial_expression": get_single_choice("facial_expression_choice"),
            "facial_expression_weight": 0,
            "face_shape": get_single_choice("face_shape_choice"),
            "face_shape_weight": 0,
            "hair_style": get_single_choice("hair_style_choice"),
            "hair_color": get_single_choice("hair_color_choice"),
            "hair_length": get_single_choice("hair_length_choice"),
            "androgynous": get_checkbox_value(
                "androgynous_check",
                BASE_CHARACTER_CHECK_DEFAULTS["androgynous"],
            ),
            "ugly": get_checkbox_value(
                "ugly_check",
                BASE_CHARACTER_CHECK_DEFAULTS["ugly"],
            ),
            "ordinary_face": get_checkbox_value(
                "ordinary_face_check",
                BASE_CHARACTER_CHECK_DEFAULTS["ordinary_face"],
            ),
            "facial_asymmetry": get_checkbox_value(
                "facial_asymmetry_check",
                BASE_CHARACTER_CHECK_DEFAULTS["facial_asymmetry"],
            ),
            "disheveled": get_checkbox_value(
                "disheveled_check",
                BASE_CHARACTER_CHECK_DEFAULTS["disheveled"],
            ),
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


# =========================
# Page Config
# =========================
st.set_page_config(
    page_title="Storyboard Face Generator",
    page_icon="🎬",
    layout="wide",
)

st.title("🎬 Storyboard Face Generator")
st.caption("Face Generation Branch UI Test")


# =========================
# Tabs
# =========================
tab1, tab2, tab3 = st.tabs(
    [
        "Step 1. CSV",
        "Step 2. Face Settings",
        "Step 3. Generate",
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

    st.subheader("Character Target")

    st.radio(
        "character_filter",
        options=["C1", "C2"],
        index=1,
        horizontal=True,
        key="character_filter",
        help="어떤 캐릭터를 face branch에서 생성할지 선택합니다.",
    )

    st.subheader("Main Character Appearance")

    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.markdown("**Appearance**")

        st.slider(
            "age",
            min_value=1,
            max_value=100,
            value=9,
            step=1,
            key="age",
        )

        st.multiselect(
            "body_type",
            options=["Slim", "Average", "Athletic", "Curvy", "Heavy"],
            default=["Slim"],
            max_selections=1,
            key="body_type_choice",
        )

        st.multiselect(
            "face_shape",
            options=[
                "Oval",
                "Round",
                "Square",
                "Square with Soft Jaw",
                "Heart",
                "Long",
                "Diamond",
            ],
            default=["Square with Soft Jaw"],
            max_selections=1,
            key="face_shape_choice",
        )

        st.multiselect(
            "facial_expression",
            options=[
                "Neutral",
                "Curious",
                "Gentle Smile",
                "Serious",
                "Sad",
                "Surprised",
                "Calm",
            ],
            default=["Curious"],
            max_selections=1,
            key="facial_expression_choice",
        )

    with col2:
        st.markdown("**Eyes**")

        st.multiselect(
            "eyes_color",
            options=["Brown", "Dark Brown", "Black", "Hazel", "Blue", "Green"],
            default=["Brown"],
            max_selections=1,
            key="eyes_color_choice",
        )

        st.multiselect(
            "eyes_shape",
            options=[
                "Double Eyelid Eyes Shape",
                "Monolid Eyes Shape",
                "Almond Eyes",
                "Round Eyes",
                "Sharp Eyes",
            ],
            default=["Double Eyelid Eyes Shape"],
            max_selections=1,
            key="eyes_shape_choice",
        )

    with col3:
        st.markdown("**Lips**")

        st.multiselect(
            "lips_color",
            options=[
                "Peach Lips",
                "Pink Lips",
                "Natural Lips",
                "Pale Lips",
                "Rose Lips",
            ],
            default=["Peach Lips"],
            max_selections=1,
            key="lips_color_choice",
        )

        st.multiselect(
            "lips_shape",
            options=["Thin Lips", "Full Lips", "Small Lips", "Soft Lips"],
            default=["Thin Lips"],
            max_selections=1,
            key="lips_shape_choice",
        )

    with col4:
        st.markdown("**Hair**")

        st.multiselect(
            "hair_style",
            options=[
                "Bob",
                "Straight",
                "Wavy",
                "Braided Pigtails",
                "Ponytail",
                "Short Hair",
                "Long Hair",
            ],
            default=["Bob"],
            max_selections=1,
            key="hair_style_choice",
        )

        st.multiselect(
            "hair_color",
            options=[
                "Chestnut",
                "Black",
                "Dark Brown",
                "Brown",
                "Blonde",
                "Auburn",
            ],
            default=["Chestnut"],
            max_selections=1,
            key="hair_color_choice",
        )

        st.multiselect(
            "hair_length",
            options=["Short", "Medium", "Long", "Shoulder Length"],
            default=[],
            max_selections=1,
            key="hair_length_choice",
        )

    with st.expander("Advanced Base Character Settings", expanded=False):
        adv1, adv2 = st.columns(2)

        with adv1:
            st.markdown("**Identity / Face Character**")

            st.multiselect(
                "nationality",
                options=[
                    "South Korean",
                    "Korean",
                    "East Asian",
                    "Japanese",
                    "Chinese",
                ],
                default=["South Korean"],
                max_selections=1,
                key="nationality_choice",
            )

            st.checkbox(
                "ordinary_face",
                value=True,
                key="ordinary_face_check",
            )

            st.checkbox(
                "androgynous",
                value=False,
                key="androgynous_check",
            )

            st.checkbox(
                "ugly",
                value=False,
                key="ugly_check",
            )

        with adv2:
            st.markdown("**Face / Hair Condition**")

            st.checkbox(
                "facial_asymmetry",
                value=False,
                key="facial_asymmetry_check",
            )

            st.checkbox(
                "disheveled",
                value=False,
                key="disheveled_check",
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


# =========================
# Step 3. Generate
# =========================
with tab3:
    st.header("Step 3. Generate")

    st.info(
        "현재는 UI 테스트 단계입니다. Generate Face를 누르면 RunComfy 요청 대신 "
        "수집된 Face Branch 설정값을 JSON으로 확인합니다."
    )

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
