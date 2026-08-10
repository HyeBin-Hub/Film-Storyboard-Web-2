import base64
import csv
import io
import pandas as pd
import streamlit as st

from backend import (
    run_csv_parser_test,
    run_face_generation,
    run_body_generation,
    run_scene_generation,
    run_camera_refinement,
)

# =========================
# Fixed Values
# =========================
FIXED_BASE_BACKGROUND_CLOTHING_PROMPT = "gray background"

# Temporary UI feature flags
# True로 변경하면 각 수동 입력/가이드 UI를 다시 표시할 수 있습니다.
ENABLE_MANUAL_FACE_REFERENCE_INPUT = False
SHOW_REFERENCE_PROMPT_GUIDELINES = False
ENABLE_MANUAL_FULL_BODY_REFERENCE_INPUT = False
ENABLE_MANUAL_SCENE_REFERENCE_INPUT = False

# Step 2A 결과를 UI 없이 미리 주입하는 테스트용 플래그
# True  = 아래 PRESET URL을 Boy/Girl 2A 결과로 자동 등록
# False = 기존 Step 2A 생성 결과만 사용
ENABLE_PRESET_2A_RESULTS = True

# Step 2B 결과를 UI 없이 미리 주입하는 테스트용 플래그
# True  = 아래 PRESET URL을 Boy/Girl 2B 결과로 자동 등록
# False = 기존 Step 2B 생성 결과만 사용
ENABLE_PRESET_2B_RESULTS = True

# Step 3 결과를 UI 없이 미리 주입하는 테스트용 플래그
# True  = 아래 PRESET URL 3장을 Generated Storyboard Preview에 자동 등록
# False = 기존 Step 3 생성 결과만 사용
ENABLE_PRESET_STEP3_RESULTS = True
# Step 4 결과를 UI 없이 미리 주입하는 테스트용 플래그
# True  = 아래 PRESET URL 3장을 Generated Storyboard Preview에 자동 등록
# False = 기존 Step 4 생성 결과만 사용
ENABLE_PRESET_STEP4_RESULTS = True

ENABLE_CAMERA_SAMPLING_CONTROL = False

FIXED_CAMERA_REFINEMENT_STEPS = 8
FIXED_CAMERA_REFINEMENT_CFG = 1.0

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

# ----------------------------- 업로드 파일 텍스트 변환 함수 -----------------------------
# 업로드된 파일의 바이너리 데이터를 여러 인코딩 방식으로 시도해 문자열 텍스트로 안전하게 디코딩하는 함수
def decode_uploaded_file(uploaded_file):
    raw = uploaded_file.getvalue()
    for encoding in ["utf-8-sig", "utf-8", "cp949"]:
        try:
            return raw.decode(encoding)
        except Exception:
            pass
    return raw.decode("utf-8", errors="ignore")

# ----------------------------- 업로드 이미지 Data URI 변환 함수 -----------------------------
# Streamlit file_uploader로 받은 이미지 파일을
# RunComfy LoadImageFromUrl 노드에 전달할 수 있는 base64 data URI 문자열로 변환합니다.
def uploaded_image_to_data_uri(uploaded_file):
    if uploaded_file is None:
        return ""

    raw = uploaded_file.getvalue()
    mime_type = getattr(uploaded_file, "type", None) or "image/png"

    encoded = base64.b64encode(raw).decode("ascii")
    return f"data:{mime_type};base64,{encoded}"


# ----------------------------- CSV 샷 ID 추출 함수 -----------------------------
# CSV 텍스트의 첫 번째 열에서 중복 없이 샷 ID 목록을 추출하는 함수입니다.
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

# ----------------------------- CSV 데이터프레임 변환 함수 -----------------------------
# CSV 텍스트를 pandas DataFrame으로 변환하고, 실패하거나 비어 있으면 빈 DataFrame을 반환하는 함수
def read_csv_as_dataframe(csv_text):
    if not csv_text.strip():
        return pd.DataFrame()
    try:
        return pd.read_csv(io.StringIO(csv_text))
    except Exception:
        return pd.DataFrame()

# ----------------------------- 샷 ID 컬럼 탐색 함수 -----------------------------
# DataFrame에서 샷 ID로 보이는 컬럼을 찾고, 없으면 첫 번째 컬럼을 반환하는 함수
def get_shot_id_column(df):
    if df.empty:
        return None

    candidates = ["shot", "shot_id", "shot id", "id", "Shot", "Shot ID", "Shot_ID"]
    for col in df.columns:
        if str(col).strip() in candidates:
            return col
    return df.columns[0]

# ----------------------------- 선택 샷 DataFrame 추출 함수 -----------------------------
# Streamlit 세션의 CSV 데이터에서 현재 선택된 샷 필터에 해당하는 행만 추출해 DataFrame으로 반환하는 함수
# CSV를 DataFrame으로 읽은 뒤, ALL이면 전체를 반환하고 CUSTOM이면 선택된 샷 ID만 필터링함
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

# ----------------------------- 스토리보드 입력 설정 구성 함수 -----------------------------
# Streamlit 세션의 CSV와 샷 선택 정보를 모아 RunComfy 요청용 storyboard_input 설정 딕셔너리로 구성하는 함수
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

# ------------------------- 캐릭터 라벨 변환 함수 ----------------------------- 
# 선택된 캐릭터 라벨을 RunComfy 워크플로우에서 사용하는 C1, C2 값으로 변환하는 함수
# 라벨이 Image 1 - Boy이면 C1, Image 2 - Girl이면 C2를 반환하고 기본값은 함수별로 다르게 설정
def character_label_to_value(label):
    return {"Image 1 - Boy": "C1", "Image 2 - Girl": "C2"}.get(label, "C2")

# ------------------------- 전신 프롬프트 초기화 함수 -------------------------
# 전신 생성에서 선택된 캐릭터 라벨을 워크플로우용 C1, C2 값으로 변환하는 함수
# 라벨이 Image 1 - Boy이면 C1, Image 2 - Girl이면 C2를 반환하고, 알 수 없는 라벨이면 기본값으로 C1을 반환
def body_character_label_to_value(label):
    return {"Image 1 - Boy": "C1", "Image 2 - Girl": "C2"}.get(label, "C1")

