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

# Step1(캐스팅 누적 방식)
if "num_characters" not in st.session_state:
    st.session_state.num_characters = 2
if "shots_per_character" not in st.session_state:
    st.session_state.shots_per_character = 2
if "current_char_idx" not in st.session_state:
    st.session_state.current_char_idx = 0
if "casting_groups" not in st.session_state:
    st.session_state.casting_groups = []          # List[List[str]]
if "selected_cast" not in st.session_state:
    st.session_state.selected_cast = []           # List[Optional[str]]

# 단일 호환(기존 변수 유지)
if "generated_faces" not in st.session_state:
    st.session_state.generated_faces = []
if "selected_face_url" not in st.session_state:
    st.session_state.selected_face_url = None

# Step2/3
if "final_character_urls" not in st.session_state:
    st.session_state.final_character_urls = []    # List[Optional[str]]
if "final_character_url" not in st.session_state:
    st.session_state.final_character_url = None
if "final_scene_url" not in st.session_state:
    st.session_state.final_scene_url = None


def _ensure_len(lst, n, fill=None):
    if len(lst) < n:
        lst.extend([fill] * (n - len(lst)))
    elif len(lst) > n:
        del lst[n:]
    return lst


def _all_selected(selected_list):
    return len(selected_list) > 0 and all(u is not None for u in selected_list)


# =========================================================
# 3. 상수
# =========================================================
DEFAULT_W = 896
DEFAULT_H = 1152

# =========================================================
# 4. 메인 화면 (탭 구성)
# =========================================================
st.header("🎬 Cinematic Storyboard AI")

tab1, tab2, tab3, tab4 = st.tabs([
    "Step1 | 👤 CHARACTER PROFILE",
    "Step2 | 👗 CLOTHING TRANSLATE",
    "Step3 | 🏞️ BACKGROUND GENERATION",
    "Step4 | 📝 SCRIPT"
])

