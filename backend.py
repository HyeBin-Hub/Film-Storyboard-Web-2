import csv
import io
import json
import streamlit as st


# =========================
# Fixed Face Branch Values
# =========================
FIXED_BASE_BACKGROUND_CLOTHING_PROMPT = "gray background, white t-shirt"

# These values are intentionally fixed and hidden from the UI:
# Model: flux1-krea-dev.safetensors
# LoRA: UltraRealPhoto.safetensors
# VAE: FLUX1/ae.safetensors
# Shot: Head and shoulders portrait
# CSV input_mode: text
# ThinkingLLM: fixed
# Resolution megapixel: 1


# =========================
# Helper Functions
# =========================
def extract_shot_ids_from_csv(csv_text: str) -> list[str]:
    """
    Extract shot IDs from the first column of CSV text.
    Falls back safely if the CSV is incomplete or pasted without a header.
    """
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

        # Skip likely header names
        if first_value.lower() in {"shot", "shot_id", "shot id", "id"}:
            continue

        if first_value not in shot_ids:
            shot_ids.append(first_value)

    return shot_ids


def build_face_ui_config() -> dict:
    """
    Collect all UI values into one dictionary.
    This dictionary will later be used to override the Face workflow_api_json.
    """
    return {
        "csv": {
            "input_mode": "text",
            "csv_text": st.session_state.get("csv_text", ""),
            "shot_filter": st.session_state.get("shot_filter", "ALL"),
        },
        "character_registry": {
            "character_filter": st.session_state.get("character_filter", "C2"),
            "age": st.session_state.get("age", 9),
            "include_character_id": "false",
        },
        "base_prompt": {
            "text": FIXED_BASE_BACKGROUND_CLOTHING_PROMPT,
        },
        "portrait_master_base_character": {
            "shot": "Head and shoulders portrait",
            "body_type": st.session_state.get("body_type", "Slim"),
            "eyes_color": st.session_state.get("eyes_color", "Brown"),
            "eyes_shape": st.session_state.get("eyes_shape", "Double Eyelid Eyes Shape"),
            "lips_color": st.session_state.get("lips_color", "Peach Lips"),
            "lips_shape": st.session_state.get("lips_shape", "Thin Lips"),
            "facial_expression": st.session_state.get("facial_expression", "Curious"),
            "face_shape": st.session_state.get("face_shape", "Square with Soft Jaw"),
            "hair_style": st.session_state.get("hair_style", "Bob"),
            "hair_color": st.session_state.get("hair_color", "Chestnut"),
            "hair_length": st.session_state.get("hair_length", "-"),

            # Advanced values
            "gender": st.session_state.get("gender", "Woman"),
            "nationality_1": st.session_state.get("nationality_1", "South Korean"),
            "nationality_2": st.session_state.get("nationality_2", "-"),
            "nationality_mix": st.session_state.get("nationality_mix", 0.0),
            "androgynous": st.session_state.get("androgynous", 0.0),
            "ugly": st.session_state.get("ugly", 0.0),
            "ordinary_face": st.session_state.get("ordinary_face", 0.25),
            "body_type_weight": st.session_state.get("body_type_weight", 0.0),
            "breast_size": st.session_state.get("breast_size", "-"),
            "breast_size_weight": st.session_state.get("breast_size_weight", 0.0),
            "butt_size": st.session_state.get("butt_size", "-"),
            "butt_size_weight": st.session_state.get("butt_size_weight", 0.0),
            "facial_expression_weight": st.session_state.get("facial_expression_weight", 0.0),
            "face_shape_weight": st.session_state.get("face_shape_weight", 0.0),
            "facial_asymmetry": st.session_state.get("facial_asymmetry", 0.0),
            "disheveled": st.session_state.get("disheveled", 0.0),
            "beard": st.session_state.get("beard", "-"),
            "beard_color": st.session_state.get("beard_color", "-"),
        },
        "portrait_master_skin_details": {
            "natural_skin": st.session_state.get("natural_skin", 0.74),
            "bare_face": st.session_state.get("bare_face", 0.75),
            "washed_face": st.session_state.get("washed_face", 0.0),
            "dried_face": st.session_state.get("dried_face", 0.0),
            "skin_details": st.session_state.get("skin_details", 0.3),
            "skin_pores": st.session_state.get("skin_pores", 0.1),
            "dimples": st.session_state.get("dimples", 0.0),
            "wrinkles": st.session_state.get("wrinkles", 0.0),
            "freckles": st.session_state.get("freckles", 0.0),
            "moles": st.session_state.get("moles", 0.0),
            "skin_imperfections": st.session_state.get("skin_imperfections", 0.0),
            "skin_acne": st.session_state.get("skin_acne", 0.0),
            "tanned_skin": st.session_state.get("tanned_skin", 0.0),
            "eyes_details": st.session_state.get("eyes_details", 1.01),
            "iris_details": st.session_state.get("iris_details", 0.0),
            "circular_iris": st.session_state.get("circular_iris", 0.0),
            "circular_pupil": st.session_state.get("circular_pupil", 0.0),
        },
    }