# ------------------------- 의상 레퍼런스 입력 초기화 함수 -------------------------
# 2B Outfit Change에서 캐릭터별 입력 모드와 Garment / Outfit reference data URI를 세션에 유지합니다.
def initialize_outfit_reference_inputs():
    for character_code in ("c1", "c2"):
        st.session_state.setdefault(
            f"outfit_input_mode_{character_code}",
            "Separate Garments",
        )
        st.session_state.setdefault(f"outfit_top_reference_{character_code}", "")
        st.session_state.setdefault(f"outfit_bottom_reference_{character_code}", "")
        st.session_state.setdefault(f"outfit_shoes_reference_{character_code}", "")
        st.session_state.setdefault(f"outfit_single_reference_{character_code}", "")

# ------------------------- 장면 샷 필터 설정 조회 함수 -------------------------
# 장면 생성에 사용할 현재 샷 필터 값과 커스텀 샷 ID 값을 가져오는 함수
# build_storyboard_input_config()에서 storyboard_input을 만들고, 그 안의 shot_filter와 custom_shot_ids를 반환
def get_scene_shot_filter_config():
    storyboard_input = build_storyboard_input_config()["storyboard_input"]
    return storyboard_input["shot_filter"], storyboard_input["custom_shot_ids"]

# ------------------------- 선택 후보 조회 함수 -------------------------
# 후보 목록에서 선택된 라벨과 일치하는 항목을 찾아 반환하는 함수
# candidates를 순회하며 label이 selected_label과 같은 항목을 반환하고, 없으면 None을 반환
def get_selected_candidate(candidates, selected_label):
    for item in candidates:
        if item["label"] == selected_label:
            return item
    return None


# ------------------------- 장면 레퍼런스 선택 동기화 함수 -------------------------
# 장면 생성용 레퍼런스 선택값이 후보 목록과 일치하도록 세션 상태를 보정하는 함수
# 후보 라벨이 없으면 선택값을 비우고, 현재 선택값이 후보에 없으면 첫 번째 후보 라벨로 자동 설정
def sync_scene_reference_selection(session_key, candidates):
    labels = [item["label"] for item in candidates]

    if not labels:
        st.session_state[session_key] = ""
        return

    if st.session_state.get(session_key) not in labels:
        st.session_state[session_key] = labels[0]

# ------------------------- 얼굴 생성 UI 설정 구성 함수 -------------------------
# Streamlit에서 선택한 스토리보드·캐릭터·외형 설정을 얼굴 생성 워크플로우용 설정 딕셔너리로 구성하는 함수
# 세션 상태에서 CSV, 샷 필터, 캐릭터 정보, 얼굴 외형 옵션, 피부 디테일 값을 가져와 RunComfy 요청에 맞는 노드별 입력값으로 정리
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
            "gender": "-",
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

# ------------------------- 의상 변경 UI 설정 구성 함수 -------------------------
# 선택한 2A 캐릭터 결과와 업로드된 Top / Bottom / Shoes 레퍼런스를 2B Outfit Change 설정으로 구성합니다.
# 함수명 build_body_ui_config는 기존 app-backend 연결을 최소 변경하기 위해 유지합니다.
def build_body_ui_config():
    character_filter_label = st.session_state.get(
        "body_character_filter_label",
        "Image 1 - Boy",
    )

    character_filter = body_character_label_to_value(character_filter_label)
    character_code = "c1" if character_filter == "C1" else "c2"

    if character_filter == "C1":
        label = "Image 1 - Boy"
        character_image_url = st.session_state.get("face_result_image_c1", "")
        character_filename = st.session_state.get("face_result_filename_c1", "")
    else:
        label = "Image 2 - Girl"
        character_image_url = st.session_state.get("face_result_image_c2", "")
        character_filename = st.session_state.get("face_result_filename_c2", "")

    input_mode = st.session_state.get(
        f"outfit_input_mode_{character_code}",
        "Separate Garments",
    )

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
 
# ------------------------- 장면 생성 UI 설정 구성 함수 -------------------------
# 스토리보드 선택 정보와 남자/여자 전신 레퍼런스를 장면 생성용 설정 딕셔너리로 구성하는 함수
# 스토리보드 입력값을 만든 뒤, 선택된 c1 남자 전신 후보와 c2 여자 전신 후보의 라벨·이미지·파일명을 reference_images에 넣어 반환
def build_scene_ui_config():
    storyboard_input = build_storyboard_input_config()["storyboard_input"]

    boy_body_image = st.session_state.get("body_result_image_c1", "")
    boy_body_filename = st.session_state.get("body_result_filename_c1", "")

    girl_body_image = st.session_state.get("body_result_image_c2", "")
    girl_body_filename = st.session_state.get("body_result_filename_c2", "")

    return {
        "storyboard_input": storyboard_input,
        "scene_generation": {
            "shot_filter": storyboard_input["shot_filter"],
            "custom_shot_ids": storyboard_input["custom_shot_ids"],
            "selected_shot_count": storyboard_input["selected_shot_count"],
            "selected_shot_data": storyboard_input["selected_shot_data"],
            "reference_images": {
                "image_1_boy_body": {
                    "label": "Image 1 - Boy Character Reference",
                    "image": boy_body_image,
                    "filename": boy_body_filename,
                },
                "image_2_girl_body": {
                    "label": "Image 2 - Gril Character Reference",
                    "image": girl_body_image,
                    "filename": girl_body_filename,
                },
            },
        },
    }

# ------------------------- 장면 결과 후보 조회 함수 -------------------------
# 장면 생성 결과 이미지 후보 목록을 Streamlit 세션에서 가져와 화면 표시용으로 정리하는 함수
# scene_candidates를 label, image, filename 형태로 정리하고, 후보가 없으면 기존 단일 장면 결과 이미지를 fallback으로 추가
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

# ------------------------- 카메라 보정 UI 설정 구성 함수 -------------------------
# Step 3에서 선택한 장면과 Qwen Multi-Angle Camera 제어값을
# 새 Camera Refinement workflow용 설정 딕셔너리로 구성합니다.
def build_camera_refinement_ui_config():
    scene_candidates = get_scene_result_candidates()

    selected_scene = get_selected_candidate(
        scene_candidates,
        st.session_state.get("camera_input_scene_label", ""),
    )

    return {
        "camera_angle_refinement": {
            "input_scene": {
                "label": selected_scene["label"] if selected_scene else "",
                "image": selected_scene.get("image", "") if selected_scene else "",
                "filename": selected_scene.get("filename", "") if selected_scene else "",
            },
            "camera_control": {
                "horizontal_angle": st.session_state.get("camera_horizontal_angle", 0),
                "vertical_angle": st.session_state.get("camera_vertical_angle", 0),
                "zoom": st.session_state.get("camera_zoom", 5),
                "default_prompts": st.session_state.get("camera_default_prompts", True),
                "camera_view": st.session_state.get("camera_view", False),
            },
        },
    }

