import base64
import csv
import io
import pandas as pd
import streamlit as st
from preset_results import (apply_preset_2a_results,apply_preset_2b_results,apply_preset_step3_results,apply_preset_step4_results)
from backend import (run_face_generation, run_body_generation, run_scene_generation, run_camera_refinement)

# =============================================================================================================================
# 1. Feature Flags
# =============================================================================================================================
ENABLE_MANUAL_REFERENCE_INPUT = False

ENABLE_PRESET_2A_RESULTS = False
ENABLE_PRESET_2B_RESULTS = False
ENABLE_PRESET_STEP3_RESULTS = False
ENABLE_PRESET_STEP4_RESULTS = False

# =============================================================================================================================
# 2. UI Defaults
# =============================================================================================================================
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
NATIONALITY_OPTIONS = [
    "South Korean", "Korean", "East Asian",
    "Japanese", "Chinese"
]
HAIR_LENGTH_OPTIONS = ["-", "Short", "Medium", "Long"]

# =============================================================================================================================
# 3. File and Upload Helpers
# =============================================================================================================================

def decode_uploaded_file(uploaded_file):
    
    raw = uploaded_file.getvalue()
    
    for encoding in ["utf-8-sig", "cp949"]:
        try:
            return raw.decode(encoding)
        except UnicodeDecodeError:
            continue
            
    return raw.decode("utf-8", errors="ignore")


def uploaded_image_to_data_uri(uploaded_file):
    
    if uploaded_file is None:
        return ""

    raw = uploaded_file.getvalue()
    mime_type = getattr(uploaded_file, "type", None) or "image/png"

    encoded = base64.b64encode(raw).decode("ascii")
    
    return f"data:{mime_type};base64,{encoded}"


# =============================================================================================================================
# 4. CSV and Shot Helpers
# =============================================================================================================================

def read_csv_as_dataframe(csv_text):
    
    if not csv_text.strip():
        return pd.DataFrame()
    try:
        return pd.read_csv(io.StringIO(csv_text), dtype=str)
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


def extract_shot_ids_from_csv(csv_text):
    
    df = read_csv_as_dataframe(csv_text)

    shot_col = get_shot_id_column(df)

    if shot_col is None:
        return []

    shot_ids = df[shot_col].dropna().astype(str).str.strip()

    return shot_ids[shot_ids != ""].drop_duplicates().tolist()


def get_selected_shot_dataframe():
    
    csv_text = st.session_state.get("csv_text", "")
    df = read_csv_as_dataframe(csv_text)

    if df.empty:
        return pd.DataFrame()

    shot_col = get_shot_id_column(df)

    shot_filter_mode = st.session_state.get("shot_filter_mode", "ALL")
    custom_shots = st.session_state.get("custom_shots", [])

    if shot_filter_mode == "ALL":
        return df

    if not custom_shots:
        return pd.DataFrame()

    normalized_shot_ids = df[shot_col].fillna("").astype(str).str.strip()

    return df[normalized_shot_ids.isin([str(x).strip() for x in custom_shots])]


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


# =============================================================================================================================
# 5. Character and Outfit Helpers
# =============================================================================================================================

def character_label_to_value(label, default="C2"):
    return {"Image 1 - Boy": "C1", "Image 2 - Girl": "C2"}.get(label, default)


def initialize_outfit_reference_inputs():
    
    for character_code in ("c1", "c2"):
        st.session_state.setdefault(f"outfit_input_mode_{character_code}","Separate Garments")

        for garment in ("top", "bottom", "shoes", "single"):
            st.session_state.setdefault(f"outfit_{garment}_reference_{character_code}","")
            

def clear_outfit_reference_on_remove(upload_key, reference_key):
    if st.session_state.get(upload_key) is None:
        st.session_state.pop(reference_key, None)


def clear_downstream_results(step, character_code=None):

    if step == "2A":
        keys = [
            f"body_result_image_{character_code}",
            f"body_result_filename_{character_code}",
        ]
    else:
        keys = []

    if step in ("2A", "2B"):
        keys.extend([
            "scene_candidates",
            "scene_result_image",
            "scene_result_filename",
            "scene_selected_label",
        ])

    if step in ("2A", "2B", "3"):
        keys.extend([
            "camera_refined_candidates",
            "camera_refined_result_image",
            "camera_refined_result_filename",
            "camera_refined_selected_label",
            "camera_input_scene_label",
        ])

    for key in keys:
        st.session_state.pop(key, None)


# =============================================================================================================================
# 6. Scene Result Selection
# =============================================================================================================================

def get_selected_candidate(candidates, selected_label):
    
    for item in candidates:
        if item["label"] == selected_label:
            return item
    return None


def sync_scene_reference_selection(session_key, candidates):
    
    labels = [item["label"] for item in candidates]

    if not labels:
        st.session_state[session_key] = ""
        return

    if st.session_state.get(session_key) not in labels:
        st.session_state[session_key] = labels[0]


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


# =============================================================================================================================
# 7. Workflow Configuration Builders
# =============================================================================================================================

