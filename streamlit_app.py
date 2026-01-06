import streamlit as st
import backend
import time

# --- 1. 페이지 설정 (사이드바 상태: Collapsed) ---
st.set_page_config(
    page_title="Neon Darkroom: Director's Suite",
    page_icon="🎬",
    layout="wide",
    initial_sidebar_state="collapsed" # 사이드바 숨김
)

# # 1. secrets.toml 파일에서 먼저 찾아봄
# if "RUNCOMFY_API_KEY" in st.secrets:
#     api_key = st.secrets["RUNCOMFY_API_KEY"]
#     deployment_id = st.secrets["DEPLOYMENT_ID"]
#     # st.sidebar.success("API Key가 로드되었습니다! ✅")
# else:
#     # 2. 파일이 없으면 입력창 표시
#     api_key = st.sidebar.text_input("RunComfy API Key", type="password")
#     deployment_id = st.sidebar.text_input("Deployment ID")
#     if not api_key or not deployment_id:
#         st.sidebar.warning("API Key와 Deployment ID를 입력해주세요.")
#         st.stop() # 키가 없으면 앱 실행 중단
        

# --- 2. CSS 매직: 와이드 콘솔 디자인 ---
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Rajdhani:wght@500;700&family=Roboto+Mono:wght@400;700&display=swap');

    /* [1] 배경 및 폰트 */
    .stApp {
        background-color: #050505;
        background-image: radial-gradient(#151515 1px, transparent 1px);
        background-size: 30px 30px;
        color: #e0e0e0;
        font-family: 'Rajdhani', sans-serif;
    }

    /* [2] 상단 컨트롤 패널 (Dashboard) */
    .dashboard-container {
        background: linear-gradient(180deg, #161616 0%, #0a0a0a 100%);
        border-bottom: 2px solid #333;
        padding: 20px;
        margin-top: -50px; /* Streamlit 기본 여백 제거 */
        margin-left: -5rem; margin-right: -5rem; /* 좌우 꽉 채우기 */
        padding-left: 5rem; padding-right: 5rem;
        box-shadow: 0 10px 20px rgba(0,0,0,0.8);
        margin-bottom: 20px;
    }
    .control-label {
        color: #888;
        font-size: 12px;
        letter-spacing: 1px;
        margin-bottom: 5px;
    }
    
    /* 입력 필드 커스텀 */
    .stTextInput>div>div, .stSelectbox>div>div, .stNumberInput>div>div {
        background-color: #222 !important;
        border: 1px solid #444 !important;
        color: #FFD700 !important; /* Gold Text */
        border-radius: 4px;
    }
    
    /* [3] 메인 뷰포트 (중앙) */
    .viewport-frame {
        border: 2px solid #333;
        border-radius: 12px;
        background-color: #000;
        min-height: 500px;
        position: relative;
        display: flex;
        align-items: center;
        justify-content: center;
        box-shadow: 0 0 30px rgba(0, 255, 255, 0.05);
    }
    
    /* [4] 액션 버튼 (하단 중앙 배치) */
    .stButton>button {
        background: linear-gradient(90deg, #FFD700, #ffaa00) !important;
        color: #000 !important;
        border: none;
        font-weight: bold;
        font-size: 20px;
        padding: 15px 40px;
        text-transform: uppercase;
        letter-spacing: 2px;
        transition: all 0.3s;
        width: 100%;
        border-radius: 8px;
    }
    .stButton>button:hover {
        box-shadow: 0 0 20px #FFD700;
        transform: scale(1.02);
    }

    /* 필름 스트립 */
    .film-strip {
        display: flex;
        gap: 10px;
        overflow-x: auto;
        padding: 20px 0;
        border-top: 1px dashed #333;
        margin-top: 30px;
    }
    
    /* 탭 스타일 재정의 (상단 패널용) */
    .stTabs [data-baseweb="tab-list"] { background-color: transparent; }
    .stTabs [data-baseweb="tab"] { color: #666; }
    .stTabs [aria-selected="true"] { color: #FFD700 !important; border-bottom-color: #FFD700 !important; }
    
    </style>
""", unsafe_allow_html=True)

# --- 3. 세션 상태 관리 ---
if "step" not in st.session_state: st.session_state.step = 1
if "generated_faces" not in st.session_state: st.session_state.generated_faces = []
if "selected_face_url" not in st.session_state: st.session_state.selected_face_url = None
if "final_character_url" not in st.session_state: st.session_state.final_character_url = None
if "processing" not in st.session_state: st.session_state.processing = False

# =========================================================
# [SECTION 1] TOP CONTROL DECK (상단 계기판)
# =========================================================

# 1-2. 메인 컨트롤 패널 (여기가 사이드바를 대체함)
st.markdown(f"### 🕹️ CONTROL CONSOLE | MODE: STEP {st.session_state.step}")

# 탭을 사용하여 공간 절약
tab1, tab2, tab3, tab4 = st.tabs(["👤 CHARACTER PROFILE", "👗 CLOTHING TRANSLATE", "🏞️ BACKGROUND GENERATION", "📝 SCRIPT"])

pm_options = {}

with tab1:
    # 캐릭터 설정 (4열 배치)
    col_g, col_a, col_n, col_b = st.columns(4)
    
    with col_g: 
        pm_options["gender"] = st.selectbox("GENDER", ["Man", "Woman"])
        
    with col_a: 
        pm_options["age"] = st.number_input("AGE", 10, 80, 25)
        
    with col_n: 
        pm_options["nationality"] = st.selectbox("ORIGIN", ["Korean", "American", "British", "French"])
        
    with col_b: 
        pm_options["body_type"] = st.selectbox("BODY", ["Fit", "Slim", "Muscular", "Average"])

with tab2:
    # 기술 설정 (3열 배치)
    col_r, col_l, col_q = st.columns(3)
    with col_r: 
        ratio = st.selectbox("ASPECT RATIO", ["Cinematic (16:9)", "Portrait (9:16)", "Square (1:1)"])
        if "16:9" in ratio: width, height = 1152, 896
        elif "9:16" in ratio: width, height = 896, 1152
        else: width, height = 1024, 1024
    with col_l: st.select_slider("LIGHTING MOOD", ["Dark", "Cinematic", "Bright"], value="Cinematic")
    with col_q: batch_size = st.slider("BATCH SIZE", 1, 4, 2)

with tab3:
    # 프롬프트 입력
    base_prompt = st.text_input("LOGLINE / PROMPT", "Cinematic shot, highly detailed masterpiece, 8k resolution")

st.markdown('</div>', unsafe_allow_html=True) # End Dashboard


# =========================================================
# [SECTION 2] MAIN VIEWPORT (중앙 화면)
# =========================================================

# 레이아웃: 왼쪽(뷰포트) - 오른쪽(작업 버튼)
col_view, col_action = st.columns([3, 1])

with col_view:
    st.markdown('<div class="viewport-frame">', unsafe_allow_html=True)
    
    # 이미지 표시 로직
    display_img = None
    overlay_text = "STANDBY"
    
    if st.session_state.step == 1 and st.session_state.generated_faces:
        display_img = st.session_state.generated_faces[-1]
        overlay_text = "CASTING COMPLETE"
    elif st.session_state.step == 3: # 의상 단계
        display_img = st.session_state.selected_face_url
        overlay_text = "REFERENCE LOADED"
    elif st.session_state.step == 4:
        display_img = st.session_state.final_character_url
        overlay_text = "FINAL RENDER"

    if display_img:
        st.image(display_img, use_container_width=True)
    else:
        st.markdown(f"<h2 style='color:#333'>{overlay_text}</h2>", unsafe_allow_html=True)
        
    st.markdown('</div>', unsafe_allow_html=True)

with col_action:
    st.markdown("### 🎬 ACTION")
    st.markdown("---")
    
    # 단계별 액션 버튼 로직
    if st.session_state.step == 1:
        st.info("Define character profile above and start casting.")
        if st.button("RUN CASTING\n(GENERATE)", use_container_width=True):
            if not api_key:
                st.error("API KEY REQUIRED")
            else:
                with st.spinner("CASTING ACTORS..."):
                    imgs = backend.generate_faces(base_prompt, pm_options, api_key, deployment_id, width, height, batch_size)
                    if imgs:
                        st.session_state.generated_faces = imgs
                        st.session_state.step = 2
                        st.rerun()

    elif st.session_state.step == 2:
        st.success("Select an actor from the Film Strip below.")
        if st.button("↺ RESTART", use_container_width=True):
            st.session_state.step = 1
            st.rerun()

    elif st.session_state.step == 3:
        outfit = st.text_area("WARDROBE", "White t-shirt, jeans, sneakers")
        if st.button("APPLY COSTUME", use_container_width=True):
            with st.spinner("FITTING..."):
                res = backend.generate_full_body(st.session_state.selected_face_url, outfit, api_key, deployment_id)
                if res:
                    st.session_state.final_character_url = res[-1]
                    st.session_state.step = 4
                    st.rerun()
                    
    elif st.session_state.step == 4:
        st.balloons()
        st.markdown("### ✅ SCENE CUT")
        if st.button("NEW PROJECT", use_container_width=True):
            st.session_state.step = 1
            st.rerun()

# =========================================================
# [SECTION 3] FILM STRIP (하단 갤러리)
# =========================================================
st.markdown("### 🎞️ RUSHES (FILM STRIP)")

if st.session_state.generated_faces:
    cols = st.columns(len(st.session_state.generated_faces))
    for idx, img in enumerate(st.session_state.generated_faces):
        with cols[idx]:
            # 선택 효과
            border = "2px solid #FFD700" if img == st.session_state.selected_face_url else "1px solid #333"
            st.markdown(f"<div style='border:{border}; padding:2px'>", unsafe_allow_html=True)
            st.image(img, use_container_width=True)
            st.markdown("</div>", unsafe_allow_html=True)
            
            if st.button(f"SELECT #{idx+1}", key=f"sel_{idx}"):
                st.session_state.selected_face_url = img
                st.session_state.step = 3
                st.rerun()
else:
    st.caption("No footage available.")
