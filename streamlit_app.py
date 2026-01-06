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
<style>
/* 기본 폰트 (중립적, 가독성 위주) */
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600&display=swap');

/* [1] 전체 앱: 밝고 중립적인 배경 */
.stApp {
        background-color: #050505;
        background-image: radial-gradient(#1a1a1a 1px, transparent 1px), radial-gradient(#1a1a1a 1px, transparent 1px);
        background-size: 20px 20px;
        background-position: 0 0, 10px 10px;
        color: #e0e0e0;
        font-family: 'Rajdhani', sans-serif;
    }
    
/* [2] 사이드바 (Control Deck) 스타일 */
    [data-testid="stSidebar"] {
        background-color: #0f1115;
        border-right: 1px solid #333;
        box-shadow: 5px 0 15px rgba(0,0,0,0.5);
    }
    [data-testid="stSidebar"] h1, h2, h3 {
        color: #FFD700; /* Amber Gold */
        text-transform: uppercase;
        letter-spacing: 2px;
        text-shadow: 0 0 5px rgba(255, 215, 0, 0.5);
    }
    
/* [3] 입력 필드 */
.stTextInput>div>div,
.stTextArea>div>textarea,
.stSelectbox>div>div {
    background-color: #ffffff;
    color: #111;
    border: 1px solid #ccc;
    border-radius: 4px;
}

/* [4] 메인 이미지 영역 (증명사진 프레임) */
.id-photo-container {
    border: 1px solid #ccc;
    background-color: #eaeaea;
    padding: 12px;
    margin-bottom: 20px;
}

.id-photo-frame {
    width: 100%;
    height: 420px;
    background-color: #dcdcdc;
    display: flex;
    align-items: center;
    justify-content: center;
    border: 1px solid #bbb;
}

/* [5] 실행 버튼 (중립 강조) */
.action-btn-container button {
    background-color: #2c6bed !important;
    color: #ffffff !important;
    font-size: 16px !important;
    font-weight: 600 !important;
    border-radius: 4px !important;
    height: 48px;
    border: none !important;
}

.action-btn-container button:hover {
    background-color: #1f55c8 !important;
}

/* [6] 탭 스타일 */
.stTabs [data-baseweb="tab-list"] {
    background-color: #f5f6f7;
}

.stTabs [data-baseweb="tab"] {
    background-color: #eaeaea;
    border: 1px solid #ccc;
    color: #555;
}

.stTabs [aria-selected="true"] {
    background-color: #ffffff !important;
    color: #111 !important;
    font-weight: 600;
}
</style>
""", unsafe_allow_html=True)

# --- 2. 세션 상태 초기화 (워크플로우 메모리) ---
if "step" not in st.session_state: 
    st.session_state.step = 1
    
if "generated_faces" not in st.session_state: 
    st.session_state.generated_faces = []
    
if "selected_face_url" not in st.session_state: 
    st.session_state.selected_face_url = None
    
if "final_character_url" not in st.session_state: 
    st.session_state.final_character_url = None
    
if "scene_url" not in st.session_state: 
    st.session_state.scene_url = None


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