# =========================
# Streamlit Page Config
# =========================
st.set_page_config(
    page_title="Storyboard Face Generator",
    page_icon="🎬",
    layout="wide",
)

st.title("🎬 Storyboard Face Generator")
st.caption("Face Generation Branch UI Test")


# =========================
# Secret Check
# =========================
missing_secrets = []
if "RUNCOMFY_API_KEY" not in st.secrets:
    missing_secrets.append("RUNCOMFY_API_KEY")
if "RUNCOMFY_DEPLOYMENT_ID" not in st.secrets:
    missing_secrets.append("RUNCOMFY_DEPLOYMENT_ID")

if missing_secrets:
    st.warning(
        "Streamlit secrets에 다음 값이 없으면 실제 RunComfy 실행 단계에서 오류가 날 수 있습니다: "
        + ", ".join(missing_secrets)
    )


# =========================
# Step 1. CSV File Upload
# =========================
st.header("Step 1. CSV file upload")

csv_text = st.text_area(
    "CSV text",
    value=st.session_state.get(
        "csv_text",
        "7-1,From the empty field head, a girl and a boy are walking in a line toward the right of the screen.\n"
        "7-2,The boy and the girl are standing facing each other in the field."
    ),
    height=160,
    key="csv_text",
    help="CSV 내용을 그대로 붙여넣으세요. 첫 번째 열에서 shot id를 자동 추출합니다.",
)

shot_ids = extract_shot_ids_from_csv(csv_text)
shot_options = ["ALL"] + shot_ids if shot_ids else ["ALL"]

st.selectbox(
    "shot_filter",
    options=shot_options,
    index=0,
    key="shot_filter",
    help="CSV에서 추출된 shot id를 선택하거나 ALL을 선택합니다.",
)


# =========================
# Step 2. Face Generation Branch
# =========================
st.header("Step 2. Face Generation Branch")

st.subheader("Character Target")
st.radio(
    "character_filter",
    options=["C1", "C2"],
    index=1,
    horizontal=True,
    key="character_filter",
    help="CSV/Character parser에서 어떤 캐릭터를 얼굴 생성 대상으로 사용할지 선택합니다.",
)

st.subheader("Main Character Appearance")

appearance_col, eyes_col, lips_col, hair_col = st.columns(4)

with appearance_col:
    st.markdown("**Appearance**")
    st.slider("age", min_value=1, max_value=100, value=9, step=1, key="age")
    st.selectbox("body_type", ["-", "Slim", "Average", "Athletic", "Curvy", "Heavy"], index=1, key="body_type")
    st.selectbox(
        "face_shape",
        ["-", "Oval", "Round", "Square", "Square with Soft Jaw", "Heart", "Long", "Diamond"],
        index=4,
        key="face_shape",
    )
    st.selectbox(
        "facial_expression",
        ["-", "Neutral", "Curious", "Gentle Smile", "Serious", "Sad", "Surprised", "Calm"],
        index=2,
        key="facial_expression",
    )

with eyes_col:
    st.markdown("**Eyes**")
    st.selectbox("eyes_color", ["-", "Brown", "Dark Brown", "Black", "Hazel", "Blue", "Green"], index=1, key="eyes_color")
    st.selectbox(
        "eyes_shape",
        ["-", "Double Eyelid Eyes Shape", "Monolid Eyes Shape", "Almond Eyes", "Round Eyes", "Sharp Eyes"],
        index=1,
        key="eyes_shape",
    )

with lips_col:
    st.markdown("**Lips**")
    st.selectbox("lips_color", ["-", "Peach Lips", "Pink Lips", "Natural Lips", "Pale Lips", "Rose Lips"], index=1, key="lips_color")
    st.selectbox("lips_shape", ["-", "Thin Lips", "Full Lips", "Small Lips", "Soft Lips"], index=1, key="lips_shape")

with hair_col:
    st.markdown("**Hair**")
    st.selectbox(
        "hair_style",
        ["-", "Bob", "Straight", "Wavy", "Braided Pigtails", "Ponytail", "Short Hair", "Long Hair"],
        index=1,
        key="hair_style",
    )
    st.selectbox("hair_color", ["-", "Chestnut", "Black", "Dark Brown", "Brown", "Blonde", "Auburn"], index=1, key="hair_color")
    st.selectbox("hair_length", ["-", "Short", "Medium", "Long", "Shoulder Length"], index=0, key="hair_length")


