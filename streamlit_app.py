import streamlit as st
import backend

# 1. secrets.toml 파일에서 먼저 찾아봄
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
# 1. 페이지 설정 및 디자인 (유지)
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

# 멀티 캐릭터용 상태
if "num_characters" not in st.session_state:
    st.session_state.num_characters = 2
if "shots_per_character" not in st.session_state:
    st.session_state.shots_per_character = 2

if "pm_options_list" not in st.session_state:
    st.session_state.pm_options_list = []   # List[Dict]
if "casting_groups" not in st.session_state:
    st.session_state.casting_groups = []    # List[List[str]]
if "selected_cast" not in st.session_state:
    st.session_state.selected_cast = []     # List[Optional[str]]
if "final_character_urls" not in st.session_state:
    st.session_state.final_character_urls = []  # Step2에서 사용

# 단일 호환(기존 코드 깨짐 방지)
if "generated_faces" not in st.session_state:
    st.session_state.generated_faces = []
if "selected_face_url" not in st.session_state:
    st.session_state.selected_face_url = None
if "final_character_url" not in st.session_state:
    st.session_state.final_character_url = None
if "final_scene_url" not in st.session_state:
    st.session_state.final_scene_url = None

# =========================================================
# 3. 상수
# =========================================================
DEFAULT_W = 896
DEFAULT_H = 1152
DEFAULT_BASE_PROMPT = "Grey background, white t-shirt, documentary photograph"
DEFAULT_TEXT = DEFAULT_BASE_PROMPT


def _default_pm_options(idx: int):
    # 기존 프리셋 유지
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


def _ensure_len(lst, n, fill):
    if len(lst) < n:
        lst.extend([fill] * (n - len(lst)))
    elif len(lst) > n:
        del lst[n:]
    return lst


def _ensure_character_state(n: int):
    # pm_options_list
    if not isinstance(st.session_state.pm_options_list, list):
        st.session_state.pm_options_list = []
    if len(st.session_state.pm_options_list) != n:
        new_list = []
        for i in range(n):
            if i < len(st.session_state.pm_options_list) and isinstance(st.session_state.pm_options_list[i], dict):
                new_list.append(st.session_state.pm_options_list[i])
            else:
                new_list.append(_default_pm_options(i))
        st.session_state.pm_options_list = new_list

    # selected_cast / final_character_urls 길이 보정
    st.session_state.selected_cast = _ensure_len(st.session_state.selected_cast, n, None)
    st.session_state.final_character_urls = _ensure_len(st.session_state.final_character_urls, n, None)


def _all_selected(selected_list):
    return all(u is not None for u in selected_list)


# =========================================================
# 4. 메인 화면 (탭 구성) (유지)
# =========================================================
st.header("🎬 Cinematic Storyboard AI")

tab1, tab2, tab3, tab4 = st.tabs([
    "Step1 | 👤 CHARACTER PROFILE",
    "Step2 | 👗 APPLY OUTFIT",
    "Step3 | 🏞️ BACKGROUND",
    "Step4 | 📝 STORYBOARD"
])