# =========================================================
# [TAB 1] 얼굴 생성 (멀티: “한 명씩 생성 → 선택 → 저장 → 다음 캐릭터”)
# =========================================================
with tab1:
    if st.session_state.step == 1:
        st.markdown("### 1. Define Your Actor Profile")

        col_left, col_right = st.columns([3, 1])

        with col_right:
            st.markdown("#### Advanced Setting")

            # 멀티 설정
            n_chars = st.slider("Number of Characters", 1, 5, st.session_state.num_characters)
            shots = st.slider("Shots per Character", 1, 4, st.session_state.shots_per_character)

            # 변경 반영 + 리스트 길이 보정
            if int(n_chars) != int(st.session_state.num_characters):
                st.session_state.num_characters = int(n_chars)
                st.session_state.current_char_idx = min(st.session_state.current_char_idx, st.session_state.num_characters - 1)

            if int(shots) != int(st.session_state.shots_per_character):
                st.session_state.shots_per_character = int(shots)

            st.session_state.casting_groups = _ensure_len(st.session_state.casting_groups, st.session_state.num_characters, [])
            st.session_state.selected_cast = _ensure_len(st.session_state.selected_cast, st.session_state.num_characters, None)
            st.session_state.final_character_urls = _ensure_len(st.session_state.final_character_urls, st.session_state.num_characters, None)

            st.caption(f"Now casting: Character {st.session_state.current_char_idx + 1} / {st.session_state.num_characters}")

            # 후보 수 = shots_per_character
            base_prompt = st.text_area(
                "Base Portrait Prompt",
                "Grey background, a 12-year-old Korean boy, white t-shirt, Buzz cut hair, documentary photograph, cinematic still frame",
                height=140
            )

            st.markdown("<br>", unsafe_allow_html=True)
            if st.button("🚀 CASTING START \n(Generate Faces)", use_container_width=True):
                try:
                    with st.spinner("Casting in progress... (Switch Mode: 1)"):
                        imgs = backend.generate_faces(
                            base_prompt=base_prompt,
                            api_key=api_key,
                            deployment_id=deployment_id,
                            width=DEFAULT_W,
                            height=DEFAULT_H,
                            batch_size=int(st.session_state.shots_per_character),
                        )

                    if imgs:
                        # 현재 캐릭터 그룹에 저장
                        idx = st.session_state.current_char_idx
                        st.session_state.casting_groups[idx] = imgs
                        st.session_state.generated_faces = imgs  # 단일 호환
                        st.rerun()
                    else:
                        st.warning("이미지 URL을 받지 못했습니다. RunComfy result outputs를 확인하세요.")
                except Exception as e:
                    st.error(str(e))

        with col_left:
            st.markdown("#### Casting Result")

            # 캐릭터별 결과 표시 + 선택
            n_chars = st.session_state.num_characters
            for char_idx in range(n_chars):
                st.markdown(f"##### Character {char_idx + 1}")

                group = st.session_state.casting_groups[char_idx] if char_idx < len(st.session_state.casting_groups) else []
                if not group:
                    st.info("No footage available for this character.")
                    continue

                cols = st.columns(2)
                for i, img_url in enumerate(group):
                    with cols[i % 2]:
                        st.image(img_url, use_container_width=True)

                        is_selected = (st.session_state.selected_cast[char_idx] == img_url)
                        btn_label = "✅ Selected" if is_selected else f"✅ Select (Char {char_idx+1} / #{i+1})"

                        if st.button(btn_label, key=f"sel_char{char_idx}_{i}"):
                            st.session_state.selected_cast[char_idx] = img_url

                            # 단일 호환(첫 캐릭터를 main으로)
                            if char_idx == 0:
                                st.session_state.selected_face_url = img_url
                            st.rerun()

            st.markdown("---")

            # 다음 캐릭터 / Step2 진행
            all_done = _all_selected(st.session_state.selected_cast)

            c1, c2 = st.columns(2)
            with c1:
                if st.button("➡️ Next Character", use_container_width=True, disabled=all_done):
                    if st.session_state.current_char_idx < st.session_state.num_characters - 1:
                        st.session_state.current_char_idx += 1
                        st.session_state.generated_faces = []  # 현재 캐릭터 후보 UI만 비우고 싶으면 유지
                        st.rerun()

            with c2:
                if st.button("➡️ Proceed to Step2", use_container_width=True, disabled=not all_done):
                    # Step2는 우선 “선택된 얼굴들”을 사용
                    st.session_state.selected_face_url = st.session_state.selected_cast[0]
                    st.session_state.step = 2
                    st.rerun()

    else:
        st.success("✅ Step 1 Completed")
        if st.session_state.selected_cast:
            cols = st.columns(min(4, len(st.session_state.selected_cast)))
            for i, u in enumerate(st.session_state.selected_cast):
                with cols[i % len(cols)]:
                    if u:
                        st.image(u, use_container_width=True, caption=f"Character {i+1}")

# =========================================================
# [TAB 2] 전신 생성 (멀티: 선택된 캐릭터들 모두 처리)
# =========================================================
with tab2:
    if st.session_state.step == 2:
        st.markdown("### 2. Wardrobe & Styling")

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
                            face_url = selected_cast[i] if i < len(selected_cast) else None
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

# =========================================================
# [TAB 3] 최종 씬 생성 (char1/char2 사용, 없으면 복제)
# =========================================================
with tab3:
    if st.session_state.step == 3:
        st.markdown("### 3. Final Scene Composition")

        col_assets, col_prompt, col_final = st.columns([1, 1, 2])

        finals = st.session_state.final_character_urls or []
        char1_url = finals[0] if len(finals) > 0 else None
        char2_url = finals[1] if len(finals) > 1 else None

        with col_assets:
            st.markdown("#### Assets")
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

# =========================================================
# [TAB 4] (미구현)
# =========================================================
with tab4:
    st.info("Step4는 추후 Shot Script/Shotlist 파서를 연결하세요.")
