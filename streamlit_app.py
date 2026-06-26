# app.py
import streamlit as st
import backend

# ========================================================================
# 0. 페이지 설정 (반드시 첫 Streamlit 호출이어야 함)
# ========================================================================
st.set_page_config(
    page_title="Neon Darkroom: Director's Suite",
    page_icon="🎬",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# ========================================================================
# 1. API Key / Deployment ID 로드
# ========================================================================
if "RUNCOMFY_API_KEY" in st.secrets:
    api_key = st.secrets["RUNCOMFY_API_KEY"]
    deployment_id = st.secrets["DEPLOYMENT_ID"]
else:
    api_key = st.sidebar.text_input("RunComfy API Key", type="password")
    deployment_id = st.sidebar.text_input("Deployment ID")
    if not api_key or not deployment_id:
        st.sidebar.warning("API Key와 Deployment ID를 입력해주세요.")
        st.stop()

# ========================================================================
# 2. 디자인
# ========================================================================        
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

# ========================================================================
# 3. 세션 상태 초기화 (앱 상태 유지) — 다중 캐릭터 정책 기준
# ========================================================================

# 현재 단계 (1~4)
if "step" not in st.session_state:
    st.session_state.step = 1

# 캐릭터별 얼굴 후보 이미지 URL 리스트
# List[List[str]]
if "generated_faces_by_char" not in st.session_state:
    st.session_state.generated_faces_by_char = []

# 캐릭터별 선택된 얼굴 URL
# List[Optional[str]]
if "selected_face_urls" not in st.session_state:
    st.session_state.selected_face_urls = []

# 캐릭터별 전신 결과 URL
# List[Optional[str]]
if "final_character_urls" not in st.session_state:
    st.session_state.final_character_urls = []

# 캐릭터별 의상 프롬프트 (Step2 유지용)
# List[str]
if "outfit_prompts" not in st.session_state:
    st.session_state.outfit_prompts = []

# 최종 씬 결과 이미지 URL (Step3)
if "final_scene_url" not in st.session_state:
    st.session_state.final_scene_url = None

# # 캐릭터 옵션 저장소 (선택)
# if "pm_options" not in st.session_state:
#     st.session_state.pm_options = {}

# Step1: 현재 편집/생성 중인 캐릭터 인덱스 (0-based)
if "current_char_idx" not in st.session_state:
    st.session_state.current_char_idx = 0

# 캐릭터별 Portrait 옵션 저장소
# List[Dict[str, Any]]
if "pm_options_by_char" not in st.session_state:
    st.session_state.pm_options_by_char = []



# ========================================================================
#                             4. 상수 (기본값) 
# ========================================================================
DEFAULT_W = 896
DEFAULT_H = 1152


# ========================================================================
#                           5. 메인 화면 (탭 구성)
# ========================================================================
st.header("🎬 Cinematic Storyboard AI")

tab1, tab2, tab3, tab4 = st.tabs([
    "Step1 | 👤 CHARACTER PROFILE",
    "Step2 | 👗 APPLY OUTFIT",
    "Step3 | 🏞️ BACKGROUND",
    "Step4 | 📝 STORYBOARD SCRIPT"
])

# ---------------------------------------------------------
# [TAB 1] Step1: 얼굴 생성
# ---------------------------------------------------------
# ---------------------------------------------------------
# [TAB 1] Step1: 얼굴 생성 (순차 캐릭터 캐스팅)
# ---------------------------------------------------------
with tab1:
    if st.session_state.step != 1:
        st.success("✅ Step 1 Completed")

        # =====================================================
        # Storyboard CSV Upload Test
        # =====================================================
        st.markdown("### 📄 Storyboard CSV Upload Test")

        uploaded_csv = st.file_uploader(
            "Upload storyboard CSV",
            type=["csv"],
            key="storyboard_csv_uploader"
        )

        if uploaded_csv is not None:
            st.session_state.uploaded_csv_name = uploaded_csv.name
            st.session_state.uploaded_csv_bytes = uploaded_csv.getvalue()

            st.success(f"CSV uploaded: {uploaded_csv.name}")
            st.caption(f"File size: {len(st.session_state.uploaded_csv_bytes)} bytes")

            # CSV 내용 미리보기
            try:
                csv_text = st.session_state.uploaded_csv_bytes.decode("utf-8-sig")
            except UnicodeDecodeError:
                try:
                    csv_text = st.session_state.uploaded_csv_bytes.decode("cp949")
                except UnicodeDecodeError:
                    csv_text = ""

            if csv_text:
                st.text_area(
                    "CSV Preview",
                    csv_text[:3000],
                    height=220,
                    key="storyboard_csv_preview"
                )
            else:
                st.error("CSV 파일을 utf-8-sig 또는 cp949로 읽지 못했습니다.")

            st.markdown("---")
            # =====================================================

    if st.session_state.step == 1:
        st.markdown("### 1. Define Your Actor Profile")

        col_left, col_right = st.columns([3, 1])

        # ============================
        # Right: Advanced + Navigator + Portrait Setting
        # ============================
        with col_right:
            st.markdown("#### Advanced Setting")

            with st.expander("Advanced Setting", expanded=True):
                num_characters = st.slider("Number of Characters", 1, 2, 2, key="num_characters")
                shots_per_character = st.slider("Shots per Character", 1, 4, 2, key="shots_per_character")
                batch_size = shots_per_character

                seed_mode = st.radio("Seed mode", ["Random", "Fixed"], index=0, key="seed_mode")
                if seed_mode == "Fixed":
                    fixed_seed = st.number_input(
                        "Fixed Seed",
                        min_value=0, max_value=2**31-1,
                        value=12345, step=1,
                        key="fixed_seed"
                    )

                st.markdown("<hr style='margin:6px 0; border:10; border-top:1px solid #333;'>", unsafe_allow_html=True)

                DEFAULT_BASE_PROMPT = "Grey background, white t-shirt, documentary photograph"
                use_custom_base_prompt = st.checkbox("Use custom base prompt", value=False)

                if use_custom_base_prompt:
                    base_prompt = st.text_area("Base Portrait Prompt", DEFAULT_BASE_PROMPT, height=140)
                else:
                    base_prompt = DEFAULT_BASE_PROMPT
                    st.caption("Using default base prompt.")

            # ---- 길이 맞추기 (캐릭터 수 변경 대응) ----
            # faces
            while len(st.session_state.generated_faces_by_char) < num_characters:
                st.session_state.generated_faces_by_char.append([])
            st.session_state.generated_faces_by_char = st.session_state.generated_faces_by_char[:num_characters]

            # selected
            while len(st.session_state.selected_face_urls) < num_characters:
                st.session_state.selected_face_urls.append(None)
            st.session_state.selected_face_urls = st.session_state.selected_face_urls[:num_characters]

            # pm options
            while len(st.session_state.pm_options_by_char) < num_characters:
                st.session_state.pm_options_by_char.append({})
            st.session_state.pm_options_by_char = st.session_state.pm_options_by_char[:num_characters]

            # current index clamp
            if st.session_state.current_char_idx >= num_characters:
                st.session_state.current_char_idx = num_characters - 1

            cur = st.session_state.current_char_idx  # 0-based
            pm_options = st.session_state.pm_options_by_char[cur]

            # ============================
            # Portrait Setting (현재 캐릭터만 편집)
            # ============================
            st.markdown("### Portrait Setting")

            with st.expander("Portrait Setting", expanded=True):
                with st.expander("Gender & Nationality"):
                    pm_options["Gender"] = st.selectbox(
                        "Gender", ["Man", "Woman"],
                        index=["Man", "Woman"].index(pm_options.get("Gender", "Man")),
                        key=f"gender_{cur}",
                    )
                    nat_list = ["Chinese","Japanese","Korean","South Korean","Indian","Saudi","British","French","German","Italian","Spanish","American","Canadian","Brazilian","Mexican","Argentine","Egyptian","South African","Nigerian","Kenyan","Moroccan","Australian","New Zealander","Fijian","Samoan","Tongan"]
                    cur_nat = pm_options.get("Nationality", "Korean")
                    pm_options["Nationality"] = st.selectbox(
                        "Nationality", nat_list,
                        index=nat_list.index(cur_nat) if cur_nat in nat_list else nat_list.index("Korean"),
                        key=f"nat_{cur}",
                    )
                    pm_options["age"] = st.number_input(
                        "AGE", 10, 80, int(pm_options.get("age", 25)),
                        key=f"age_{cur}",
                    )

                with st.expander("Face & Body Type"):
                    face_shapes = ["Oval","Round","Square","Heart","Diamond","Triangle","Inverted Triangle","Pear","Rectangle","Oblong","Long"]
                    cur_face = pm_options.get("Face Shape", "Oval")
                    pm_options["Face Shape"] = st.selectbox(
                        "Face Shape", face_shapes,
                        index=face_shapes.index(cur_face) if cur_face in face_shapes else 0,
                        key=f"face_{cur}",
                    )
                    body_types = ["Chubby","Curvy","Fat","Fit","Hefty","Large","Lanky","Muscular","Obese","Overweight","Petite","Plump","Short","Skinny","Slight","Slim","Small","Stout","Stocky","Tall","Thick","Tiny","Underweight","Well-built"]
                    cur_body = pm_options.get("Body Type", "Fit")
                    pm_options["Body Type"] = st.selectbox(
                        "Body Type", body_types,
                        index=body_types.index(cur_body) if cur_body in body_types else body_types.index("Fit"),
                        key=f"body_{cur}",
                    )

                with st.expander("Eyes Type"):
                    eye_colors = ["Albino","Amber","Blue","Brown","Green","Gray","Hazel","Heterochromia","Red","Violet"]
                    cur_ec = pm_options.get("Eyes Color", "Brown")
                    pm_options["Eyes Color"] = st.selectbox(
                        "Eyes Color", eye_colors,
                        index=eye_colors.index(cur_ec) if cur_ec in eye_colors else eye_colors.index("Brown"),
                        key=f"eye_color_{cur}",
                    )
                    eye_shapes = ["Almond Eyes Shape","Asian Eyes Shape","Close-Set Eyes Shape","Deep Set Eyes Shape","Downturned Eyes Shape","Double Eyelid Eyes Shape","Hooded Eyes Shape","Monolid Eyes Shape","Oval Eyes Shape","Protruding Eyes Shape","Round Eyes Shape","Upturned Eyes Shape"]
                    cur_es = pm_options.get("Eyes Shape", "Monolid Eyes Shape")
                    pm_options["Eyes Shape"] = st.selectbox(
                        "Eyes Shape", eye_shapes,
                        index=eye_shapes.index(cur_es) if cur_es in eye_shapes else 0,
                        key=f"eye_shape_{cur}",
                    )

                with st.expander("Lips Type"):
                    lips_colors = ["Berry Lips","Black Lips","Blue Lips","Brown Lips","Burgundy Lips","Coral Lips","Glossy Red Lips","Mauve Lips","Orange Lips","Peach Lips","Pink Lips","Plum Lips","Purple Lips","Red Lips","Yellow Lips"]
                    cur_lc = pm_options.get("Lips Color", "Berry Lips")
                    pm_options["Lips Color"] = st.selectbox(
                        "Lips Color", lips_colors,
                        index=lips_colors.index(cur_lc) if cur_lc in lips_colors else 0,
                        key=f"lips_color_{cur}",
                    )
                    lips_shapes = ["Full Lips","Thin Lips","Plump Lips","Small Lips","Large Lips","Wide Lips","Round Lips","Heart-shaped Lips","Cupid's Bow Lips"]
                    cur_ls = pm_options.get("Lips Shape", "Thin Lips")
                    pm_options["Lips Shape"] = st.selectbox(
                        "Lips Shape", lips_shapes,
                        index=lips_shapes.index(cur_ls) if cur_ls in lips_shapes else 1,
                        key=f"lips_shape_{cur}",
                    )

                with st.expander("Hair Style"):
                    hair_styles = ["Bald","Buzz","Crew","Pixie","Bob","Long bob","Long straight","Wavy","Curly","Afro","Faded afro","Braided","Box braids","Cornrows","Dreadlocks","Pigtails","Ponytail","High ponytail","Bangs","Curtain bangs","Side-swept bangs","Mohawk","Faux hawk","Undercut","Pompadour","Quiff","Top Knot","Bun","Updo"]
                    cur_hs = pm_options.get("Hair Style", "Buzz")
                    pm_options["Hair Style"] = st.selectbox(
                        "Hair Style", hair_styles,
                        index=hair_styles.index(cur_hs) if cur_hs in hair_styles else 1,
                        key=f"hair_style_{cur}",
                    )
                    hair_colors = ["Black","Jet Black","Blonde","Platinum","Brown","Chestnut","Auburn","Red","Strawberry","Gray","Silver","White","Salt and pepper"]
                    cur_hc = pm_options.get("Hair Color", "Black")
                    pm_options["Hair Color"] = st.selectbox(
                        "Hair Color", hair_colors,
                        index=hair_colors.index(cur_hc) if cur_hc in hair_colors else 0,
                        key=f"hair_color_{cur}",
                    )
                    hair_lengths = ["Short","Medium","Long"]
                    cur_hl = pm_options.get("Hair Length", "Short")
                    pm_options["Hair Length"] = st.selectbox(
                        "Hair Length", hair_lengths,
                        index=hair_lengths.index(cur_hl) if cur_hl in hair_lengths else 0,
                        key=f"hair_len_{cur}",
                    )

            
        # ============================
        # Left: 현재 캐릭터의 후보 + 선택
        # ============================
        with col_left:
            cur = st.session_state.current_char_idx
            st.markdown(f"#### Casting Result — Character {cur+1}")

            faces = st.session_state.generated_faces_by_char[cur]
            if faces:
                cols = st.columns(2)
                for i, img_url in enumerate(faces):
                    with cols[i % 2]:
                        st.image(img_url, use_container_width=True)

                        if st.button(f"✅ Select Actor {i+1}", key=f"sel_{cur}_{i}"):
                            st.session_state.selected_face_urls[cur] = img_url

                            # 다음 캐릭터로 자동 이동(마지막이면 Step2)
                            if cur < st.session_state.get("num_characters", 1) - 1:
                                st.session_state.current_char_idx = cur + 1
                            else:
                                # 전원 선택 완료면 Step2
                                if all(st.session_state.selected_face_urls):
                                    st.session_state.step = 2
                            st.rerun()
            else:
                st.info("No footage available. Generate faces for this character.")

            # 상태 요약(선택 여부)
            st.markdown("---")
            st.markdown("#### Selection Status")
            n = st.session_state.get("num_characters", 1)
            for idx in range(n):
                status = "✅ Selected" if st.session_state.selected_face_urls[idx] else "— Not selected"
                st.caption(f"Character {idx+1}: {status}")
        
        # ============================
        # Generate Faces (현재 캐릭터만 생성)
        # ============================
        st.markdown("<br>", unsafe_allow_html=True)

        if st.button("🚀 GENERATE FACES\n(Current Character)", use_container_width=True, key="gen_faces_cur"):
            try:
                with st.spinner(f"Casting in progress... (Character {cur+1})"):
                    seed_value = None
                    if st.session_state.get("seed_mode") == "Fixed":
                        fixed_seed = st.session_state.get("fixed_seed", 12345)
                        seed_value = backend.derive_seed(fixed_seed, cur)

                    imgs = backend.generate_faces(
                        base_prompt=base_prompt,
                        api_key=api_key,
                        deployment_id=deployment_id,
                        width=DEFAULT_W,
                        height=DEFAULT_H,
                        batch_size=batch_size,
                        seed=seed_value,
                        pm_options=pm_options,  # ✅ 추가 (현재 캐릭터 옵션 전달)
                    )
                    st.session_state.generated_faces_by_char[cur] = imgs or []
                st.rerun()
            except Exception as e:
                st.error(str(e))
                
        # ============================
        # Navigator: Prev / Next
        # ============================
        # st.markdown("### Character Navigator")
        nav1, nav2 = st.columns(2)

        with nav1:
            if st.button(
                "⬅️ PREV\nCHARACTER",
                use_container_width=True,
                disabled=(cur == 0),
                key="prev_char",
            ):
                st.session_state.current_char_idx = max(0, cur - 1)
                st.rerun()
        
        # ✅ 선택 전에는 다음으로 못 가게
        disabled_next = (cur == num_characters - 1) or (st.session_state.selected_face_urls[cur] is None)
        
        with nav2:
            if st.button(
                "➡️ NEXT\nCHARACTER",
                use_container_width=True,
                disabled=disabled_next,   # ✅ 여기
                key="next_char",
            ):
                st.session_state.current_char_idx = min(num_characters - 1, cur + 1)
                st.rerun()
        
        st.caption(f"Editing: Character {cur + 1} / {num_characters}")

    
    else:
        # Step1 완료 요약
        st.success("✅ Actor Selected")
        n = st.session_state.get("num_characters", 2)
        selected = st.session_state.get("selected_face_urls", [])
        cols = st.columns(n)
        for i in range(n):
            with cols[i]:
                url = selected[i] if i < len(selected) else None
                if url:
                    st.image(url, use_container_width=True, caption=f"Character {i+1}")
                else:
                    st.caption(f"Character {i+1}: Not selected")


# ---------------------------------------------------------
# [TAB 2] Step 2: 전신 생성 - 다중 캐릭
# ---------------------------------------------------------
with tab2:
    if st.session_state.step == 2:
        st.markdown("### 2. Wardrobe & Styling")

        selected = st.session_state.get("selected_face_urls", [])
        n = len(selected)

        if n == 0 or any(u is None for u in selected):
            st.warning("Step 1에서 모든 캐릭터를 먼저 선택해주세요.")
            st.stop()

        # 길이 보정
        while len(st.session_state.final_character_urls) < n:
            st.session_state.final_character_urls.append(None)
        while len(st.session_state.outfit_prompts) < n:
            st.session_state.outfit_prompts.append("")

        st.session_state.final_character_urls = st.session_state.final_character_urls[:n]
        st.session_state.outfit_prompts = st.session_state.outfit_prompts[:n]

        # 캐릭터별 UI
        for char_i in range(n):
            st.markdown(f"#### Character {char_i+1}")
            col_face, col_outfit, col_result = st.columns([1, 1, 1])
            
            with col_face:
                st.markdown("#### Reference Actor")
                st.image(selected[char_i], use_container_width=True)
    
            with col_outfit:
                st.markdown("#### Outfit Description")
                default_outfit = st.session_state.outfit_prompts[char_i] or "white t-shirt, black pants, yellow sneakers"
                outfit_prompt = st.text_area(
                    f"Describe the outfit (Character {char_i+1})",
                    default_outfit,
                    height=160,
                    key=f"outfit_prompt_{char_i}",
                )
                st.session_state.outfit_prompts[char_i] = outfit_prompt
    
                st.markdown("<br>", unsafe_allow_html=True)
                if st.button("👗 APPLY OUTFIT", use_container_width=True, key=f"apply_outfit_{char_i}"):
                    try:
                        with st.spinner("Fitting room... \n (Switch Mode: 2)"):

                            # seed 결정
                            seed_value = None
                            if st.session_state.get("seed_mode") == "Fixed":
                                fixed_seed = st.session_state.get("fixed_seed", 12345)
                                seed_value = backend.derive_seed(fixed_seed + 1000, char_i)  # ✅ Step1과 분리

                            res = backend.generate_full_body(
                                face_url=selected[char_i],
                                outfit_prompt=outfit_prompt,
                                api_key=api_key,
                                deployment_id=deployment_id,
                                seed=seed_value,  # ✅ 추가
                            )
                        if res:
                            st.session_state.final_character_urls[char_i] = res[0]
                            st.rerun()
                        else:
                            st.warning("전신 결과 이미지 URL을 받지 못했습니다.")
                    except Exception as e:
                        st.error(str(e))
    
            with col_result:
                st.markdown("#### Fitted Result")
                out = st.session_state.final_character_urls[char_i]
                if out:
                    st.image(out, use_container_width=True)
                else:
                    st.info("의상 프롬프트를 입력하고 버튼을 누르세요.")
                    
         # 전원 완료 시 Step3 이동
        if all(st.session_state.final_character_urls):
            if st.button("✨ CONFIRM ALL & GO TO SET", use_container_width=True, key="confirm_all"):
                st.session_state.step = 3
                st.rerun()
        else:
            st.info("모든 캐릭터의 전신 생성이 완료되면 다음 단계로 진행할 수 있습니다.")

    elif st.session_state.step > 2:
        st.success("✅ Costume Fitted")
        n = st.session_state.get("num_characters", 2)
        cols = st.columns(n)
        for i in range(n):
            with cols[i]:
                url = st.session_state.final_character_urls[i] if i < len(st.session_state.final_character_urls) else None
                if url:
                    st.image(url, use_container_width=True, caption=f"Final Character {i+1}")
                else:
                    st.caption(f"Final Character {i+1}: Not ready")
    else:
        st.warning("Step 1을 먼저 완료해주세요.")       


# ---------------------------------------------------------
# [TAB 3] 최종 씬 생성 (다중 캐릭터 2명 기준)
# ---------------------------------------------------------
with tab3:
    if st.session_state.step == 3:
        st.markdown("### 3. Final Scene Composition")

        finals = st.session_state.get("final_character_urls", [])
        if len(finals) < 1 or finals[0] is None:
            st.warning("Step 2에서 Character 1 전신을 먼저 생성해주세요.")
            st.stop()

        char1_url = finals[0]
        char2_url = finals[1] if len(finals) > 1 else None

        col_assets, col_prompt, col_final = st.columns([1, 1, 2])

        with col_assets:
            st.markdown("#### Assets")
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
            if st.button("🎬 ACTION! (Generate Scene)", use_container_width=True, key="generate_scene"):
                try:
                    with st.spinner("Shooting the scene... (Switch Mode: 3)"):
                        
                        # seed 결정
                        seed_value = None
                        if st.session_state.get("seed_mode") == "Fixed":
                            fixed_seed = st.session_state.get("fixed_seed", 12345)
                            seed_value = backend.derive_seed(fixed_seed + 2000, 0)

                        final_imgs = backend.generate_scene(
                            char1_url=char1_url,
                            char2_url=char2_url,
                            bg_url=bg_url,
                            story_prompt=story_prompt,
                            api_key=api_key,
                            deployment_id=deployment_id,
                            seed=seed_value,  # ✅ 추가
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
