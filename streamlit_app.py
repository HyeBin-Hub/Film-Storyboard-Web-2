import csv
import io
import pandas as pd
import streamlit as st

from backend import run_csv_parser_test, run_face_generation

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

BODY_TYPE_OPTIONS = [
    "Beefy", "Buxom", "Buff", "Chubby", "Curvy", "Fat", "Fit", "Flyweight",
    "Hefty", "Large", "Lanky", "Midweight", "Morbidly obese", "Muscular",
    "Obese", "Overweight", "Petite", "Plump", "Portly", "Rotund", "Short",
    "Skinny", "Slight", "Slim", "Small", "Stout", "Stocky", "Tall", "Thick",
    "Tiny", "Voluptuous", "Well-built", "Well-endowed", "Underweight",
]

FACE_SHAPE_OPTIONS = [
    "Circle", "Diamond", "Heart", "Heart with Pointed Chin", "Heart with Rounded Chin",
    "Heart with V-Shape Chin", "Inverted Triangle", "Long", "Oblong", "Oval", "Pear",
    "Rectangle", "Round", "Round with Defined Cheekbones", "Round with High Cheekbones",
    "Round with Soft Cheekbones", "Square", "Square Oval", "Square Round",
    "Square with Rounded Jaw", "Square with Sharp Jaw", "Square with Soft Jaw", "Triangle",
]

EXPRESSION_OPTIONS = [
    "Amused", "Angry", "Anxious", "Bored", "Calm", "Cautious", "Confused",
    "Contemptuous", "Content", "Curious", "Disappointed", "Disgusted", "Envious",
    "Excited", "Fearful", "Happy", "In love", "Nervous", "Peaceful", "Pensive",
    "Prideful", "Proud", "Relieved", "Sad", "Sarcastic", "Serene", "Serious",
    "Shy", "Silly", "Smiling", "Surprised", "Surprised and Amused",
]

EYES_COLOR_OPTIONS = ["Albino", "Amber", "Brown", "Dark Brown", "Black", "Hazel", "Blue", "Green", "Gray"]
EYES_SHAPE_OPTIONS = [
    "Almond Eyes Shape", "Asian Eyes Shape", "Close-Set Eyes Shape", "Deep Set Eyes Shape",
    "Downturned Eyes Shape", "Double Eyelid Eyes Shape", "Hooded Eyes Shape",
    "Monolid Eyes Shape", "Oval Eyes Shape", "Protruding Eyes Shape", "Round Eyes Shape",
    "Upturned Eyes Shape",
]
LIPS_COLOR_OPTIONS = [
    "Berry Lips", "Black Lips", "Blue Lips", "Brown Lips", "Burgundy Lips", "Coral Lips",
    "Glossy Red Lips", "Mauve Lips", "Orange Lips", "Peach Lips", "Pink Lips", "Plum Lips",
    "Purple Lips", "Red Lips", "Yellow Lips",
]
LIPS_SHAPE_OPTIONS = [
    "Biting Lips", "Bow-shaped Lips", "Closed Lips", "Cupid's Bow Lips",
    "Defined Cupid's Bow Lips", "Flat Cupid's Bow Lips", "Full Lips", "Heart-shaped Lips",
    "Large Lips", "Medium Lips", "Neutral Lips", "Parted Lips", "Plump Lips", "Pouting Lips",
    "Round Lips", "Small Lips", "Smiling Lips", "Soft Cupid's Bow Lips", "Thin Lips",
    "Upper Lip Mole Lips", "Wide Lips",
]
HAIR_STYLE_OPTIONS = [
    "Afro", "A-line bob", "Asymmetrical", "Balayage", "Bald", "Ballerina bun", "Bangs",
    "Beehive", "Beehivecut", "Bleached spikes", "Blunt bob", "Blunt", "Bob", "Bouffant",
    "Bowl", "Box braids", "Box fade", "Braided", "Braided bob", "Braided pigtails",
    "Brave shortcut with shaved sides", "Bushy", "Buzz", "Caesar", "Chignon", "Choppy",
    "Cloudy", "Cornrows", "Crew", "Curly", "Curly bob", "Curly Frizzy", "Curtain bangs",
    "Deep side part", "Double Bun", "Dreadlocks", "Faded afro", "Faux hawk",
    "Faux hawk short pixie", "Feathered", "Female bald", "Fishtail braids", "Flat topcut",
    "French bob", "French braids", "French twist", "Frohawk", "Hair ringlets", "High ponytail",
    "High skin fade", "Honey", "Italian bob", "Layered", "Lemonade braids", "Long bob",
    "Long with bangs", "Long pixie", "Long ponytail", "Long straight", "Loose Curly Afro",
    "Marmaid waves", "Micro braids", "Middle part ponytails", "Modern caesar", "Mohawk",
    "Multicolored", "Pastel", "Pigtails", "Pixie", "Platinum", "Pompadour", "Quiff",
    "Razor fade with curls", "Red", "Right side shaved", "Salt and pepper", "Shag", "Short curly",
    "Short curly pixie", "Short", "Short messy curls", "Shoulder Length with Bangs",
    "Shoulder length straight", "Side braid", "Side Part Comb-Overstyle With High Fade",
    "Side-swept bangs", "Side-swept fringe", "Sideswept pixie", "Smooth lob", "Space buns",
    "Spiky", "Stacked bob", "Stacked Curls in Short Bob", "Stitch braids", "Strawberry",
    "Strawberry blonde", "Sweeping pixie", "Taper fade with waves", "Taperedcut with shaved side",
    "Textured brush back", "Textured", "Tomboy", "Top Knot", "Twin braids", "Twintails",
    "Two dutch braids", "Undercut", "Updo", "Very long wave", "Waterfall braids", "Wavy",
    "Wavy bob", "Wavy with curtain bangs", "Wavy French Bob Vibes from 1920", "Wavy undercut",
]
HAIR_COLOR_OPTIONS = [
    "Auburn", "Black", "Blonde", "Burgundy", "Caramel", "Chestnut", "Chocolate", "Copper",
    "Dirty", "Gray", "Honey", "Jet Black", "Mahogany", "Multicolored", "Pastel", "Platinum",
    "Red", "Salt and pepper", "Silver", "Strawberry", "White",
]


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

    candidates = ["shot", "shot_id", "shot id", "id", "Shot", "Shot ID", "Shot_ID"]
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


def build_storyboard_input_config():
    csv_text = st.session_state.get("csv_text", "")
    shot_filter_mode = st.session_state.get("shot_filter_mode", "ALL")
    custom_shots = st.session_state.get("custom_shots", [])
    selected_shot_df = get_selected_shot_dataframe()

    if shot_filter_mode == "ALL":
        shot_filter = "ALL"
        custom_shot_ids = ""
    else:
        shot_filter = "CUSTOM"
        custom_shot_ids = ", ".join([str(x) for x in custom_shots])

    return {
        "storyboard_input": {
            "csv_text": csv_text,
            "shot_filter": shot_filter,
            "custom_shot_ids": custom_shot_ids,
            "selected_shot_count": len(selected_shot_df),
            "selected_shot_data": selected_shot_df.to_dict(orient="records"),
        }
    }


def character_label_to_value(label):
    return {"Image 1 - Boy": "C1", "Image 2 - Girl": "C2"}.get(label, "C2")


def body_character_label_to_value(label):
    return {"Image 1 - Boy": "C1", "Image 2 - Girl": "C2"}.get(label, "C1")


def initialize_body_prompts():
    st.session_state.setdefault("body_prompt_c1", "")
    st.session_state.setdefault("body_prompt_c2", "")


def get_scene_shot_filter_config():
    storyboard_input = build_storyboard_input_config()["storyboard_input"]
    return storyboard_input["shot_filter"], storyboard_input["custom_shot_ids"]


def get_body_reference_candidates(character_code):
    candidates_key = f"body_candidates_{character_code}"
    candidates = st.session_state.get(candidates_key, [])
    normalized = []

    for i, item in enumerate(candidates, start=1):
        if not isinstance(item, dict):
            continue
        normalized.append(
            {
                "label": item.get("label", f"{'Boy' if character_code == 'c1' else 'Girl'} Body {i}"),
                "image": item.get("image"),
                "filename": item.get("filename", ""),
            }
        )

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


def get_face_reference_candidates(character_code):
    candidates_key = f"face_candidates_{character_code}"
    candidates = st.session_state.get(candidates_key, [])
    normalized = []

    for i, item in enumerate(candidates, start=1):
        if not isinstance(item, dict):
            continue
        normalized.append(
            {
                "label": item.get("label", f"{'Boy' if character_code == 'c1' else 'Girl'} Face {i}"),
                "image": item.get("image"),
                "filename": item.get("filename", ""),
            }
        )

    fallback_image = st.session_state.get(f"face_result_image_{character_code}")
    fallback_filename = st.session_state.get(f"face_result_filename_{character_code}", "")

    if not normalized and fallback_image is not None:
        normalized.append(
            {
                "label": f"{'Boy' if character_code == 'c1' else 'Girl'} Face 1",
                "image": fallback_image,
                "filename": fallback_filename,
            }
        )

    return normalized


def get_selected_candidate(candidates, selected_label):
    for item in candidates:
        if item["label"] == selected_label:
            return item
    return None


def append_face_reference_order(character_code):
    selected_order = list(st.session_state.get("selected_face_reference_order", []))
    selected_order = [code for code in selected_order if code in {"c1", "c2"}]

    if character_code not in selected_order:
        selected_order.append(character_code)

    st.session_state["selected_face_reference_order"] = selected_order


def ensure_face_selection_state():
    """
    기존 session_state에 이미지 URL은 있는데 selected label/order가 비어 있는 경우를 보정합니다.
    디버그 결과처럼 face_result_image_c2는 있는데 selected_face_reference_order가 ['c1']로만 남는 상태를 방지합니다.
    """
    for character_code in ["c1", "c2"]:
        candidates = get_face_reference_candidates(character_code)
        if not candidates:
            continue

        label_key = f"face_selected_label_{character_code}"
        result_image_key = f"face_result_image_{character_code}"
        result_filename_key = f"face_result_filename_{character_code}"

        labels = [item["label"] for item in candidates]
        current_label = st.session_state.get(label_key)

        if current_label not in labels:
            st.session_state[label_key] = labels[0]
            current_label = labels[0]

        selected_candidate = get_selected_candidate(candidates, current_label) or candidates[0]

        if selected_candidate.get("image") is not None:
            st.session_state[result_image_key] = selected_candidate["image"]
            st.session_state[result_filename_key] = selected_candidate.get("filename", "")
            append_face_reference_order(character_code)