# ---------------------------------------------------------
# [TAB 1] 얼굴 생성 (캐릭터별 설정 드롭다운 방식)
# ---------------------------------------------------------
with tab1:
    if st.session_state.step == 1:
        st.markdown("### 1. Define Your Actor Profile")

        col_left, col_right = st.columns([3, 1])

        with col_right:
            st.markdown("#### Casting Config")

            # ---- Advanced Setting 먼저: n_chars/shots 결정 후 state 맞춤 ----
            st.markdown("#### Advanced Setting")
            with st.expander("Image Count"):
                seed_mode = st.radio("Seed mode", ["Random", "Fixed"], index=0)
                fixed_seed = st.number_input("Fixed seed", min_value=0, value=42, step=1) if seed_mode == "Fixed" else None

                n_chars = st.slider("Number of Characters", 1, 5, int(st.session_state.num_characters))
                shots = st.slider("Shots per Character", 1, 4, int(st.session_state.shots_per_character))

                st.session_state.num_characters = int(n_chars)
                st.session_state.shots_per_character = int(shots)

                _ensure_character_state(st.session_state.num_characters)

            # ---- 어떤 캐릭터 설정을 편집할지 선택 ----
            edit_idx = st.selectbox(
                "Editing Character",
                options=list(range(st.session_state.num_characters)),
                format_func=lambda i: f"Character {i+1}",
            )
            # 현재 편집중인 캐릭터 dict 참조
            pm_options = st.session_state.pm_options_list[edit_idx]

            # ---- Portrait Setting (기존 UI 유지, 단 key/저장만 캐릭터별) ----
            with st.expander("Portrait Setting"):
                with st.expander("Gender & Nationality"):
                    pm_options["Gender"] = st.selectbox(
                        "Gender",
                        ["Man", "Woman"],
                        index=0 if pm_options.get("Gender", "Man") == "Man" else 1,
                        key=f"c{edit_idx}_Gender",
                    )
                    nations = ["Chinese","Japanese","Korean","South Korean","Indian","Saudi","British","French","German","Italian","Spanish","American","Canadian","Brazilian","Mexican","Argentine","Egyptian","South African","Nigerian","Kenyan","Moroccan","Australian","New Zealander","Fijian","Samoan","Tongan"]
                    cur_nat = pm_options.get("Nationality", "Korean")
                    pm_options["Nationality"] = st.selectbox(
                        "Nationality",
                        nations,
                        index=nations.index(cur_nat) if cur_nat in nations else nations.index("Korean"),
                        key=f"c{edit_idx}_Nationality",
                    )
                    pm_options["age"] = st.number_input(
                        "AGE", 10, 80, int(pm_options.get("age", 25)),
                        key=f"c{edit_idx}_age",
                    )

                with st.expander("Face & Body Type"):
                    face_shapes = ["Oval","Round","Square","Heart","Diamond","Triangle","Inverted Triangle","Pear","Rectangle","Oblong","Long"]
                    cur_face = pm_options.get("Face Shape", "Oval")
                    pm_options["Face Shape"] = st.selectbox(
                        "Face Shape",
                        face_shapes,
                        index=face_shapes.index(cur_face) if cur_face in face_shapes else 0,
                        key=f"c{edit_idx}_FaceShape",
                    )
                    body_types = ["Chubby","Curvy","Fat","Fit","Hefty","Large","Lanky","Muscular","Obese","Overweight","Petite","Plump","Short","Skinny","Slight","Slim","Small","Stout","Stocky","Tall","Thick","Tiny","Underweight","Well-built"]
                    cur_body = pm_options.get("Body Type", "Fit")
                    pm_options["Body Type"] = st.selectbox(
                        "Body Type",
                        body_types,
                        index=body_types.index(cur_body) if cur_body in body_types else body_types.index("Fit"),
                        key=f"c{edit_idx}_BodyType",
                    )

                with st.expander("Eyes Type"):
                    eye_colors = ["Albino","Amber","Blue","Brown","Green","Gray","Hazel","Heterochromia","Red","Violet"]
                    cur_ec = pm_options.get("Eyes Color", "Brown")
                    pm_options["Eyes Color"] = st.selectbox(
                        "Eyes Color",
                        eye_colors,
                        index=eye_colors.index(cur_ec) if cur_ec in eye_colors else eye_colors.index("Brown"),
                        key=f"c{edit_idx}_EyesColor",
                    )
                    eye_shapes = ["Almond Eyes Shape","Asian Eyes Shape","Close-Set Eyes Shape","Deep Set Eyes Shape","Downturned Eyes Shape","Double Eyelid Eyes Shape","Hooded Eyes Shape","Monolid Eyes Shape","Oval Eyes Shape","Protruding Eyes Shape","Round Eyes Shape","Upturned Eyes Shape"]
                    cur_es = pm_options.get("Eyes Shape", "Round Eyes Shape")
                    pm_options["Eyes Shape"] = st.selectbox(
                        "Eyes Shape",
                        eye_shapes,
                        index=eye_shapes.index(cur_es) if cur_es in eye_shapes else eye_shapes.index("Round Eyes Shape"),
                        key=f"c{edit_idx}_EyesShape",
                    )

                with st.expander("Lips Type"):
                    lip_colors = ["Berry Lips","Black Lips","Blue Lips","Brown Lips","Burgundy Lips","Coral Lips","Glossy Red Lips","Mauve Lips","Orange Lips","Peach Lips","Pink Lips","Plum Lips","Purple Lips","Red Lips","Yellow Lips"]
                    cur_lc = pm_options.get("Lips Color", "Red Lips")
                    pm_options["Lips Color"] = st.selectbox(
                        "Lips Color",
                        lip_colors,
                        index=lip_colors.index(cur_lc) if cur_lc in lip_colors else lip_colors.index("Red Lips"),
                        key=f"c{edit_idx}_LipsColor",
                    )
                    lip_shapes = ["Full Lips","Thin Lips","Plump Lips","Small Lips","Large Lips","Wide Lips","Round Lips","Heart-shaped Lips","Cupid's Bow Lips"]
                    cur_ls = pm_options.get("Lips Shape", "Thin Lips")
                    pm_options["Lips Shape"] = st.selectbox(
                        "Lips Shape",
                        lip_shapes,
                        index=lip_shapes.index(cur_ls) if cur_ls in lip_shapes else lip_shapes.index("Thin Lips"),
                        key=f"c{edit_idx}_LipsShape",
                    )

                with st.expander("Hair Style"):
                    hair_styles = ["Bald","Buzz","Crew","Pixie","Bob","Long bob","Long straight","Wavy","Curly","Afro","Faded afro","Braided","Box braids","Cornrows","Dreadlocks","Pigtails","Ponytail","High ponytail","Bangs","Curtain bangs","Side-swept bangs","Mohawk","Faux hawk","Undercut","Pompadour","Quiff","Top Knot","Bun","Updo"]
                    cur_hs = pm_options.get("Hair Style", "Short")
                    pm_options["Hair Style"] = st.selectbox(
                        "Hair Style",
                        hair_styles,
                        index=hair_styles.index(cur_hs) if cur_hs in hair_styles else hair_styles.index("Buzz"),
                        key=f"c{edit_idx}_HairStyle",
                    )
                    hair_colors = ["Black","Jet Black","Blonde","Platinum","Brown","Chestnut","Auburn","Red","Strawberry","Gray","Silver","White","Salt and pepper"]
                    cur_hc = pm_options.get("Hair Color", "Black")
                    pm_options["Hair Color"] = st.selectbox(
                        "Hair Color",
                        hair_colors,
                        index=hair_colors.index(cur_hc) if cur_hc in hair_colors else hair_colors.index("Black"),
                        key=f"c{edit_idx}_HairColor",
                    )
                    hair_lengths = ["Short","Medium","Long"]
                    cur_hl = pm_options.get("Hair Length", "Short")
                    pm_options["Hair Length"] = st.selectbox(
                        "Hair Length",
                        hair_lengths,
                        index=hair_lengths.index(cur_hl) if cur_hl in hair_lengths else hair_lengths.index("Short"),
                        key=f"c{edit_idx}_HairLength",
                    )

            # 캐릭터 dict 저장(명시적으로)
            st.session_state.pm_options_list[edit_idx] = pm_options

            # base prompt
            use_custom_prompt = st.checkbox("Use custom base prompt", value=False)
            base_prompt = st.text_area("Base Prompt", DEFAULT_TEXT, height=120) if use_custom_prompt else None

            st.markdown("<br>", unsafe_allow_html=True)
            if st.button("🚀 CASTING START \n(Generate Faces)", use_container_width=True):
                try:
                    with st.spinner("Casting in progress... (Switch Mode: 1)"):
                        n_chars = int(st.session_state.num_characters)
                        shots = int(st.session_state.shots_per_character)

                        casting_groups = []
                        for char_idx in range(n_chars):
                            pm = st.session_state.pm_options_list[char_idx]

                            group = []
                            for shot_idx in range(shots):
                                # Fixed seed라면 캐릭터/샷마다 다르게
                                this_seed = (fixed_seed + char_idx * 1000 + shot_idx) if fixed_seed is not None else None

                                res = backend.generate_faces(
                                    api_key=api_key,
                                    deployment_id=deployment_id,
                                    width=DEFAULT_W,
                                    height=DEFAULT_H,
                                    batch_size=1,          # ✅ B안: 1장씩 반복 호출
                                    pm_options=pm,         # ✅ 캐릭터별 옵션
                                    base_prompt=base_prompt,
                                    seed=this_seed,
                                )
                                if res:
                                    group.append(res[0])
                            casting_groups.append(group)

                        st.session_state.casting_groups = casting_groups
                        st.session_state.selected_cast = [None] * n_chars
                        st.rerun()

                except Exception as e:
                    st.error(str(e))

        # ---------------- LEFT: 결과 표시/선택 ----------------
        with col_left:
            st.markdown("#### Casting Result")

            if st.session_state.casting_groups:
                n_chars = st.session_state.num_characters

                for char_idx in range(n_chars):
                    st.markdown(f"##### Character {char_idx+1}")

                    group = st.session_state.casting_groups[char_idx] if char_idx < len(st.session_state.casting_groups) else []
                    if not group:
                        st.info("No footage available for this character.")
                        continue

                    cols = st.columns(2)
                    for shot_idx, img_url in enumerate(group):
                        with cols[shot_idx % 2]:
                            is_selected = (st.session_state.selected_cast[char_idx] == img_url)
                            st.image(img_url, use_container_width=True)

                            btn_label = "✅ Selected" if is_selected else f"✅ Select (Char {char_idx+1} / Shot {shot_idx+1})"
                            if st.button(btn_label, key=f"sel_char{char_idx}_shot{shot_idx}"):
                                st.session_state.selected_cast[char_idx] = img_url
                                st.rerun()

                st.markdown("---")
                if _all_selected(st.session_state.selected_cast):
                    if st.button("➡️ Proceed to Step2 (Apply Outfit)", use_container_width=True):
                        st.session_state.selected_face_url = st.session_state.selected_cast[0]
                        st.session_state.step = 2
                        st.rerun()
                else:
                    st.info("각 Character마다 1장씩 선택해주세요.")
            else:
                st.info("오른쪽에서 설정 후 'CASTING START'를 눌러주세요.")