# ------------------------- 빈 미리보기 박스 렌더링 함수 -------------------------
# 이미지가 없을 때 안내 메시지를 담은 빈 미리보기 박스를 Streamlit 화면에 표시하는 함수
# 전달받은 message와 height 값을 HTML 스타일에 넣고 st.markdown()으로 렌더링
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


# ------------------------- Step 2A Preset 결과 자동 주입 함수 -------------------------
# ENABLE_PRESET_2A_RESULTS가 True일 때만 실행됩니다.
# UI에는 아무 입력창도 표시하지 않고, 기존 Step 2A session_state 키에
# Boy / Girl 결과 URL을 미리 주입합니다.
# 이미 실제 Step 2A 생성 결과가 존재하면 덮어쓰지 않습니다.
def apply_preset_2a_results():
    if not ENABLE_PRESET_2A_RESULTS:
        return

    preset_boy_url = (
        "https://serverless-api-storage.runcomfy.net/"
        "deployment_requests/e3b5d793-e111-49fe-850f-4b0e08424dd2/"
        "output/character_appearance_boy_3063348797_00001_.png"
    )

    preset_girl_url = (
        "https://serverless-api-storage.runcomfy.net/"
        "deployment_requests/94b10bea-a4e8-4f66-9d18-603ff35e325e/"
        "output/character_appearance_girl_667573668_00001_.png"
    )

    if not st.session_state.get("face_result_image_c1"):
        st.session_state["face_result_image_c1"] = preset_boy_url
        st.session_state["face_result_filename_c1"] = (
            "character_appearance_boy_3063348797_00001_.png"
        )

    if not st.session_state.get("face_result_image_c2"):
        st.session_state["face_result_image_c2"] = preset_girl_url
        st.session_state["face_result_filename_c2"] = (
            "character_appearance_girl_667573668_00001_.png"
        )
        
def apply_preset_2b_results():
    if not ENABLE_PRESET_2B_RESULTS:
        return

    preset_boy_outfit_url = (
        "https://cdn.phototourl.com/free/2026-08-10-cc0d90a8-b115-4c15-bd6f-57d30a16bbd9.png"
    )

    preset_girl_outfit_url = (
        "https://cdn.phototourl.com/free/2026-08-10-fa2ccad6-deec-4063-9bd5-b4c9f742c285.png"
    )

    # 이미 실제 2B 결과가 있으면 덮어쓰지 않음
    if not st.session_state.get("body_result_image_c1"):
        st.session_state["body_result_image_c1"] = preset_boy_outfit_url
        st.session_state["body_result_filename_c1"] = "ComfyUI_01135_.png"

    if not st.session_state.get("body_result_image_c2"):
        st.session_state["body_result_image_c2"] = preset_girl_outfit_url
        st.session_state["body_result_filename_c2"] = "换装_00026_.png"


# ------------------------- Step 3 Preset 결과 자동 주입 함수 -------------------------
# ENABLE_PRESET_STEP3_RESULTS가 True일 때만 실행됩니다.
# UI에는 별도 입력창을 표시하지 않고, 기존 scene_candidates 구조에
# 3개의 storyboard scene 결과를 미리 등록합니다.
# 실제 Step 3 생성 결과가 이미 존재하면 덮어쓰지 않습니다.
def apply_preset_step3_results():
    if not ENABLE_PRESET_STEP3_RESULTS:
        return

    if st.session_state.get("scene_candidates"):
        return

    preset_scene_urls = [
        (
            "Scene 1",
            "https://serverless-api-storage.runcomfy.net/"
            "deployment_requests/c48de276-8299-4f96-ba30-5f3deed58153/"
            "output/scene_3123289005_00001_.png",
            "scene_3123289005_00001_.png",
        ),
        (
            # "Scene 2",
            # "https://serverless-api-storage.runcomfy.net/"
            # "deployment_requests/c48de276-8299-4f96-ba30-5f3deed58153/"
            # "output/scene_3123289005_00002_.png",
            # "scene_3123289005_00002_.png",
            "Scene 2",
            "https://cdn.phototourl.com/free/2026-08-10-98c475bc-901c-4750-9b3d-fffeafd98a13.png",
            "scene2_custom.png",
        ),
        (
            "Scene 3",
            "https://serverless-api-storage.runcomfy.net/"
            "deployment_requests/c48de276-8299-4f96-ba30-5f3deed58153/"
            "output/scene_3123289005_00003_.png",
            "scene_3123289005_00003_.png",
        ),
    ]

    preset_candidates = [
        {
            "label": label,
            "image": image_url,
            "url": image_url,
            "filename": filename,
        }
        for label, image_url, filename in preset_scene_urls
    ]

    st.session_state["scene_candidates"] = preset_candidates

    first_scene = preset_candidates[0]
    st.session_state["scene_result_image"] = first_scene["image"]
    st.session_state["scene_result_filename"] = first_scene["filename"]
    st.session_state["scene_selected_label"] = first_scene["label"]


def apply_preset_step4_results():
    if not ENABLE_PRESET_STEP4_RESULTS:
        return

    if st.session_state.get("camera_refined_result_image"):
        return

    preset_step4_result_url = (
        "https://i.postimg.cc/XqnCWSTw/image-(7).png"
    )

    st.session_state["camera_refined_candidates"] = [
        {
            "label": "Camera Refined Scene 1",
            "image": preset_step4_result_url,
            "url": preset_step4_result_url,
            "filename": "step4_preset_image.png",
        }
    ]

    st.session_state["camera_refined_result_image"] = (
        preset_step4_result_url
    )
    st.session_state["camera_refined_result_filename"] = (
        "step4_preset_image.png"
    )
    st.session_state["camera_refined_selected_label"] = (
        "Camera Refined Scene 1"
    )


