import streamlit as st
import backend 
import time

# --- 1. 페이지 및 스타일 설정 (Cinematic Dark Theme) ---
st.set_page_config(
    page_title="Storyboard Director Pro", 
    page_icon="🎬",
    layout="wide", 
    initial_sidebar_state="expanded"
)

# 커스텀 CSS: 영화 콘티 느낌의 어두운 테마와 금색 포인트
st.markdown("""
### AI ID Photo Generator

Generate a **plain ID-style photo**  
using structured facial tags.
""")


st.markdown("""
    <style>
    /* 전체 배경 및 폰트 */
    .stApp { background-color: #0e1117; color: #e0e0e0; font-family: 'Helvetica Neue', sans-serif; }
    
    /* 헤더 스타일 */
    h1, h2, h3 { color: #f5c518; font-weight: 700; letter-spacing: -1px; }
    
    /* 스토리보드 카드 스타일 */
    .storyboard-card { 
        border: 1px solid #333; 
        padding: 15px; 
        border-radius: 8px; 
        background-color: #161b22; 
        margin-bottom: 20px;
        box-shadow: 0 4px 6px rgba(0,0,0,0.3);
    }
    
    /* 버튼 스타일 (영화제 수상작 느낌의 골드 테두리) */
    div.stButton > button {
        width: 100%;
        border: 1px solid #f5c518;
        color: #f5c518;
        background-color: transparent;
        border-radius: 4px;
        transition: all 0.3s;
    }
    div.stButton > button:hover {
        background-color: #f5c518;
        color: #000000;
        border: 1px solid #f5c518;
    }
    
    /* 선택된 이미지 하이라이트 */
    .selected-img { border: 3px solid #f5c518; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. 세션 상태 초기화 (워크플로우 메모리) ---
if "step" not in st.session_state: st.session_state.step = 1
if "generated_faces" not in st.session_state: st.session_state.generated_faces = []
if "selected_face_url" not in st.session_state: st.session_state.selected_face_url = None
if "final_character_url" not in st.session_state: st.session_state.final_character_url = None
if "scene_url" not in st.session_state: st.session_state.scene_url = None

# --- 3. 사이드바: Director's Chair (설정 패널) ---
with st.sidebar:
    st.title("🎬 Director's Chair")
    
    # API 설정 (접이식)
    with st.expander("🔐 Studio Settings (API)", expanded=False):
        if "RUNCOMFY_API_KEY" in st.secrets:
            api_key = st.secrets["RUNCOMFY_API_KEY"]
            deployment_id = st.secrets["DEPLOYMENT_ID"]
            st.success("Studio License Verified ✅")
        else:
            api_key = st.text_input("API Key", type="password")
            deployment_id = st.text_input("Deployment ID")

    st.markdown("---")
    
    # 장르 프리셋 (분위기 자동 설정용 - 실제 프롬프트에 반영 가능)
    genre = st.selectbox("🎞️ Genre Preset", 
                         ["Noir (Dark, Contrast)", "Sci-Fi (Neon, Clean)", "Documentary (Raw, Realistic)", "Fantasy (Soft, Vibrant)"])
    
    st.markdown("### 👤 Casting Profile (Portrait Master)")
    
    # 탭으로 옵션 정리
    tab_bio, tab_face, tab_hair = st.tabs(["Bio", "Face", "Hair"])
    
    pm_options = {}
    with tab_bio:
        pm_options["gender"] = st.selectbox("Gender", ["Man", "Woman"])
        pm_options["age"] = st.slider("Age", 4, 80, 25)
        pm_options["nationality_1"] = st.selectbox("Nationality", ["Korean", "American", "Japanese", "British", "French"])
        pm_options["body_type"] = st.selectbox("Body Type", ["Fit", "Slim", "Muscular", "Average", "Curvy"])
    
    with tab_face:
        pm_options["face_shape"] = st.selectbox("Face Shape", ["Oval", "Square", "Round", "Diamond"])
        pm_options["eyes_color"] = st.selectbox("Eye Color", ["Brown", "Black", "Blue", "Green"])
        pm_options["facial_expression"] = st.selectbox("Expression", ["Neutral", "Smiling", "Serious", "Curious"])
        
    with tab_hair:
        pm_options["hair_style"] = st.selectbox("Hair Style", ["Short", "Long", "Bob", "Buzz cut", "Ponytail"])
        pm_options["hair_color"] = st.selectbox("Hair Color", ["Black", "Brown", "Blonde", "Red", "Grey"])

# --- 4. 메인 스테이지 (Workflow Steps) ---

st.markdown(f"## 🎥 Scene Production: Step {st.session_state.step}")

# ==========================================
# ACT 1: Casting (얼굴 생성)
# ==========================================
if st.session_state.step == 1:
    st.markdown("### Act 1: The Casting Call")
    st.caption("캐릭터의 페르소나를 정의하고 오디션(이미지 생성)을 진행합니다.")

    col1, col2 = st.columns([2, 1])
    
    with col1:
        # 영화적 비율 설정
        aspect_ratio = st.radio("Aspect Ratio", ["Cinematic (16:9)", "Portrait (9:16)", "Square (1:1)"], horizontal=True)
        if "16:9" in aspect_ratio: w, h = 1152, 896
        elif "9:16" in aspect_ratio: w, h = 896, 1152
        else: w, h = 1024, 1024
        
        base_prompt = st.text_area("Character Logline (Prompt)", 
                                   value=f"A {pm_options['age']}-year-old {pm_options['nationality_1']} {pm_options['gender']}, {pm_options['hair_style']} hair, cinematic lighting, highly detailed",
                                   height=100)
    
    with col2:
        st.info("💡 Tip: 사이드바에서 세부 외모를 조정하세요.")
        num_images = st.slider("Batch Size", 1, 4, 2)
        if st.button("🎬 Action! (Generate Face)"):
            if not api_key:
                st.error("API Key가 필요합니다.")
            else:
                with st.spinner("Casting in progress..."):
                    # Backend 호출
                    images = backend.generate_faces(base_prompt, pm_options, api_key, deployment_id, w, h, num_images)
                    if images:
                        st.session_state.generated_faces = images
                        st.session_state.step = 2
                        st.rerun()
                    else:
                        st.error("Casting Failed. Please check inputs.")

# ==========================================
# ACT 2: Selection (배우 선택)
# ==========================================
elif st.session_state.step == 2:
    st.markdown("### Act 2: Select Your Protagonist")
    if st.button("⬅️ Recast (Go Back)"):
        st.session_state.step = 1
        st.rerun()

    st.markdown("---")
    cols = st.columns(len(st.session_state.generated_faces))
    
    for idx, img_url in enumerate(st.session_state.generated_faces):
        with cols[idx]:
            st.image(img_url, use_container_width=True)
            if st.button(f"Select Actor #{idx+1}", key=f"sel_{idx}"):
                st.session_state.selected_face_url = img_url
                st.session_state.step = 3
                st.rerun()

# ==========================================
# ACT 3: Wardrobe (의상 및 전신)
# ==========================================
elif st.session_state.step == 3:
    st.markdown("### Act 3: Wardrobe & Fitting")
    
    col_ref, col_work = st.columns([1, 2])
    
    with col_ref:
        st.markdown('<div class="storyboard-card">', unsafe_allow_html=True)
        st.markdown("#### Reference Actor")
        st.image(st.session_state.selected_face_url, use_container_width=True)
        st.caption("Identity Source")
        st.markdown('</div>', unsafe_allow_html=True)
        
    with col_work:
        st.markdown("#### Costume Design Instructions")
        outfit_prompt = st.text_area("Describe the Outfit & Pose", 
                                     placeholder="wearing a oversized beige trench coat, walking in the rain, cyberpunk street background...",
                                     height=150)
        
        if st.button("✨ Finalize Character (Full Body)"):
            if not outfit_prompt:
                st.warning("Please describe the outfit.")
            else:
                with st.spinner("Applying makeup and costume..."):
                    final_imgs = backend.generate_full_body(st.session_state.selected_face_url, outfit_prompt, api_key, deployment_id)
                    if final_imgs:
                        st.session_state.final_character_url = final_imgs[-1]
                        st.session_state.step = 4 # 다음 단계(결과 확인)로
                        st.rerun()
                    else:
                        st.error("Generation Failed.")

# ==========================================
# ACT 4: Final Scene (스토리보드 뷰)
# ==========================================
elif st.session_state.step == 4:
    st.balloons()
    st.markdown("### 🎬 Final Storyboard Cut")
    
    # 상단 메뉴
    c1, c2, c3 = st.columns([1,1,1])
    with c1: 
        if st.button("🔄 New Scene (Restart)"):
            st.session_state.step = 1
            st.rerun()
    with c2:
        if st.button("👗 Change Outfit (Step 3)"):
            st.session_state.step = 3
            st.rerun()
            
    # 최종 결과물 표시 (영화 콘티 스타일)
    st.markdown("---")
    st.markdown('<div class="storyboard-card">', unsafe_allow_html=True)
    
    # 레이아웃: 이미지 + 노트
    col_img, col_note = st.columns([2, 1])
    
    with col_img:
        st.image(st.session_state.final_character_url, caption="Final Composite Shot", use_container_width=True)
        
    with col_note:
        st.markdown("#### 📝 Director's Note")
        st.text_area("Scene Description", "Scene #1: Character enters the scene...", height=100)
        st.markdown("#### ⚙️ Technical Specs")
        st.markdown(f"""
        - **Shot Type**: Full Shot
        - **Genre**: {genre}
        - **Format**: {w}x{h}
        """)
        
        # 다운로드 버튼 준비
        # (실제로는 이미지 데이터를 받아와야 하지만 여기선 URL 링크로 대체하거나 추가 구현 가능)
        st.markdown(f"[📥 Download Image]({st.session_state.final_character_url})")

    st.markdown('</div>', unsafe_allow_html=True)

    # (선택 사항) 다음 단계를 위한 확장 공간: 배경 합성 등
    with st.expander("🚀 Next Step: Scene Composition (Coming Soon)"):
        st.info("이 캐릭터를 배경 이미지와 합성하는 기능(Step 3 워크플로우)이 여기에 추가될 예정입니다.")