# ---------------------------------------------------------
# 아래 Step2~4는 네 기존 코드 그대로 두되,
# Step2에서 selected_cast / final_character_urls를 쓰는 멀티 로직을 유지하면 됨.
# ---------------------------------------------------------
# ---------------------------------------------------------
# [TAB 2] 전신 생성 (멀티: 선택된 캐릭터들 모두 처리)
# ---------------------------------------------------------
with tab2:
    if st.session_state.step == 2:
        st.markdown("### 2. Wardrobe & Styling")

        # 멀티 전신 생성은 “선택된 얼굴들(selected_cast)”을 기준으로 돌린다
        selected_cast = st.session_state.selected_cast
        n_chars = st.session_state.num_characters

        col_face, col_outfit, col_result = st.columns([1, 1, 1])

        with col_face:
            st.markdown("#### Reference Actors")
            if selected_cast:
                for i, u in enumerate(selected_cast):
                    if u:
                        st.image(u, use_container_width=True, caption=f"Character {i+1}")
            else:
                st.warning("Step 1에서 캐릭터 선택이 필요합니다.")

        with col_outfit:
            st.markdown("#### Outfit Description")
            outfit_prompt = st.text_area(
                "Describe the outfit",
                "white background, white t-shirt, black pants, yellow sneakers",
                height=160
            )

            st.markdown("<br>", unsafe_allow_html=True)
            if st.button("👗 APPLY OUTFIT (ALL CHARACTERS)", use_container_width=True):
                try:
                    with st.spinner("Fitting room... (Switch Mode: 2)"):
                        final_urls = [None] * n_chars
                        for i in range(n_chars):
                            face_url = selected_cast[i]
                            if not face_url:
                                continue
                            res = backend.generate_full_body(
                                face_url=face_url,
                                outfit_prompt=outfit_prompt,
                                api_key=api_key,
                                deployment_id=deployment_id,
                            )
                            if res:
                                final_urls[i] = res[0]

                        st.session_state.final_character_urls = final_urls

                        # 단일 호환(기존 Step3가 final_character_url만 쓰는 경우 대비)
                        st.session_state.final_character_url = final_urls[0] if final_urls and final_urls[0] else None

                        st.rerun()
                except Exception as e:
                    st.error(str(e))

        with col_result:
            st.markdown("#### Fitted Results")
            if st.session_state.final_character_urls and any(st.session_state.final_character_urls):
                for i, u in enumerate(st.session_state.final_character_urls):
                    if u:
                        st.image(u, use_container_width=True, caption=f"Final Character {i+1}")

                if st.button("✨ CONFIRM & GO TO SET", use_container_width=True):
                    st.session_state.step = 3
                    st.rerun()
            else:
                st.info("의상 프롬프트를 입력하고 버튼을 누르세요.")
    elif st.session_state.step > 2:
        st.success("✅ Step 2 Completed")
        if st.session_state.final_character_urls:
            cols = st.columns(min(4, len(st.session_state.final_character_urls)))
            for i, u in enumerate(st.session_state.final_character_urls):
                with cols[i % len(cols)]:
                    if u:
                        st.image(u, use_container_width=True, caption=f"Final {i+1}")
    else:
        st.warning("Step 1을 먼저 완료해주세요.")