# ------------------------- 비활성화된 수동 입력 상태 정리 함수 -------------------------
# 기능 플래그가 False인 수동 입력의 텍스트·이미지·선택 상태를 세션에서 제거하는 함수
# 이전 실행에서 수동 URL을 넣었더라도 현재 파이프라인이 생성 결과만 사용하도록 초기화함
def clear_disabled_manual_reference_state():
    if not ENABLE_MANUAL_FACE_REFERENCE_INPUT:
        st.session_state.pop("manual_face_reference_url", None)

        for character_code in ("c1", "c2"):
            filename_key = f"face_result_filename_{character_code}"
            image_key = f"face_result_image_{character_code}"

            if str(st.session_state.get(filename_key, "")).startswith("manual_"):
                st.session_state.pop(filename_key, None)
                st.session_state.pop(image_key, None)

    if not ENABLE_MANUAL_FULL_BODY_REFERENCE_INPUT:
        st.session_state.pop("manual_boy_body_reference_url", None)
        st.session_state.pop("manual_girl_body_reference_url", None)

        for character_code in ("c1", "c2"):
            filename_key = f"body_result_filename_{character_code}"
            image_key = f"body_result_image_{character_code}"

            if str(st.session_state.get(filename_key, "")).startswith("manual_"):
                st.session_state.pop(filename_key, None)
                st.session_state.pop(image_key, None)

    if not ENABLE_MANUAL_SCENE_REFERENCE_INPUT:
        st.session_state.pop("manual_camera_scene_reference_url", None)

        scene_candidates = st.session_state.get("scene_candidates", [])
        if isinstance(scene_candidates, list):
            filtered_candidates = [
                item
                for item in scene_candidates
                if not (
                    isinstance(item, dict)
                    and (
                        item.get("label") == "Manual Camera Input Scene"
                        or str(item.get("filename", "")).startswith("manual_camera_input_scene")
                    )
                )
            ]

            if filtered_candidates:
                st.session_state["scene_candidates"] = filtered_candidates
            else:
                st.session_state.pop("scene_candidates", None)

        if str(st.session_state.get("scene_result_filename", "")).startswith("manual_camera_input_scene"):
            st.session_state.pop("scene_result_image", None)
            st.session_state.pop("scene_result_filename", None)
            st.session_state.pop("scene_selected_label", None)

        if st.session_state.get("camera_input_scene_label") == "Manual Camera Input Scene":
            st.session_state.pop("camera_input_scene_label", None)


# =========================
# Page Config
# =========================
st.set_page_config(
    page_title="AI Storyboard Pipeline",
    page_icon="🎬",
    layout="wide",
)

clear_disabled_manual_reference_state()
apply_preset_2a_results()
apply_preset_2b_results()
apply_preset_step3_results()
apply_preset_step4_results()

st.title("🎬 AI Storyboard Generation Pipeline")
st.caption("A ComfyUI-based generation pipeline for character-consistent cinematic storyboard creation and camera-angle refinement")


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


# =================================
# Step 1. Storyboard Data Parsing
# =================================
with tab1:
    st.header("Step 1. Storyboard Data Parsing")

    # Streamlit 화면에 파일 업로드 버튼/영역을 만드는 함수
    # 사용자가 CSV 같은 파일을 선택하면, 그 파일을 코드에서 읽을 수 있는 uploaded_file 객체로 반환
    uploaded_csv = st.file_uploader(
        "Upload Storyboard CSV",
        type=["csv"],
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
                        # help="CUSTOM일 때만 shot을 선택합니다.",
                    )
                else:
                    st.warning("CSV에서 추출된 shot id가 없습니다.")

            # st.divider()
    
    else:
        st.info("CSV 파일을 업로드하면 Parsed Storyboard Data Preview와 Shot Selection Control이 표시됩니다.")