def apply_selected_face_result(character_code):
    candidates = get_face_reference_candidates(character_code)
    if not candidates:
        return None

    selected_label_key = f"face_selected_label_{character_code}"
    selected_label = st.session_state.get(selected_label_key)

    labels = [item["label"] for item in candidates]
    if selected_label not in labels:
        selected_label = labels[0]
        st.session_state[selected_label_key] = selected_label

    selected_candidate = get_selected_candidate(candidates, selected_label)

    if selected_candidate and selected_candidate.get("image") is not None:
        st.session_state[f"face_result_image_{character_code}"] = selected_candidate["image"]
        st.session_state[f"face_result_filename_{character_code}"] = selected_candidate.get("filename", "")
        append_face_reference_order(character_code)

    return selected_candidate


def get_selected_face_reference_entries():
    ensure_face_selection_state()

    selected_order = st.session_state.get("selected_face_reference_order", [])
    character_codes = ["c1", "c2"]
    display_order = [code for code in selected_order if code in character_codes]

    for code in character_codes:
        if code not in display_order and st.session_state.get(f"face_result_image_{code}") is not None:
            display_order.append(code)

    entries = []

    for code in display_order:
        image = st.session_state.get(f"face_result_image_{code}")
        if image is None:
            continue

        if code == "c1":
            label = "Image 1 - Boy"
            display_label = "Selected Boy"
        else:
            label = "Image 2 - Girl"
            display_label = "Selected Girl"

        entries.append(
            {
                "code": code,
                "label": label,
                "display_label": display_label,
                "image": image,
                "filename": st.session_state.get(f"face_result_filename_{code}", ""),
            }
        )

    return entries


def sync_scene_reference_selection(session_key, candidates):
    labels = [item["label"] for item in candidates]

    if not labels:
        st.session_state[session_key] = ""
        return

    if st.session_state.get(session_key) not in labels:
        st.session_state[session_key] = labels[0]


def build_face_ui_config():
    storyboard_input = build_storyboard_input_config()["storyboard_input"]

    return {
        "storyboard_input": storyboard_input,
        "csvstoryboardparser": {
            "input_mode": "text",
            "csv_file": "CUSTOM",
            "csv_text": storyboard_input["csv_text"],
            "shot_filter": storyboard_input["shot_filter"],
            "custom_shot_ids": storyboard_input["custom_shot_ids"],
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
            "eyes_shape": st.session_state.get("eyes_shape", "Double Eyelid Eyes Shape"),
            "lips_color": st.session_state.get("lips_color", "Peach Lips"),
            "lips_shape": st.session_state.get("lips_shape", "Thin Lips"),
            "facial_expression": st.session_state.get("facial_expression", "Curious"),
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
            key: default_value if st.session_state.get(f"skin_{key}", False) else 0.0
            for key, default_value in SKIN_DEFAULTS.items()
        },
    }


def build_body_ui_config():
    character_filter_label = st.session_state.get("body_character_filter_label", "Image 1 - Boy")
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
    storyboard_input = build_storyboard_input_config()["storyboard_input"]

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
        "storyboard_input": storyboard_input,
        "scene_generation": {
            "shot_filter": storyboard_input["shot_filter"],
            "custom_shot_ids": storyboard_input["custom_shot_ids"],
            "selected_shot_count": storyboard_input["selected_shot_count"],
            "selected_shot_data": storyboard_input["selected_shot_data"],
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
        },
    }


def get_scene_result_candidates():
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
        normalized.append({"label": "Scene 1", "image": fallback_image, "filename": fallback_filename})

    return normalized