def build_face_ui_config():
    
    storyboard_input = build_storyboard_input_config()["storyboard_input"]
    
    skin_details = {}

    for key, default_value in SKIN_DEFAULTS.items():
        if st.session_state.get(f"skin_{key}", False):
            skin_details[key] = default_value
        else:
            skin_details[key] = 0.0

    return {
        "storyboard_input": storyboard_input,
        
        "character_registry_parser": {
            "character_filter": character_label_to_value(
                st.session_state.get("character_filter_label", "Image 2 - Girl")
            ),
            "custom_character_id": "",
            "age": st.session_state.get("age", 9),
            "include_character_id": "false",
        },

        "portrait_master_base_character": {
            "shot": "Full body",
            "nationality_1": st.session_state.get("nationality", "South Korean"),
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
        },
        
        "portrait_master_skin_details": skin_details,
    }


def build_body_ui_config():
    
    character_filter_label = st.session_state.get("body_character_filter_label", "Image 1 - Boy")

    character_filter = character_label_to_value(character_filter_label, default="C1")
    character_code = "c1" if character_filter == "C1" else "c2"

    label = "Image 1 - Boy" if character_code == "c1" else "Image 2 - Girl"
    character_image_url = st.session_state.get(f"face_result_image_{character_code}", "")
    character_filename = st.session_state.get(f"face_result_filename_{character_code}", "")

    input_mode = st.session_state.get(f"outfit_input_mode_{character_code}", "Separate Garments")

    return {
        "outfit_change": {
            "character_filter": character_filter,
            "character_code": character_code,
            "label": label,
            "character_image_url": character_image_url,
            "character_filename": character_filename,
            "input_mode": input_mode,
            "garment_references": {
                "top": st.session_state.get(
                    f"outfit_top_reference_{character_code}",
                    "",
                ).strip(),
                "bottom": st.session_state.get(
                    f"outfit_bottom_reference_{character_code}",
                    "",
                ).strip(),
                "shoes": st.session_state.get(
                    f"outfit_shoes_reference_{character_code}",
                    "",
                ).strip(),
            },
            "single_outfit_reference": st.session_state.get(
                f"outfit_single_reference_{character_code}",
                "",
            ).strip(),
        }
    }


def build_scene_ui_config():
    
    storyboard_input = build_storyboard_input_config()["storyboard_input"]

    boy_body_image = st.session_state.get("body_result_image_c1", "")
    boy_body_filename = st.session_state.get("body_result_filename_c1", "")

    girl_body_image = st.session_state.get("body_result_image_c2", "")
    girl_body_filename = st.session_state.get("body_result_filename_c2", "")

    return {
        "storyboard_input": storyboard_input,
        
        "scene_generation": {
            "reference_images": {
                "image_1_boy_body": {
                    "label": "Image 1 - Boy Character Reference",
                    "image": boy_body_image,
                    "filename": boy_body_filename,
                },
                "image_2_girl_body": {
                    "label": "Image 2 - Girl Character Reference",
                    "image": girl_body_image,
                    "filename": girl_body_filename,
                },
            },
        },
    }


def build_camera_refinement_ui_config():

    scene_candidates = get_scene_result_candidates()

    selected_scene = get_selected_candidate(scene_candidates, st.session_state.get("camera_input_scene_label", "")) or {}

    return {
        "camera_angle_refinement": {
            "input_scene": {
                "label": selected_scene.get("label", ""),
                "image": selected_scene.get("image", ""),
                "filename": selected_scene.get("filename", ""),
            },
            "camera_control": {
                "horizontal_angle": st.session_state.get("camera_horizontal_angle", 0),
                "vertical_angle": st.session_state.get("camera_vertical_angle", 0),
                "zoom": st.session_state.get("camera_zoom", 5),
                "default_prompts": st.session_state.get("camera_default_prompts", True),
                "camera_view": st.session_state.get("camera_view", False),
            },
        }
    }


# =============================================================================================================================
# 8. Image Preview UI
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


# =============================================================================================================================
# 9. Manual Reference Testing
# =============================================================================================================================

def clear_disabled_manual_reference_state():

    if ENABLE_MANUAL_REFERENCE_INPUT:
        return

    manual_input_keys = (
        "manual_face_reference_url",
        "manual_boy_face_reference_url",
        "manual_girl_face_reference_url",
        "manual_boy_body_reference_url",
        "manual_girl_body_reference_url",
        "manual_camera_scene_reference_url",
    )

    for key in manual_input_keys:
        st.session_state.pop(key, None)

    for result_prefix in ("face", "body"):
        for character_code in ("c1", "c2"):

            filename_key = f"{result_prefix}_result_filename_{character_code}"
            image_key = f"{result_prefix}_result_image_{character_code}"

            filename = str(st.session_state.get(filename_key, ""))

            if filename.startswith("manual_"):
                st.session_state.pop(filename_key, None)
                st.session_state.pop(image_key, None)

    scene_candidates = st.session_state.get("scene_candidates", [])

    if isinstance(scene_candidates, list):
        remaining_candidates = [
            item
            for item in scene_candidates
            if not (
                isinstance(item, dict)
                and (
                    item.get("label") == "Manual Camera Input Scene"
                    or str(item.get("filename", "")).startswith(
                        "manual_camera_input_scene"
                    )
                )
            )
        ]

        if remaining_candidates:
            st.session_state["scene_candidates"] = remaining_candidates
        else:
            st.session_state.pop("scene_candidates", None)

    scene_filename = str(
        st.session_state.get("scene_result_filename", "")
    )

    if scene_filename.startswith("manual_camera_input_scene"):
        for key in (
            "scene_result_image",
            "scene_result_filename",
            "scene_selected_label",
        ):
            st.session_state.pop(key, None)

    if st.session_state.get("camera_input_scene_label") == "Manual Camera Input Scene":
        st.session_state.pop("camera_input_scene_label", None)