# ========================================
# Step 2. Character Reference Generation
# ========================================
with tab2:

    st.header("Step 2. Character Reference Generation")
    st.caption("Generate character appearances first, then apply garment references to build the final character references for scene generation.")

    # ------------------- 2A. Character Appearance Generation ------------------- 
    with st.container(border=True):
        st.markdown("### 2A. Character Appearance Generation")

        preview_col, settings_col = st.columns([1.25, 1.15], gap="large")

        with preview_col:
            st.subheader("Character Appearance Preview")
        
            face_preview_col1, face_preview_col2 = st.columns(2, gap="medium")
        
            with face_preview_col1:
                st.markdown("##### Image 1 - Boy")
            
                if st.session_state.get("face_result_image_c1") is not None:
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
            
                if st.session_state.get("face_result_image_c2") is not None:
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
                index=1,
                horizontal=True,
                key="character_filter_label",
            )

            if ENABLE_MANUAL_FACE_REFERENCE_INPUT:
                st.caption("Manual Face Reference")
            
                manual_url_col, manual_apply_col = st.columns(
                    [4.5, 1.0],
                    gap="small",
                )
            
                with manual_url_col:
                    manual_face_url = st.text_input(
                        "Manual Face Reference URL",
                        value="",
                        key="manual_face_reference_url",
                        placeholder="Paste an existing face reference URL",
                        label_visibility="collapsed",
                        help=(
                            "현재 Target Character Control에서 선택한 캐릭터의 "
                            "face reference로 적용합니다."
                        ),
                    )
            
                with manual_apply_col:
                    apply_manual_face_clicked = st.button(
                        "Apply",
                        type="secondary",
                        use_container_width=True,
                        key="apply_manual_face_reference",
                    )
            
                if apply_manual_face_clicked:
                    selected_face_target = st.session_state.get(
                        "character_filter_label",
                        "Image 2 - Girl",
                    )
                    manual_face_url = manual_face_url.strip()
            
                    if not manual_face_url:
                        st.error("Face reference URL을 입력하세요.")
            
                    elif not manual_face_url.lower().startswith(("http://", "https://")):
                        st.error(
                            "http:// 또는 https://로 시작하는 이미지 URL을 입력하세요."
                        )
            
                    elif selected_face_target == "Image 1 - Boy":
                        st.session_state["face_result_image_c1"] = manual_face_url
                        st.session_state["face_result_filename_c1"] = (
                            "manual_boy_face_reference.png"
                        )
                        st.success("Image 1 - Boy face reference가 적용되었습니다.")
                        st.rerun()
            
                    else:
                        st.session_state["face_result_image_c2"] = manual_face_url
                        st.session_state["face_result_filename_c2"] = (
                            "manual_girl_face_reference.png"
                        )
                        st.success("Image 2 - Girl face reference가 적용되었습니다.")
                        st.rerun()

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

            # st.divider()

            generate_clicked = st.button("Generate Character Appearance", type="primary", use_container_width=True)

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

                        with st.spinner("Character Appearance를 생성하는 중입니다..."):
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
                            with st.expander("Collected Character Appearance Config", expanded=False):
                                st.json(config)
                        else:
                            first_image = images[0]
                            
                            st.session_state[f"face_result_image_{character_code}"] = first_image["image"]
                            st.session_state[f"face_result_filename_{character_code}"] = first_image.get("filename", "")
       
                            st.success("Character Appearance 생성이 완료되었습니다.")
                            st.rerun()

                    except KeyError as e:
                        st.error("RunComfy secret 설정이 없습니다.")
                        st.caption("`.streamlit/secrets.toml`에 RUNCOMFY_API_KEY와 DEPLOYMENT_ID를 추가해야 합니다.")
                        st.exception(e)
                        with st.expander("Collected Character Appearance Config", expanded=False):
                            st.json(config)
                    except Exception as e:
                        st.error("RunComfy Character Appearance 실행 중 오류가 발생했습니다.")
                        st.exception(e)
                        with st.expander("Collected Character Appearance Config", expanded=False):
                            st.json(config)
    # st.divider()

    # ------------------- 2B. Reference-based Outfit Change -------------------
    with st.container(border=True):
        st.markdown("### 2B. Reference-based Outfit Change")
        initialize_outfit_reference_inputs()

        preview_col, settings_col = st.columns([1.45, 1.25], gap="large")

        # ================= LEFT: Outfit Change Results =================
        with preview_col:
            st.subheader("Outfit Change Preview")
            body_preview_col1, body_preview_col2 = st.columns(2, gap="medium")

            with body_preview_col1:
                st.markdown("##### Image 1 - Boy")

                if st.session_state.get("body_result_image_c1") is not None:
                    render_image_preview_box(
                        st.session_state["body_result_image_c1"],
                        caption="Image 1 - Boy Final Character Reference",
                        height=400,
                    )
                else:
                    render_empty_preview_box(
                        "Image 1 - Boy outfit-changed reference will appear here.",
                        400,
                    )

            with body_preview_col2:
                st.markdown("##### Image 2 - Girl")

                if st.session_state.get("body_result_image_c2") is not None:
                    render_image_preview_box(
                        st.session_state["body_result_image_c2"],
                        caption="Image 2 - Girl Final Character Reference",
                        height=400,
                    )
                else:
                    render_empty_preview_box(
                        "Image 2 - Girl outfit-changed reference will appear here.",
                        400,
                    )

        # ================= RIGHT: Outfit Change Controls =================
        with settings_col:
            st.subheader("Outfit Change Control")

            st.radio(
                "Target Character",
                options=["Image 1 - Boy", "Image 2 - Girl"],
                index=0,
                horizontal=True,
                key="body_character_filter_label",
            )

            selected_body_target = st.session_state.get(
                "body_character_filter_label",
                "Image 1 - Boy",
            )

            selected_character_code = (
                "c1" if selected_body_target == "Image 1 - Boy" else "c2"
            )

            # if selected_character_code == "c1":
            #     source_character_image = st.session_state.get(
            #         "face_result_image_c1",
            #         "",
            #     )
            #     source_character_label = "Image 1 - Boy"
            # else:
            #     source_character_image = st.session_state.get(
            #         "face_result_image_c2",
            #         "",
            #     )
            #     source_character_label = "Image 2 - Girl"

            # with st.container(border=True):
            #     st.markdown("###### Source Character")
            #     st.caption("Automatically uses the selected result from Step 2A.")

            #     if source_character_image:
            #         st.image(
            #             source_character_image,
            #             caption=f"{source_character_label} · Step 2A Result",
            #             use_container_width=True,
            #         )
            #     else:
            #         st.warning(
            #             f"{source_character_label}의 Step 2A 결과가 없습니다. "
            #             "먼저 Character Appearance를 생성하세요."
            #         )

            st.markdown("###### Garment Input Mode")
            input_mode = st.radio(
                "Garment Input Mode",
                options=["Separate Garments", "Single Outfit Reference"],
                horizontal=True,
                key=f"outfit_input_mode_{selected_character_code}",
                label_visibility="collapsed",
            )

            if input_mode == "Separate Garments":
                st.markdown("###### Garment References")
                st.caption(
                    "Provide separate reference images for the top, bottom, and shoes."
                )

                garment_input_col1, garment_input_col2, garment_input_col3 = st.columns(
                    3,
                    gap="medium",
                )

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
                            help=(
                                f"{garment_label} reference image를 업로드합니다. "
                                "업로드된 이미지는 base64 data URI로 변환되어 "
                                "RunComfy LoadImageFromUrl 노드에 전달됩니다."
                            ),
                        )

                        if uploaded_garment is not None:
                            garment_data_uri = uploaded_image_to_data_uri(
                                uploaded_garment
                            )
                            st.session_state[reference_key] = garment_data_uri

                            st.image(
                                uploaded_garment,
                                caption=f"{garment_label} Reference",
                                width=180,
                            )
                        else:
                            st.session_state[reference_key] = ""
                            render_empty_preview_box(
                                f"{garment_label}<br>Reference",
                                160,
                            )

            else:
                st.markdown("###### Outfit Reference")
                st.caption(
                    "Provide a single full outfit reference image to guide the outfit change."
                )

                upload_col, preview_col = st.columns(
                    [1.0, 1.0],
                    gap="medium",
                )

                single_reference_key = (
                    f"outfit_single_reference_{selected_character_code}"
                )

                with upload_col:
                    single_outfit_upload = st.file_uploader(
                        "Outfit Reference",
                        type=["png", "jpg", "jpeg", "webp"],
                        key=f"outfit_single_upload_{selected_character_code}",
                        help=(
                            "Full outfit reference image를 업로드합니다. "
                            "업로드된 이미지는 base64 data URI로 변환되어 "
                            "RunComfy LoadImageFromUrl 노드에 전달됩니다."
                        ),
                    )

                    if single_outfit_upload is not None:
                        single_outfit_data_uri = uploaded_image_to_data_uri(
                            single_outfit_upload
                        )
                        st.session_state[single_reference_key] = (
                            single_outfit_data_uri
                        )
                    else:
                        st.session_state[single_reference_key] = ""

                with preview_col:
                    st.markdown("##### Single Outfit Reference")

                    if single_outfit_upload is not None:
                        st.image(
                            single_outfit_upload,
                            caption="Single Outfit Reference",
                            width=220,
                        )
                    else:
                        render_empty_preview_box(
                            "Single Outfit<br>Reference",
                            220,
                        )

            # Garment / Outfit reference preview와 생성 버튼 사이 여백
            st.markdown(
                "<div style='height: 24px;'></div>",
                unsafe_allow_html=True,
            )

            generate_body_clicked = st.button(
                "Generate Outfit Reference",
                type="primary",
                use_container_width=True,
            )

            if generate_body_clicked:
                body_config = build_body_ui_config()
                outfit_change_config = body_config["outfit_change"]

                character_filter = outfit_change_config["character_filter"]
                character_code = "c1" if character_filter == "C1" else "c2"
                label = outfit_change_config["label"]

                character_image_url = outfit_change_config.get(
                    "character_image_url",
                    "",
                )
                input_mode = outfit_change_config.get(
                    "input_mode",
                    "Separate Garments",
                )
                garment_references = outfit_change_config.get(
                    "garment_references",
                    {},
                )
                single_outfit_reference = outfit_change_config.get(
                    "single_outfit_reference",
                    "",
                )

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
                    st.error(
                        f"{label}의 Character Appearance가 없습니다. "
                        "먼저 2A에서 해당 캐릭터를 생성하세요."
                    )

                elif input_mode == "Separate Garments" and missing_garments:
                    st.error(
                        "다음 Garment Reference 파일을 업로드하세요: "
                        + ", ".join(missing_garments)
                    )

                elif (
                    input_mode == "Single Outfit Reference"
                    and not single_outfit_reference
                ):
                    st.error("Outfit Reference 파일을 업로드하세요.")

                else:
                    try:
                        api_key = st.secrets["RUNCOMFY_API_KEY"]
                        deployment_id = st.secrets["DEPLOYMENT_ID"]

                        with st.spinner("Reference-based Outfit Change를 실행하는 중입니다..."):
                            result = run_body_generation(
                                api_key=api_key,
                                deployment_id=deployment_id,
                                config=body_config,
                                poll_interval=10,
                                timeout_seconds=1800,
                            )

                        images = result.get("images", [])

                        # backend 수정 전/응답 구조 차이를 고려한 fallback.
                        # 새 Outfit Change workflow의 final SaveImage는 node 17을 사용합니다.
                        if not images:
                            raw_result = result.get("result", result)
                            outputs = raw_result.get("outputs", {})
                            save_output = outputs.get("17", {})
                            raw_images = save_output.get("images", [])

                            images = [
                                {
                                    "label": (
                                        f"{'Boy' if character_code == 'c1' else 'Girl'} "
                                        f"Outfit Reference {idx + 1}"
                                    ),
                                    "image": item.get("url", ""),
                                    "url": item.get("url", ""),
                                    "filename": item.get("filename", ""),
                                    "node_id": "17",
                                    "raw": item,
                                }
                                for idx, item in enumerate(raw_images)
                                if item.get("url")
                            ]

                        if not images:
                            st.error(
                                "RunComfy 실행은 완료되었지만 Outfit Change 결과 이미지가 없습니다."
                            )
                            with st.expander("RunComfy Raw Result", expanded=False):
                                st.json(result)
                            with st.expander(
                                "Collected Outfit Change Config",
                                expanded=False,
                            ):
                                st.json(body_config)
                        else:
                            first_image = images[0]

                            # Step 3가 기존 키를 그대로 사용하므로 결과 저장 키는 유지합니다.
                            st.session_state[f"body_result_image_{character_code}"] = (
                                first_image["image"]
                            )
                            st.session_state[f"body_result_filename_{character_code}"] = (
                                first_image.get("filename", "")
                            )

                            st.success("Reference-based Outfit Change가 완료되었습니다.")
                            st.rerun()

                    except KeyError as e:
                        st.error("RunComfy secret 설정이 없습니다.")
                        st.caption(
                            "`.streamlit/secrets.toml`에 RUNCOMFY_API_KEY와 "
                            "DEPLOYMENT_ID를 추가해야 합니다."
                        )
                        st.exception(e)

                        with st.expander(
                            "Collected Outfit Change Config",
                            expanded=False,
                        ):
                            st.json(body_config)

                    except Exception as e:
                        st.error("RunComfy Outfit Change 실행 중 오류가 발생했습니다.")
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
    boy_body_filename = st.session_state.get("body_result_filename_c1", "")

    girl_body_image = st.session_state.get("body_result_image_c2")
    girl_body_filename = st.session_state.get("body_result_filename_c2", "")

    storyboard_input = build_storyboard_input_config()["storyboard_input"]

    preview_col, settings_col = st.columns([1.45, 1.25], gap="large")

    # ================= LEFT: Generated Storyboard Preview =================
    with preview_col:
        st.subheader("Generated Storyboard Preview")

        scene_preview_candidates = st.session_state.get(
            "scene_candidates",
            [],
        )

        valid_scene_previews = [
            item
            for item in scene_preview_candidates
            if isinstance(item, dict) and item.get("image")
        ]

        # scene_candidates가 없을 때만 기존 단일 결과를 fallback으로 사용
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
                scene_filename = scene_item.get(
                    "filename",
                    "",
                )

                st.markdown(f"##### {scene_label}")

                render_image_preview_box(
                    scene_item["image"],
                    caption=scene_label,
                    height=460,
                )

                # if scene_filename:
                #     st.caption(f"Filename: {scene_filename}")

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

    # ================= RIGHT: Scene Control + References + Button =================
    with settings_col:
        with st.container(border=True):
            # st.subheader("Scene Generation Control")
    
            st.markdown("###### Selected Storyboard Context")
    
            if storyboard_input["selected_shot_count"] == 0:
                st.warning("표시할 scene 정보가 없습니다. Step 1에서 CSV와 shot 선택을 확인하세요.")
            else:
                if storyboard_input["shot_filter"] == "ALL":
                    st.caption(f"Shot Filter: ALL / {storyboard_input['selected_shot_count']} scene(s)")
                elif storyboard_input["custom_shot_ids"]:
                    st.caption(f"Shot Filter: CUSTOM / {storyboard_input['custom_shot_ids']}")
                else:
                    st.caption("Shot Filter: CUSTOM / No shot selected")
    
                st.dataframe(
                    pd.DataFrame(storyboard_input["selected_shot_data"]),
                    use_container_width=True,
                    hide_index=True,
                )

                if ENABLE_MANUAL_FULL_BODY_REFERENCE_INPUT:
                    st.divider()

                    st.subheader("Manual Full-Body Reference Input")

                    manual_body_col1, manual_body_col2 = st.columns(2, gap="medium")

                    with manual_body_col1:
                        manual_boy_body_url = st.text_input(
                            "Manual Image 1 - Boy Full-Body Reference URL",
                            value="",
                            key="manual_boy_body_reference_url",
                            placeholder="Paste Image 1 - Boy full-body image URL here",
                            help="Step 2B를 다시 실행하지 않고, 기존 boy full-body reference URL을 Step 3 입력으로 사용합니다.",
                        )

                    with manual_body_col2:
                        manual_girl_body_url = st.text_input(
                            "Manual Image 2 - Girl Full-Body Reference URL",
                            value="",
                            key="manual_girl_body_reference_url",
                            placeholder="Paste Image 2 - Girl full-body image URL here",
                            help="Step 2B를 다시 실행하지 않고, 기존 girl full-body reference URL을 Step 3 입력으로 사용합니다.",
                        )

                    if st.button(
                        "Use these URLs as Full-Body References",
                        type="secondary",
                        use_container_width=True,
                    ):
                        updated = False

                        if manual_boy_body_url.strip():
                            st.session_state["body_result_image_c1"] = manual_boy_body_url.strip()
                            st.session_state["body_result_filename_c1"] = "manual_boy_body_reference.png"
                            updated = True

                        if manual_girl_body_url.strip():
                            st.session_state["body_result_image_c2"] = manual_girl_body_url.strip()
                            st.session_state["body_result_filename_c2"] = "manual_girl_body_reference.png"
                            updated = True

                        if updated:
                            st.success("Manual full-body reference URL이 Step 3 입력으로 설정되었습니다.")
                            st.rerun()
                        else:
                            st.error("최소 1개 이상의 full-body reference URL을 입력하세요.")

        st.divider()
    
        st.subheader("Character Reference Inputs")
    
        ref_col1, ref_col2 = st.columns(2, gap="medium")
    
        with ref_col1:
            st.markdown("##### Image 1 Reference")
    
            if boy_body_image:
                st.image(
                    boy_body_image,
                    caption="Image 1 Character Reference",
                    width=350,
                )
                # if boy_body_filename:
                #     st.caption(f"Filename: {boy_body_filename}")
            else:
                st.warning("Step 2에서 Image 1 character reference를 먼저 생성해야 합니다.")
    
        with ref_col2:
            st.markdown("##### Image 2 Reference")
    
            if girl_body_image:
                st.image(
                    girl_body_image,
                    caption="Image 2 Character Reference",
                    width=350,
                )
                # if girl_body_filename:
                #     st.caption(f"Filename: {girl_body_filename}")
            else:
                st.warning("Step 2에서 Image 2 character reference를 먼저 생성해야 합니다.")
    
        st.divider()
    
        generate_scene_clicked = st.button(
            "Generate Storyboard Scene",
            type="primary",
            use_container_width=True,
        )

        if generate_scene_clicked:
            storyboard_input = build_storyboard_input_config()["storyboard_input"]

            if not storyboard_input["csv_text"].strip():
                st.error("먼저 Step 1에서 CSV 파일을 업로드해야 합니다.")

            elif (
                storyboard_input["shot_filter"] == "CUSTOM"
                and not storyboard_input["custom_shot_ids"]
            ):
                st.error("shot_filter가 CUSTOM이면 최소 1개 이상의 shot을 선택해야 합니다.")

            elif not boy_body_image:
                st.error("Image 1 - Boy body reference가 없습니다. 먼저 Step 2B에서 생성하세요.")

            elif not girl_body_image:
                st.error("Image 2 - Girl body reference가 없습니다. 먼저 Step 2B에서 생성하세요.")

            else:
                scene_config = build_scene_ui_config()

                try:
                    api_key = st.secrets["RUNCOMFY_API_KEY"]
                    deployment_id = st.secrets["DEPLOYMENT_ID"]

                    with st.spinner("Storyboard Scene을 생성하는 중입니다..."):
                        result = run_scene_generation(
                            api_key=api_key,
                            deployment_id=deployment_id,
                            config=scene_config,
                            poll_interval=10,
                            timeout_seconds=1800,
                        )

                    images = result.get("images", [])

                    if not images:
                        st.error("RunComfy 실행은 완료되었지만 scene 결과 이미지가 없습니다.")

                        with st.expander("RunComfy Raw Scene Result", expanded=False):
                            st.json(result)

                        with st.expander("Collected Scene Generation Config", expanded=False):
                            st.json(scene_config)

                    else:
                        first_image = images[0]

                        st.session_state["scene_candidates"] = images
                        st.session_state["scene_result_image"] = first_image["image"]
                        st.session_state["scene_result_filename"] = first_image.get("filename", "")
                        st.session_state["scene_selected_label"] = first_image["label"]

                        st.success("Storyboard Scene 생성이 완료되었습니다.")
                        st.rerun()

                except KeyError as e:
                    st.error("RunComfy secret 설정이 없습니다.")
                    st.caption("`.streamlit/secrets.toml`에 RUNCOMFY_API_KEY와 DEPLOYMENT_ID를 추가해야 합니다.")
                    st.exception(e)

                    with st.expander("Collected Scene Generation Config", expanded=False):
                        st.json(scene_config)

                except Exception as e:
                    st.error("RunComfy Scene Generation 실행 중 오류가 발생했습니다.")
                    st.exception(e)

                    with st.expander("Collected Scene Generation Config", expanded=False):
                        st.json(scene_config)

