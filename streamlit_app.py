# app.py
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
# 1. 페이지 설정 및 디자인
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
if "generated_faces" not in st.session_state:
    st.session_state.generated_faces = []
if "selected_face_url" not in st.session_state:
    st.session_state.selected_face_url = None
if "final_character_url" not in st.session_state:
    st.session_state.final_character_url = None
if "final_scene_url" not in st.session_state:
    st.session_state.final_scene_url = None

# =========================================================
# 3. 상수 (기본값)
# =========================================================
DEFAULT_W = 896
DEFAULT_H = 1152

# =========================================================
# 4. 메인 화면 (탭 구성)
# =========================================================
st.header("🎬 Cinematic Storyboard AI")

tab1, tab2, tab3, tab4 = st.tabs([
    "Step1 | 👤 CHARACTER PROFILE",
    "Step2 | 👗 APPLY OUTFIT",
    "Step3 | 🏞️ BACKGROUND",
    "Step4 | 📝 STORYBOARD"
])

pm_options = {}
# ---------------------------------------------------------
# [TAB 1] 얼굴 생성
# ---------------------------------------------------------
with tab1:
    if st.session_state.step == 1:
        st.markdown("### 1. Define Your Actor Profile")

        col_left, col_right = st.columns([3, 1])
 
        with col_right:
            
            st.markdown("#### Character Setting")
            
            with st.expander("Portrait Setting"): 
                with st.expander("Gender & Nationality"): 
                    pm_options["Gender"] = st.selectbox("Gender", ["Man","Woman"])
                    pm_options["Nationality"] = st.selectbox("Nationality", ["Chinese","Japanese","Korean","South Korean","Indian","Saudi","British","French","German","Italian","Spanish","American","Canadian","Brazilian","Mexican","Argentine","Egyptian","South African","Nigerian","Kenyan","Moroccan","Australian","New Zealander","Fijian","Samoan","Tongan"])
                    pm_options["age"] = st.number_input("AGE", 10, 80, 25)
                
                with st.expander("Face & Body Type"): 
                    pm_options["Face Shape"] = st.selectbox("Face Shape", ["Oval","Round","Square","Heart","Diamond","Triangle","Inverted Triangle","Pear","Rectangle","Oblong","Long"])
                    pm_options["Body Type"] = st.selectbox("Body Type", ["Chubby","Curvy","Fat","Fit","Hefty","Large","Lanky","Muscular","Obese","Overweight","Petite","Plump","Short","Skinny","Slight","Slim","Small","Stout","Stocky","Tall","Thick","Tiny","Underweight","Well-built"])
                
                with st.expander("Eyes Type"): 
                    pm_options["Eyes Color"] = st.selectbox("Eyes Color", ["Albino", "Amber", "Blue", "Brown", "Green", "Gray", "Hazel", "Heterochromia", "Red", "Violet"])
                    pm_options["Eyes Shape"] = st.selectbox("Eyes Shape", ["Almond Eyes Shape","Asian Eyes Shape","Close-Set Eyes Shape","Deep Set Eyes Shape","Downturned Eyes Shape","Double Eyelid Eyes Shape","Hooded Eyes Shape","Monolid Eyes Shape","Oval Eyes Shape","Protruding Eyes Shape","Round Eyes Shape","Upturned Eyes Shape"])
                
                with st.expander("Lips Type"): 
                    pm_options["Lips Color"] = st.selectbox("Lips Color", ["Berry Lips","Black Lips","Blue Lips","Brown Lips","Burgundy Lips","Coral Lips","Glossy Red Lips","Mauve Lips","Orange Lips","Peach Lips","Pink Lips","Plum Lips","Purple Lips","Red Lips","Yellow Lips"])
                    pm_options["Lips Shape"] = st.selectbox("Lips Shape", ["Full Lips","Thin Lips","Plump Lips","Small Lips","Large Lips","Wide Lips","Round Lips","Heart-shaped Lips","Cupid's Bow Lips"])
                
                with st.expander("Hair Style"): 
                    pm_options["Hair Style"] = st.selectbox("Hair Style", ["Bald","Buzz","Crew","Pixie","Bob","Long bob","Long straight","Wavy","Curly","Afro","Faded afro","Braided","Box braids","Cornrows","Dreadlocks","Pigtails","Ponytail","High ponytail","Bangs","Curtain bangs","Side-swept bangs","Mohawk","Faux hawk","Undercut","Pompadour","Quiff","Top Knot","Bun","Updo"])
                    pm_options["Hair Color"] = st.selectbox("Hair Color", ["Black","Jet Black","Blonde","Platinum","Brown","Chestnut","Auburn","Red","Strawberry","Gray","Silver","White","Salt and pepper"])
                    pm_options["Hair Length"] = st.selectbox("Hair Length", ["Short","Medium","Long"])

            st.markdown("#### Advanced Setting")
            
            with st.expander("Image Count"): 
                batch_size = st.slider("Number of Images", 1, 4, 2)
                seed_mode = st.radio("Seed mode", ["Random", "Fixed"], index=0)
                if seed_mode == "Fixed":
                    fixed_seed = st.number_input("Fixed seed", min_value=0, value=42, step=1)
                else:
                    fixed_seed = None

            # base_prompt = st.text_area(
            #     "Base Portrait Prompt",
            #     "Grey background, a 12-year-old Korean boy, white t-shirt, Buzz cut hair, documentary photograph, cinematic still frame",
            #     height=140
            # )

            st.markdown("<br>", unsafe_allow_html=True)
            if st.button("🚀 CASTING START \n(Generate Faces)", use_container_width=True):
                try:
                    with st.spinner("Casting in progress... (Switch Mode: 1)"):
                        
                        use_custom_prompt = st.checkbox("Use custom base prompt", value=False)

                        if use_custom_prompt:
                            base_prompt = st.text_area("Base Prompt", DEFAULT_TEXT)
                        else:
                            base_prompt = None
                        
                        imgs = backend.generate_faces(
                            api_key=api_key,
                            deployment_id=deployment_id,
                            width=DEFAULT_W,
                            height=DEFAULT_H,
                            batch_size=batch_size,
                            pm_options=pm_options
                        )
                    if imgs:
                        st.session_state.generated_faces = imgs
                        st.rerun()
                    else:
                        st.warning("이미지 URL을 받지 못했습니다. RunComfy result outputs를 확인하세요.")
                except Exception as e:
                    st.error(str(e))

        with col_left:
            st.markdown("#### Casting Result")
            if st.session_state.generated_faces:
                cols = st.columns(2)
                for i, img_url in enumerate(st.session_state.generated_faces):
                    with cols[i % 2]:
                        st.image(img_url, use_container_width=True)
                        if st.button(f"✅ Select Actor {i+1}", key=f"sel_{i}"):
                            st.session_state.selected_face_url = img_url
                            st.session_state.step = 2
                            st.rerun()
            else:
                st.info("오른쪽에서 프롬프트 설정 후 'CASTING START'를 눌러주세요.")
    else:
        st.success("✅ Actor Selected")
        if st.session_state.selected_face_url:
            st.image(st.session_state.selected_face_url, width=160, caption="Main Actor")