def build_camera_refinement_ui_config():
    storyboard_input = build_storyboard_input_config()["storyboard_input"]
    scene_candidates = get_scene_result_candidates()
    selected_scene = get_selected_candidate(scene_candidates, st.session_state.get("camera_input_scene_label", ""))
    prompt_source = st.session_state.get("camera_prompt_source", "Use Camera Angle Prompt")
    switch_setting = 1 if prompt_source == "Preserve Original Scene Prompt" else 2

    return {
        "storyboard_input": storyboard_input,
        "camera_angle_refinement": {
            "input_scene": {
                "label": selected_scene["label"] if selected_scene else "",
                "filename": selected_scene.get("filename", "") if selected_scene else "",
            },
            "selected_shot_count": storyboard_input["selected_shot_count"],
            "selected_shot_data": storyboard_input["selected_shot_data"],
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
        },
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
st.caption(
    "A ComfyUI-based generation pipeline for character-consistent cinematic storyboard creation and camera-angle refinement"
)

# 기존 session_state 보정
ensure_face_selection_state()

# =========================
# Tabs
# =========================
tab1, tab2, tab3, tab4 = st.tabs(
    [
        "Step 1. Storyboard Data",
        "Step 2. Character Reference",
        "Step 3. Scene Generation",
        "Step 4. Camera Refinement",
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
                    st.dataframe(preview_df, use_container_width=True, hide_index=True)
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

            st.divider()
            st.subheader("RunComfy CSV Parser Test")
            st.caption("Step 1에서 업로드한 CSV가 RunComfy의 CSVStoryboardParser까지 정상적으로 전달되는지 먼저 확인합니다.")

            csv_parser_test_disabled = not bool(st.session_state.get("csv_text", "").strip())

            if st.button("Test CSV Parser on RunComfy", type="secondary", disabled=csv_parser_test_disabled):
                try:
                    api_key = st.secrets["RUNCOMFY_API_KEY"]
                    deployment_id = st.secrets["DEPLOYMENT_ID"]
                    storyboard_input_config = build_storyboard_input_config()

                    with st.spinner("RunComfy에서 CSVStoryboardParser 테스트를 실행하는 중입니다..."):
                        result = run_csv_parser_test(
                            api_key=api_key,
                            deployment_id=deployment_id,
                            storyboard_input_config=storyboard_input_config,
                            poll_interval=5,
                            timeout_seconds=900,
                        )

                    st.session_state["csv_parser_test_result"] = result
                    st.session_state["csv_parser_test_images"] = result.get("images", [])

                    images = result.get("images", [])
                    if images:
                        st.success("CSV Parser Test 성공: RunComfy에서 output image가 반환되었습니다.")
                    else:
                        st.success(
                            "CSV Parser Test 완료: RunComfy에서 workflow가 정상 실행되었습니다. "
                            "현재 테스트 workflow에는 SaveImage가 없으므로 image output이 비어 있는 것은 정상입니다."
                        )
                    st.rerun()

                except KeyError:
                    st.error("RunComfy secret 설정이 없습니다.")
                    st.caption("`.streamlit/secrets.toml`에 RUNCOMFY_API_KEY와 DEPLOYMENT_ID를 추가해야 합니다.")
                except Exception as e:
                    st.error("RunComfy CSV Parser Test 실행 중 오류가 발생했습니다.")
                    st.exception(e)
                    with st.expander("Debug: Storyboard Input Config", expanded=False):
                        st.json(build_storyboard_input_config())

            csv_parser_test_result = st.session_state.get("csv_parser_test_result")
            csv_parser_test_images = st.session_state.get("csv_parser_test_images", [])

            if csv_parser_test_result:
                st.markdown("#### CSV Parser Test Result")
                if csv_parser_test_images:
                    cols = st.columns(min(len(csv_parser_test_images), 3))
                    for idx, image_item in enumerate(csv_parser_test_images):
                        with cols[idx % len(cols)]:
                            st.image(
                                image_item.get("url", ""),
                                caption=image_item.get("filename", f"CSV Parser Test Output {idx + 1}"),
                                use_container_width=True,
                            )
                else:
                    st.info("CSV Parser Test workflow는 텍스트/JSON 출력 검증용이며 SaveImage가 없기 때문에 image output은 표시되지 않습니다.")

                with st.expander("Debug: RunComfy Request", expanded=False):
                    st.json(csv_parser_test_result.get("request", {}))
                with st.expander("Debug: RunComfy Result", expanded=False):
                    st.json(csv_parser_test_result.get("result", {}))
                with st.expander("Debug: Patched workflow_api_json", expanded=False):
                    st.json(csv_parser_test_result.get("workflow_api_json", {}))
    else:
        st.info("CSV 파일을 업로드하면 Parsed Storyboard Data Preview와 Shot Selection Control이 표시됩니다.")


# =========================
# Step 2. Character Reference Generation
# =========================
with tab2:
    ensure_face_selection_state()

    st.header("Step 2. Character Reference Generation")
    st.caption("Generate face identity references first, then convert them into full-body references for scene generation.")

    with st.container(border=True):
        st.markdown("#### Character Reference Pipeline")
        st.markdown("**Face Identity** → **Full-Body Reference** → **Scene Input**")
        st.caption("2A defines each character's visual identity, and 2B converts that identity into full-body references used by Scene Generation.")

    with st.container(border=True):
        st.markdown("### 2A. Character Identity Generation")

        preview_col, settings_col = st.columns([1.25, 1.15], gap="large")

        with preview_col:
            st.subheader("Character Identity Preview")
        
            face_preview_col1, face_preview_col2 = st.columns(2, gap="medium")
        
            with face_preview_col1:
                st.markdown("##### Image 1 - Boy")
        
                if st.session_state.get("face_result_image_c1") is not None:
                    st.image(
                        st.session_state["face_result_image_c1"],
                        caption="Image 1 - Boy Face Reference",
                        width=240,
                    )
                else:
                    render_empty_preview_box(
                        "Image 1 - Boy face reference will appear here.",
                        400,
                    )
        
            with face_preview_col2:
                st.markdown("##### Image 2 - Girl")
        
                if st.session_state.get("face_result_image_c2") is not None:
                    st.image(
                        st.session_state["face_result_image_c2"],
                        caption="Image 2 - Girl Face Reference",
                        width=220,
                    )
                else:
                    render_empty_preview_box(
                        "Image 2 - Girl face reference will appear here.",
                        400,
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
                        st.slider("Age", min_value=1, max_value=100, value=9, step=1, key="age")
                    with basic_col2:
                        st.selectbox(
                            "Nationality",
                            options=["South Korean", "Korean", "East Asian", "Japanese", "Chinese"],
                            index=0,
                            key="nationality",
                        )

                with st.container(border=True):
                    st.markdown("###### Face")
                    face_col1, face_col2, face_col3 = st.columns(3)

                    with face_col1:
                        st.selectbox("Body Type", options=BODY_TYPE_OPTIONS, index=23, key="body_type")
                    with face_col2:
                        st.selectbox("Face Shape", options=FACE_SHAPE_OPTIONS, index=21, key="face_shape")
                    with face_col3:
                        st.selectbox("Expression", options=EXPRESSION_OPTIONS, index=9, key="facial_expression")

                with st.container(border=True):
                    st.markdown("###### Eyes / Lips")
                    eye_col1, eye_col2 = st.columns(2)

                    with eye_col1:
                        st.selectbox("Eyes Color", options=EYES_COLOR_OPTIONS, index=2, key="eyes_color")
                        st.selectbox("Eyes Shape", options=EYES_SHAPE_OPTIONS, index=1, key="eyes_shape")
                    with eye_col2:
                        st.selectbox("Lips Color", options=LIPS_COLOR_OPTIONS, index=9, key="lips_color")
                        st.selectbox("Lips Shape", options=LIPS_SHAPE_OPTIONS, index=18, key="lips_shape")

                with st.container(border=True):
                    st.markdown("###### Hair")
                    hair_col1, hair_col2, hair_col3 = st.columns(3)

                    with hair_col1:
                        st.selectbox("Hair Style", options=HAIR_STYLE_OPTIONS, index=12, key="hair_style")
                    with hair_col2:
                        st.selectbox("Hair Color", options=HAIR_COLOR_OPTIONS, index=5, key="hair_color")
                    with hair_col3:
                        st.selectbox("Hair Length", options=["-", "Short", "Medium", "Long"], index=0, key="hair_length")

            with st.expander("Fine-Grained Appearance Attributes", expanded=False):
                skin_keys = list(SKIN_DEFAULTS.keys())
                skin_cols = st.columns(3)
                for i, key in enumerate(skin_keys):
                    with skin_cols[i % 3]:
                        default_checked = SKIN_DEFAULTS[key] > 0
                        st.checkbox(key, value=default_checked, key=f"skin_{key}")

            st.divider()

            generate_clicked = st.button("Generate Character Identity", type="primary", use_container_width=True)

            if generate_clicked:
                csv_text = st.session_state.get("csv_text", "")

                if not csv_text.strip():
                    st.error("먼저 Step 1에서 CSV 파일을 업로드해야 합니다.")
                elif st.session_state.get("shot_filter_mode", "ALL") == "CUSTOM" and len(st.session_state.get("custom_shots", [])) == 0:
                    st.error("shot_filter가 CUSTOM이면 최소 1개 이상의 shot을 선택해야 합니다.")
                else:
                    config = build_face_ui_config()
                    character_filter = config["character_registry_parser"]["character_filter"]
                    character_code = "c1" if character_filter == "C1" else "c2"

                    try:
                        api_key = st.secrets["RUNCOMFY_API_KEY"]
                        deployment_id = st.secrets["DEPLOYMENT_ID"]

                        with st.spinner("RunComfy에서 Character Identity를 생성하는 중입니다..."):
                            result = run_face_generation(
                                api_key=api_key,
                                deployment_id=deployment_id,
                                config=config,
                                poll_interval=5,
                                timeout_seconds=900,
                            )

                        images = result.get("images", [])

                        if not images:
                            st.error("RunComfy 실행은 완료되었지만 결과 이미지가 없습니다.")
                            with st.expander("RunComfy Raw Result", expanded=False):
                                st.json(result)
                            with st.expander("Collected Character Identity Config", expanded=False):
                                st.json(config)
                        else:
                            st.session_state[f"face_candidates_{character_code}"] = images

                            first_image = images[0]
                            st.session_state[f"face_result_image_{character_code}"] = first_image["image"]
                            st.session_state[f"face_result_filename_{character_code}"] = first_image.get("filename", "")
                            st.session_state[f"face_selected_label_{character_code}"] = first_image["label"]

                            append_face_reference_order(character_code)
                            ensure_face_selection_state()

                            st.success("Character Identity 생성이 완료되었습니다.")
                            st.rerun()

                    except KeyError as e:
                        st.error("RunComfy secret 설정이 없습니다.")
                        st.caption("`.streamlit/secrets.toml`에 RUNCOMFY_API_KEY와 DEPLOYMENT_ID를 추가해야 합니다.")
                        st.exception(e)
                        with st.expander("Collected Character Identity Config", expanded=False):
                            st.json(config)
                    except Exception as e:
                        st.error("RunComfy Character Identity 실행 중 오류가 발생했습니다.")
                        st.exception(e)
                        with st.expander("Collected Character Identity Config", expanded=False):
                            st.json(config)

    st.divider()

    with st.container(border=True):
        st.markdown("### 2B. Full-Body Reference Generation")
        initialize_body_prompts()

        preview_col, settings_col = st.columns([1.45, 1.25], gap="large")

        with preview_col:
            st.subheader("Full-Body Reference Preview")
            body_preview_col1, body_preview_col2 = st.columns(2, gap="medium")

            with body_preview_col1:
                st.markdown("##### Image 1 - Boy")
                if "body_result_image_c1" in st.session_state:
                    st.image(st.session_state["body_result_image_c1"], caption="Image 1 - Boy Body Reference", width=240)
                else:
                    render_empty_preview_box("Image 1 - Boy body reference will appear here.", 400)

            with body_preview_col2:
                st.markdown("##### Image 2 - Girl")
                if "body_result_image_c2" in st.session_state:
                    st.image(st.session_state["body_result_image_c2"], caption="Image 2 - Girl Body Reference", width=240)
                else:
                    render_empty_preview_box("Image 2 - Girl body reference will appear here.", 400)

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

            # st.divider()
            st.markdown("""
                    <div style="margin: 0.05rem 0;">
                      <hr style="margin:0; border:none; border-top:1px solid rgba(128,128,128,0.3);">
                    </div>
                    """, unsafe_allow_html=True)
            st.markdown("### Full-Body Prompt Editor")
            selected_body_target = st.session_state.get("body_character_filter_label", "Image 1 - Boy")

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
            generate_body_clicked = st.button("Generate Full-Body Reference", type="primary", use_container_width=True)

            if generate_body_clicked:
                csv_text = st.session_state.get("csv_text", "")

                if not csv_text.strip():
                    st.error("먼저 Step 1에서 CSV 파일을 업로드해야 합니다.")
                elif st.session_state.get("shot_filter_mode", "ALL") == "CUSTOM" and len(st.session_state.get("custom_shots", [])) == 0:
                    st.error("shot_filter가 CUSTOM이면 최소 1개 이상의 shot을 선택해야 합니다.")
                else:
                    body_config = build_body_ui_config()
                    st.success("Body branch UI 입력값이 정상적으로 수집되었습니다.")
                    st.subheader("Collected Full-Body Reference Config")
                    st.json(body_config)


# =========================
# Step 3. Reference-Guided Scene Generation
# =========================
with tab3:
    st.header("Step 3. Reference-Guided Scene Generation")

    boy_candidates = get_body_reference_candidates("c1")
    girl_candidates = get_body_reference_candidates("c2")
    sync_scene_reference_selection("scene_boy_reference_label", boy_candidates)
    sync_scene_reference_selection("scene_girl_reference_label", girl_candidates)

    preview_col, settings_col = st.columns([1.45, 1.25], gap="large")

    with preview_col:
        st.subheader("Generated Storyboard Preview")
        storyboard_input = build_storyboard_input_config()["storyboard_input"]

        if storyboard_input["selected_shot_count"] == 0:
            st.caption("Selected Storyboard Context: None")
        else:
            st.caption(f"Selected Scene Count: {storyboard_input['selected_shot_count']}")

        if "scene_result_image" in st.session_state:
            st.image(st.session_state["scene_result_image"], caption="Generated Storyboard Scene", use_container_width=True)
        else:
            render_empty_preview_box("Generated storyboard scene will appear here.", 560)

    with settings_col:
        st.subheader("Scene Generation Control")

        with st.container(border=True):
            st.markdown("###### Selected Storyboard Context")
            storyboard_input = build_storyboard_input_config()["storyboard_input"]

            if storyboard_input["selected_shot_count"] == 0:
                st.warning("표시할 scene 정보가 없습니다. Step 1에서 CSV와 shot 선택을 확인하세요.")
            else:
                if storyboard_input["shot_filter"] == "ALL":
                    st.caption(f"Shot Filter: ALL / {storyboard_input['selected_shot_count']} scene(s)")
                elif storyboard_input["custom_shot_ids"]:
                    st.caption(f"Shot Filter: CUSTOM / {storyboard_input['custom_shot_ids']}")
                else:
                    st.caption("Shot Filter: CUSTOM / No shot selected")

                st.dataframe(pd.DataFrame(storyboard_input["selected_shot_data"]), use_container_width=True, hide_index=True)

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
            selected_boy = get_selected_candidate(boy_candidates, st.session_state.get("scene_boy_reference_label", ""))
            if selected_boy and selected_boy.get("image") is not None:
                st.image(selected_boy["image"], caption=selected_boy["label"], width=240)
            else:
                render_empty_preview_box("Selected boy body reference preview is not available.", 220)
        else:
            st.warning("Step 2에서 Image 1 - Boy body reference를 먼저 생성해야 합니다.")

        st.divider()
        st.markdown("##### Image 2 - Girl Body Reference")
        if girl_candidates:
            st.selectbox(
                "Select Image 2 - Girl Body Reference",
                options=[item["label"] for item in girl_candidates],
                key="scene_girl_reference_label",
                label_visibility="collapsed",
            )
            selected_girl = get_selected_candidate(girl_candidates, st.session_state.get("scene_girl_reference_label", ""))
            if selected_girl and selected_girl.get("image") is not None:
                st.image(selected_girl["image"], caption=selected_girl["label"], width=240)
            else:
                render_empty_preview_box("Selected girl body reference preview is not available.", 220)
        else:
            st.warning("Step 2에서 Image 2 - Girl body reference를 먼저 생성해야 합니다.")

        st.divider()
        generate_scene_clicked = st.button("Generate Storyboard Scene", type="primary", use_container_width=True)

        if generate_scene_clicked:
            csv_text = st.session_state.get("csv_text", "")

            if not csv_text.strip():
                st.error("먼저 Step 1에서 CSV 파일을 업로드해야 합니다.")
            elif st.session_state.get("shot_filter_mode", "ALL") == "CUSTOM" and len(st.session_state.get("custom_shots", [])) == 0:
                st.error("shot_filter가 CUSTOM이면 최소 1개 이상의 shot을 선택해야 합니다.")
            elif not boy_candidates:
                st.error("Image 1 - Boy body reference 후보가 없습니다. 먼저 Step 2를 진행하세요.")
            elif not girl_candidates:
                st.error("Image 2 - Girl body reference 후보가 없습니다. 먼저 Step 2를 진행하세요.")
            else:
                scene_config = build_scene_ui_config()
                st.success("Scene branch UI 입력값이 정상적으로 수집되었습니다.")
                st.subheader("Collected Scene Generation Config")
                st.json(scene_config)


# =========================
# Step 4. Camera Angle Refinement
# =========================
with tab4:
    st.header("Step 4. Camera Angle Refinement")

    scene_candidates = get_scene_result_candidates()
    sync_scene_reference_selection("camera_input_scene_label", scene_candidates)

    preview_col, settings_col = st.columns([1.6, 1.1], gap="large")

    with preview_col:
        st.subheader("Camera Refinement Preview")
        st.markdown("#### Input Scene")
        selected_input_scene = get_selected_candidate(scene_candidates, st.session_state.get("camera_input_scene_label", ""))

        if selected_input_scene and selected_input_scene.get("image") is not None:
            st.image(selected_input_scene["image"], caption=selected_input_scene["label"], use_container_width=True)
        else:
            render_empty_preview_box("A generated scene from Step 3 will appear here.", 360)

        st.divider()
        st.markdown("#### Refined Scene")

        if "camera_refined_result_image" in st.session_state:
            st.image(st.session_state["camera_refined_result_image"], caption="Camera-Refined Storyboard Scene", use_container_width=True)
        else:
            render_empty_preview_box("The camera-refined scene will appear here.", 360)

    with settings_col:
        st.subheader("Camera Refinement Control")

        with st.container(border=True):
            st.markdown("###### Source Scene Input")

            if scene_candidates:
                st.selectbox("Select Input Scene", options=[item["label"] for item in scene_candidates], key="camera_input_scene_label")
                selected_input_scene = get_selected_candidate(scene_candidates, st.session_state.get("camera_input_scene_label", ""))
                if selected_input_scene:
                    filename = selected_input_scene.get("filename", "")
                    if filename:
                        st.caption(f"Selected File: {filename}")
            else:
                st.warning("Step 3에서 생성된 scene 이미지가 없습니다. 먼저 Scene Generation을 진행하세요.")

        st.divider()
        with st.container(border=True):
            st.markdown("###### Prompt Source Control")
            st.radio(
                "Prompt Source",
                options=["Preserve Original Scene Prompt", "Use Camera Angle Prompt"],
                index=1,
                key="camera_prompt_source",
                help=("Preserve Original Scene Prompt는 기존 scene description을 유지하고, " "Use Camera Angle Prompt는 Qwen Multi-Angle Camera의 앵글 제어 프롬프트를 사용합니다."),
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
                    st.slider("Horizontal Angle", min_value=-180, max_value=180, value=0, step=1, key="camera_horizontal_angle", help="좌우 시점 변화를 제어합니다.")
                    st.slider("Vertical Angle", min_value=-90, max_value=90, value=0, step=1, key="camera_vertical_angle", help="상하 시점 변화를 제어합니다.")

                with angle_col2:
                    st.slider("Zoom", min_value=0, max_value=10, value=5, step=1, key="camera_zoom", help="카메라 줌 강도를 제어합니다.")
                    st.checkbox("Use Default Angle Prompts", value=True, key="camera_default_prompts", help="Qwen Multi-Angle Camera의 기본 프롬프트를 사용합니다.")
                    st.checkbox("Enable Camera View Mode", value=False, key="camera_view", help="카메라 관점 중심의 view 해석을 활성화합니다.")
        else:
            st.info("Camera Angle Control is available only when 'Use Camera Angle Prompt' is selected.")

        with st.expander("Camera Refinement Guide", expanded=False):
            st.markdown(
                """
                - Step 4는 Step 3에서 생성된 장면을 입력으로 받아 카메라 앵글을 다시 조정하는 단계입니다.
                - Preserve Original Scene Prompt는 기존 storyboard scene description을 유지하는 모드입니다.
                - Use Camera Angle Prompt는 Qwen Multi-Angle Camera가 생성한 앵글 제어 프롬프트를 사용하는 모드입니다.
                - Horizontal Angle은 좌/우 시점 변화를, Vertical Angle은 상/하 시점 변화를 의미합니다.
                - Zoom은 인물 및 장면의 프레이밍 강도를 조정합니다.
                """
            )

        st.divider()
        generate_camera_clicked = st.button("Generate Camera-Refined Scene", type="primary", use_container_width=True)

        if generate_camera_clicked:
            storyboard_input = build_storyboard_input_config()["storyboard_input"]

            if not scene_candidates:
                st.error("Step 3 결과 이미지가 없습니다. 먼저 Scene Generation을 진행하세요.")
            elif st.session_state.get("camera_prompt_source") == "Preserve Original Scene Prompt" and storyboard_input["selected_shot_count"] == 0:
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

# from backend import run_csv_parser_test, run_face_generation

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


# def build_storyboard_input_config():
#     """
#     Step 1에서 업로드/선택된 storyboard 입력값을
#     Step 2, Step 3, Step 4에서 공통으로 사용할 수 있는 형태로 정리합니다.

#     이 함수는 RunComfy를 직접 호출하지 않습니다.
#     이후 각 branch workflow에 넘길 공통 입력값을 준비하는 역할만 합니다.
#     """
#     csv_text = st.session_state.get("csv_text", "")
#     shot_filter_mode = st.session_state.get("shot_filter_mode", "ALL")
#     custom_shots = st.session_state.get("custom_shots", [])

#     selected_shot_df = get_selected_shot_dataframe()

#     if shot_filter_mode == "ALL":
#         shot_filter = "ALL"
#         custom_shot_ids = ""
#     else:
#         shot_filter = "CUSTOM"
#         custom_shot_ids = ", ".join([str(x) for x in custom_shots])

#     return {
#         "storyboard_input": {
#             "csv_text": csv_text,
#             "shot_filter": shot_filter,
#             "custom_shot_ids": custom_shot_ids,
#             "selected_shot_count": len(selected_shot_df),
#             "selected_shot_data": selected_shot_df.to_dict(orient="records"),
#         }
#     }


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


# def initialize_body_prompts():
#     if "body_prompt_c1" not in st.session_state:
#         st.session_state["body_prompt_c1"] = ""

#     if "body_prompt_c2" not in st.session_state:
#         st.session_state["body_prompt_c2"] = ""


# def get_scene_shot_filter_config():
#     storyboard_input = build_storyboard_input_config()["storyboard_input"]

#     return (
#         storyboard_input["shot_filter"],
#         storyboard_input["custom_shot_ids"],
#     )


# def get_body_reference_candidates(character_code):
#     """
#     character_code: 'c1' or 'c2'

#     Step 2B에서 여러 body 후보를 저장해둔 경우:
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


# def get_face_reference_candidates(character_code):
#     """
#     character_code: 'c1' or 'c2'

#     Step 2A에서 여러 face 후보를 저장해둔 경우:
#     st.session_state["face_candidates_c1"] = [
#         {"label": "Boy Face 1", "image": ..., "filename": "..."},
#         {"label": "Boy Face 2", "image": ..., "filename": "..."},
#     ]

#     후보 리스트가 없으면 face_result_image_c1 / face_result_image_c2를 단일 후보로 fallback.
#     """
#     candidates_key = f"face_candidates_{character_code}"
#     candidates = st.session_state.get(candidates_key, [])

#     normalized = []

#     for i, item in enumerate(candidates, start=1):
#         if not isinstance(item, dict):
#             continue

#         normalized.append(
#             {
#                 "label": item.get(
#                     "label",
#                     f"{'Boy' if character_code == 'c1' else 'Girl'} Face {i}",
#                 ),
#                 "image": item.get("image"),
#                 "filename": item.get("filename", ""),
#             }
#         )

#     fallback_image = st.session_state.get(f"face_result_image_{character_code}")
#     fallback_filename = st.session_state.get(
#         f"face_result_filename_{character_code}",
#         "",
#     )

#     if not normalized and fallback_image is not None:
#         normalized.append(
#             {
#                 "label": f"{'Boy' if character_code == 'c1' else 'Girl'} Face 1",
#                 "image": fallback_image,
#                 "filename": fallback_filename,
#             }
#         )

#     return normalized


# def apply_selected_face_result(character_code):
#     selected_label = st.session_state.get(f"face_selected_label_{character_code}", "")
#     candidates = get_face_reference_candidates(character_code)
#     selected_candidate = get_selected_candidate(candidates, selected_label)

#     if selected_candidate and selected_candidate.get("image") is not None:
#         st.session_state[f"face_result_image_{character_code}"] = selected_candidate["image"]
#         st.session_state[f"face_result_filename_{character_code}"] = selected_candidate.get("filename", "")

#         selected_order = st.session_state.get("selected_face_reference_order", [])
#         if character_code not in selected_order:
#             selected_order.append(character_code)
#             st.session_state["selected_face_reference_order"] = selected_order

#     return selected_candidate


# def get_selected_face_reference_entries():
#     """
#     Selected Face Reference 영역에 표시할 최종 선택 이미지 목록을 반환합니다.

#     - 먼저 선택된 캐릭터가 먼저 표시됩니다.
#     - 이후 다른 캐릭터를 선택하면 기존 이미지 옆에 추가됩니다.
#     - order가 없지만 face_result_image가 존재하는 경우에도 누락되지 않도록 보정합니다.
#     """
#     selected_order = st.session_state.get("selected_face_reference_order", [])
#     character_codes = ["c1", "c2"]

#     display_order = [code for code in selected_order if code in character_codes]

#     for code in character_codes:
#         if code not in display_order and st.session_state.get(f"face_result_image_{code}") is not None:
#             display_order.append(code)

#     entries = []

#     for code in display_order:
#         image = st.session_state.get(f"face_result_image_{code}")

#         if image is None:
#             continue

#         if code == "c1":
#             label = "Image 1 - Boy"
#             display_label = "Selected Boy"
#         else:
#             label = "Image 2 - Girl"
#             display_label = "Selected Girl"

#         entries.append(
#             {
#                 "code": code,
#                 "label": label,
#                 "display_label": display_label,
#                 "image": image,
#                 "filename": st.session_state.get(f"face_result_filename_{code}", ""),
#             }
#         )

#     return entries


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
#     storyboard_input = build_storyboard_input_config()["storyboard_input"]

#     return {
#         "storyboard_input": storyboard_input,
#         "csvstoryboardparser": {
#             "input_mode": "text",
#             "csv_file": "CUSTOM",
#             "csv_text": storyboard_input["csv_text"],
#             "shot_filter": storyboard_input["shot_filter"],
#             "custom_shot_ids": storyboard_input["custom_shot_ids"],
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
#     storyboard_input = build_storyboard_input_config()["storyboard_input"]

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

#     return {
#         "storyboard_input": storyboard_input,
#         "scene_generation": {
#             "shot_filter": storyboard_input["shot_filter"],
#             "custom_shot_ids": storyboard_input["custom_shot_ids"],
#             "selected_shot_count": storyboard_input["selected_shot_count"],
#             "selected_shot_data": storyboard_input["selected_shot_data"],
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
#         },
#     }


# def get_scene_result_candidates():
#     """
#     Step 3에서 생성된 scene 후보를 Step 4 입력 이미지로 사용하기 위한 helper.

#     st.session_state["scene_candidates"] = [
#         {"label": "Scene 1", "image": ..., "filename": "..."},
#         {"label": "Scene 2", "image": ..., "filename": "..."},
#     ]

#     후보 리스트가 없으면 scene_result_image를 단일 후보로 fallback.
#     """
#     candidates = st.session_state.get("scene_candidates", [])
#     normalized = []

#     for i, item in enumerate(candidates, start=1):
#         if not isinstance(item, dict):
#             continue

#         normalized.append(
#             {
#                 "label": item.get("label", f"Scene {i}"),
#                 "image": item.get("image"),
#                 "filename": item.get("filename", ""),
#             }
#         )

#     fallback_image = st.session_state.get("scene_result_image")
#     fallback_filename = st.session_state.get("scene_result_filename", "")

#     if not normalized and fallback_image is not None:
#         normalized.append(
#             {
#                 "label": "Scene 1",
#                 "image": fallback_image,
#                 "filename": fallback_filename,
#             }
#         )

#     return normalized


# def build_camera_refinement_ui_config():
#     storyboard_input = build_storyboard_input_config()["storyboard_input"]

#     scene_candidates = get_scene_result_candidates()
#     selected_scene = get_selected_candidate(
#         scene_candidates,
#         st.session_state.get("camera_input_scene_label", ""),
#     )

#     prompt_source = st.session_state.get(
#         "camera_prompt_source",
#         "Use Camera Angle Prompt",
#     )

#     switch_setting = 1 if prompt_source == "Preserve Original Scene Prompt" else 2

#     return {
#         "storyboard_input": storyboard_input,
#         "camera_angle_refinement": {
#             "input_scene": {
#                 "label": selected_scene["label"] if selected_scene else "",
#                 "filename": selected_scene.get("filename", "") if selected_scene else "",
#             },
#             "selected_shot_count": storyboard_input["selected_shot_count"],
#             "selected_shot_data": storyboard_input["selected_shot_data"],
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
#         },
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
# st.caption(
#     "A ComfyUI-based generation pipeline for character-consistent cinematic storyboard creation and camera-angle refinement"
# )


# # =========================
# # Tabs
# # =========================
# tab1, tab2, tab3, tab4 = st.tabs(
#     [
#         "Step 1. Storyboard Data",
#         "Step 2. Character Reference",
#         "Step 3. Scene Generation",
#         "Step 4. Camera Refinement",
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

#             st.divider()
            
#             st.subheader("RunComfy CSV Parser Test")
            
#             st.caption(
#                 "Step 1에서 업로드한 CSV가 RunComfy의 CSVStoryboardParser까지 정상적으로 전달되는지 먼저 확인합니다."
#             )
            
#             csv_parser_test_disabled = not bool(st.session_state.get("csv_text", "").strip())
            
#             if st.button(
#                 "Test CSV Parser on RunComfy",
#                 type="secondary",
#                 disabled=csv_parser_test_disabled,
#             ):
#                 try:
#                     api_key = st.secrets["RUNCOMFY_API_KEY"]
#                     deployment_id = st.secrets["DEPLOYMENT_ID"]
            
#                     storyboard_input_config = build_storyboard_input_config()
            
#                     with st.spinner("RunComfy에서 CSVStoryboardParser 테스트를 실행하는 중입니다..."):
#                         result = run_csv_parser_test(
#                             api_key=api_key,
#                             deployment_id=deployment_id,
#                             storyboard_input_config=storyboard_input_config,
#                             poll_interval=5,
#                             timeout_seconds=900,
#                         )
            
#                     st.session_state["csv_parser_test_result"] = result
#                     st.session_state["csv_parser_test_images"] = result.get("images", [])
            
#                     images = result.get("images", [])
            
#                     if images:
#                         st.success("CSV Parser Test 성공: RunComfy에서 output image가 반환되었습니다.")
#                     else:
#                         st.success(
#                             "CSV Parser Test 완료: RunComfy에서 workflow가 정상 실행되었습니다. "
#                             "현재 테스트 workflow에는 SaveImage가 없으므로 image output이 비어 있는 것은 정상입니다."
#                         )
            
#                     st.rerun()
            
#                 except KeyError:
#                     st.error("RunComfy secret 설정이 없습니다.")
#                     st.caption("`.streamlit/secrets.toml`에 RUNCOMFY_API_KEY와 DEPLOYMENT_ID를 추가해야 합니다.")
            
#                 except Exception as e:
#                     st.error("RunComfy CSV Parser Test 실행 중 오류가 발생했습니다.")
#                     st.exception(e)
            
#                     with st.expander("Debug: Storyboard Input Config", expanded=False):
#                         st.json(build_storyboard_input_config())
            
            
#             csv_parser_test_result = st.session_state.get("csv_parser_test_result")
#             csv_parser_test_images = st.session_state.get("csv_parser_test_images", [])
            
#             if csv_parser_test_result:
#                 st.markdown("#### CSV Parser Test Result")
            
#                 if csv_parser_test_images:
#                     cols = st.columns(min(len(csv_parser_test_images), 3))
            
#                     for idx, image_item in enumerate(csv_parser_test_images):
#                         with cols[idx % len(cols)]:
#                             st.image(
#                                 image_item.get("url", ""),
#                                 caption=image_item.get("filename", f"CSV Parser Test Output {idx + 1}"),
#                                 use_container_width=True,
#                             )
#                 else:
#                     st.info(
#                             "CSV Parser Test workflow는 텍스트/JSON 출력 검증용이며 SaveImage가 없기 때문에 image output은 표시되지 않습니다."
#                         )
            
#                 with st.expander("Debug: RunComfy Request", expanded=False):
#                     st.json(csv_parser_test_result.get("request", {}))
            
#                 with st.expander("Debug: RunComfy Result", expanded=False):
#                     st.json(csv_parser_test_result.get("result", {}))
            
#                 with st.expander("Debug: Patched workflow_api_json", expanded=False):
#                     st.json(csv_parser_test_result.get("workflow_api_json", {}))

#     else:
#         st.info(
#             "CSV 파일을 업로드하면 Parsed Storyboard Data Preview와 Shot Selection Control이 표시됩니다."
#         )


# # =========================
# # Step 2. Character Reference Generation
# # =========================
# with tab2:
#     st.header("Step 2. Character Reference Generation")
#     st.caption(
#         "Generate face identity references first, then convert them into full-body references for scene generation."
#     )

#     with st.container(border=True):
#         st.markdown("#### Character Reference Pipeline")
#         st.markdown("**Face Identity** → **Full-Body Reference** → **Scene Input**")
#         st.caption(
#             "2A defines each character's visual identity, and 2B converts that identity into full-body references used by Scene Generation."
#         )

#     with st.container(border=True):
#         st.markdown("## 2A. Character Identity Generation")

#         preview_col, settings_col = st.columns([1.25, 1.15], gap="large")

#         with preview_col:
#             st.subheader("Character Identity Preview")

#             active_character_label = st.session_state.get(
#                 "character_filter_label",
#                 "Image 2 - Girl",
#             )
#             active_character_code = (
#                 "c1" if active_character_label == "Image 1 - Boy" else "c2"
#             )
#             active_candidates = get_face_reference_candidates(active_character_code)
#             apply_selected_face_result(active_character_code)

#             st.caption(
#                 f"Current Target: {active_character_label} | Generated candidates appear at the top, and the selected final reference appears below."
#             )

#             if active_candidates:
#                 st.markdown(f"#### {active_character_label} Candidate Images")

#                 candidate_cols = st.columns(len(active_candidates), gap="small")

#                 for idx, candidate in enumerate(active_candidates):
#                     with candidate_cols[idx]:
#                         if candidate.get("image") is not None:
#                             st.image(
#                                 candidate["image"],
#                                 caption=candidate["label"],
#                                 # use_container_width=True,
#                                 width=220,
#                             )
#                         else:
#                             render_empty_preview_box(
#                                 f"{candidate['label']} preview is not available.",
#                                 180,
#                             )

#                 st.radio(
#                     "Select Face Candidate",
#                     options=[item["label"] for item in active_candidates],
#                     horizontal=True,
#                     key=f"face_selected_label_{active_character_code}",
#                     help="생성된 후보 중 최종 reference로 사용할 얼굴 이미지를 선택합니다.",
#                 )

#                 apply_selected_face_result(active_character_code)

#             else:
#                 render_empty_preview_box(
#                     f"{active_character_label} candidate images will appear here after generation.",
#                     180,
#                 )

#             st.markdown("#### Selected Face Reference")

#             selected_face_entries = get_selected_face_reference_entries()

#             if selected_face_entries:
#                 selected_cols = st.columns(len(selected_face_entries), gap="small")

#                 for idx, entry in enumerate(selected_face_entries):
#                     with selected_cols[idx]:
#                         st.markdown(f"##### {entry['display_label']}")
#                         st.caption(entry["label"])

#                         st.image(
#                             entry["image"],
#                             caption=f"{entry['display_label']} Face Reference",
#                             # use_container_width=True,
#                             width=220,
#                         )
#             else:
#                 render_empty_preview_box(
#                     "Selected face references will appear here. Choose a candidate for Image 1 - Boy and Image 2 - Girl.",
#                     300,
#                 )

#         with settings_col:
#             st.subheader("Target Character Control")

#             st.radio(
#                 "character_filter",
#                 options=["Image 1 - Boy", "Image 2 - Girl"],
#                 index=1,
#                 horizontal=True,
#                 key="character_filter_label",
#                 help="UI에서는 Image 1 / Image 2로 표시하고, workflow에는 C1 / C2로 전달합니다.",
#             )

#             with st.expander("Identity Attribute Controls", expanded=True):
#                 with st.container(border=True):
#                     st.markdown("###### Core Identity")

#                     basic_col1, basic_col2 = st.columns(2)

#                     with basic_col1:
#                         st.slider(
#                             "Age",
#                             min_value=1,
#                             max_value=100,
#                             value=9,
#                             step=1,
#                             key="age",
#                         )

#                     with basic_col2:
#                         st.selectbox(
#                             "Nationality",
#                             options=[
#                                 "South Korean",
#                                 "Korean",
#                                 "East Asian",
#                                 "Japanese",
#                                 "Chinese",
#                             ],
#                             index=0,
#                             key="nationality",
#                         )

#                 with st.container(border=True):
#                     st.markdown("###### Face")

#                     face_col1, face_col2, face_col3 = st.columns(3)

#                     with face_col1:
#                         st.selectbox(
#                             "Body Type",
#                             options=[
#                                 "Beefy",
#                                 "Buxom",
#                                 "Buff",
#                                 "Chubby",
#                                 "Curvy",
#                                 "Fat",
#                                 "Fit",
#                                 "Flyweight",
#                                 "Hefty",
#                                 "Large",
#                                 "Lanky",
#                                 "Midweight",
#                                 "Morbidly obese",
#                                 "Muscular",
#                                 "Obese",
#                                 "Overweight",
#                                 "Petite",
#                                 "Plump",
#                                 "Portly",
#                                 "Rotund",
#                                 "Short",
#                                 "Skinny",
#                                 "Slight",
#                                 "Slim",
#                                 "Small",
#                                 "Stout",
#                                 "Stocky",
#                                 "Tall",
#                                 "Thick",
#                                 "Tiny",
#                                 "Voluptuous",
#                                 "Well-built",
#                                 "Well-endowed",
#                                 "Underweight",
#                             ],
#                             index=23,
#                             key="body_type",
#                         )

#                     with face_col2:
#                         st.selectbox(
#                             "Face Shape",
#                             options=[
#                                 "Circle",
#                                 "Diamond",
#                                 "Heart",
#                                 "Heart with Pointed Chin",
#                                 "Heart with Rounded Chin",
#                                 "Heart with V-Shape Chin",
#                                 "Inverted Triangle",
#                                 "Long",
#                                 "Oblong",
#                                 "Oval",
#                                 "Pear",
#                                 "Rectangle",
#                                 "Round",
#                                 "Round with Defined Cheekbones",
#                                 "Round with High Cheekbones",
#                                 "Round with Soft Cheekbones",
#                                 "Square",
#                                 "Square Oval",
#                                 "Square Round",
#                                 "Square with Rounded Jaw",
#                                 "Square with Sharp Jaw",
#                                 "Square with Soft Jaw",
#                                 "Triangle",
#                             ],
#                             index=21,
#                             key="face_shape",
#                         )

#                     with face_col3:
#                         st.selectbox(
#                             "Expression",
#                             options=[
#                                 "Amused",
#                                 "Angry",
#                                 "Anxious",
#                                 "Bored",
#                                 "Calm",
#                                 "Cautious",
#                                 "Confused",
#                                 "Contemptuous",
#                                 "Content",
#                                 "Curious",
#                                 "Disappointed",
#                                 "Disgusted",
#                                 "Envious",
#                                 "Excited",
#                                 "Fearful",
#                                 "Happy",
#                                 "In love",
#                                 "Nervous",
#                                 "Peaceful",
#                                 "Pensive",
#                                 "Prideful",
#                                 "Proud",
#                                 "Relieved",
#                                 "Sad",
#                                 "Sarcastic",
#                                 "Serene",
#                                 "Serious",
#                                 "Shy",
#                                 "Silly",
#                                 "Smiling",
#                                 "Surprised",
#                                 "Surprised and Amused",
#                             ],
#                             index=9,
#                             key="facial_expression",
#                         )

#                 with st.container(border=True):
#                     st.markdown("###### Eyes / Lips")

#                     eye_col1, eye_col2 = st.columns(2)

#                     with eye_col1:
#                         st.selectbox(
#                             "Eyes Color",
#                             options=[
#                                 "Albino",
#                                 "Amber",
#                                 "Brown",
#                                 "Dark Brown",
#                                 "Black",
#                                 "Hazel",
#                                 "Blue",
#                                 "Green",
#                                 "Gray", 
#                             ],
#                             index=2,
#                             key="eyes_color",
#                         )

#                         st.selectbox(
#                             "Eyes Shape",
#                             options=[
#                                 "Almond Eyes Shape",
#                                 "Asian Eyes Shape",
#                                 "Close-Set Eyes Shape",
#                                 "Deep Set Eyes Shape",
#                                 "Downturned Eyes Shape",
#                                 "Double Eyelid Eyes Shape",
#                                 "Hooded Eyes Shape",
#                                 "Monolid Eyes Shape",
#                                 "Oval Eyes Shape",
#                                 "Protruding Eyes Shape",
#                                 "Round Eyes Shape",
#                                 "Upturned Eyes Shape",
#                             ],
#                             index=1,
#                             key="eyes_shape",
#                         )

#                     with eye_col2:
#                         st.selectbox(
#                             "Lips Color",
#                             options=[
#                                 "Berry Lips",
#                                 "Black Lips",
#                                 "Blue Lips",
#                                 "Brown Lips",
#                                 "Burgundy Lips",
#                                 "Coral Lips",
#                                 "Glossy Red Lips",
#                                 "Mauve Lips",
#                                 "Orange Lips",
#                                 "Peach Lips",
#                                 "Pink Lips",
#                                 "Plum Lips",
#                                 "Purple Lips",
#                                 "Red Lips",
#                                 "Yellow Lips",
#                             ],
#                             index=9,
#                             key="lips_color",
#                         )

#                         st.selectbox(
#                             "Lips Shape",
#                             options=[
#                                 "Biting Lips",
#                                 "Bow-shaped Lips",
#                                 "Closed Lips",
#                                 "Cupid's Bow Lips",
#                                 "Defined Cupid's Bow Lips",
#                                 "Flat Cupid's Bow Lips",
#                                 "Full Lips",
#                                 "Heart-shaped Lips",
#                                 "Large Lips",
#                                 "Medium Lips",
#                                 "Neutral Lips",
#                                 "Parted Lips",
#                                 "Plump Lips",
#                                 "Pouting Lips",
#                                 "Round Lips",
#                                 "Small Lips",
#                                 "Smiling Lips",
#                                 "Soft Cupid's Bow Lips",
#                                 "Thin Lips",
#                                 "Upper Lip Mole Lips",
#                                 "Wide Lips",
#                             ],
#                             index=18,
#                             key="lips_shape",
#                         )

#                 with st.container(border=True):
#                     st.markdown("###### Hair")

#                     hair_col1, hair_col2, hair_col3 = st.columns(3)

#                     with hair_col1:
#                         st.selectbox(
#                             "Hair Style",
#                             options=[
#                                 "Afro",
#                                 "A-line bob",
#                                 "Asymmetrical",
#                                 "Balayage",
#                                 "Bald",
#                                 "Ballerina bun",
#                                 "Bangs",
#                                 "Beehive",
#                                 "Beehivecut",
#                                 "Bleached spikes",
#                                 "Blunt bob",
#                                 "Blunt",
#                                 "Bob",
#                                 "Bouffant",
#                                 "Bowl",
#                                 "Box braids",
#                                 "Box fade",
#                                 "Braided",
#                                 "Braided bob",
#                                 "Braided pigtails",
#                                 "Brave shortcut with shaved sides",
#                                 "Bushy",
#                                 "Buzz",
#                                 "Caesar",
#                                 "Chignon",
#                                 "Choppy",
#                                 "Cloudy",
#                                 "Cornrows",
#                                 "Crew",
#                                 "Curly",
#                                 "Curly bob",
#                                 "Curly Frizzy",
#                                 "Curtain bangs",
#                                 "Deep side part",
#                                 "Double Bun",
#                                 "Dreadlocks",
#                                 "Faded afro",
#                                 "Faux hawk",
#                                 "Faux hawk short pixie",
#                                 "Feathered",
#                                 "Female bald",
#                                 "Fishtail braids",
#                                 "Flat topcut",
#                                 "French bob",
#                                 "French braids",
#                                 "French twist",
#                                 "Frohawk",
#                                 "Hair ringlets",
#                                 "High ponytail",
#                                 "High skin fade",
#                                 "Honey",
#                                 "Italian bob",
#                                 "Layered",
#                                 "Lemonade braids",
#                                 "Long bob",
#                                 "Long with bangs",
#                                 "Long pixie",
#                                 "Long ponytail",
#                                 "Long straight",
#                                 "Loose Curly Afro",
#                                 "Marmaid waves",
#                                 "Micro braids",
#                                 "Middle part ponytails",
#                                 "Modern caesar",
#                                 "Mohawk",
#                                 "Multicolored",
#                                 "Pastel",
#                                 "Pigtails",
#                                 "Pixie",
#                                 "Platinum",
#                                 "Pompadour",
#                                 "Quiff",
#                                 "Razor fade with curls",
#                                 "Red",
#                                 "Right side shaved",
#                                 "Salt and pepper",
#                                 "Shag",
#                                 "Short curly",
#                                 "Short curly pixie",
#                                 "Short",
#                                 "Short messy curls",
#                                 "Shoulder Length with Bangs",
#                                 "Shoulder length straight",
#                                 "Side braid",
#                                 "Side Part Comb-Overstyle With High Fade",
#                                 "Side-swept bangs",
#                                 "Side-swept fringe",
#                                 "Sideswept pixie",
#                                 "Smooth lob",
#                                 "Space buns",
#                                 "Spiky",
#                                 "Stacked bob",
#                                 "Stacked Curls in Short Bob",
#                                 "Stitch braids",
#                                 "Strawberry",
#                                 "Strawberry blonde",
#                                 "Sweeping pixie",
#                                 "Taper fade with waves",
#                                 "Taperedcut with shaved side",
#                                 "Textured brush back",
#                                 "Textured",
#                                 "Tomboy",
#                                 "Top Knot",
#                                 "Twin braids",
#                                 "Twintails",
#                                 "Two dutch braids",
#                                 "Undercut",
#                                 "Updo",
#                                 "Very long wave",
#                                 "Waterfall braids",
#                                 "Wavy",
#                                 "Wavy bob",
#                                 "Wavy with curtain bangs",
#                                 "Wavy French Bob Vibes from 1920",
#                                 "Wavy undercut",
#                             ],
#                             index=12,  # Bob 기본 선택
#                             key="hair_style",
#                         )

#                     with hair_col2:
#                         st.selectbox(
#                             "Hair Color",
#                             options=[
#                                 "Auburn",
#                                 "Black",
#                                 "Blonde",
#                                 "Burgundy",
#                                 "Caramel",
#                                 "Chestnut",
#                                 "Chocolate",
#                                 "Copper",
#                                 "Dirty",
#                                 "Gray",
#                                 "Honey",
#                                 "Jet Black",
#                                 "Mahogany",
#                                 "Multicolored",
#                                 "Pastel",
#                                 "Platinum",
#                                 "Red",
#                                 "Salt and pepper",
#                                 "Silver",
#                                 "Strawberry",
#                                 "White",
#                             ],
#                             index=5,
#                             key="hair_color",
#                         )

#                     with hair_col3:
#                         st.selectbox(
#                             "Hair Length",
#                             options=["-", "Short", "Medium", "Long"],
#                             index=0,
#                             key="hair_length",
#                         )

#             with st.expander("Fine-Grained Appearance Attributes", expanded=False):
#                 skin_keys = list(SKIN_DEFAULTS.keys())
#                 skin_cols = st.columns(3)

#                 for i, key in enumerate(skin_keys):
#                     with skin_cols[i % 3]:
#                         default_checked = SKIN_DEFAULTS[key] > 0

#                         st.checkbox(
#                             key,
#                             value=default_checked,
#                             key=f"skin_{key}",
#                         )

#             st.divider()

#             generate_clicked = st.button(
#                 "Generate Character Identity",
#                 type="primary",
#                 # use_container_width=True,
#                 width=220,
#             )
            
#             if generate_clicked:
#                 csv_text = st.session_state.get("csv_text", "")
            
#                 if not csv_text.strip():
#                     st.error("먼저 Step 1에서 CSV 파일을 업로드해야 합니다.")
            
#                 elif (
#                     st.session_state.get("shot_filter_mode", "ALL") == "CUSTOM"
#                     and len(st.session_state.get("custom_shots", [])) == 0
#                 ):
#                     st.error("shot_filter가 CUSTOM이면 최소 1개 이상의 shot을 선택해야 합니다.")
            
#                 else:
#                     config = build_face_ui_config()
            
#                     character_filter = config["character_registry_parser"]["character_filter"]
#                     character_code = "c1" if character_filter == "C1" else "c2"
            
#                     try:
#                         api_key = st.secrets["RUNCOMFY_API_KEY"]
#                         deployment_id = st.secrets["DEPLOYMENT_ID"]
            
#                         with st.spinner("RunComfy에서 Character Identity를 생성하는 중입니다..."):
#                             result = run_face_generation(
#                                 api_key=api_key,
#                                 deployment_id=deployment_id,
#                                 config=config,
#                                 poll_interval=5,
#                                 timeout_seconds=900,
#                             )
            
#                         images = result.get("images", [])
#                         # --------------------------------DEBUG--------------------------------
#                         # st.write("DEBUG character_filter:", character_filter)
#                         # st.write("DEBUG character_code:", character_code)
#                         # st.write("DEBUG images:", images)
#                         # --------------------------------DEBUG--------------------------------
                        
#                         with st.expander("DEBUG Full Face Generation Result", expanded=True):
#                             st.json(result)
            
#                         if not images:
#                             st.error("RunComfy 실행은 완료되었지만 결과 이미지가 없습니다.")
            
#                             with st.expander("RunComfy Raw Result", expanded=False):
#                                 st.json(result)
            
#                             with st.expander("Collected Character Identity Config", expanded=False):
#                                 st.json(config)
            
#                         else:
#                             st.session_state[f"face_candidates_{character_code}"] = images
                        
#                             first_image = images[0]
                        
#                             st.session_state[f"face_result_image_{character_code}"] = first_image["image"]
#                             st.session_state[f"face_result_filename_{character_code}"] = first_image.get("filename", "")
#                             st.session_state[f"face_selected_label_{character_code}"] = first_image["label"]
                        
#                             selected_order = st.session_state.get("selected_face_reference_order", [])
                        
#                             if character_code not in selected_order:
#                                 selected_order.append(character_code)
                        
#                             st.session_state["selected_face_reference_order"] = selected_order
                        
#                             st.success("Character Identity 생성이 완료되었습니다.")
#                             st.rerun()
                            
#                             # --------------------------------DEBUG--------------------------------
#                             # st.write("DEBUG saved candidates:", st.session_state.get(f"face_candidates_{character_code}"))
#                             # st.write("DEBUG saved result image:", st.session_state.get(f"face_result_image_{character_code}"))
#                             # st.write("DEBUG saved filename:", st.session_state.get(f"face_result_filename_{character_code}"))
#                             # st.write("DEBUG saved selected label:", st.session_state.get(f"face_selected_label_{character_code}"))
                            
#                             # with st.expander("DEBUG Face Session State", expanded=True):
#                             #     st.write("face_candidates_c1:", st.session_state.get("face_candidates_c1"))
#                             #     st.write("face_candidates_c2:", st.session_state.get("face_candidates_c2"))
#                             #     st.write("face_result_image_c1:", st.session_state.get("face_result_image_c1"))
#                             #     st.write("face_result_image_c2:", st.session_state.get("face_result_image_c2"))
#                             #     st.write("face_selected_label_c1:", st.session_state.get("face_selected_label_c1"))
#                             #     st.write("face_selected_label_c2:", st.session_state.get("face_selected_label_c2"))
#                             #     st.write("selected_face_reference_order:", st.session_state.get("selected_face_reference_order"))
#                             # --------------------------------DEBUG--------------------------------
            
            
#                     except KeyError as e:
#                         st.error("RunComfy secret 설정이 없습니다.")
#                         st.caption("`.streamlit/secrets.toml`에 RUNCOMFY_API_KEY와 DEPLOYMENT_ID를 추가해야 합니다.")
#                         st.exception(e)
            
#                         with st.expander("Collected Character Identity Config", expanded=False):
#                             st.json(config)
            
#                     except Exception as e:
#                         st.error("RunComfy Character Identity 실행 중 오류가 발생했습니다.")
#                         st.exception(e)
            
#                         with st.expander("Collected Character Identity Config", expanded=False):
#                             st.json(config)

#     st.divider()

#     with st.container(border=True):
#         st.markdown("## 2B. Full-Body Reference Generation")

#         initialize_body_prompts()

#         preview_col, settings_col = st.columns([1.45, 1.25], gap="large")

#         with preview_col:
#             st.subheader("Full-Body Reference Preview")

#             body_preview_col1, body_preview_col2 = st.columns(2, gap="medium")

#             with body_preview_col1:
#                 st.markdown("#### Image 1 - Boy")

#                 if "body_result_image_c1" in st.session_state:
#                     st.image(
#                         st.session_state["body_result_image_c1"],
#                         caption="Image 1 - Boy Body Reference",
#                         # use_container_width=True,
#                         width=240,
#                     )
#                 else:
#                     render_empty_preview_box(
#                         "Image 1 - Boy body reference will appear here.",
#                         520,
#                     )

#             with body_preview_col2:
#                 st.markdown("#### Image 2 - Girl")

#                 if "body_result_image_c2" in st.session_state:
#                     st.image(
#                         st.session_state["body_result_image_c2"],
#                         caption="Image 2 - Girl Body Reference",
#                         # use_container_width=True,
#                         width=240,
#                     )
#                 else:
#                     render_empty_preview_box(
#                         "Image 2 - Girl body reference will appear here.",
#                         520,
#                     )

#         with settings_col:
#             st.subheader("Reference Generation Control")

#             st.radio(
#                 "body_character_filter",
#                 options=["Image 1 - Boy", "Image 2 - Girl"],
#                 index=0,
#                 horizontal=True,
#                 key="body_character_filter_label",
#                 help="UI에서는 Image 1 / Image 2로 표시하고, workflow에는 C1 / C2로 전달합니다.",
#             )

#             st.divider()

#             st.markdown("### Full-Body Prompt Editor")

#             selected_body_target = st.session_state.get(
#                 "body_character_filter_label",
#                 "Image 1 - Boy",
#             )

#             if selected_body_target == "Image 1 - Boy":
#                 st.text_area(
#                     "Image 1 - Boy Body Prompt",
#                     key="body_prompt_c1",
#                     height=260,
#                     placeholder=BODY_PROMPT_PLACEHOLDER,
#                     help="Image 1 - Boy의 전신 reference 생성을 위한 프롬프트입니다. 사용자가 직접 수정할 수 있습니다.",
#                 )

#             else:
#                 st.text_area(
#                     "Image 2 - Girl Body Prompt",
#                     key="body_prompt_c2",
#                     height=260,
#                     placeholder=BODY_PROMPT_PLACEHOLDER,
#                     help="Image 2 - Girl의 전신 reference 생성을 위한 프롬프트입니다. 사용자가 직접 수정할 수 있습니다.",
#                 )

#             with st.expander("Reference Prompt Guidelines", expanded=False):
#                 st.markdown(
#                     """
#                     - 얼굴 reference와 같은 인물로 보이도록 identity 유지 문장을 포함하는 것이 좋습니다.
#                     - 전신이 모두 보이도록 `full-body`, `head to toe`, `entire body visible` 표현을 포함하세요.
#                     - 의상은 상의, 하의, 양말, 신발까지 구체적으로 작성하는 것이 좋습니다.
#                     - 이후 Scene Generation에서 reference로 쓰기 좋게 `clean background`를 유지하는 것이 좋습니다.
#                     - 복잡한 포즈나 강한 카메라 앵글은 전신 reference 생성 단계에서는 피하는 것이 좋습니다.
#                     """
#                 )

#             st.divider()

#             generate_body_clicked = st.button(
#                 "Generate Full-Body Reference",
#                 type="primary",
#                 # use_container_width=True,
#                 width=220,
#             )

#             if generate_body_clicked:
#                 csv_text = st.session_state.get("csv_text", "")

#                 if not csv_text.strip():
#                     st.error("먼저 Step 1에서 CSV 파일을 업로드해야 합니다.")

#                 elif (
#                     st.session_state.get("shot_filter_mode", "ALL") == "CUSTOM"
#                     and len(st.session_state.get("custom_shots", [])) == 0
#                 ):
#                     st.error("shot_filter가 CUSTOM이면 최소 1개 이상의 shot을 선택해야 합니다.")

#                 else:
#                     body_config = build_body_ui_config()

#                     st.success("Body branch UI 입력값이 정상적으로 수집되었습니다.")
#                     st.subheader("Collected Full-Body Reference Config")
#                     st.json(body_config)


# # =========================
# # Step 3. Reference-Guided Scene Generation
# # =========================
# with tab3:
#     st.header("Step 3. Reference-Guided Scene Generation")

#     boy_candidates = get_body_reference_candidates("c1")
#     girl_candidates = get_body_reference_candidates("c2")

#     sync_scene_reference_selection("scene_boy_reference_label", boy_candidates)
#     sync_scene_reference_selection("scene_girl_reference_label", girl_candidates)

#     preview_col, settings_col = st.columns([1.45, 1.25], gap="large")

#     with preview_col:
#         st.subheader("Generated Storyboard Preview")

#         storyboard_input = build_storyboard_input_config()["storyboard_input"]

#         if storyboard_input["selected_shot_count"] == 0:
#             st.caption("Selected Storyboard Context: None")
#         else:
#             st.caption(f"Selected Scene Count: {storyboard_input['selected_shot_count']}")

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

#             storyboard_input = build_storyboard_input_config()["storyboard_input"]

#             if storyboard_input["selected_shot_count"] == 0:
#                 st.warning("표시할 scene 정보가 없습니다. Step 1에서 CSV와 shot 선택을 확인하세요.")
#             else:
#                 if storyboard_input["shot_filter"] == "ALL":
#                     st.caption(
#                         f"Shot Filter: ALL / {storyboard_input['selected_shot_count']} scene(s)"
#                     )
#                 elif storyboard_input["custom_shot_ids"]:
#                     st.caption(
#                         f"Shot Filter: CUSTOM / {storyboard_input['custom_shot_ids']}"
#                     )
#                 else:
#                     st.caption("Shot Filter: CUSTOM / No shot selected")

#                 st.dataframe(
#                     pd.DataFrame(storyboard_input["selected_shot_data"]),
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
#                     # use_container_width=True,
#                     width=240,
#                 )
#             else:
#                 render_empty_preview_box(
#                     "Selected boy body reference preview is not available.",
#                     220,
#                 )

#         else:
#             st.warning("Step 2에서 Image 1 - Boy body reference를 먼저 생성해야 합니다.")

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
#                     # use_container_width=True,
#                     width=240,
#                 )
#             else:
#                 render_empty_preview_box(
#                     "Selected girl body reference preview is not available.",
#                     220,
#                 )

#         else:
#             st.warning("Step 2에서 Image 2 - Girl body reference를 먼저 생성해야 합니다.")

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
#                 st.error("Image 1 - Boy body reference 후보가 없습니다. 먼저 Step 2를 진행하세요.")

#             elif not girl_candidates:
#                 st.error("Image 2 - Girl body reference 후보가 없습니다. 먼저 Step 2를 진행하세요.")

#             else:
#                 scene_config = build_scene_ui_config()

#                 st.success("Scene branch UI 입력값이 정상적으로 수집되었습니다.")
#                 st.subheader("Collected Scene Generation Config")
#                 st.json(scene_config)


# # =========================
# # Step 4. Camera Angle Refinement
# # =========================
# with tab4:
#     st.header("Step 4. Camera Angle Refinement")

#     scene_candidates = get_scene_result_candidates()
#     sync_scene_reference_selection("camera_input_scene_label", scene_candidates)

#     preview_col, settings_col = st.columns([1.6, 1.1], gap="large")

#     with preview_col:
#         st.subheader("Camera Refinement Preview")

#         st.markdown("#### Input Scene")

#         selected_input_scene = get_selected_candidate(
#             scene_candidates,
#             st.session_state.get("camera_input_scene_label", ""),
#         )

#         if selected_input_scene and selected_input_scene.get("image") is not None:
#             st.image(
#                 selected_input_scene["image"],
#                 caption=selected_input_scene["label"],
#                 use_container_width=True,
#             )
#         else:
#             render_empty_preview_box(
#                 "A generated scene from Step 3 will appear here.",
#                 360,
#             )

#         st.divider()

#         st.markdown("#### Refined Scene")

#         if "camera_refined_result_image" in st.session_state:
#             st.image(
#                 st.session_state["camera_refined_result_image"],
#                 caption="Camera-Refined Storyboard Scene",
#                 use_container_width=True,
#             )
#         else:
#             render_empty_preview_box(
#                 "The camera-refined scene will appear here.",
#                 360,
#             )

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
#                 st.warning("Step 3에서 생성된 scene 이미지가 없습니다. 먼저 Scene Generation을 진행하세요.")

#         st.divider()

#         with st.container(border=True):
#             st.markdown("###### Prompt Source Control")

#             st.radio(
#                 "Prompt Source",
#                 options=[
#                     "Preserve Original Scene Prompt",
#                     "Use Camera Angle Prompt",
#                 ],
#                 index=1,
#                 key="camera_prompt_source",
#                 help=(
#                     "Preserve Original Scene Prompt는 기존 scene description을 유지하고, "
#                     "Use Camera Angle Prompt는 Qwen Multi-Angle Camera의 앵글 제어 프롬프트를 사용합니다."
#                 ),
#             )

#             if st.session_state.get("camera_prompt_source") == "Preserve Original Scene Prompt":
#                 st.caption("TwoWaySwitch Selection: 1 (ScenePromptBuilder output)")
#             else:
#                 st.caption("TwoWaySwitch Selection: 2 (Qwen Multi-Angle Camera output)")

#         if st.session_state.get("camera_prompt_source") == "Use Camera Angle Prompt":
#             st.divider()

#             with st.container(border=True):
#                 st.markdown("###### Camera Angle Control")

#                 angle_col1, angle_col2 = st.columns(2)

#                 with angle_col1:
#                     st.slider(
#                         "Horizontal Angle",
#                         min_value=-180,
#                         max_value=180,
#                         value=0,
#                         step=1,
#                         key="camera_horizontal_angle",
#                         help="좌우 시점 변화를 제어합니다.",
#                     )

#                     st.slider(
#                         "Vertical Angle",
#                         min_value=-90,
#                         max_value=90,
#                         value=0,
#                         step=1,
#                         key="camera_vertical_angle",
#                         help="상하 시점 변화를 제어합니다.",
#                     )

#                 with angle_col2:
#                     st.slider(
#                         "Zoom",
#                         min_value=0,
#                         max_value=10,
#                         value=5,
#                         step=1,
#                         key="camera_zoom",
#                         help="카메라 줌 강도를 제어합니다.",
#                     )

#                     st.checkbox(
#                         "Use Default Angle Prompts",
#                         value=True,
#                         key="camera_default_prompts",
#                         help="Qwen Multi-Angle Camera의 기본 프롬프트를 사용합니다.",
#                     )

#                     st.checkbox(
#                         "Enable Camera View Mode",
#                         value=False,
#                         key="camera_view",
#                         help="카메라 관점 중심의 view 해석을 활성화합니다.",
#                     )

#         else:
#             st.info(
#                 "Camera Angle Control is available only when "
#                 "'Use Camera Angle Prompt' is selected."
#             )

#         with st.expander("Camera Refinement Guide", expanded=False):
#             st.markdown(
#                 """
#                 - Step 4는 Step 3에서 생성된 장면을 입력으로 받아 카메라 앵글을 다시 조정하는 단계입니다.
#                 - Preserve Original Scene Prompt는 기존 storyboard scene description을 유지하는 모드입니다.
#                 - Use Camera Angle Prompt는 Qwen Multi-Angle Camera가 생성한 앵글 제어 프롬프트를 사용하는 모드입니다.
#                 - Horizontal Angle은 좌/우 시점 변화를, Vertical Angle은 상/하 시점 변화를 의미합니다.
#                 - Zoom은 인물 및 장면의 프레이밍 강도를 조정합니다.
#                 """
#             )

#         st.divider()

#         generate_camera_clicked = st.button(
#             "Generate Camera-Refined Scene",
#             type="primary",
#             use_container_width=True,
#         )

#         if generate_camera_clicked:
#             storyboard_input = build_storyboard_input_config()["storyboard_input"]

#             if not scene_candidates:
#                 st.error("Step 3 결과 이미지가 없습니다. 먼저 Scene Generation을 진행하세요.")

#             elif (
#                 st.session_state.get("camera_prompt_source") == "Preserve Original Scene Prompt"
#                 and storyboard_input["selected_shot_count"] == 0
#             ):
#                 st.error("Preserve Original Scene Prompt를 사용하려면 Step 1의 shot 데이터가 필요합니다.")

#             else:
#                 camera_config = build_camera_refinement_ui_config()

#                 st.success("Camera refinement UI 입력값이 정상적으로 수집되었습니다.")
#                 st.subheader("Collected Camera Refinement Config")
#                 st.json(camera_config)