def render_manual_reference_inputs():

    if not ENABLE_MANUAL_REFERENCE_INPUT:
        return

    with st.expander("Manual Reference Inputs (Testing)", expanded=False):
        st.caption("Enter image URLs to bypass generation in the corresponding step.")

        with st.form("manual_reference_inputs_form"):
            st.markdown("**Step 2A — Character Appearance**")
            face_boy_col, face_girl_col = st.columns(2)
            with face_boy_col:
                boy_face_url = st.text_input(
                    "Boy Appearance URL", key="manual_boy_face_reference_url"
                )
            with face_girl_col:
                girl_face_url = st.text_input(
                    "Girl Appearance URL", key="manual_girl_face_reference_url"
                )

            st.markdown("**Step 3 — Full-Body References (Step 2B results)**")
            body_boy_col, body_girl_col = st.columns(2)
            with body_boy_col:
                boy_body_url = st.text_input(
                    "Boy Full-Body URL", key="manual_boy_body_reference_url"
                )
            with body_girl_col:
                girl_body_url = st.text_input(
                    "Girl Full-Body URL", key="manual_girl_body_reference_url"
                )

            st.markdown("**Step 4 — Camera Input Scene**")
            scene_url = st.text_input(
                "Scene URL", key="manual_camera_scene_reference_url"
            )
            submitted = st.form_submit_button(
                "Apply Manual Reference URLs", use_container_width=True
            )

        if not submitted:
            return

        urls = {
            "Boy Appearance": boy_face_url.strip(),
            "Girl Appearance": girl_face_url.strip(),
            "Boy Full-Body": boy_body_url.strip(),
            "Girl Full-Body": girl_body_url.strip(),
            "Scene": scene_url.strip(),
        }
        if not any(urls.values()):
            st.error("Enter at least one reference URL.")
            return

        invalid_labels = [
            label for label, url in urls.items()
            if url and not url.lower().startswith(("https://", "http://"))
        ]
        if invalid_labels:
            st.error("URLs must start with http:// or https://: " + ", ".join(invalid_labels))
            return

        for label, code in (("Boy", "c1"), ("Girl", "c2")):
            face_url = urls[f"{label} Appearance"]
            if face_url:
                st.session_state[f"face_result_image_{code}"] = face_url
                st.session_state[f"face_result_filename_{code}"] = f"manual_{label.lower()}_face_reference.png"

            body_url = urls[f"{label} Full-Body"]
            if body_url:
                st.session_state[f"body_result_image_{code}"] = body_url
                st.session_state[f"body_result_filename_{code}"] = f"manual_{label.lower()}_body_reference.png"

        if urls["Scene"]:
            scene_item = {
                "label": "Manual Camera Input Scene",
                "image": urls["Scene"],
                "url": urls["Scene"],
                "filename": "manual_camera_input_scene.png",
            }
            st.session_state["scene_candidates"] = [scene_item]
            st.session_state["scene_result_image"] = urls["Scene"]
            st.session_state["scene_result_filename"] = scene_item["filename"]
            st.session_state["scene_selected_label"] = scene_item["label"]
            st.session_state["camera_input_scene_label"] = scene_item["label"]

        st.success("Manual reference URLs applied.")
        st.rerun()


# =============================================================================================================================
# Page Config
# =============================================================================================================================
st.set_page_config(
    page_title="AI Storyboard Pipeline",
    page_icon="🎬",
    layout="wide",
)

clear_disabled_manual_reference_state()

if ENABLE_PRESET_2A_RESULTS:
    apply_preset_2a_results()

if ENABLE_PRESET_2B_RESULTS:
    apply_preset_2b_results()

if ENABLE_PRESET_STEP3_RESULTS:
    apply_preset_step3_results()

if ENABLE_PRESET_STEP4_RESULTS:
    apply_preset_step4_results()

st.title("🎬 AI Storyboard Generation Pipeline")
st.caption("A ComfyUI-based generation pipeline for character-consistent cinematic storyboard creation and camera-angle refinement")

render_manual_reference_inputs()

# =============================================================================================================================
# Tabs
# =============================================================================================================================
tab1, tab2, tab3, tab4 = st.tabs(
    [
        "Step 1. Storyboard Data",
        "Step 2. Character Reference",
        "Step 3. Scene Generation",
        "Step 4. Camera Refinement",
    ]
)


