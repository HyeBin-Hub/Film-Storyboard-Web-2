"""CSV, character-reference, session-state, and workflow config helpers."""

import base64
import io

import pandas as pd
import streamlit as st

from app_constants import ENABLE_MANUAL_REFERENCE_INPUT, SKIN_DEFAULTS


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
# 8. Manual Reference Testing
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