# ---------------------------------------------------------
# [TAB 2] 전신 생성
# ---------------------------------------------------------
with tab2:
    if st.session_state.step == 2:
        st.markdown("### 2. Wardrobe & Styling")

        col_face, col_outfit, col_result = st.columns([1, 1, 1])

        with col_face:
            st.markdown("#### Reference Actor")
            st.image(st.session_state.selected_face_url, use_container_width=True)

        with col_outfit:
            st.markdown("#### Outfit Description")
            outfit_prompt = st.text_area(
                "Describe the outfit",
                "white background, white t-shirt, black pants, yellow sneakers",
                height=160
            )

            st.markdown("<br>", unsafe_allow_html=True)
            if st.button("👗 APPLY OUTFIT", use_container_width=True):
                try:
                    with st.spinner("Fitting room... (Switch Mode: 2)"):
                        res = backend.generate_full_body(
                            face_url=st.session_state.selected_face_url,
                            outfit_prompt=outfit_prompt,
                            api_key=api_key,
                            deployment_id=deployment_id,
                        )
                    if res:
                        st.session_state.final_character_url = res[0]
                        st.rerun()
                    else:
                        st.warning("전신 결과 이미지 URL을 받지 못했습니다.")
                except Exception as e:
                    st.error(str(e))

        with col_result:
            st.markdown("#### Fitted Result")
            if st.session_state.final_character_url:
                st.image(st.session_state.final_character_url, use_container_width=True)
                if st.button("✨ CONFIRM & GO TO SET", use_container_width=True):
                    st.session_state.step = 3
                    st.rerun()
            else:
                st.info("의상 프롬프트를 입력하고 버튼을 누르세요.")
    elif st.session_state.step > 2:
        st.success("✅ Costume Fitted")
        if st.session_state.final_character_url:
            st.image(st.session_state.final_character_url, width=160, caption="Final Character")
    else:
        st.warning("Step 1을 먼저 완료해주세요.")

# ---------------------------------------------------------
# [TAB 3] 최종 씬 생성
# ---------------------------------------------------------
with tab3:
    if st.session_state.step == 3:
        st.markdown("### 3. Final Scene Composition")

        col_assets, col_prompt, col_final = st.columns([1, 1, 2])

        with col_assets:
            st.markdown("#### Assets")
            st.image(st.session_state.final_character_url, width=160, caption="Character 1 (URL ref)")

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
                    with st.spinner("Shooting the scene... (Switch Mode: 3)"):
                        final_imgs = backend.generate_scene(
                            char1_url=st.session_state.final_character_url,
                            char2_url=None,
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