# =============================================================================================================================
# Step 1. Storyboard Data Parsing
# =============================================================================================================================
with tab1:
    st.header("Step 1. Storyboard Data Parsing")

    uploaded_csv = st.file_uploader("Upload Storyboard CSV", type=["csv"])

    if uploaded_csv is not None:
        csv_text = decode_uploaded_file(uploaded_csv)

        if csv_text != st.session_state.get("csv_text", ""):
            st.session_state["custom_shots"] = []

        st.session_state["csv_text"] = csv_text
        st.success(f"Upload complete: {uploaded_csv.name}")

    else:
        csv_text = st.session_state.get("csv_text", "")

    if csv_text:
        with st.expander("Parsed Storyboard Data Preview", expanded=True):

            preview_df = read_csv_as_dataframe(csv_text)

            if not preview_df.empty:
                st.dataframe(preview_df, use_container_width=True, hide_index=True)
            else:
                st.warning("Unable to read CSV data or the CSV contains no rows.")
                st.code(csv_text)

        st.subheader("Shot Selection Control")

        shot_ids = extract_shot_ids_from_csv(csv_text)

        st.radio(
            "shot_filter",
            options=["ALL", "CUSTOM"],
            horizontal=True,
            key="shot_filter_mode",
            help="ALL selects all shots, while CUSTOM selects only specified shots",
        )

        if st.session_state.get("shot_filter_mode", "ALL") == "CUSTOM":

            if shot_ids:
                st.multiselect("Select Storyboard Shots", options=shot_ids, key="custom_shots",)
            else:
                st.warning("No Shot IDs were found in the CSV.")

    else:
        st.info("Upload a CSV file to display the storyboard data preview and shot selection controls.")