# ---------------------------------------------------------
# [TAB 3] 최종 씬 생성 (멀티: 캐릭터 1,2 사용 / 없으면 복제)
# ---------------------------------------------------------
with tab3:
    if st.session_state.step == 3:
        st.markdown("### 3. Final Scene Composition")

        col_assets, col_prompt, col_final = st.columns([1, 1, 2])

        with col_assets:
            st.markdown("#### Assets")

            finals = st.session_state.final_character_urls or []
            char1_url = finals[0] if len(finals) > 0 else None
            char2_url = finals[1] if len(finals) > 1 else None

            if char1_url:
                st.image(char1_url, width=160, caption="Character 1 (URL ref)")
            if char2_url:
                st.image(char2_url, width=160, caption="Character 2 (URL ref)")

            bg_url = st.text_input(
                "Background Image URL",
                "https://images.unsplash.com/photo-1579546929518-9e396f3cc809?auto=format&fit=crop&w=1000&q=80",
                help="배경으로 쓸 이미지 URL"
            )
            if bg_url:
                st.image(bg_url, width=160, caption="Background (URL ref)")

        with col_prompt:
            st.markdown("#### Director's Note")
            story_prompt = st.text_area(
                "Scene Description",
                "소년과 소녀가 카메라 오른쪽 방향으로 나란히 걸어가고 있습니다.",
                height=140
            )

            st.info("💡 Tip: Character 2가 없으면 Character 1이 복제되어 사용됩니다.")

            st.markdown("<br>", unsafe_allow_html=True)
            if st.button("🎬 ACTION! (Generate Scene)", use_container_width=True):
                try:
                    if not char1_url:
                        st.error("Character 1이 없습니다. Step2에서 전신 생성이 완료되어야 합니다.")
                    else:
                        with st.spinner("Shooting the scene... (Switch Mode: 3)"):
                            final_imgs = backend.generate_scene(
                                char1_url=char1_url,
                                char2_url=char2_url,  # None이면 backend에서 char1로 대체
                                bg_url=bg_url,
                                story_prompt=story_prompt,
                                api_key=api_key,
                                deployment_id=deployment_id,
                            )
                        if final_imgs:
                            st.session_state.final_scene_url = final_imgs[0]
                            st.rerun()
                        else:
                            st.warning("최종 씬 이미지 URL을 받지 못했습니다.")
                except Exception as e:
                    st.error(str(e))

        with col_final:
            st.markdown("#### 🏁 Final Cut")
            if st.session_state.final_scene_url:
                st.image(st.session_state.final_scene_url, use_container_width=True)
                st.success("Workflow Complete!")
            else:
                st.info("배경과 지문을 입력하고 큐 사인을 주세요.")
    else:
        st.warning("이전 단계를 먼저 완료해주세요.")

# ---------------------------------------------------------
# [TAB 4] (미구현)
# ---------------------------------------------------------
with tab4:
    st.info("Step4는 추후 Shot Script/Shotlist 파서를 연결하세요.")
