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

# ------------------------- 전신 프롬프트 초기화 함수 -------------------------
# 전신 생성용 캐릭터별 프롬프트 값을 Streamlit 세션에 기본값으로 만들어두는 함수
# body_prompt_c1, body_prompt_c2가 없으면 각각 빈 문자열로 초기화
def initialize_body_prompts():
    st.session_state.setdefault("body_prompt_c1", "")
    st.session_state.setdefault("body_prompt_c2", "")

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

# ------------------------- 전신 생성 UI 설정 구성 함수 -------------------------
# Streamlit에서 선택한 캐릭터의 전신 생성 프롬프트와 얼굴 레퍼런스를 전신 생성용 설정 딕셔너리로 구성하는 함수
# 선택 라벨을 C1/C2로 변환한 뒤, 해당 캐릭터의 전신 프롬프트·얼굴 이미지 URL·파일명을 세션에서 가져와 반환
def build_body_ui_config():
    character_filter_label = st.session_state.get(
        "body_character_filter_label",
        "Image 1 - Boy",
    )

    character_filter = body_character_label_to_value(character_filter_label)

    if character_filter == "C1":
        body_prompt = st.session_state.get("body_prompt_c1", "")
        label = "Image 1 - Boy"
        face_image_url = st.session_state.get("face_result_image_c1", "")
        face_filename = st.session_state.get("face_result_filename_c1", "")
    else:
        body_prompt = st.session_state.get("body_prompt_c2", "")
        label = "Image 2 - Girl"
        face_image_url = st.session_state.get("face_result_image_c2", "")
        face_filename = st.session_state.get("face_result_filename_c2", "")

    return {
        "body_generation": {
            "character_filter": character_filter,
            "label": label,
            "body_prompt": body_prompt,
            "face_image_url": face_image_url,
            "face_filename": face_filename,
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
# 선택된 장면 이미지와 카메라 조정값을 카메라 앵글 보정 워크플로우용 설정 딕셔너리로 구성하는 함수
# 스토리보드 입력값과 선택된 장면 후보를 가져온 뒤, 수평/수직 앵글·줌·프롬프트 소스 설정을 정리해 반환
def build_camera_refinement_ui_config():
    storyboard_input = build_storyboard_input_config()["storyboard_input"]

    scene_candidates = get_scene_result_candidates()

    selected_scene = get_selected_candidate(
        scene_candidates,
        st.session_state.get("camera_input_scene_label", ""),
    )

    prompt_source = st.session_state.get(
        "camera_prompt_source",
        "Use Camera Angle Prompt",
    )

    switch_setting = 1 if prompt_source == "Preserve Original Scene Prompt" else 2

    return {
        "storyboard_input": storyboard_input,
        "camera_angle_refinement": {
            "input_scene": {
                "label": selected_scene["label"] if selected_scene else "",
                "image": selected_scene.get("image", "") if selected_scene else "",
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
    st.caption("Generate face identity references first, then convert them into full-body references for scene generation.")

    # ------------------- 2A. Character Identity Generation ------------------- 
    with st.container(border=True):
        st.markdown("### 2A. Character Identity Generation")

        preview_col, settings_col = st.columns([1.25, 1.15], gap="large")

        with preview_col:
            st.subheader("Character Identity Preview")
        
            face_preview_col1, face_preview_col2 = st.columns(2, gap="medium")
        
            with face_preview_col1:
                st.markdown("##### Image 1 - Boy")
            
                if st.session_state.get("face_result_image_c1") is not None:
                    render_image_preview_box(
                        st.session_state["face_result_image_c1"],
                        caption="Image 1 - Boy Face Reference",
                        height=400,
                    )
                else:
                    render_empty_preview_box(
                        "Image 1 - Boy face reference will appear here.",
                        400,
                    )
        
            with face_preview_col2:
                st.markdown("##### Image 2 - Girl")
            
                if st.session_state.get("face_result_image_c2") is not None:
                    render_image_preview_box(
                        st.session_state["face_result_image_c2"],
                        caption="Image 2 - Girl Face Reference",
                        height=400,
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

            # st.divider()

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

                        with st.spinner("Character Identity를 생성하는 중입니다..."):
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
                            first_image = images[0]
                            
                            st.session_state[f"face_result_image_{character_code}"] = first_image["image"]
                            st.session_state[f"face_result_filename_{character_code}"] = first_image.get("filename", "")
       
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
    # st.divider()

    # ------------------- 2B. Full-Body Reference Generation ------------------- 
    with st.container(border=True):
        st.markdown("### 2B. Full-Body Reference Generation")
        initialize_body_prompts()

        preview_col, settings_col = st.columns([1.45, 1.25], gap="large")

        with preview_col:
            st.subheader("Full-Body Reference Preview")
            body_preview_col1, body_preview_col2 = st.columns(2, gap="medium")

            with body_preview_col1:
                st.markdown("##### Image 1 - Boy")
            
                if st.session_state.get("body_result_image_c1") is not None:
                    render_image_preview_box(
                        st.session_state["body_result_image_c1"],
                        caption="Image 1 - Boy Full-Body Reference",
                        height=400,
                    )
                else:
                    render_empty_preview_box(
                        "Image 1 - Boy full-body reference will appear here.",
                        400,
                    )
            
            with body_preview_col2:
                st.markdown("##### Image 2 - Girl")
            
                if st.session_state.get("body_result_image_c2") is not None:
                    render_image_preview_box(
                        st.session_state["body_result_image_c2"],
                        caption="Image 2 - Girl Full-Body Reference",
                        height=400,
                    )
                else:
                    render_empty_preview_box(
                        "Image 2 - Girl full-body reference will appear here.",
                        400,
                    )

        with settings_col:
            st.subheader("Reference Generation Control")

            if ENABLE_MANUAL_FACE_REFERENCE_INPUT:
                st.markdown("### Manual Face Reference Input")

                manual_face_url = st.text_input(
                    "Manual Face Reference URL for 2B Test",
                    value="",
                    key="manual_face_reference_url",
                    placeholder="Paste a RunComfy output image URL here",
                    help="2A를 다시 실행하지 않고, 기존 face reference URL을 직접 넣어서 2B만 테스트합니다.",
                )

                if st.button("Use this URL as Face Reference", type="secondary", use_container_width=True):
                    selected_body_target = st.session_state.get(
                        "body_character_filter_label",
                        "Image 1 - Boy",
                    )

                    if not manual_face_url.strip():
                        st.error("Face reference URL을 입력하세요.")

                    elif selected_body_target == "Image 1 - Boy":
                        st.session_state["face_result_image_c1"] = manual_face_url.strip()
                        st.session_state["face_result_filename_c1"] = "manual_boy_face_reference.png"
                        st.success("Image 1 - Boy face reference URL이 수동으로 설정되었습니다.")
                        st.rerun()

                    else:
                        st.session_state["face_result_image_c2"] = manual_face_url.strip()
                        st.session_state["face_result_filename_c2"] = "manual_girl_face_reference.png"
                        st.success("Image 2 - Girl face reference URL이 수동으로 설정되었습니다.")
                        st.rerun()

            st.radio(
                "body_character_filter",
                options=["Image 1 - Boy", "Image 2 - Girl"],
                index=0,
                horizontal=True,
                key="body_character_filter_label",
            )

            # st.divider()
            st.markdown("### Full-Body Prompt Editor")
            selected_body_target = st.session_state.get("body_character_filter_label", "Image 1 - Boy")

            if selected_body_target == "Image 1 - Boy":
                st.text_area(
                    "Image 1 - Boy Body Prompt",
                    key="body_prompt_c1",
                    height=260,
                    placeholder=BODY_PROMPT_PLACEHOLDER,
                )
            else:
                st.text_area(
                    "Image 2 - Girl Body Prompt",
                    key="body_prompt_c2",
                    height=260,
                    placeholder=BODY_PROMPT_PLACEHOLDER,
                )

            if SHOW_REFERENCE_PROMPT_GUIDELINES:
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

            # st.divider()
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
                    body_generation_config = body_config["body_generation"]
            
                    character_filter = body_generation_config["character_filter"]
                    character_code = "c1" if character_filter == "C1" else "c2"
                    label = body_generation_config["label"]
            
                    face_image_url = body_generation_config.get("face_image_url", "")
                    body_prompt = body_generation_config.get("body_prompt", "")
            
                    if not face_image_url:
                        st.error(f"{label}의 Face Reference가 없습니다. 먼저 2A에서 얼굴 이미지를 생성하세요.")
            
                    elif not body_prompt.strip():
                        st.error(f"{label}의 Full-Body Prompt를 입력하세요.")
            
                    else:
                        try:
                            api_key = st.secrets["RUNCOMFY_API_KEY"]
                            deployment_id = st.secrets["DEPLOYMENT_ID"]
            
                            with st.spinner("RunComfy에서 Full-Body Reference를 생성하는 중입니다..."):
                                result = run_body_generation(
                                    api_key=api_key,
                                    deployment_id=deployment_id,
                                    config=body_config,
                                    poll_interval=10,
                                    timeout_seconds=1800,
                                )
            
                            images = result.get("images", [])

                            if not images:
                                raw_result = result.get("result", result)
                                outputs = raw_result.get("outputs", {})
                                save_output = outputs.get("1244", {})
                                raw_images = save_output.get("images", [])
                            
                                images = [
                                    {
                                        "label": f"{'Boy Body' if character_code == 'c1' else 'Girl Body'} {idx + 1}",
                                        "image": item.get("url", ""),
                                        "url": item.get("url", ""),
                                        "filename": item.get("filename", ""),
                                        "node_id": "1244",
                                        "raw": item,
                                    }
                                    for idx, item in enumerate(raw_images)
                                    if item.get("url")
                                ]
            
                            if not images:
                                st.error("RunComfy 실행은 완료되었지만 결과 이미지가 없습니다.")
                                with st.expander("RunComfy Raw Result", expanded=False):
                                    st.json(result)
                                with st.expander("Collected Full-Body Reference Config", expanded=False):
                                    st.json(body_config)
                            else:
                                first_image = images[0]
                            
                                st.session_state[f"body_result_image_{character_code}"] = first_image["image"]
                                st.session_state[f"body_result_filename_{character_code}"] = first_image.get("filename", "")
                            
                                st.success("Full-Body Reference 생성이 완료되었습니다.")
                                st.rerun()
            
                        except KeyError as e:
                            st.error("RunComfy secret 설정이 없습니다.")
                            st.caption("`.streamlit/secrets.toml`에 RUNCOMFY_API_KEY와 DEPLOYMENT_ID를 추가해야 합니다.")
                            st.exception(e)
            
                            with st.expander("Collected Full-Body Reference Config", expanded=False):
                                st.json(body_config)
            
                        except Exception as e:
                            st.error("RunComfy Full-Body Reference 실행 중 오류가 발생했습니다.")
                            st.exception(e)
            
                            with st.expander("Collected Full-Body Reference Config", expanded=False):
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

        if storyboard_input["selected_shot_count"] == 0:
            st.caption("Selected Storyboard Context: None")
        else:
            st.caption(f"Selected Scene Count: {storyboard_input['selected_shot_count']}")

        if "scene_result_image" in st.session_state:
            st.image(
                st.session_state["scene_result_image"],
                caption="Generated Storyboard Scene",
                use_container_width=True,
            )
        else:
            render_empty_preview_box("Generated storyboard scene will appear here.", 560)

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
                    use_container_width=True,
                )
                if boy_body_filename:
                    st.caption(f"Filename: {boy_body_filename}")
            else:
                st.warning("Step 2에서 Image 1 character reference를 먼저 생성해야 합니다.")
    
        with ref_col2:
            st.markdown("##### Image 2 Reference")
    
            if girl_body_image:
                st.image(
                    girl_body_image,
                    caption="Image 2 Character Reference",
                    use_container_width=True,
                )
                if girl_body_filename:
                    st.caption(f"Filename: {girl_body_filename}")
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

                    with st.spinner("RunComfy에서 Storyboard Scene을 생성하는 중입니다..."):
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
# Step 4. Camera Angle Refinement
# =========================
# =========================
# Step 4. Camera Angle Refinement
# =========================
with tab4:
    st.header("Step 4. Camera Angle Refinement")

    scene_candidates = get_scene_result_candidates()
    sync_scene_reference_selection("camera_input_scene_label", scene_candidates)

    preview_col, settings_col = st.columns([1.6, 1.1], gap="large")

    # ================= LEFT: Camera Refinement Preview =================
    with preview_col:
        st.subheader("Camera Refinement Preview")

        st.markdown("#### Input Scene")

        selected_input_scene = get_selected_candidate(
            scene_candidates,
            st.session_state.get("camera_input_scene_label", ""),
        )

        if selected_input_scene and selected_input_scene.get("image"):
            st.image(
                selected_input_scene["image"],
                caption=selected_input_scene.get("label", "Input Scene"),
                use_container_width=True,
            )
        else:
            render_empty_preview_box(
                "A generated scene from Step 3 will appear here.",
                360,
            )

        st.divider()

        st.markdown("#### Refined Scene")

        if st.session_state.get("camera_refined_result_image"):
            st.image(
                st.session_state["camera_refined_result_image"],
                caption="Camera-Refined Storyboard Scene",
                use_container_width=True,
            )

            refined_filename = st.session_state.get("camera_refined_result_filename", "")
            if refined_filename:
                st.caption(f"Filename: {refined_filename}")
        else:
            render_empty_preview_box(
                "The camera-refined scene will appear here.",
                360,
            )

    # ================= RIGHT: Camera Refinement Control =================
    with settings_col:
        st.subheader("Camera Refinement Control")

        # -------------------------------------------------
        # Source Scene Input
        # -------------------------------------------------
        with st.container(border=True):
            st.markdown("###### Source Scene Input")

            if ENABLE_MANUAL_SCENE_REFERENCE_INPUT:
                st.markdown("### Manual Scene Reference Input")

                manual_scene_url = st.text_input(
                    "Manual Scene Reference URL for Step 4 Test",
                    value="",
                    key="manual_camera_scene_reference_url",
                    placeholder="Paste a RunComfy scene output image URL here",
                    help="Step 3를 다시 실행하지 않고, 기존 scene image URL을 Step 4 Camera Refinement 입력으로 사용합니다.",
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
                        st.session_state["scene_result_filename"] = "manual_camera_input_scene.png"
                        st.session_state["scene_selected_label"] = "Manual Camera Input Scene"
                        st.session_state["camera_input_scene_label"] = "Manual Camera Input Scene"

                        st.success("Manual scene reference URL이 Step 4 입력으로 설정되었습니다.")
                        st.rerun()

                st.divider()

            st.markdown("### Select Existing Scene")

            scene_candidates = get_scene_result_candidates()
            sync_scene_reference_selection("camera_input_scene_label", scene_candidates)

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
                st.warning(
                    "Step 3에서 생성된 scene 이미지가 없습니다. 먼저 Scene Generation을 진행하세요."
                )

        st.divider()

        # -------------------------------------------------
        # Prompt Source Control
        # -------------------------------------------------
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

        # -------------------------------------------------
        # Camera Angle Control
        # -------------------------------------------------
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
            st.info("Camera Angle Control is available only when 'Use Camera Angle Prompt' is selected.")

        # -------------------------------------------------
        # Sampling Control
        # -------------------------------------------------
        st.divider()

        with st.container(border=True):
            st.markdown("###### Sampling Control")

            sample_col1, sample_col2 = st.columns(2)

            with sample_col1:
                st.slider(
                    "Camera Refinement Steps",
                    min_value=5,
                    max_value=30,
                    value=15,
                    step=1,
                    key="camera_steps",
                    help="프롬프트 반영력과 디테일을 조정합니다. 기본 workflow의 5 steps보다 12~20 정도가 안정적입니다.",
                )

            with sample_col2:
                st.slider(
                    "Camera Refinement CFG",
                    min_value=1.0,
                    max_value=5.0,
                    value=2.0,
                    step=0.1,
                    key="camera_cfg",
                    help="카메라 프롬프트 반영 강도를 조정합니다.",
                )

        # -------------------------------------------------
        # Guide
        # -------------------------------------------------
        with st.expander("Camera Refinement Guide", expanded=False):
            st.markdown(
                """
                - Step 4는 Step 3에서 생성된 장면을 입력으로 받아 카메라 앵글을 다시 조정하는 단계입니다.
                - Preserve Original Scene Prompt는 기존 storyboard scene description을 유지하는 모드입니다.
                - Use Camera Angle Prompt는 Qwen Multi-Angle Camera가 생성한 앵글 제어 프롬프트를 사용하는 모드입니다.
                - Horizontal Angle은 좌/우 시점 변화를, Vertical Angle은 상/하 시점 변화를 의미합니다.
                - Zoom은 인물 및 장면의 프레이밍 강도를 조정합니다.
                - Steps와 CFG가 너무 낮으면 camera angle prompt가 약하게 반영될 수 있습니다.
                """
            )

        # -------------------------------------------------
        # Generate Button
        # -------------------------------------------------
        st.divider()

        generate_camera_clicked = st.button(
            "Generate Camera-Refined Scene",
            type="primary",
            use_container_width=True,
        )

        if generate_camera_clicked:
            storyboard_input = build_storyboard_input_config()["storyboard_input"]

            scene_candidates = get_scene_result_candidates()

            selected_input_scene = get_selected_candidate(
                scene_candidates,
                st.session_state.get("camera_input_scene_label", ""),
            )

            if not scene_candidates:
                st.error("Step 3 결과 이미지가 없습니다. 먼저 Scene Generation을 진행하세요.")

            elif not selected_input_scene:
                st.error("Camera refinement에 사용할 입력 scene을 선택하세요.")

            elif not selected_input_scene.get("image"):
                st.error("선택된 scene 이미지 URL이 비어 있습니다. Step 3 결과를 다시 확인하세요.")

            elif not storyboard_input["csv_text"].strip():
                st.error("Step 1의 CSV 데이터가 없습니다. Camera refinement를 위해 CSV를 먼저 업로드하세요.")

            elif (
                storyboard_input["shot_filter"] == "CUSTOM"
                and not storyboard_input["custom_shot_ids"]
            ):
                st.error("shot_filter가 CUSTOM이면 최소 1개 이상의 shot을 선택해야 합니다.")

            elif (
                st.session_state.get("camera_prompt_source") == "Preserve Original Scene Prompt"
                and storyboard_input["selected_shot_count"] == 0
            ):
                st.error("Preserve Original Scene Prompt를 사용하려면 Step 1의 shot 데이터가 필요합니다.")

            else:
                camera_config = build_camera_refinement_ui_config()

                # backend.py에서 camera_control.get("steps"), camera_control.get("cfg")를 읽을 수 있도록 추가
                camera_config["camera_angle_refinement"]["camera_control"]["steps"] = st.session_state.get(
                    "camera_steps",
                    15,
                )
                camera_config["camera_angle_refinement"]["camera_control"]["cfg"] = st.session_state.get(
                    "camera_cfg",
                    2.0,
                )

                try:
                    api_key = st.secrets["RUNCOMFY_API_KEY"]
                    deployment_id = st.secrets["DEPLOYMENT_ID"]

                    with st.spinner("RunComfy에서 Camera-Refined Scene을 생성하는 중입니다..."):
                        result = run_camera_refinement(
                            api_key=api_key,
                            deployment_id=deployment_id,
                            config=camera_config,
                            poll_interval=10,
                            timeout_seconds=1800,
                        )

                    images = result.get("images", [])

                    if not images:
                        st.error("RunComfy 실행은 완료되었지만 camera refinement 결과 이미지가 없습니다.")

                        with st.expander("RunComfy Raw Camera Refinement Result", expanded=False):
                            st.json(result)

                        with st.expander("Collected Camera Refinement Config", expanded=False):
                            st.json(camera_config)

                        with st.expander("Patched Camera Refinement Workflow", expanded=False):
                            st.json(result.get("workflow_api_json", {}))

                    else:
                        first_image = images[0]

                        st.session_state["camera_refined_candidates"] = images
                        st.session_state["camera_refined_result_image"] = first_image["image"]
                        st.session_state["camera_refined_result_filename"] = first_image.get("filename", "")
                        st.session_state["camera_refined_selected_label"] = first_image.get(
                            "label",
                            "Camera Refined Scene 1",
                        )

                        st.success("Camera-Refined Scene 생성이 완료되었습니다.")
                        st.rerun()

                except KeyError as e:
                    st.error("RunComfy secret 설정이 없습니다.")
                    st.caption("`.streamlit/secrets.toml`에 RUNCOMFY_API_KEY와 DEPLOYMENT_ID를 추가해야 합니다.")
                    st.exception(e)

                    with st.expander("Collected Camera Refinement Config", expanded=False):
                        st.json(camera_config)

                except Exception as e:
                    st.error("RunComfy Camera Refinement 실행 중 오류가 발생했습니다.")
                    st.exception(e)

                    with st.expander("Collected Camera Refinement Config", expanded=False):
                        st.json(camera_config)

                    if "result" in locals():
                        with st.expander("RunComfy Raw Camera Refinement Result", expanded=False):
                            st.json(result)

# import csv
# import io
# import pandas as pd
# import streamlit as st

# from backend import (
#     run_csv_parser_test,
#     run_face_generation,
#     run_body_generation,
#     run_scene_generation,
#     run_camera_refinement,
# )

# # =========================
# # Fixed Values
# # =========================
# FIXED_BASE_BACKGROUND_CLOTHING_PROMPT = "gray background"

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

# BODY_TYPE_OPTIONS = [
#     "Beefy", "Buxom", "Buff", "Chubby", "Curvy", "Fat", "Fit", "Flyweight",
#     "Hefty", "Large", "Lanky", "Midweight", "Morbidly obese", "Muscular",
#     "Obese", "Overweight", "Petite", "Plump", "Portly", "Rotund", "Short",
#     "Skinny", "Slight", "Slim", "Small", "Stout", "Stocky", "Tall", "Thick",
#     "Tiny", "Voluptuous", "Well-built", "Well-endowed", "Underweight",
# ]

# FACE_SHAPE_OPTIONS = [
#     "Circle", "Diamond", "Heart", "Heart with Pointed Chin", "Heart with Rounded Chin",
#     "Heart with V-Shape Chin", "Inverted Triangle", "Long", "Oblong", "Oval", "Pear",
#     "Rectangle", "Round", "Round with Defined Cheekbones", "Round with High Cheekbones",
#     "Round with Soft Cheekbones", "Square", "Square Oval", "Square Round",
#     "Square with Rounded Jaw", "Square with Sharp Jaw", "Square with Soft Jaw", "Triangle",
# ]

# EXPRESSION_OPTIONS = [
#     "Amused", "Angry", "Anxious", "Bored", "Calm", "Cautious", "Confused",
#     "Contemptuous", "Content", "Curious", "Disappointed", "Disgusted", "Envious",
#     "Excited", "Fearful", "Happy", "In love", "Nervous", "Peaceful", "Pensive",
#     "Prideful", "Proud", "Relieved", "Sad", "Sarcastic", "Serene", "Serious",
#     "Shy", "Silly", "Smiling", "Surprised", "Surprised and Amused",
# ]

# EYES_COLOR_OPTIONS = ["Albino", "Amber", "Brown", "Dark Brown", "Black", "Hazel", "Blue", "Green", "Gray"]
# EYES_SHAPE_OPTIONS = [
#     "Almond Eyes Shape", "Asian Eyes Shape", "Close-Set Eyes Shape", "Deep Set Eyes Shape",
#     "Downturned Eyes Shape", "Double Eyelid Eyes Shape", "Hooded Eyes Shape",
#     "Monolid Eyes Shape", "Oval Eyes Shape", "Protruding Eyes Shape", "Round Eyes Shape",
#     "Upturned Eyes Shape",
# ]
# LIPS_COLOR_OPTIONS = [
#     "Berry Lips", "Black Lips", "Blue Lips", "Brown Lips", "Burgundy Lips", "Coral Lips",
#     "Glossy Red Lips", "Mauve Lips", "Orange Lips", "Peach Lips", "Pink Lips", "Plum Lips",
#     "Purple Lips", "Red Lips", "Yellow Lips",
# ]
# LIPS_SHAPE_OPTIONS = [
#     "Biting Lips", "Bow-shaped Lips", "Closed Lips", "Cupid's Bow Lips",
#     "Defined Cupid's Bow Lips", "Flat Cupid's Bow Lips", "Full Lips", "Heart-shaped Lips",
#     "Large Lips", "Medium Lips", "Neutral Lips", "Parted Lips", "Plump Lips", "Pouting Lips",
#     "Round Lips", "Small Lips", "Smiling Lips", "Soft Cupid's Bow Lips", "Thin Lips",
#     "Upper Lip Mole Lips", "Wide Lips",
# ]
# HAIR_STYLE_OPTIONS = [
#     "Afro", "A-line bob", "Asymmetrical", "Balayage", "Bald", "Ballerina bun", "Bangs",
#     "Beehive", "Beehivecut", "Bleached spikes", "Blunt bob", "Blunt", "Bob", "Bouffant",
#     "Bowl", "Box braids", "Box fade", "Braided", "Braided bob", "Braided pigtails",
#     "Brave shortcut with shaved sides", "Bushy", "Buzz", "Caesar", "Chignon", "Choppy",
#     "Cloudy", "Cornrows", "Crew", "Curly", "Curly bob", "Curly Frizzy", "Curtain bangs",
#     "Deep side part", "Double Bun", "Dreadlocks", "Faded afro", "Faux hawk",
#     "Faux hawk short pixie", "Feathered", "Female bald", "Fishtail braids", "Flat topcut",
#     "French bob", "French braids", "French twist", "Frohawk", "Hair ringlets", "High ponytail",
#     "High skin fade", "Honey", "Italian bob", "Layered", "Lemonade braids", "Long bob",
#     "Long with bangs", "Long pixie", "Long ponytail", "Long straight", "Loose Curly Afro",
#     "Marmaid waves", "Micro braids", "Middle part ponytails", "Modern caesar", "Mohawk",
#     "Multicolored", "Pastel", "Pigtails", "Pixie", "Platinum", "Pompadour", "Quiff",
#     "Razor fade with curls", "Red", "Right side shaved", "Salt and pepper", "Shag", "Short curly",
#     "Short curly pixie", "Short", "Short messy curls", "Shoulder Length with Bangs",
#     "Shoulder length straight", "Side braid", "Side Part Comb-Overstyle With High Fade",
#     "Side-swept bangs", "Side-swept fringe", "Sideswept pixie", "Smooth lob", "Space buns",
#     "Spiky", "Stacked bob", "Stacked Curls in Short Bob", "Stitch braids", "Strawberry",
#     "Strawberry blonde", "Sweeping pixie", "Taper fade with waves", "Taperedcut with shaved side",
#     "Textured brush back", "Textured", "Tomboy", "Top Knot", "Twin braids", "Twintails",
#     "Two dutch braids", "Undercut", "Updo", "Very long wave", "Waterfall braids", "Wavy",
#     "Wavy bob", "Wavy with curtain bangs", "Wavy French Bob Vibes from 1920", "Wavy undercut",
# ]
# HAIR_COLOR_OPTIONS = [
#     "Auburn", "Black", "Blonde", "Burgundy", "Caramel", "Chestnut", "Chocolate", "Copper",
#     "Dirty", "Gray", "Honey", "Jet Black", "Mahogany", "Multicolored", "Pastel", "Platinum",
#     "Red", "Salt and pepper", "Silver", "Strawberry", "White",
# ]


# # =========================
# # Helper Functions
# # =========================

# # ----------------------------- 업로드 파일 텍스트 변환 함수 -----------------------------
# # 업로드된 파일의 바이너리 데이터를 여러 인코딩 방식으로 시도해 문자열 텍스트로 안전하게 디코딩하는 함수
# def decode_uploaded_file(uploaded_file):
#     raw = uploaded_file.getvalue()
#     for encoding in ["utf-8-sig", "utf-8", "cp949"]:
#         try:
#             return raw.decode(encoding)
#         except Exception:
#             pass
#     return raw.decode("utf-8", errors="ignore")

# # ----------------------------- CSV 샷 ID 추출 함수 -----------------------------
# # CSV 텍스트의 첫 번째 열에서 중복 없이 샷 ID 목록을 추출하는 함수입니다.
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

# # ----------------------------- CSV 데이터프레임 변환 함수 -----------------------------
# # CSV 텍스트를 pandas DataFrame으로 변환하고, 실패하거나 비어 있으면 빈 DataFrame을 반환하는 함수
# def read_csv_as_dataframe(csv_text):
#     if not csv_text.strip():
#         return pd.DataFrame()
#     try:
#         return pd.read_csv(io.StringIO(csv_text))
#     except Exception:
#         return pd.DataFrame()

# # ----------------------------- 샷 ID 컬럼 탐색 함수 -----------------------------
# # DataFrame에서 샷 ID로 보이는 컬럼을 찾고, 없으면 첫 번째 컬럼을 반환하는 함수
# def get_shot_id_column(df):
#     if df.empty:
#         return None

#     candidates = ["shot", "shot_id", "shot id", "id", "Shot", "Shot ID", "Shot_ID"]
#     for col in df.columns:
#         if str(col).strip() in candidates:
#             return col
#     return df.columns[0]

# # ----------------------------- 선택 샷 DataFrame 추출 함수 -----------------------------
# # Streamlit 세션의 CSV 데이터에서 현재 선택된 샷 필터에 해당하는 행만 추출해 DataFrame으로 반환하는 함수
# # CSV를 DataFrame으로 읽은 뒤, ALL이면 전체를 반환하고 CUSTOM이면 선택된 샷 ID만 필터링함
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

# # ----------------------------- 스토리보드 입력 설정 구성 함수 -----------------------------
# # Streamlit 세션의 CSV와 샷 선택 정보를 모아 RunComfy 요청용 storyboard_input 설정 딕셔너리로 구성하는 함수
# def build_storyboard_input_config():
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

# # ------------------------- 캐릭터 라벨 변환 함수 ----------------------------- 
# # 선택된 캐릭터 라벨을 RunComfy 워크플로우에서 사용하는 C1, C2 값으로 변환하는 함수
# # 라벨이 Image 1 - Boy이면 C1, Image 2 - Girl이면 C2를 반환하고 기본값은 함수별로 다르게 설정
# def character_label_to_value(label):
#     return {"Image 1 - Boy": "C1", "Image 2 - Girl": "C2"}.get(label, "C2")

# # ------------------------- 전신 프롬프트 초기화 함수 -------------------------
# # 전신 생성에서 선택된 캐릭터 라벨을 워크플로우용 C1, C2 값으로 변환하는 함수
# # 라벨이 Image 1 - Boy이면 C1, Image 2 - Girl이면 C2를 반환하고, 알 수 없는 라벨이면 기본값으로 C1을 반환
# def body_character_label_to_value(label):
#     return {"Image 1 - Boy": "C1", "Image 2 - Girl": "C2"}.get(label, "C1")

# # ------------------------- 전신 프롬프트 초기화 함수 -------------------------
# # 전신 생성용 캐릭터별 프롬프트 값을 Streamlit 세션에 기본값으로 만들어두는 함수
# # body_prompt_c1, body_prompt_c2가 없으면 각각 빈 문자열로 초기화
# def initialize_body_prompts():
#     st.session_state.setdefault("body_prompt_c1", "")
#     st.session_state.setdefault("body_prompt_c2", "")

# # ------------------------- 장면 샷 필터 설정 조회 함수 -------------------------
# # 장면 생성에 사용할 현재 샷 필터 값과 커스텀 샷 ID 값을 가져오는 함수
# # build_storyboard_input_config()에서 storyboard_input을 만들고, 그 안의 shot_filter와 custom_shot_ids를 반환
# def get_scene_shot_filter_config():
#     storyboard_input = build_storyboard_input_config()["storyboard_input"]
#     return storyboard_input["shot_filter"], storyboard_input["custom_shot_ids"]

# # ------------------------- 선택 후보 조회 함수 -------------------------
# # 후보 목록에서 선택된 라벨과 일치하는 항목을 찾아 반환하는 함수
# # candidates를 순회하며 label이 selected_label과 같은 항목을 반환하고, 없으면 None을 반환
# def get_selected_candidate(candidates, selected_label):
#     for item in candidates:
#         if item["label"] == selected_label:
#             return item
#     return None


# # ------------------------- 장면 레퍼런스 선택 동기화 함수 -------------------------
# # 장면 생성용 레퍼런스 선택값이 후보 목록과 일치하도록 세션 상태를 보정하는 함수
# # 후보 라벨이 없으면 선택값을 비우고, 현재 선택값이 후보에 없으면 첫 번째 후보 라벨로 자동 설정
# def sync_scene_reference_selection(session_key, candidates):
#     labels = [item["label"] for item in candidates]

#     if not labels:
#         st.session_state[session_key] = ""
#         return

#     if st.session_state.get(session_key) not in labels:
#         st.session_state[session_key] = labels[0]

# # ------------------------- 얼굴 생성 UI 설정 구성 함수 -------------------------
# # Streamlit에서 선택한 스토리보드·캐릭터·외형 설정을 얼굴 생성 워크플로우용 설정 딕셔너리로 구성하는 함수
# # 세션 상태에서 CSV, 샷 필터, 캐릭터 정보, 얼굴 외형 옵션, 피부 디테일 값을 가져와 RunComfy 요청에 맞는 노드별 입력값으로 정리
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
#             "gender": "-",
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
#             "eyes_shape": st.session_state.get("eyes_shape", "Double Eyelid Eyes Shape"),
#             "lips_color": st.session_state.get("lips_color", "Peach Lips"),
#             "lips_shape": st.session_state.get("lips_shape", "Thin Lips"),
#             "facial_expression": st.session_state.get("facial_expression", "Curious"),
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
#             key: default_value if st.session_state.get(f"skin_{key}", False) else 0.0
#             for key, default_value in SKIN_DEFAULTS.items()
#         },
#     }

# # ------------------------- 전신 생성 UI 설정 구성 함수 -------------------------
# # Streamlit에서 선택한 캐릭터의 전신 생성 프롬프트와 얼굴 레퍼런스를 전신 생성용 설정 딕셔너리로 구성하는 함수
# # 선택 라벨을 C1/C2로 변환한 뒤, 해당 캐릭터의 전신 프롬프트·얼굴 이미지 URL·파일명을 세션에서 가져와 반환
# def build_body_ui_config():
#     character_filter_label = st.session_state.get(
#         "body_character_filter_label",
#         "Image 1 - Boy",
#     )

#     character_filter = body_character_label_to_value(character_filter_label)

#     if character_filter == "C1":
#         body_prompt = st.session_state.get("body_prompt_c1", "")
#         label = "Image 1 - Boy"
#         face_image_url = st.session_state.get("face_result_image_c1", "")
#         face_filename = st.session_state.get("face_result_filename_c1", "")
#     else:
#         body_prompt = st.session_state.get("body_prompt_c2", "")
#         label = "Image 2 - Girl"
#         face_image_url = st.session_state.get("face_result_image_c2", "")
#         face_filename = st.session_state.get("face_result_filename_c2", "")

#     return {
#         "body_generation": {
#             "character_filter": character_filter,
#             "label": label,
#             "body_prompt": body_prompt,
#             "face_image_url": face_image_url,
#             "face_filename": face_filename,
#         }
#     }
 
# # ------------------------- 장면 생성 UI 설정 구성 함수 -------------------------
# # 스토리보드 선택 정보와 남자/여자 전신 레퍼런스를 장면 생성용 설정 딕셔너리로 구성하는 함수
# # 스토리보드 입력값을 만든 뒤, 선택된 c1 남자 전신 후보와 c2 여자 전신 후보의 라벨·이미지·파일명을 reference_images에 넣어 반환
# def build_scene_ui_config():
#     storyboard_input = build_storyboard_input_config()["storyboard_input"]

#     boy_body_image = st.session_state.get("body_result_image_c1", "")
#     boy_body_filename = st.session_state.get("body_result_filename_c1", "")

#     girl_body_image = st.session_state.get("body_result_image_c2", "")
#     girl_body_filename = st.session_state.get("body_result_filename_c2", "")

#     return {
#         "storyboard_input": storyboard_input,
#         "scene_generation": {
#             "shot_filter": storyboard_input["shot_filter"],
#             "custom_shot_ids": storyboard_input["custom_shot_ids"],
#             "selected_shot_count": storyboard_input["selected_shot_count"],
#             "selected_shot_data": storyboard_input["selected_shot_data"],
#             "reference_images": {
#                 "image_1_boy_body": {
#                     "label": "Image 1 - Boy Character Reference",
#                     "image": boy_body_image,
#                     "filename": boy_body_filename,
#                 },
#                 "image_2_girl_body": {
#                     "label": "Image 2 - Gril Character Reference",
#                     "image": girl_body_image,
#                     "filename": girl_body_filename,
#                 },
#             },
#         },
#     }

# # ------------------------- 장면 결과 후보 조회 함수 -------------------------
# # 장면 생성 결과 이미지 후보 목록을 Streamlit 세션에서 가져와 화면 표시용으로 정리하는 함수
# # scene_candidates를 label, image, filename 형태로 정리하고, 후보가 없으면 기존 단일 장면 결과 이미지를 fallback으로 추가
# def get_scene_result_candidates():
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
#         normalized.append({"label": "Scene 1", "image": fallback_image, "filename": fallback_filename})

#     return normalized

# # ------------------------- 카메라 보정 UI 설정 구성 함수 -------------------------
# # 선택된 장면 이미지와 카메라 조정값을 카메라 앵글 보정 워크플로우용 설정 딕셔너리로 구성하는 함수
# # 스토리보드 입력값과 선택된 장면 후보를 가져온 뒤, 수평/수직 앵글·줌·프롬프트 소스 설정을 정리해 반환
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
#                 "image": selected_scene.get("image", "") if selected_scene else "",
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

# # ------------------------- 빈 미리보기 박스 렌더링 함수 -------------------------
# # 이미지가 없을 때 안내 메시지를 담은 빈 미리보기 박스를 Streamlit 화면에 표시하는 함수
# # 전달받은 message와 height 값을 HTML 스타일에 넣고 st.markdown()으로 렌더링
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

# def render_image_preview_box(image_url, caption="", height=400):
#     max_img_height = height - 55

#     html = (
#         f'<div style="'
#         f'border: 1px dashed #999;'
#         f'border-radius: 12px;'
#         f'height: {height}px;'
#         f'display: flex;'
#         f'flex-direction: column;'
#         f'align-items: center;'
#         f'justify-content: center;'
#         f'color: #777;'
#         f'font-size: 14px;'
#         f'text-align: center;'
#         f'padding: 12px;'
#         f'">'
#         f'<img src="{image_url}" style="'
#         f'max-width: 100%;'
#         f'max-height: {max_img_height}px;'
#         f'object-fit: contain;'
#         f'border-radius: 8px;'
#         f'">'
#         f'<div style="margin-top: 8px;">{caption}</div>'
#         f'</div>'
#     )

#     st.markdown(html, unsafe_allow_html=True)


# # =========================
# # Page Config
# # =========================
# st.set_page_config(
#     page_title="AI Storyboard Pipeline",
#     page_icon="🎬",
#     layout="wide",
# )

# st.title("🎬 AI Storyboard Generation Pipeline")
# st.caption("A ComfyUI-based generation pipeline for character-consistent cinematic storyboard creation and camera-angle refinement")


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


# # =================================
# # Step 1. Storyboard Data Parsing
# # =================================
# with tab1:
#     st.header("Step 1. Storyboard Data Parsing")

#     # Streamlit 화면에 파일 업로드 버튼/영역을 만드는 함수
#     # 사용자가 CSV 같은 파일을 선택하면, 그 파일을 코드에서 읽을 수 있는 uploaded_file 객체로 반환
#     uploaded_csv = st.file_uploader(
#         "Upload Storyboard CSV",
#         type=["csv"],
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
#                     st.dataframe(preview_df, use_container_width=True, hide_index=True)
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
#                         # help="CUSTOM일 때만 shot을 선택합니다.",
#                     )
#                 else:
#                     st.warning("CSV에서 추출된 shot id가 없습니다.")

#             # st.divider()
    
#     else:
#         st.info("CSV 파일을 업로드하면 Parsed Storyboard Data Preview와 Shot Selection Control이 표시됩니다.")


# # ========================================
# # Step 2. Character Reference Generation
# # ========================================
# with tab2:

#     st.header("Step 2. Character Reference Generation")
#     st.caption("Generate face identity references first, then convert them into full-body references for scene generation.")

#     # ------------------- 2A. Character Identity Generation ------------------- 
#     with st.container(border=True):
#         st.markdown("### 2A. Character Identity Generation")

#         preview_col, settings_col = st.columns([1.25, 1.15], gap="large")

#         with preview_col:
#             st.subheader("Character Identity Preview")
        
#             face_preview_col1, face_preview_col2 = st.columns(2, gap="medium")
        
#             with face_preview_col1:
#                 st.markdown("##### Image 1 - Boy")
            
#                 if st.session_state.get("face_result_image_c1") is not None:
#                     render_image_preview_box(
#                         st.session_state["face_result_image_c1"],
#                         caption="Image 1 - Boy Face Reference",
#                         height=400,
#                     )
#                 else:
#                     render_empty_preview_box(
#                         "Image 1 - Boy face reference will appear here.",
#                         400,
#                     )
        
#             with face_preview_col2:
#                 st.markdown("##### Image 2 - Girl")
            
#                 if st.session_state.get("face_result_image_c2") is not None:
#                     render_image_preview_box(
#                         st.session_state["face_result_image_c2"],
#                         caption="Image 2 - Girl Face Reference",
#                         height=400,
#                     )
#                 else:
#                     render_empty_preview_box(
#                         "Image 2 - Girl face reference will appear here.",
#                         400,
#                     )

            
#         with settings_col:
#             st.subheader("Target Character Control")

#             st.radio(
#                 "character_filter",
#                 options=["Image 1 - Boy", "Image 2 - Girl"],
#                 index=1,
#                 horizontal=True,
#                 key="character_filter_label",
#             )

#             with st.expander("Identity Attribute Controls", expanded=True):
#                 with st.container(border=True):
#                     st.markdown("###### Core Identity")
#                     basic_col1, basic_col2 = st.columns(2)

#                     with basic_col1:
#                         st.slider("Age", min_value=1, max_value=100, value=9, step=1, key="age")
#                     with basic_col2:
#                         st.selectbox(
#                             "Nationality",
#                             options=["South Korean", "Korean", "East Asian", "Japanese", "Chinese"],
#                             index=0,
#                             key="nationality",
#                         )

#                 with st.container(border=True):
#                     st.markdown("###### Face")
#                     face_col1, face_col2, face_col3 = st.columns(3)

#                     with face_col1:
#                         st.selectbox("Body Type", options=BODY_TYPE_OPTIONS, index=23, key="body_type")
#                     with face_col2:
#                         st.selectbox("Face Shape", options=FACE_SHAPE_OPTIONS, index=21, key="face_shape")
#                     with face_col3:
#                         st.selectbox("Expression", options=EXPRESSION_OPTIONS, index=9, key="facial_expression")

#                 with st.container(border=True):
#                     st.markdown("###### Eyes / Lips")
#                     eye_col1, eye_col2 = st.columns(2)

#                     with eye_col1:
#                         st.selectbox("Eyes Color", options=EYES_COLOR_OPTIONS, index=2, key="eyes_color")
#                         st.selectbox("Eyes Shape", options=EYES_SHAPE_OPTIONS, index=1, key="eyes_shape")
#                     with eye_col2:
#                         st.selectbox("Lips Color", options=LIPS_COLOR_OPTIONS, index=9, key="lips_color")
#                         st.selectbox("Lips Shape", options=LIPS_SHAPE_OPTIONS, index=18, key="lips_shape")

#                 with st.container(border=True):
#                     st.markdown("###### Hair")
#                     hair_col1, hair_col2, hair_col3 = st.columns(3)

#                     with hair_col1:
#                         st.selectbox("Hair Style", options=HAIR_STYLE_OPTIONS, index=12, key="hair_style")
#                     with hair_col2:
#                         st.selectbox("Hair Color", options=HAIR_COLOR_OPTIONS, index=5, key="hair_color")
#                     with hair_col3:
#                         st.selectbox("Hair Length", options=["-", "Short", "Medium", "Long"], index=0, key="hair_length")

#             with st.expander("Fine-Grained Appearance Attributes", expanded=False):
#                 skin_keys = list(SKIN_DEFAULTS.keys())
#                 skin_cols = st.columns(3)
#                 for i, key in enumerate(skin_keys):
#                     with skin_cols[i % 3]:
#                         default_checked = SKIN_DEFAULTS[key] > 0
#                         st.checkbox(key, value=default_checked, key=f"skin_{key}")

#             # st.divider()

#             generate_clicked = st.button("Generate Character Identity", type="primary", use_container_width=True)

#             if generate_clicked:
#                 csv_text = st.session_state.get("csv_text", "")

#                 if not csv_text.strip():
#                     st.error("먼저 Step 1에서 CSV 파일을 업로드해야 합니다.")
#                 elif st.session_state.get("shot_filter_mode", "ALL") == "CUSTOM" and len(st.session_state.get("custom_shots", [])) == 0:
#                     st.error("shot_filter가 CUSTOM이면 최소 1개 이상의 shot을 선택해야 합니다.")
#                 else:
#                     config = build_face_ui_config()
#                     character_filter = config["character_registry_parser"]["character_filter"]
#                     character_code = "c1" if character_filter == "C1" else "c2"

#                     try:
#                         api_key = st.secrets["RUNCOMFY_API_KEY"]
#                         deployment_id = st.secrets["DEPLOYMENT_ID"]

#                         with st.spinner("Character Identity를 생성하는 중입니다..."):
#                             result = run_face_generation(
#                                 api_key=api_key,
#                                 deployment_id=deployment_id,
#                                 config=config,
#                                 poll_interval=5,
#                                 timeout_seconds=900,
#                             )

#                         images = result.get("images", [])

#                         if not images:
#                             st.error("RunComfy 실행은 완료되었지만 결과 이미지가 없습니다.")
#                             with st.expander("RunComfy Raw Result", expanded=False):
#                                 st.json(result)
#                             with st.expander("Collected Character Identity Config", expanded=False):
#                                 st.json(config)
#                         else:
#                             first_image = images[0]
                            
#                             st.session_state[f"face_result_image_{character_code}"] = first_image["image"]
#                             st.session_state[f"face_result_filename_{character_code}"] = first_image.get("filename", "")
       
#                             st.success("Character Identity 생성이 완료되었습니다.")
#                             st.rerun()

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
#     # st.divider()

#     # ------------------- 2B. Full-Body Reference Generation ------------------- 
#     with st.container(border=True):
#         st.markdown("### 2B. Full-Body Reference Generation")
#         initialize_body_prompts()

#         preview_col, settings_col = st.columns([1.45, 1.25], gap="large")

#         with preview_col:
#             st.subheader("Full-Body Reference Preview")
#             body_preview_col1, body_preview_col2 = st.columns(2, gap="medium")

#             with body_preview_col1:
#                 st.markdown("##### Image 1 - Boy")
            
#                 if st.session_state.get("body_result_image_c1") is not None:
#                     render_image_preview_box(
#                         st.session_state["body_result_image_c1"],
#                         caption="Image 1 - Boy Full-Body Reference",
#                         height=400,
#                     )
#                 else:
#                     render_empty_preview_box(
#                         "Image 1 - Boy full-body reference will appear here.",
#                         400,
#                     )
            
#             with body_preview_col2:
#                 st.markdown("##### Image 2 - Girl")
            
#                 if st.session_state.get("body_result_image_c2") is not None:
#                     render_image_preview_box(
#                         st.session_state["body_result_image_c2"],
#                         caption="Image 2 - Girl Full-Body Reference",
#                         height=400,
#                     )
#                 else:
#                     render_empty_preview_box(
#                         "Image 2 - Girl full-body reference will appear here.",
#                         400,
#                     )

#         with settings_col:
#             st.subheader("Reference Generation Control")

#             st.markdown("### Manual Face Reference Input")

#             manual_face_url = st.text_input(
#                 "Manual Face Reference URL for 2B Test",
#                 value="",
#                 key="manual_face_reference_url",
#                 placeholder="Paste a RunComfy output image URL here",
#                 help="2A를 다시 실행하지 않고, 기존 face reference URL을 직접 넣어서 2B만 테스트합니다.",
#             )
            
#             if st.button("Use this URL as Face Reference", type="secondary", use_container_width=True):
#                 selected_body_target = st.session_state.get(
#                     "body_character_filter_label",
#                     "Image 1 - Boy",
#                 )
            
#                 if not manual_face_url.strip():
#                     st.error("Face reference URL을 입력하세요.")
            
#                 elif selected_body_target == "Image 1 - Boy":
#                     st.session_state["face_result_image_c1"] = manual_face_url.strip()
#                     st.session_state["face_result_filename_c1"] = "manual_boy_face_reference.png"
#                     st.success("Image 1 - Boy face reference URL이 수동으로 설정되었습니다.")
#                     st.rerun()
            
#                 else:
#                     st.session_state["face_result_image_c2"] = manual_face_url.strip()
#                     st.session_state["face_result_filename_c2"] = "manual_girl_face_reference.png"
#                     st.success("Image 2 - Girl face reference URL이 수동으로 설정되었습니다.")
#                     st.rerun()
            
#             st.radio(
#                 "body_character_filter",
#                 options=["Image 1 - Boy", "Image 2 - Girl"],
#                 index=0,
#                 horizontal=True,
#                 key="body_character_filter_label",
#             )

#             # st.divider()
#             st.markdown("### Full-Body Prompt Editor")
#             selected_body_target = st.session_state.get("body_character_filter_label", "Image 1 - Boy")

#             if selected_body_target == "Image 1 - Boy":
#                 st.text_area(
#                     "Image 1 - Boy Body Prompt",
#                     key="body_prompt_c1",
#                     height=260,
#                     placeholder=BODY_PROMPT_PLACEHOLDER,
#                 )
#             else:
#                 st.text_area(
#                     "Image 2 - Girl Body Prompt",
#                     key="body_prompt_c2",
#                     height=260,
#                     placeholder=BODY_PROMPT_PLACEHOLDER,
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

#             # st.divider()
#             generate_body_clicked = st.button(
#                 "Generate Full-Body Reference",
#                 type="primary",
#                 use_container_width=True,
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
#                     body_generation_config = body_config["body_generation"]
            
#                     character_filter = body_generation_config["character_filter"]
#                     character_code = "c1" if character_filter == "C1" else "c2"
#                     label = body_generation_config["label"]
            
#                     face_image_url = body_generation_config.get("face_image_url", "")
#                     body_prompt = body_generation_config.get("body_prompt", "")
            
#                     if not face_image_url:
#                         st.error(f"{label}의 Face Reference가 없습니다. 먼저 2A에서 얼굴 이미지를 생성하세요.")
            
#                     elif not body_prompt.strip():
#                         st.error(f"{label}의 Full-Body Prompt를 입력하세요.")
            
#                     else:
#                         try:
#                             api_key = st.secrets["RUNCOMFY_API_KEY"]
#                             deployment_id = st.secrets["DEPLOYMENT_ID"]
            
#                             with st.spinner("RunComfy에서 Full-Body Reference를 생성하는 중입니다..."):
#                                 result = run_body_generation(
#                                     api_key=api_key,
#                                     deployment_id=deployment_id,
#                                     config=body_config,
#                                     poll_interval=10,
#                                     timeout_seconds=1800,
#                                 )
            
#                             images = result.get("images", [])

#                             if not images:
#                                 raw_result = result.get("result", result)
#                                 outputs = raw_result.get("outputs", {})
#                                 save_output = outputs.get("1244", {})
#                                 raw_images = save_output.get("images", [])
                            
#                                 images = [
#                                     {
#                                         "label": f"{'Boy Body' if character_code == 'c1' else 'Girl Body'} {idx + 1}",
#                                         "image": item.get("url", ""),
#                                         "url": item.get("url", ""),
#                                         "filename": item.get("filename", ""),
#                                         "node_id": "1244",
#                                         "raw": item,
#                                     }
#                                     for idx, item in enumerate(raw_images)
#                                     if item.get("url")
#                                 ]
            
#                             if not images:
#                                 st.error("RunComfy 실행은 완료되었지만 결과 이미지가 없습니다.")
#                                 with st.expander("RunComfy Raw Result", expanded=False):
#                                     st.json(result)
#                                 with st.expander("Collected Full-Body Reference Config", expanded=False):
#                                     st.json(body_config)
#                             else:
#                                 first_image = images[0]
                            
#                                 st.session_state[f"body_result_image_{character_code}"] = first_image["image"]
#                                 st.session_state[f"body_result_filename_{character_code}"] = first_image.get("filename", "")
                            
#                                 st.success("Full-Body Reference 생성이 완료되었습니다.")
#                                 st.rerun()
            
#                         except KeyError as e:
#                             st.error("RunComfy secret 설정이 없습니다.")
#                             st.caption("`.streamlit/secrets.toml`에 RUNCOMFY_API_KEY와 DEPLOYMENT_ID를 추가해야 합니다.")
#                             st.exception(e)
            
#                             with st.expander("Collected Full-Body Reference Config", expanded=False):
#                                 st.json(body_config)
            
#                         except Exception as e:
#                             st.error("RunComfy Full-Body Reference 실행 중 오류가 발생했습니다.")
#                             st.exception(e)
            
#                             with st.expander("Collected Full-Body Reference Config", expanded=False):
#                                 st.json(body_config)


# # ===========================================
# # Step 3. Reference-Guided Scene Generation
# # ===========================================
# with tab3:
#     st.header("Step 3. Reference-Guided Scene Generation")

#     boy_body_image = st.session_state.get("body_result_image_c1")
#     boy_body_filename = st.session_state.get("body_result_filename_c1", "")

#     girl_body_image = st.session_state.get("body_result_image_c2")
#     girl_body_filename = st.session_state.get("body_result_filename_c2", "")

#     storyboard_input = build_storyboard_input_config()["storyboard_input"]

#     preview_col, settings_col = st.columns([1.45, 1.25], gap="large")

#     # ================= LEFT: Generated Storyboard Preview =================
#     with preview_col:
#         st.subheader("Generated Storyboard Preview")

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
#             render_empty_preview_box("Generated storyboard scene will appear here.", 560)

#     # ================= RIGHT: Scene Control + References + Button =================
#     with settings_col:
#         with st.container(border=True):
#             # st.subheader("Scene Generation Control")
    
#             st.markdown("###### Selected Storyboard Context")
    
#             if storyboard_input["selected_shot_count"] == 0:
#                 st.warning("표시할 scene 정보가 없습니다. Step 1에서 CSV와 shot 선택을 확인하세요.")
#             else:
#                 if storyboard_input["shot_filter"] == "ALL":
#                     st.caption(f"Shot Filter: ALL / {storyboard_input['selected_shot_count']} scene(s)")
#                 elif storyboard_input["custom_shot_ids"]:
#                     st.caption(f"Shot Filter: CUSTOM / {storyboard_input['custom_shot_ids']}")
#                 else:
#                     st.caption("Shot Filter: CUSTOM / No shot selected")
    
#                 st.dataframe(
#                     pd.DataFrame(storyboard_input["selected_shot_data"]),
#                     use_container_width=True,
#                     hide_index=True,
#                 )

#                 st.divider()

#                 st.subheader("Manual Full-Body Reference Input")
        
#                 manual_body_col1, manual_body_col2 = st.columns(2, gap="medium")
        
#                 with manual_body_col1:
#                     manual_boy_body_url = st.text_input(
#                         "Manual Image 1 - Boy Full-Body Reference URL",
#                         value="",
#                         key="manual_boy_body_reference_url",
#                         placeholder="Paste Image 1 - Boy full-body image URL here",
#                         help="Step 2B를 다시 실행하지 않고, 기존 boy full-body reference URL을 Step 3 입력으로 사용합니다.",
#                     )
        
#                 with manual_body_col2:
#                     manual_girl_body_url = st.text_input(
#                         "Manual Image 2 - Girl Full-Body Reference URL",
#                         value="",
#                         key="manual_girl_body_reference_url",
#                         placeholder="Paste Image 2 - Girl full-body image URL here",
#                         help="Step 2B를 다시 실행하지 않고, 기존 girl full-body reference URL을 Step 3 입력으로 사용합니다.",
#                     )
        
#                 if st.button(
#                     "Use these URLs as Full-Body References",
#                     type="secondary",
#                     use_container_width=True,
#                 ):
#                     updated = False
        
#                     if manual_boy_body_url.strip():
#                         st.session_state["body_result_image_c1"] = manual_boy_body_url.strip()
#                         st.session_state["body_result_filename_c1"] = "manual_boy_body_reference.png"
#                         updated = True
        
#                     if manual_girl_body_url.strip():
#                         st.session_state["body_result_image_c2"] = manual_girl_body_url.strip()
#                         st.session_state["body_result_filename_c2"] = "manual_girl_body_reference.png"
#                         updated = True
        
#                     if updated:
#                         st.success("Manual full-body reference URL이 Step 3 입력으로 설정되었습니다.")
#                         st.rerun()
#                     else:
#                         st.error("최소 1개 이상의 full-body reference URL을 입력하세요.")
        
#         st.divider()
    
#         st.subheader("Character Reference Inputs")
    
#         ref_col1, ref_col2 = st.columns(2, gap="medium")
    
#         with ref_col1:
#             st.markdown("##### Image 1 Reference")
    
#             if boy_body_image:
#                 st.image(
#                     boy_body_image,
#                     caption="Image 1 Character Reference",
#                     use_container_width=True,
#                 )
#                 if boy_body_filename:
#                     st.caption(f"Filename: {boy_body_filename}")
#             else:
#                 st.warning("Step 2에서 Image 1 character reference를 먼저 생성해야 합니다.")
    
#         with ref_col2:
#             st.markdown("##### Image 2 Reference")
    
#             if girl_body_image:
#                 st.image(
#                     girl_body_image,
#                     caption="Image 2 Character Reference",
#                     use_container_width=True,
#                 )
#                 if girl_body_filename:
#                     st.caption(f"Filename: {girl_body_filename}")
#             else:
#                 st.warning("Step 2에서 Image 2 character reference를 먼저 생성해야 합니다.")
    
#         st.divider()
    
#         generate_scene_clicked = st.button(
#             "Generate Storyboard Scene",
#             type="primary",
#             use_container_width=True,
#         )

#         if generate_scene_clicked:
#             storyboard_input = build_storyboard_input_config()["storyboard_input"]

#             if not storyboard_input["csv_text"].strip():
#                 st.error("먼저 Step 1에서 CSV 파일을 업로드해야 합니다.")

#             elif (
#                 storyboard_input["shot_filter"] == "CUSTOM"
#                 and not storyboard_input["custom_shot_ids"]
#             ):
#                 st.error("shot_filter가 CUSTOM이면 최소 1개 이상의 shot을 선택해야 합니다.")

#             elif not boy_body_image:
#                 st.error("Image 1 - Boy body reference가 없습니다. 먼저 Step 2B에서 생성하세요.")

#             elif not girl_body_image:
#                 st.error("Image 2 - Girl body reference가 없습니다. 먼저 Step 2B에서 생성하세요.")

#             else:
#                 scene_config = build_scene_ui_config()

#                 try:
#                     api_key = st.secrets["RUNCOMFY_API_KEY"]
#                     deployment_id = st.secrets["DEPLOYMENT_ID"]

#                     with st.spinner("RunComfy에서 Storyboard Scene을 생성하는 중입니다..."):
#                         result = run_scene_generation(
#                             api_key=api_key,
#                             deployment_id=deployment_id,
#                             config=scene_config,
#                             poll_interval=10,
#                             timeout_seconds=1800,
#                         )

#                     images = result.get("images", [])

#                     if not images:
#                         st.error("RunComfy 실행은 완료되었지만 scene 결과 이미지가 없습니다.")

#                         with st.expander("RunComfy Raw Scene Result", expanded=False):
#                             st.json(result)

#                         with st.expander("Collected Scene Generation Config", expanded=False):
#                             st.json(scene_config)

#                     else:
#                         first_image = images[0]

#                         st.session_state["scene_candidates"] = images
#                         st.session_state["scene_result_image"] = first_image["image"]
#                         st.session_state["scene_result_filename"] = first_image.get("filename", "")
#                         st.session_state["scene_selected_label"] = first_image["label"]

#                         st.success("Storyboard Scene 생성이 완료되었습니다.")
#                         st.rerun()

#                 except KeyError as e:
#                     st.error("RunComfy secret 설정이 없습니다.")
#                     st.caption("`.streamlit/secrets.toml`에 RUNCOMFY_API_KEY와 DEPLOYMENT_ID를 추가해야 합니다.")
#                     st.exception(e)

#                     with st.expander("Collected Scene Generation Config", expanded=False):
#                         st.json(scene_config)

#                 except Exception as e:
#                     st.error("RunComfy Scene Generation 실행 중 오류가 발생했습니다.")
#                     st.exception(e)

#                     with st.expander("Collected Scene Generation Config", expanded=False):
#                         st.json(scene_config)

# # =========================
# # Step 4. Camera Angle Refinement
# # =========================
# # =========================
# # Step 4. Camera Angle Refinement
# # =========================
# with tab4:
#     st.header("Step 4. Camera Angle Refinement")

#     scene_candidates = get_scene_result_candidates()
#     sync_scene_reference_selection("camera_input_scene_label", scene_candidates)

#     preview_col, settings_col = st.columns([1.6, 1.1], gap="large")

#     # ================= LEFT: Camera Refinement Preview =================
#     with preview_col:
#         st.subheader("Camera Refinement Preview")

#         st.markdown("#### Input Scene")

#         selected_input_scene = get_selected_candidate(
#             scene_candidates,
#             st.session_state.get("camera_input_scene_label", ""),
#         )

#         if selected_input_scene and selected_input_scene.get("image"):
#             st.image(
#                 selected_input_scene["image"],
#                 caption=selected_input_scene.get("label", "Input Scene"),
#                 use_container_width=True,
#             )
#         else:
#             render_empty_preview_box(
#                 "A generated scene from Step 3 or manual scene reference will appear here.",
#                 360,
#             )

#         st.divider()

#         st.markdown("#### Refined Scene")

#         if st.session_state.get("camera_refined_result_image"):
#             st.image(
#                 st.session_state["camera_refined_result_image"],
#                 caption="Camera-Refined Storyboard Scene",
#                 use_container_width=True,
#             )

#             refined_filename = st.session_state.get("camera_refined_result_filename", "")
#             if refined_filename:
#                 st.caption(f"Filename: {refined_filename}")
#         else:
#             render_empty_preview_box(
#                 "The camera-refined scene will appear here.",
#                 360,
#             )

#     # ================= RIGHT: Camera Refinement Control =================
#     with settings_col:
#         st.subheader("Camera Refinement Control")

#         # -------------------------------------------------
#         # Source Scene Input
#         # -------------------------------------------------
#         with st.container(border=True):
#             st.markdown("###### Source Scene Input")

#             st.markdown("### Manual Scene Reference Input")

#             manual_scene_url = st.text_input(
#                 "Manual Scene Reference URL for Step 4 Test",
#                 value="",
#                 key="manual_camera_scene_reference_url",
#                 placeholder="Paste a RunComfy scene output image URL here",
#                 help="Step 3를 다시 실행하지 않고, 기존 scene image URL을 Step 4 Camera Refinement 입력으로 사용합니다.",
#             )

#             if st.button(
#                 "Use this URL as Camera Input Scene",
#                 type="secondary",
#                 use_container_width=True,
#             ):
#                 if not manual_scene_url.strip():
#                     st.error("Scene reference URL을 입력하세요.")
#                 else:
#                     manual_scene_item = {
#                         "label": "Manual Camera Input Scene",
#                         "image": manual_scene_url.strip(),
#                         "url": manual_scene_url.strip(),
#                         "filename": "manual_camera_input_scene.png",
#                     }

#                     st.session_state["scene_candidates"] = [manual_scene_item]
#                     st.session_state["scene_result_image"] = manual_scene_url.strip()
#                     st.session_state["scene_result_filename"] = "manual_camera_input_scene.png"
#                     st.session_state["scene_selected_label"] = "Manual Camera Input Scene"
#                     st.session_state["camera_input_scene_label"] = "Manual Camera Input Scene"

#                     st.success("Manual scene reference URL이 Step 4 입력으로 설정되었습니다.")
#                     st.rerun()

#             st.divider()

#             st.markdown("### Select Existing Scene")

#             scene_candidates = get_scene_result_candidates()
#             sync_scene_reference_selection("camera_input_scene_label", scene_candidates)

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
#                 st.warning(
#                     "Step 3에서 생성된 scene 이미지가 없습니다. 먼저 Scene Generation을 진행하거나 manual scene URL을 입력하세요."
#                 )

#         st.divider()

#         # -------------------------------------------------
#         # Prompt Source Control
#         # -------------------------------------------------
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

#         # -------------------------------------------------
#         # Camera Angle Control
#         # -------------------------------------------------
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
#             st.info("Camera Angle Control is available only when 'Use Camera Angle Prompt' is selected.")

#         # -------------------------------------------------
#         # Sampling Control
#         # -------------------------------------------------
#         st.divider()

#         with st.container(border=True):
#             st.markdown("###### Sampling Control")

#             sample_col1, sample_col2 = st.columns(2)

#             with sample_col1:
#                 st.slider(
#                     "Camera Refinement Steps",
#                     min_value=5,
#                     max_value=30,
#                     value=15,
#                     step=1,
#                     key="camera_steps",
#                     help="프롬프트 반영력과 디테일을 조정합니다. 기본 workflow의 5 steps보다 12~20 정도가 안정적입니다.",
#                 )

#             with sample_col2:
#                 st.slider(
#                     "Camera Refinement CFG",
#                     min_value=1.0,
#                     max_value=5.0,
#                     value=2.0,
#                     step=0.1,
#                     key="camera_cfg",
#                     help="카메라 프롬프트 반영 강도를 조정합니다.",
#                 )

#         # -------------------------------------------------
#         # Guide
#         # -------------------------------------------------
#         with st.expander("Camera Refinement Guide", expanded=False):
#             st.markdown(
#                 """
#                 - Step 4는 Step 3에서 생성된 장면 또는 manual scene URL을 입력으로 받아 카메라 앵글을 다시 조정하는 단계입니다.
#                 - Manual Scene Reference Input을 사용하면 Step 3를 다시 실행하지 않고 Step 4만 테스트할 수 있습니다.
#                 - Preserve Original Scene Prompt는 기존 storyboard scene description을 유지하는 모드입니다.
#                 - Use Camera Angle Prompt는 Qwen Multi-Angle Camera가 생성한 앵글 제어 프롬프트를 사용하는 모드입니다.
#                 - Horizontal Angle은 좌/우 시점 변화를, Vertical Angle은 상/하 시점 변화를 의미합니다.
#                 - Zoom은 인물 및 장면의 프레이밍 강도를 조정합니다.
#                 - Steps와 CFG가 너무 낮으면 camera angle prompt가 약하게 반영될 수 있습니다.
#                 """
#             )

#         # -------------------------------------------------
#         # Generate Button
#         # -------------------------------------------------
#         st.divider()

#         generate_camera_clicked = st.button(
#             "Generate Camera-Refined Scene",
#             type="primary",
#             use_container_width=True,
#         )

#         if generate_camera_clicked:
#             storyboard_input = build_storyboard_input_config()["storyboard_input"]

#             scene_candidates = get_scene_result_candidates()

#             selected_input_scene = get_selected_candidate(
#                 scene_candidates,
#                 st.session_state.get("camera_input_scene_label", ""),
#             )

#             if not scene_candidates:
#                 st.error("Step 3 결과 이미지 또는 manual scene reference가 없습니다.")

#             elif not selected_input_scene:
#                 st.error("Camera refinement에 사용할 입력 scene을 선택하세요.")

#             elif not selected_input_scene.get("image"):
#                 st.error("선택된 scene 이미지 URL이 비어 있습니다. Step 3 결과 또는 manual URL을 다시 확인하세요.")

#             elif not storyboard_input["csv_text"].strip():
#                 st.error("Step 1의 CSV 데이터가 없습니다. Camera refinement를 위해 CSV를 먼저 업로드하세요.")

#             elif (
#                 storyboard_input["shot_filter"] == "CUSTOM"
#                 and not storyboard_input["custom_shot_ids"]
#             ):
#                 st.error("shot_filter가 CUSTOM이면 최소 1개 이상의 shot을 선택해야 합니다.")

#             elif (
#                 st.session_state.get("camera_prompt_source") == "Preserve Original Scene Prompt"
#                 and storyboard_input["selected_shot_count"] == 0
#             ):
#                 st.error("Preserve Original Scene Prompt를 사용하려면 Step 1의 shot 데이터가 필요합니다.")

#             else:
#                 camera_config = build_camera_refinement_ui_config()

#                 # backend.py에서 camera_control.get("steps"), camera_control.get("cfg")를 읽을 수 있도록 추가
#                 camera_config["camera_angle_refinement"]["camera_control"]["steps"] = st.session_state.get(
#                     "camera_steps",
#                     15,
#                 )
#                 camera_config["camera_angle_refinement"]["camera_control"]["cfg"] = st.session_state.get(
#                     "camera_cfg",
#                     2.0,
#                 )

#                 try:
#                     api_key = st.secrets["RUNCOMFY_API_KEY"]
#                     deployment_id = st.secrets["DEPLOYMENT_ID"]

#                     with st.spinner("RunComfy에서 Camera-Refined Scene을 생성하는 중입니다..."):
#                         result = run_camera_refinement(
#                             api_key=api_key,
#                             deployment_id=deployment_id,
#                             config=camera_config,
#                             poll_interval=10,
#                             timeout_seconds=1800,
#                         )

#                     images = result.get("images", [])

#                     if not images:
#                         st.error("RunComfy 실행은 완료되었지만 camera refinement 결과 이미지가 없습니다.")

#                         with st.expander("RunComfy Raw Camera Refinement Result", expanded=False):
#                             st.json(result)

#                         with st.expander("Collected Camera Refinement Config", expanded=False):
#                             st.json(camera_config)

#                         with st.expander("Patched Camera Refinement Workflow", expanded=False):
#                             st.json(result.get("workflow_api_json", {}))

#                     else:
#                         first_image = images[0]

#                         st.session_state["camera_refined_candidates"] = images
#                         st.session_state["camera_refined_result_image"] = first_image["image"]
#                         st.session_state["camera_refined_result_filename"] = first_image.get("filename", "")
#                         st.session_state["camera_refined_selected_label"] = first_image.get(
#                             "label",
#                             "Camera Refined Scene 1",
#                         )

#                         st.success("Camera-Refined Scene 생성이 완료되었습니다.")
#                         st.rerun()

#                 except KeyError as e:
#                     st.error("RunComfy secret 설정이 없습니다.")
#                     st.caption("`.streamlit/secrets.toml`에 RUNCOMFY_API_KEY와 DEPLOYMENT_ID를 추가해야 합니다.")
#                     st.exception(e)

#                     with st.expander("Collected Camera Refinement Config", expanded=False):
#                         st.json(camera_config)

#                 except Exception as e:
#                     st.error("RunComfy Camera Refinement 실행 중 오류가 발생했습니다.")
#                     st.exception(e)

#                     with st.expander("Collected Camera Refinement Config", expanded=False):
#                         st.json(camera_config)

#                     if "result" in locals():
#                         with st.expander("RunComfy Raw Camera Refinement Result", expanded=False):
#                             st.json(result)