# =============================================================================================================================
# Step 2. Character Reference Generation
# =============================================================================================================================
with tab2:
    st.header("Step 2. Character Reference Generation")
    st.caption(
        "Generate character appearances first, then apply garment "
        "references to build the final character references for scene generation."
    )

    # ------------------- 2A. Character Appearance Generation ------------------- 
    with st.container(border=True):
        st.markdown("### 2A. Character Appearance Generation")

        preview_col, settings_col = st.columns([1.25, 1.15], gap="large")

        with preview_col:
            st.subheader("Character Appearance Preview")
        
            face_preview_col1, face_preview_col2 = st.columns(2, gap="medium")
        
            with face_preview_col1:
                st.markdown("##### Image 1 - Boy")
            
                if st.session_state.get("face_result_image_c1"):
                    render_image_preview_box(
                        st.session_state["face_result_image_c1"],
                        caption="Image 1 - Boy Appearance Reference",
                        height=400,
                    )
                else:
                    render_empty_preview_box(
                        "Image 1 - Boy appearance reference will appear here.",
                        400,
                    )
        
            with face_preview_col2:
                st.markdown("##### Image 2 - Girl")
            
                if st.session_state.get("face_result_image_c2"):
                    render_image_preview_box(
                        st.session_state["face_result_image_c2"],
                        caption="Image 2 - Girl Appearance Reference",
                        height=400,
                    )
                else:
                    render_empty_preview_box(
                        "Image 2 - Girl appearance reference will appear here.",
                        400,
                    )

            
        with settings_col:
            st.subheader("Target Character Control")

            st.radio(
                "character_filter",
                options=["Image 1 - Boy", "Image 2 - Girl"],
                index=0,
                horizontal=True,
                key="character_filter_label",
            )

            with st.expander("Identity Attribute Controls", expanded=False):
                with st.container(border=True):
                    st.markdown("###### Core Identity")
                    basic_col1, basic_col2 = st.columns(2)

                    with basic_col1:
                        st.slider("Age", min_value=1, max_value=100, value=9, step=1, key="age")
                    with basic_col2:
                        st.selectbox("Nationality", options=NATIONALITY_OPTIONS, index=0, key="nationality")

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
                        st.selectbox("Eyes Shape", options=EYES_SHAPE_OPTIONS, index=EYES_SHAPE_OPTIONS.index("Double Eyelid Eyes Shape"), key="eyes_shape")
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
                        st.selectbox("Hair Length", options=HAIR_LENGTH_OPTIONS, index=0, key="hair_length")

            with st.expander("Fine-Grained Appearance Attributes", expanded=False):

                skin_cols = st.columns(3)
            
                for i, (key, default_value) in enumerate(SKIN_DEFAULTS.items()):
                    with skin_cols[i % 3]:
                        st.checkbox(key, value=default_value > 0, key=f"skin_{key}")

            # st.divider()

            generate_clicked = st.button("Generate Character Appearance", type="primary", use_container_width=True)

            if generate_clicked:
                csv_text = st.session_state.get("csv_text", "")

                if not csv_text.strip():
                    st.error("Upload a CSV file in Step 1 first.")
                elif st.session_state.get("shot_filter_mode", "ALL") == "CUSTOM" and len(st.session_state.get("custom_shots", [])) == 0:
                    st.error("Select at least one shot when CUSTOM mode is enabled.")
                else:
                    config = build_face_ui_config()
                    character_filter = config["character_registry_parser"]["character_filter"]
                    character_code = "c1" if character_filter == "C1" else "c2"

                    try:
                        api_key = st.secrets["RUNCOMFY_API_KEY"]
                        deployment_id = st.secrets["DEPLOYMENT_ID"]

                        with st.spinner("Generating character appearance..."):
                            result = run_face_generation(
                                api_key=api_key,
                                deployment_id=deployment_id,
                                config=config,
                                poll_interval=5,
                                timeout_seconds=900,
                            )

                        images = result.get("images", [])

                        if not images:
                            st.error("Completed, but no output images were returned.")
                            with st.expander("RunComfy Raw Result", expanded=False):
                                st.json(result)
                            with st.expander("Collected Character Appearance Config", expanded=False):
                                st.json(config)
                        else:
                            first_image = images[0]
                            
                            st.session_state[f"face_result_image_{character_code}"] = first_image["image"]
                            st.session_state[f"face_result_filename_{character_code}"] = first_image.get("filename", "")

                            clear_downstream_results("2A", character_code)
       
                            st.success("Character appearance generated successfully.")
                            st.rerun()

                    except KeyError as e:
                        st.error(f"A required configuration key is missing: {e}")
                        st.exception(e)
                        with st.expander("Collected Character Appearance Config", expanded=False):
                            st.json(config)
                            
                    except Exception as e:
                        st.error("An error occurred during character appearance generation.")
                        st.exception(e)
                        with st.expander("Collected Character Appearance Config", expanded=False):
                            st.json(config)
                            

    # ------------------- 2B. Reference-based Outfit Change -------------------
    with st.container(border=True):
        st.markdown("### 2B. Reference-based Outfit Change")
        initialize_outfit_reference_inputs()

        preview_col, settings_col = st.columns([1.45, 1.25], gap="large")

        with preview_col:
            st.subheader("Outfit Change Preview")
            body_preview_col1, body_preview_col2 = st.columns(2, gap="medium")

            with body_preview_col1:
                st.markdown("##### Image 1 - Boy")

                if st.session_state.get("body_result_image_c1"):
                    render_image_preview_box(
                        st.session_state["body_result_image_c1"],
                        caption="Image 1 - Boy Final Character Reference",
                        height=400,
                    )
                else:
                    render_empty_preview_box("Image 1 - Boy outfit-changed reference will appear here.", 400)

            with body_preview_col2:
                st.markdown("##### Image 2 - Girl")

                if st.session_state.get("body_result_image_c2"):
                    render_image_preview_box(
                        st.session_state["body_result_image_c2"],
                        caption="Image 2 - Girl Final Character Reference",
                        height=400,
                    )
                else:
                    render_empty_preview_box("Image 2 - Girl outfit-changed reference will appear here.", 400)

        with settings_col:
            st.subheader("Outfit Change Control")

            st.radio(
                "Target Character",
                options=["Image 1 - Boy", "Image 2 - Girl"],
                index=0,
                horizontal=True,
                key="body_character_filter_label",
            )

            selected_body_target = st.session_state.get("body_character_filter_label", "Image 1 - Boy")

            selected_character_code = ("c1" if selected_body_target == "Image 1 - Boy" else "c2")

            st.markdown("###### Garment Input Mode")
            input_mode = st.radio(
                "Garment Input Mode",
                options=["Separate Garments", "Single Outfit Reference"],
                horizontal=True,
                key=f"outfit_input_mode_{selected_character_code}",
                label_visibility="collapsed",
            )

            if input_mode == "Separate Garments":
                garment_input_col1, garment_input_col2, garment_input_col3 = st.columns(3, gap="medium")

                garment_input_specs = [
                    (
                        garment_input_col1,
                        "Top",
                        f"outfit_top_upload_{selected_character_code}",
                        f"outfit_top_reference_{selected_character_code}",
                    ),
                    (
                        garment_input_col2,
                        "Bottom",
                        f"outfit_bottom_upload_{selected_character_code}",
                        f"outfit_bottom_reference_{selected_character_code}",
                    ),
                    (
                        garment_input_col3,
                        "Shoes",
                        f"outfit_shoes_upload_{selected_character_code}",
                        f"outfit_shoes_reference_{selected_character_code}",
                    ),
                ]

                for column, garment_label, upload_key, reference_key in garment_input_specs:
                    with column:
                        uploaded_garment = st.file_uploader(
                            garment_label,
                            type=["png", "jpg", "jpeg", "webp"],
                            key=upload_key,
                            on_change=clear_outfit_reference_on_remove,
                            args=(upload_key, reference_key),
                        )

                        if uploaded_garment is not None:
                            garment_data_uri = uploaded_image_to_data_uri(uploaded_garment)
                            st.session_state[reference_key] = garment_data_uri
                            st.image(
                                uploaded_garment,
                                caption=f"{garment_label} Reference",
                                width=180,
                            )
                        else:
                            saved_reference = st.session_state.get(reference_key, "")
                        
                            if saved_reference:
                                render_image_preview_box(
                                    saved_reference,
                                    caption=f"{garment_label} Reference",
                                    height=160,
                                )
                            else:
                                render_empty_preview_box(f"{garment_label}<br>Reference", 160)

            else:
                single_reference_key = f"outfit_single_reference_{selected_character_code}"
            
                single_upload_key = f"outfit_single_upload_{selected_character_code}"

                single_outfit_upload = st.file_uploader(
                    "Outfit Reference Image",
                    type=["png", "jpg", "jpeg", "webp"],
                    key=single_upload_key,
                    label_visibility="collapsed",
                    on_change=clear_outfit_reference_on_remove,
                    args=(single_upload_key, single_reference_key),
                )
            
                if single_outfit_upload is not None:
                    st.session_state[single_reference_key] = uploaded_image_to_data_uri(
                        single_outfit_upload
                    )
            
                st.markdown("##### Single Outfit Reference")
            
                if single_outfit_upload is not None:
                    st.image(
                        single_outfit_upload,
                        caption="Single Outfit Reference",
                        width=220,
                    )
                else:
                    saved_reference = st.session_state.get(single_reference_key, "")
            
                    if saved_reference:
                        render_image_preview_box(
                            saved_reference,
                            caption="Single Outfit Reference",
                            height=220,
                        )
                    else:
                        render_empty_preview_box(
                            "Single Outfit<br>Reference",
                            220,
                        )

            st.markdown("<div style='height: 24px;'></div>", unsafe_allow_html=True)

            generate_body_clicked = st.button("Generate Outfit Reference", type="primary", use_container_width=True)

            if generate_body_clicked:
                body_config = build_body_ui_config()
                outfit_change_config = body_config["outfit_change"]

                character_filter = outfit_change_config["character_filter"]
                character_code = "c1" if character_filter == "C1" else "c2"
                label = outfit_change_config["label"]

                character_image_url = outfit_change_config.get("character_image_url", "")
                input_mode = outfit_change_config.get("input_mode", "Separate Garments")
                garment_references = outfit_change_config.get("garment_references", {})
                single_outfit_reference = outfit_change_config.get("single_outfit_reference", "")

                top_reference_url = garment_references.get("top", "")
                bottom_reference_url = garment_references.get("bottom", "")
                shoes_reference_url = garment_references.get("shoes", "")

                missing_garments = [
                    garment_name
                    for garment_name, garment_url in (
                        ("Top", top_reference_url),
                        ("Bottom", bottom_reference_url),
                        ("Shoes", shoes_reference_url),
                    )
                    if not garment_url
                ]

                if not character_image_url:
                    st.error(f"No character appearance found for {label}. Generate the character in Step 2A first.")

                elif input_mode == "Separate Garments" and missing_garments:
                    st.error("Upload the following garment references: " + ", ".join(missing_garments))

                elif input_mode == "Single Outfit Reference" and not single_outfit_reference:
                    st.error("Upload a single outfit reference image.")

                else:
                    try:
                        api_key = st.secrets["RUNCOMFY_API_KEY"]
                        deployment_id = st.secrets["DEPLOYMENT_ID"]

                        with st.spinner("Generating outfit reference..."):
                            result = run_body_generation(
                                api_key=api_key,
                                deployment_id=deployment_id,
                                config=body_config,
                                poll_interval=10,
                                timeout_seconds=1800,
                            )

                        images = result.get("images", [])

                        if not images:
                            st.error("Completed, but no outfit images were returned.")
                            
                            with st.expander("RunComfy Raw Result", expanded=False):
                                st.json(result)
                                
                            with st.expander("Collected Outfit Change Config", expanded=False,):
                                st.json(body_config)
                                
                        else:
                            first_image = images[0]

                            st.session_state[f"body_result_image_{character_code}"] = first_image["image"]
                            st.session_state[f"body_result_filename_{character_code}"] = first_image.get("filename", "")

                            clear_downstream_results("2B")

                            st.success("Outfit reference generated successfully.")
                            st.rerun()

                    except KeyError as e:
                        st.error(f"A required key is missing: {e}")
                        st.exception(e)

                        with st.expander(
                            "Collected Outfit Change Config",
                            expanded=False,
                        ):
                            st.json(body_config)

                    except Exception as e:
                        st.error("An error occurred during outfit reference generation.")
                        st.exception(e)

                        with st.expander(
                            "Collected Outfit Change Config",
                            expanded=False,
                        ):
                            st.json(body_config)