# =========================
# Advanced Base Character Settings
# =========================
with st.expander("Advanced Base Character Settings", expanded=False):
    adv_col1, adv_col2, adv_col3 = st.columns(3)

    with adv_col1:
        st.selectbox("gender", ["Woman", "Man", "Girl", "Boy", "-"], index=0, key="gender")
        st.selectbox("nationality_1", ["South Korean", "Korean", "East Asian", "Japanese", "Chinese", "-"], index=0, key="nationality_1")
        st.selectbox("nationality_2", ["-", "South Korean", "Korean", "East Asian", "Japanese", "Chinese"], index=0, key="nationality_2")
        st.slider("nationality_mix", 0.0, 2.0, 0.0, 0.05, key="nationality_mix")
        st.slider("androgynous", 0.0, 2.0, 0.0, 0.05, key="androgynous")
        st.slider("ugly", 0.0, 2.0, 0.0, 0.05, key="ugly")
        st.slider("ordinary_face", 0.0, 2.0, 0.25, 0.05, key="ordinary_face")

    with adv_col2:
        st.slider("body_type_weight", 0.0, 2.0, 0.0, 0.05, key="body_type_weight")
        st.selectbox("breast_size", ["-", "Small", "Medium", "Large"], index=0, key="breast_size")
        st.slider("breast_size_weight", 0.0, 2.0, 0.0, 0.05, key="breast_size_weight")
        st.selectbox("butt_size", ["-", "Small", "Medium", "Large"], index=0, key="butt_size")
        st.slider("butt_size_weight", 0.0, 2.0, 0.0, 0.05, key="butt_size_weight")

    with adv_col3:
        st.slider("facial_expression_weight", 0.0, 2.0, 0.0, 0.05, key="facial_expression_weight")
        st.slider("face_shape_weight", 0.0, 2.0, 0.0, 0.05, key="face_shape_weight")
        st.slider("facial_asymmetry", 0.0, 2.0, 0.0, 0.05, key="facial_asymmetry")
        st.slider("disheveled", 0.0, 2.0, 0.0, 0.05, key="disheveled")
        st.selectbox("beard", ["-", "None", "Light Beard", "Mustache"], index=0, key="beard")
        st.selectbox("beard_color", ["-", "Black", "Brown", "Dark Brown", "Gray"], index=0, key="beard_color")


# =========================
# Advanced Skin Details
# =========================
with st.expander("Advanced Skin Details", expanded=False):
    skin_col1, skin_col2, skin_col3 = st.columns(3)

    with skin_col1:
        st.slider("natural_skin", 0.0, 2.0, 0.74, 0.01, key="natural_skin")
        st.slider("bare_face", 0.0, 2.0, 0.75, 0.01, key="bare_face")
        st.slider("washed_face", 0.0, 2.0, 0.0, 0.01, key="washed_face")
        st.slider("dried_face", 0.0, 2.0, 0.0, 0.01, key="dried_face")
        st.slider("skin_details", 0.0, 2.0, 0.3, 0.01, key="skin_details")
        st.slider("skin_pores", 0.0, 2.0, 0.1, 0.01, key="skin_pores")

    with skin_col2:
        st.slider("dimples", 0.0, 2.0, 0.0, 0.01, key="dimples")
        st.slider("wrinkles", 0.0, 2.0, 0.0, 0.01, key="wrinkles")
        st.slider("freckles", 0.0, 2.0, 0.0, 0.01, key="freckles")
        st.slider("moles", 0.0, 2.0, 0.0, 0.01, key="moles")
        st.slider("skin_imperfections", 0.0, 2.0, 0.0, 0.01, key="skin_imperfections")
        st.slider("skin_acne", 0.0, 2.0, 0.0, 0.01, key="skin_acne")

    with skin_col3:
        st.slider("tanned_skin", 0.0, 2.0, 0.0, 0.01, key="tanned_skin")
        st.slider("eyes_details", 0.0, 2.0, 1.01, 0.01, key="eyes_details")
        st.slider("iris_details", 0.0, 2.0, 0.0, 0.01, key="iris_details")
        st.slider("circular_iris", 0.0, 2.0, 0.0, 0.01, key="circular_iris")
        st.slider("circular_pupil", 0.0, 2.0, 0.0, 0.01, key="circular_pupil")


# =========================
# Run / Preview
# =========================
st.divider()

left, right = st.columns([1, 2])

with left:
    generate_clicked = st.button("Generate Face", type="primary", use_container_width=True)

with right:
    st.caption("현재 단계에서는 UI 입력값 확인용입니다. 다음 단계에서 Face workflow_api_json override와 RunComfy 요청을 연결합니다.")

if generate_clicked:
    config = build_face_ui_config()

    if not config["csv"]["csv_text"].strip():
        st.error("CSV text를 입력해야 합니다.")
    else:
        st.success("Face branch UI 입력값이 정상적으로 수집되었습니다.")
        st.subheader("Collected Face Branch Config")
        st.json(config)
