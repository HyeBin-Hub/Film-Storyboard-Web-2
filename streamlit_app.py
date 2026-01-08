# app.py
import streamlit as st
import backend

# =========================================================
# 0. RunComfy Key/Deployment 로드
# =========================================================
if "RUNCOMFY_API_KEY" in st.secrets:
    api_key = st.secrets["RUNCOMFY_API_KEY"]
    deployment_id = st.secrets["DEPLOYMENT_ID"]
else:
    api_key = st.sidebar.text_input("RunComfy API Key", type="password")
    deployment_id = st.sidebar.text_input("Deployment ID")
    if not api_key or not deployment_id:
        st.sidebar.warning("API Key와 Deployment ID를 입력해주세요.")
        st.stop()

# =========================================================
# 1. 페이지 설정 및 디자인 (절대 변경하지 않음)
# =========================================================
st.set_page_config(
    page_title="Neon Darkroom: Director's Suite",
    page_icon="🎬",
    layout="wide",
    initial_sidebar_state="collapsed"
)

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Rajdhani:wght@500;700&family=Roboto+Mono:wght@400;700&display=swap');

.stApp {
    background-color: #050505;
    background-image: radial-gradient(#151515 1px, transparent 1px);
    background-size: 40px 40px;
    color: #e0e0e0;
    font-family: 'Rajdhani', sans-serif;
}

.stTextInput>div>div, 
.stSelectbox>div>div, 
.stNumberInput>div>div, 
.stTextArea>div>div {
    background-color: #1a1a1a !important;
    border: 1px solid #333 !important;
    color: #FFD700 !important;
    border-radius: 4px;
    font-family: 'Roboto Mono', monospace;
}

.stTextInput>div>div:focus-within {
    border-color: #FFD700 !important;
    box-shadow: 0 0 5px rgba(255, 215, 0, 0.5);
}

.stButton>button {
    background: linear-gradient(90deg, #FFD700, #ffaa00) !important;
    color: #000 !important;
    border: none;
    font-weight: 800;
    font-size: 18px;
    padding: 12px 24px;
    text-transform: uppercase;
    letter-spacing: 1px;
    transition: all 0.3s cubic-bezier(0.25, 0.8, 0.25, 1);
    border-radius: 6px;
    width: 100%;
    white-space: pre-wrap;
    height: auto !important;
    min-height: 60px;
    line-height: 1.4 !important;
}

.stButton>button:hover {
    box-shadow: 0 0 20px rgba(255, 215, 0, 0.6);
    transform: translateY(-2px);
}

.stButton>button:active {
    transform: translateY(1px);
    box-shadow: 0 0 10px rgba(255, 215, 0, 0.4);
}

.stTabs [data-baseweb="tab-list"] {
    gap: 8px;
    background-color: transparent;
}
.stTabs [data-baseweb="tab"] {
    height: 50px;
    background-color: #111;
    border-radius: 8px 8px 0 0;
    border: 1px solid #333;
    color: #888;
    font-weight: bold;
    flex-grow: 1;
    text-align: center;
}
.stTabs [aria-selected="true"] {
    background-color: #222 !important;
    color: #FFD700 !important;
    border-bottom: 2px solid #FFD700 !important;
}

.streamlit-expanderHeader {
    background-color: #111 !important;
    color: #e0e0e0 !important;
    border-radius: 4px;
}
</style>
""", unsafe_allow_html=True)

# =========================================================
# 2. 세션 상태 초기화
# =========================================================
if "step" not in st.session_state:
    st.session_state.step = 1

if "num_characters" not in st.session_state:
    st.session_state.num_characters = 2
if "shots_per_character" not in st.session_state:
    st.session_state.shots_per_character = 2

if "current_char_idx" not in st.session_state:
    st.session_state.current_char_idx = 0

if "pm_options_list" not in st.session_state:
    st.session_state.pm_options_list = []

if "casting_groups" not in st.session_state:
    st.session_state.casting_groups = []      # List[List[str]]
if "selected_cast" not in st.session_state:
    st.session_state.selected_cast = []       # List[Optional[str]]

if "final_character_urls" not in st.session_state:
    st.session_state.final_character_urls = []

if "final_scene_url" not in st.session_state:
    st.session_state.final_scene_url = None


def _default_pm_options(idx: int):
    # 필요하면 idx별 기본값 커스터마이즈 가능
    if idx == 0:
        return {
            "Gender": "Man",
            "Nationality": "Korean",
            "age": 12,
            "Face Shape": "Oval",
            "Body Type": "Slim",
            "Eyes Color": "Brown",
            "Eyes Shape": "Monolid Eyes Shape",
            "Lips Color": "Berry Lips",
            "Lips Shape": "Thin Lips",
            "Hair Style": "Buzz",
            "Hair Color": "Black",
            "Hair Length": "Short",
        }
    if idx == 1:
        return {
            "Gender": "Woman",
            "Nationality": "Korean",
            "age": 12,
            "Face Shape": "Oval",
            "Body Type": "Slim",
            "Eyes Color": "Brown",
            "Eyes Shape": "Monolid Eyes Shape",
            "Lips Color": "Berry Lips",
            "Lips Shape": "Thin Lips",
            "Hair Style": "Long straight",
            "Hair Color": "Black",
            "Hair Length": "Long",
        }
    return {
        "Gender": "Man",
        "Nationality": "Korean",
        "age": 25,
        "Face Shape": "Oval",
        "Body Type": "Fit",
        "Eyes Color": "Brown",
        "Eyes Shape": "Round Eyes Shape",
        "Lips Color": "Red Lips",
        "Lips Shape": "Thin Lips",
        "Hair Style": "Short",
        "Hair Color": "Black",
        "Hair Length": "Short",
    }


def _ensure_lists(n: int):
    # pm_options_list
    if len(st.session_state.pm_options_list) < n:
        for i in range(len(st.session_state.pm_options_list), n):
            st.session_state.pm_options_list.append(_default_pm_options(i))
    elif len(st.session_state.pm_options_list) > n:
        st.session_state.pm_options_list = st.session_state.pm_options_list[:n]

    # casting_groups
    if len(st.session_state.casting_groups) < n:
        st.session_state.casting_groups.extend([[] for _ in range(n - len(st.session_state.casting_groups))])
    elif len(st.session_state.casting_groups) > n:
        st.session_state.casting_groups = st.session_state.casting_groups[:n]

    # selected_cast
    if len(st.session_state.selected_cast) < n:
        st.session_state.selected_cast.extend([None for _ in range(n - len(st.session_state.selected_cast))])
    elif len(st.session_state.selected_cast) > n:
        st.session_state.selected_cast = st.session_state.selected_cast[:n]


def _all_selected() -> bool:
    return all(u is not None for u in st.session_state.selected_cast)


# ----------------------------
# constants
# ----------------------------
DEFAULT_W = 896
DEFAULT_H = 1152
DEFAULT_BASE_PROMPT = "Grey background, white t-shirt, documentary photograph"

# ----------------------------
# UI
# ----------------------------
st.header("🎬 Cinematic Storyboard AI")

tab1, tab2, tab3, tab4 = st.tabs([
    "Step1 | 👤 CHARACTER PROFILE",
    "Step2 | 👗 APPLY OUTFIT",
    "Step3 | 🏞️ BACKGROUND",
    "Step4 | 📝 STORYBOARD",
])

# ----------------------------
# Step1
# ----------------------------
with tab1:
    if st.session_state.step != 1:
        st.success("✅ Step 1 Completed")
    else:
        col_left, col_right = st.columns([3, 1])

        with col_right:
            st.markdown("#### Advanced Setting")

            n_chars = st.slider("Number of Characters", 1, 5, st.session_state.num_characters)
            shots = st.slider("Shots per Character", 1, 4, st.session_state.shots_per_character)

            st.session_state.num_characters = int(n_chars)
            st.session_state.shots_per_character = int(shots)

            _ensure_lists(st.session_state.num_characters)
            st.session_state.current_char_idx = min(st.session_state.current_char_idx, st.session_state.num_characters - 1)

            seed_mode = st.radio("Seed mode", ["Random", "Fixed"], index=0)
            fixed_seed = st.number_input("Fixed seed", min_value=0, value=42, step=1) if seed_mode == "Fixed" else None

            use_custom_prompt = st.checkbox("Use custom base prompt", value=False)
            base_prompt = st.text_area("Base Prompt", DEFAULT_BASE_PROMPT, height=120) if use_custom_prompt else DEFAULT_BASE_PROMPT

            st.markdown("---")
            st.markdown("#### Character Setting")

            char_idx = st.session_state.current_char_idx
            pm_options = st.session_state.pm_options_list[char_idx]  # ✅ 캐릭터별 dict

            st.caption(f"Editing: Character {char_idx+1} / {st.session_state.num_characters}")

            # ---- 여기부터: 너가 준 UI 블록을 '캐릭터별 key'만 추가해서 그대로 사용 ----
            with st.expander("Portrait Setting"):
                with st.expander("Gender & Nationality"):
                    pm_options["Gender"] = st.selectbox(
                        "Gender", ["Man", "Woman"],
                        index=["Man","Woman"].index(pm_options.get("Gender","Man")),
                        key=f"gender_{char_idx}",
                    )
                    nat_list = ["Chinese","Japanese","Korean","South Korean","Indian","Saudi","British","French","German","Italian","Spanish","American","Canadian","Brazilian","Mexican","Argentine","Egyptian","South African","Nigerian","Kenyan","Moroccan","Australian","New Zealander","Fijian","Samoan","Tongan"]
                    cur_nat = pm_options.get("Nationality","Korean")
                    pm_options["Nationality"] = st.selectbox(
                        "Nationality", nat_list,
                        index=nat_list.index(cur_nat) if cur_nat in nat_list else nat_list.index("Korean"),
                        key=f"nat_{char_idx}",
                    )
                    pm_options["age"] = st.number_input(
                        "AGE", 10, 80, int(pm_options.get("age",25)),
                        key=f"age_{char_idx}",
                    )

                with st.expander("Face & Body Type"):
                    face_shapes = ["Oval","Round","Square","Heart","Diamond","Triangle","Inverted Triangle","Pear","Rectangle","Oblong","Long"]
                    cur_face = pm_options.get("Face Shape","Oval")
                    pm_options["Face Shape"] = st.selectbox(
                        "Face Shape", face_shapes,
                        index=face_shapes.index(cur_face) if cur_face in face_shapes else 0,
                        key=f"face_{char_idx}",
                    )
                    body_types = ["Chubby","Curvy","Fat","Fit","Hefty","Large","Lanky","Muscular","Obese","Overweight","Petite","Plump","Short","Skinny","Slight","Slim","Small","Stout","Stocky","Tall","Thick","Tiny","Underweight","Well-built"]
                    cur_body = pm_options.get("Body Type","Fit")
                    pm_options["Body Type"] = st.selectbox(
                        "Body Type", body_types,
                        index=body_types.index(cur_body) if cur_body in body_types else body_types.index("Fit"),
                        key=f"body_{char_idx}",
                    )

                with st.expander("Eyes Type"):
                    eye_colors = ["Albino","Amber","Blue","Brown","Green","Gray","Hazel","Heterochromia","Red","Violet"]
                    cur_ec = pm_options.get("Eyes Color","Brown")
                    pm_options["Eyes Color"] = st.selectbox(
                        "Eyes Color", eye_colors,
                        index=eye_colors.index(cur_ec) if cur_ec in eye_colors else eye_colors.index("Brown"),
                        key=f"eye_color_{char_idx}",
                    )
                    eye_shapes = ["Almond Eyes Shape","Asian Eyes Shape","Close-Set Eyes Shape","Deep Set Eyes Shape","Downturned Eyes Shape","Double Eyelid Eyes Shape","Hooded Eyes Shape","Monolid Eyes Shape","Oval Eyes Shape","Protruding Eyes Shape","Round Eyes Shape","Upturned Eyes Shape"]
                    cur_es = pm_options.get("Eyes Shape","Monolid Eyes Shape")
                    pm_options["Eyes Shape"] = st.selectbox(
                        "Eyes Shape", eye_shapes,
                        index=eye_shapes.index(cur_es) if cur_es in eye_shapes else 0,
                        key=f"eye_shape_{char_idx}",
                    )

                with st.expander("Lips Type"):
                    lips_colors = ["Berry Lips","Black Lips","Blue Lips","Brown Lips","Burgundy Lips","Coral Lips","Glossy Red Lips","Mauve Lips","Orange Lips","Peach Lips","Pink Lips","Plum Lips","Purple Lips","Red Lips","Yellow Lips"]
                    cur_lc = pm_options.get("Lips Color","Berry Lips")
                    pm_options["Lips Color"] = st.selectbox(
                        "Lips Color", lips_colors,
                        index=lips_colors.index(cur_lc) if cur_lc in lips_colors else 0,
                        key=f"lips_color_{char_idx}",
                    )
                    lips_shapes = ["Full Lips","Thin Lips","Plump Lips","Small Lips","Large Lips","Wide Lips","Round Lips","Heart-shaped Lips","Cupid's Bow Lips"]
                    cur_ls = pm_options.get("Lips Shape","Thin Lips")
                    pm_options["Lips Shape"] = st.selectbox(
                        "Lips Shape", lips_shapes,
                        index=lips_shapes.index(cur_ls) if cur_ls in lips_shapes else 1,
                        key=f"lips_shape_{char_idx}",
                    )

                with st.expander("Hair Style"):
                    hair_styles = ["Bald","Buzz","Crew","Pixie","Bob","Long bob","Long straight","Wavy","Curly","Afro","Faded afro","Braided","Box braids","Cornrows","Dreadlocks","Pigtails","Ponytail","High ponytail","Bangs","Curtain bangs","Side-swept bangs","Mohawk","Faux hawk","Undercut","Pompadour","Quiff","Top Knot","Bun","Updo"]
                    cur_hs = pm_options.get("Hair Style","Buzz")
                    pm_options["Hair Style"] = st.selectbox(
                        "Hair Style", hair_styles,
                        index=hair_styles.index(cur_hs) if cur_hs in hair_styles else 1,
                        key=f"hair_style_{char_idx}",
                    )
                    hair_colors = ["Black","Jet Black","Blonde","Platinum","Brown","Chestnut","Auburn","Red","Strawberry","Gray","Silver","White","Salt and pepper"]
                    cur_hc = pm_options.get("Hair Color","Black")
                    pm_options["Hair Color"] = st.selectbox(
                        "Hair Color", hair_colors,
                        index=hair_colors.index(cur_hc) if cur_hc in hair_colors else 0,
                        key=f"hair_color_{char_idx}",
                    )
                    hair_lengths = ["Short","Medium","Long"]
                    cur_hl = pm_options.get("Hair Length","Short")
                    pm_options["Hair Length"] = st.selectbox(
                        "Hair Length", hair_lengths,
                        index=hair_lengths.index(cur_hl) if cur_hl in hair_lengths else 0,
                        key=f"hair_len_{char_idx}",
                    )
            # ---- 여기까지 UI 블록 ----

            st.markdown("<br>", unsafe_allow_html=True)

            if st.button("🚀 CAST CURRENT CHARACTER", use_container_width=True):
                try:
                    with st.spinner(f"Casting Character {char_idx+1}... (Switch Mode: 1)"):
                        # Fixed seed면 캐릭터별로 다르게
                        seed = (fixed_seed + char_idx * 1000) if fixed_seed is not None else None

                        imgs = backend.generate_faces(
                            api_key=api_key,
                            deployment_id=deployment_id,
                            width=DEFAULT_W,
                            height=DEFAULT_H,
                            batch_size=st.session_state.shots_per_character,
                            pm_options=pm_options,
                            base_prompt=base_prompt,
                            seed=seed,
                        )

                    st.session_state.casting_groups[char_idx] = imgs
                    st.session_state.selected_cast[char_idx] = None  # 생성했으니 선택 초기화
                    st.rerun()
                except Exception as e:
                    st.error(str(e))

            c1, c2 = st.columns(2)
            with c1:
                if st.button("⬅️ PREV CHARACTER", use_container_width=True):
                    st.session_state.current_char_idx = max(0, st.session_state.current_char_idx - 1)
                    st.rerun()
            with c2:
                if st.button("➡️ NEXT CHARACTER", use_container_width=True):
                    st.session_state.current_char_idx = min(
                        st.session_state.num_characters - 1,
                        st.session_state.current_char_idx + 1,
                    )
                    st.rerun()

        # ---------------- LEFT: results + selection ----------------
        with col_left:
            st.markdown("#### Casting Result")

            for ci in range(st.session_state.num_characters):
                st.markdown(f"##### Character {ci+1}")

                group = st.session_state.casting_groups[ci]
                if not group:
                    st.info("No footage available for this character.")
                    continue

                cols = st.columns(2)
                for si, img_url in enumerate(group):
                    with cols[si % 2]:
                        st.image(img_url, use_container_width=True)

                        is_selected = (st.session_state.selected_cast[ci] == img_url)
                        label = "✅ SELECTED" if is_selected else f"✅ SELECT (CHAR {ci+1} / #{si+1})"
                        if st.button(label, key=f"sel_{ci}_{si}"):
                            st.session_state.selected_cast[ci] = img_url
                            st.rerun()

            st.markdown("---")
            if _all_selected():
                if st.button("➡️ PROCEED TO STEP2", use_container_width=True):
                    st.session_state.step = 2
                    st.rerun()
            else:
                st.info("각 Character마다 1장씩 선택해주세요.")

# ----------------------------
# Step2 (Apply Outfit) - 모든 캐릭터 처리
# ----------------------------
with tab2:
    if st.session_state.step != 2:
        st.info("Step2는 Step1 완료 후 진행됩니다.")
    else:
        st.markdown("### 2. Wardrobe & Styling")

        selected = st.session_state.selected_cast
        n = st.session_state.num_characters

        col_face, col_outfit, col_result = st.columns([1, 1, 1])

        with col_face:
            st.markdown("#### Reference Actors")
            for i, u in enumerate(selected):
                if u:
                    st.image(u, use_container_width=True, caption=f"Character {i+1}")

        with col_outfit:
            outfit_prompt = st.text_area(
                "Describe the outfit",
                "white background, white t-shirt, black pants, yellow sneakers",
                height=160,
            )
            if st.button("👗 APPLY OUTFIT (ALL)", use_container_width=True):
                try:
                    with st.spinner("Fitting room... (Switch Mode: 2)"):
                        final_urls = [None] * n
                        for i in range(n):
                            if not selected[i]:
                                continue
                            res = backend.generate_full_body(
                                face_url=selected[i],
                                outfit_prompt=outfit_prompt,
                                api_key=api_key,
                                deployment_id=deployment_id,
                            )
                            if res:
                                final_urls[i] = res[0]

                    st.session_state.final_character_urls = final_urls
                    st.rerun()
                except Exception as e:
                    st.error(str(e))

        with col_result:
            st.markdown("#### Fitted Results")
            if st.session_state.final_character_urls:
                for i, u in enumerate(st.session_state.final_character_urls):
                    if u:
                        st.image(u, use_container_width=True, caption=f"Final Character {i+1}")

                if all(u is not None for u in st.session_state.final_character_urls):
                    if st.button("✨ CONFIRM & GO TO SET", use_container_width=True):
                        st.session_state.step = 3
                        st.rerun()
            else:
                st.info("의상 프롬프트 입력 후 실행하세요.")

# ----------------------------
# Step3 (Scene) - char1/char2 + background
# ----------------------------
with tab3:
    if st.session_state.step != 3:
        st.info("Step3는 Step2 완료 후 진행됩니다.")
    else:
        st.markdown("### 3. Final Scene Composition")

        finals = st.session_state.final_character_urls or []
        char1_url = finals[0] if len(finals) > 0 else None
        char2_url = finals[1] if len(finals) > 1 else None

        col_assets, col_prompt, col_final = st.columns([1, 1, 2])

        with col_assets:
            st.markdown("#### Assets")
            if char1_url:
                st.image(char1_url, width=160, caption="Character 1")
            if char2_url:
                st.image(char2_url, width=160, caption="Character 2")

            bg_url = st.text_input(
                "Background Image URL",
                "https://images.unsplash.com/photo-1579546929518-9e396f3cc809?auto=format&fit=crop&w=1000&q=80",
            )
            if bg_url:
                st.image(bg_url, width=160, caption="Background")

        with col_prompt:
            story_prompt = st.text_area(
                "Scene Description",
                "소년과 소녀가 카메라 오른쪽 방향으로 나란히 걸어가고 있습니다.",
                height=140,
            )
            if st.button("🎬 ACTION! (Generate Scene)", use_container_width=True):
                try:
                    if not char1_url:
                        st.error("Character 1이 없습니다. Step2 전신 생성이 필요합니다.")
                    else:
                        with st.spinner("Shooting the scene... (Switch Mode: 3)"):
                            imgs = backend.generate_scene(
                                char1_url=char1_url,
                                char2_url=char2_url,
                                bg_url=bg_url,
                                story_prompt=story_prompt,
                                api_key=api_key,
                                deployment_id=deployment_id,
                            )
                        st.session_state.final_scene_url = imgs[0] if imgs else None
                        st.rerun()
                except Exception as e:
                    st.error(str(e))

        with col_final:
            st.markdown("#### 🏁 Final Cut")
            if st.session_state.final_scene_url:
                st.image(st.session_state.final_scene_url, use_container_width=True)

with tab4:
    st.info("Step4는 추후 Shot Script/Shotlist 파서를 연결하세요.")