# ===========================================
# Step 3. Reference-Guided Scene Generation
# ===========================================
with tab3:
    st.header("Step 3. Reference-Guided Scene Generation")

    boy_body_image = st.session_state.get("body_result_image_c1")
    girl_body_image = st.session_state.get("body_result_image_c2")

    storyboard_input = build_storyboard_input_config()["storyboard_input"]

    preview_col, settings_col = st.columns([1.45, 1.25], gap="large")

    with preview_col:
        st.subheader("Generated Storyboard Preview")

        scene_preview_candidates = st.session_state.get("scene_candidates",[])

        valid_scene_previews = [
            item
            for item in scene_preview_candidates
            if isinstance(item, dict) and item.get("image")
        ]

        if not valid_scene_previews and st.session_state.get("scene_result_image"):
            valid_scene_previews = [
                {
                    "label": st.session_state.get(
                        "scene_selected_label",
                        "Scene 1",
                    ),
                    "image": st.session_state["scene_result_image"],
                    "filename": st.session_state.get(
                        "scene_result_filename",
                        "",
                    ),
                }
            ]

        if valid_scene_previews:
            for idx, scene_item in enumerate(valid_scene_previews):
                scene_label = scene_item.get(
                    "label",
                    f"Scene {idx + 1}",
                )

                st.markdown(f"##### {scene_label}")

                render_image_preview_box(
                    scene_item["image"],
                    caption=scene_label,
                    height=460,
                )

                if idx < len(valid_scene_previews) - 1:
                    st.markdown(
                        "<div style='height: 18px;'></div>",
                        unsafe_allow_html=True,
                    )
        else:
            render_empty_preview_box(
                "Generated storyboard scenes will appear here.",
                560,
            )

    with settings_col:
        with st.container(border=True):
    
            st.markdown("###### Selected Storyboard Context")
    
            if storyboard_input["selected_shot_count"] == 0:
                st.warning("No storyboard data available. Check the CSV file and shot selection in Step 1.")
            else:
                if storyboard_input["shot_filter"] == "ALL":
                    st.caption(f"Shot Filter: ALL / {storyboard_input['selected_shot_count']} CSV row(s)")
                elif storyboard_input["custom_shot_ids"]:
                    st.caption(f"Shot Filter: CUSTOM / {storyboard_input['custom_shot_ids']}")
                else:
                    st.caption("Shot Filter: CUSTOM / No shot selected")
    
                st.dataframe(
                    pd.DataFrame(storyboard_input["selected_shot_data"]),
                    use_container_width=True,
                    hide_index=True,
                )

        st.divider()
    
        st.subheader("Character Reference Inputs")
    
        ref_col1, ref_col2 = st.columns(2, gap="medium")
    
        with ref_col1:
            st.markdown("##### Image 1 Reference")
    
            if boy_body_image:
                st.image(
                    boy_body_image,
                    caption="Image 1 Character Reference",
                    width=220,
                )

            else:
                st.warning("Generate the Image 1 character reference in Step 2B first.")
    
        with ref_col2:
            st.markdown("##### Image 2 Reference")
    
            if girl_body_image:
                st.image(
                    girl_body_image,
                    caption="Image 2 Character Reference",
                    width=220,
                )

            else:
                st.warning("Generate the Image 2 character reference in Step 2B first.")
    
        st.divider()
    
        generate_scene_clicked = st.button(
            "Generate Storyboard Scene",
            type="primary",
            use_container_width=True,
        )

        if generate_scene_clicked:
            storyboard_input = build_storyboard_input_config()["storyboard_input"]

            if not storyboard_input["csv_text"].strip():
                st.error("Upload a CSV file in Step 1 first.")

            elif (
                storyboard_input["shot_filter"] == "CUSTOM"
                and not storyboard_input["custom_shot_ids"]
            ):
                st.error("Select at least one shot when CUSTOM mode is enabled.")

            elif storyboard_input["selected_shot_count"] == 0:
                st.error("No valid storyboard shots found. Check the CSV data and shot selection.")

            elif not boy_body_image:
                st.error("Generate the Image 1 - Boy body reference in Step 2B first.")

            elif not girl_body_image:
                st.error("Generate the Image 2 - Girl body reference in Step 2B first.")

            else:
                scene_config = build_scene_ui_config()

                try:
                    api_key = st.secrets["RUNCOMFY_API_KEY"]
                    deployment_id = st.secrets["DEPLOYMENT_ID"]

                    with st.spinner("Generating storyboard scenes..."):
                        result = run_scene_generation(
                            api_key=api_key,
                            deployment_id=deployment_id,
                            config=scene_config,
                            poll_interval=10,
                            timeout_seconds=1800,
                        )

                    images = result.get("images", [])

                    if not images:
                        st.error("Completed, but no scene images were returned.")

                        with st.expander("RunComfy Raw Scene Result", expanded=False):
                            st.json(result)

                        with st.expander("Collected Scene Generation Config", expanded=False):
                            st.json(scene_config)

                    else:
                        first_image = images[0]

                        st.session_state["scene_candidates"] = images
                        st.session_state["scene_result_image"] = first_image["image"]
                        st.session_state["scene_result_filename"] = first_image.get("filename", "")
                        st.session_state["scene_selected_label"] = first_image.get("label", "Scene 1")

                        clear_downstream_results("3")

                        st.success("Storyboard scenes generated successfully.")
                        st.rerun()

                except KeyError as e:
                    st.error(f"A required key is missing: {e}")
                    st.exception(e)
                
                    with st.expander("Collected Scene Generation Config", expanded=False):
                        st.json(scene_config)
                
                except Exception as e:
                    st.error("An error occurred during storyboard scene generation.")
                    st.exception(e)
                
                    with st.expander("Collected Scene Generation Config", expanded=False):
                        st.json(scene_config)