# =========================
# Step 4. Camera Refinement
# =========================
with tab4:
    st.header("Step 4. Camera Refinement")
    st.caption(
        "Refine the camera viewpoint of a generated Step 3 scene "
        "using Qwen Multi-Angle Camera control."
    )

    scene_candidates = get_scene_result_candidates()
    sync_scene_reference_selection("camera_input_scene_label", scene_candidates)

    preview_col, settings_col = st.columns([1.6, 1.1], gap="large")

    # ================= LEFT: Camera Refinement Preview =================
    with preview_col:
        st.subheader("Camera Refinement Preview")
    
        st.markdown("#### Refined Scene")
    
        if st.session_state.get("camera_refined_result_image"):
            render_image_preview_box(
                st.session_state["camera_refined_result_image"],
                caption="Camera-Refined Storyboard Scene",
                height=500,
            )
    
            # refined_filename = st.session_state.get(
            #     "camera_refined_result_filename",
            #     "",
            # )
    
            # if refined_filename:
            #     st.caption(f"Filename: {refined_filename}")
    
        else:
            render_empty_preview_box(
                "The camera-refined scene will appear here.",
                500,
        )

    # ================= RIGHT: Camera Refinement Control =================
    with settings_col:
        st.subheader("Camera Refinement Control")

        # -------------------------------------------------
        # Source Scene Input
        # -------------------------------------------------
        with st.container(border=True):
            st.markdown("###### Source Scene")

            if ENABLE_MANUAL_SCENE_REFERENCE_INPUT:
                manual_scene_url = st.text_input(
                    "Manual Scene Reference URL",
                    value="",
                    key="manual_camera_scene_reference_url",
                    placeholder="Paste a RunComfy scene output image URL here",
                    help=(
                        "Step 3를 다시 실행하지 않고 기존 scene image URL을 "
                        "Camera Refinement 입력으로 사용합니다."
                    ),
                )

                if st.button(
                    "Use this URL as Camera Input Scene",
                    type="secondary",
                    use_container_width=True,
                ):
                    if not manual_scene_url.strip():
                        st.error("Scene reference URL을 입력하세요.")
                    else:
                        manual_scene_item = {
                            "label": "Manual Camera Input Scene",
                            "image": manual_scene_url.strip(),
                            "url": manual_scene_url.strip(),
                            "filename": "manual_camera_input_scene.png",
                        }

                        st.session_state["scene_candidates"] = [manual_scene_item]
                        st.session_state["scene_result_image"] = manual_scene_url.strip()
                        st.session_state["scene_result_filename"] = (
                            "manual_camera_input_scene.png"
                        )
                        st.session_state["scene_selected_label"] = (
                            "Manual Camera Input Scene"
                        )
                        st.session_state["camera_input_scene_label"] = (
                            "Manual Camera Input Scene"
                        )

                        st.success(
                            "Manual scene reference URL이 Camera Refinement 입력으로 설정되었습니다."
                        )
                        st.rerun()

                st.divider()

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
                    # filename = selected_input_scene.get("filename", "")
                    # if filename:
                    #     st.caption(f"Selected File: {filename}")

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
                    "Step 3에서 생성된 scene 이미지가 없습니다. "
                    "먼저 Scene Generation을 진행하세요."
                )

        st.divider()

        # -------------------------------------------------
        # Camera Angle Control
        # -------------------------------------------------
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
                    help="좌우 카메라 시점 변화를 제어합니다.",
                )

                st.slider(
                    "Vertical Angle",
                    min_value=-90,
                    max_value=90,
                    value=0,
                    step=1,
                    key="camera_vertical_angle",
                    help="상하 카메라 시점 변화를 제어합니다.",
                )

            with angle_col2:
                st.slider(
                    "Zoom",
                    min_value=0,
                    max_value=10,
                    value=5,
                    step=1,
                    key="camera_zoom",
                    help="카메라 줌과 프레이밍 강도를 제어합니다.",
                )

                # st.checkbox(
                #     "Use Default Angle Prompts",
                #     value=True,
                #     key="camera_default_prompts",
                #     help="Qwen Multi-Angle Camera의 기본 앵글 프롬프트를 사용합니다.",
                # )

                # st.checkbox(
                #     "Enable Camera View Mode",
                #     value=False,
                #     key="camera_view",
                #     help="카메라 관점 중심의 view 해석을 활성화합니다.",
                # )

        # -------------------------------------------------
        # Guide
        # -------------------------------------------------
        # with st.expander("Camera Refinement Guide", expanded=False):
        #     st.markdown(
        #         """
        #         - Step 4는 Step 3에서 생성한 장면을 직접 입력으로 사용합니다.
        #         - Horizontal Angle은 좌/우 카메라 시점을 조정합니다.
        #         - Vertical Angle은 상/하 카메라 시점을 조정합니다.
        #         - Zoom은 장면의 확대/축소와 프레이밍을 조정합니다.
        #         - Use Default Angle Prompts는 Qwen Multi-Angle Camera의 기본 앵글 프롬프트를 사용합니다.
        #         - Camera View Mode는 카메라 관점 중심의 해석을 활성화합니다.
        #         - Sampling 설정은 workflow의 고정값을 사용합니다.
        #         """
        #     )

        # -------------------------------------------------
        # Generate Button
        # -------------------------------------------------
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
                st.error(
                    "Step 3 결과 이미지가 없습니다. 먼저 Scene Generation을 진행하세요."
                )

            elif not selected_input_scene:
                st.error("Camera Refinement에 사용할 입력 scene을 선택하세요.")

            elif not selected_input_scene.get("image"):
                st.error(
                    "선택된 scene 이미지가 비어 있습니다. Step 3 결과를 다시 확인하세요."
                )

            else:
                camera_config = build_camera_refinement_ui_config()

                try:
                    api_key = st.secrets["RUNCOMFY_API_KEY"]
                    deployment_id = st.secrets["DEPLOYMENT_ID"]

                    with st.spinner("Camera-Refined Scene을 생성하는 중입니다..."):
                        result = run_camera_refinement(
                            api_key=api_key,
                            deployment_id=deployment_id,
                            config=camera_config,
                            poll_interval=10,
                            timeout_seconds=1800,
                        )

                    images = result.get("images", [])

                    if not images:
                        st.error(
                            "RunComfy 실행은 완료되었지만 "
                            "camera refinement 결과 이미지가 없습니다."
                        )

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

                        st.success("Camera-Refined Scene 생성이 완료되었습니다.")
                        st.rerun()

                except KeyError as e:
                    st.error("RunComfy secret 설정이 없습니다.")
                    st.caption(
                        "`.streamlit/secrets.toml`에 RUNCOMFY_API_KEY와 "
                        "DEPLOYMENT_ID를 추가해야 합니다."
                    )
                    st.exception(e)

                    with st.expander(
                        "Collected Camera Refinement Config",
                        expanded=False,
                    ):
                        st.json(camera_config)

                except Exception as e:
                    st.error(
                        "RunComfy Camera Refinement 실행 중 오류가 발생했습니다."
                    )
                    st.exception(e)

                    with st.expander(
                        "Collected Camera Refinement Config",
                        expanded=False,
                    ):
                        st.json(camera_config)

                    if "result" in locals():
                        with st.expander(
                            "RunComfy Raw Camera Refinement Result",
                            expanded=False,
                        ):
                            st.json(result)