# =============================================================================================================================
# Step 4. Camera Refinement
# =============================================================================================================================
with tab4:
    st.header("Step 4. Camera Refinement")
    st.caption(
        "Refine the camera viewpoint of a generated Step 3 scene "
        "using Qwen Multi-Angle Camera control."
    )

    preview_col, settings_col = st.columns([1.6, 1.1], gap="large")

    with preview_col:
        st.subheader("Camera Refinement Preview")
    
        st.markdown("#### Refined Scene")
    
        if st.session_state.get("camera_refined_result_image"):
            render_image_preview_box(
                st.session_state["camera_refined_result_image"],
                caption="Camera-Refined Storyboard Scene",
                height=500,
            )
    
        else:
            render_empty_preview_box(
                "The camera-refined scene will appear here.",
                500,
            )

    with settings_col:
        st.subheader("Camera Refinement Control")

        with st.container(border=True):
            st.markdown("###### Source Scene")

            scene_candidates = get_scene_result_candidates()
            
            sync_scene_reference_selection(
                "camera_input_scene_label",
                scene_candidates,
            )

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

                    if selected_input_scene.get("image"):
                        st.image(
                            selected_input_scene["image"],
                            caption=selected_input_scene.get("label", "Source Scene"),
                            use_container_width=True,
                        )
                    else:
                        render_empty_preview_box(
                            "The selected source scene will appear here.",
                            260,
                        )
            else:
                st.warning(
                    "No scene images available. Generate storyboard scenes in Step 3 first."
                )

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
                    help="Adjust the horizontal camera angle.",
                )

                st.slider(
                    "Vertical Angle",
                    min_value=-90,
                    max_value=90,
                    value=0,
                    step=1,
                    key="camera_vertical_angle",
                    help="Adjust the vertical camera angle.",
                )

            with angle_col2:
                st.slider(
                    "Zoom",
                    min_value=0,
                    max_value=10,
                    value=5,
                    step=1,
                    key="camera_zoom",
                    help="Adjust the camera zoom and framing.",
                )

        st.markdown(
            "<div style='height: 16px;'></div>",
            unsafe_allow_html=True,
        )

        generate_camera_clicked = st.button(
            "Generate Camera-Refined Scene",
            type="primary",
            use_container_width=True,
        )

        if generate_camera_clicked:
            scene_candidates = get_scene_result_candidates()

            selected_input_scene = get_selected_candidate(
                scene_candidates,
                st.session_state.get("camera_input_scene_label", ""),
            )

            if not scene_candidates:
                st.error("No scene images available. Generate storyboard scenes in Step 3 first.")
            
            elif not selected_input_scene:
                st.error("Select an input scene for camera refinement.")
            
            elif not selected_input_scene.get("image"):
                st.error("The selected scene image is empty. Check the Step 3 results.")

            else:
                camera_config = build_camera_refinement_ui_config()
                result = None

                try:
                    api_key = st.secrets["RUNCOMFY_API_KEY"]
                    deployment_id = st.secrets["DEPLOYMENT_ID"]

                    with st.spinner("Generating camera-refined scene..."):
                        result = run_camera_refinement(
                            api_key=api_key,
                            deployment_id=deployment_id,
                            config=camera_config,
                            poll_interval=10,
                            timeout_seconds=1800,
                        )

                    images = result.get("images", [])

                    if not images:
                        st.error("RunComfy completed, but no camera-refined images were returned.")

                        with st.expander(
                            "RunComfy Raw Camera Refinement Result",
                            expanded=False,
                        ):
                            st.json(result)

                        with st.expander(
                            "Collected Camera Refinement Config",
                            expanded=False,
                        ):
                            st.json(camera_config)

                        with st.expander(
                            "Patched Camera Refinement Workflow",
                            expanded=False,
                        ):
                            st.json(result.get("workflow_api_json", {}))

                    else:
                        first_image = images[0]

                        st.session_state["camera_refined_candidates"] = images
                        st.session_state["camera_refined_result_image"] = (
                            first_image["image"]
                        )
                        st.session_state["camera_refined_result_filename"] = (
                            first_image.get("filename", "")
                        )
                        st.session_state["camera_refined_selected_label"] = (
                            first_image.get(
                                "label",
                                "Camera Refined Scene 1",
                            )
                        )

                        st.success("Camera-refined scene generated successfully.")
                        st.rerun()

                except KeyError as e:
                    st.error(f"A required key is missing: {e}")
                    st.exception(e)
                
                    with st.expander("Collected Camera Refinement Config", expanded=False):
                        st.json(camera_config)
                
                except Exception as e:
                    st.error("An error occurred during camera refinement.")
                    st.exception(e)
                
                    with st.expander("Collected Camera Refinement Config", expanded=False):
                        st.json(camera_config)
                
                    if result is not None:
                        with st.expander("RunComfy Raw Camera Refinement Result", expanded=False):
                            st.json(result)
