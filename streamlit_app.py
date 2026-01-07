import streamlit as st
import backend
import time

# 1. secrets.toml 파일에서 먼저 찾아봄
if "RUNCOMFY_API_KEY" in st.secrets:
    api_key = st.secrets["RUNCOMFY_API_KEY"]
    deployment_id = st.secrets["DEPLOYMENT_ID"]
    # st.sidebar.success("API Key가 로드되었습니다! ✅")
else:
    # 2. 파일이 없으면 입력창 표시
    api_key = st.sidebar.text_input("RunComfy API Key", type="password")
    deployment_id = st.sidebar.text_input("Deployment ID")
    if not api_key or not deployment_id:
        st.sidebar.warning("API Key와 Deployment ID를 입력해주세요.")
        st.stop() # 키가 없으면 앱 실행 중단

# =========================================================
# 1. 페이지 설정 및 디자인
# =========================================================
st.set_page_config(
    page_title="Neon Darkroom: Director's Suite",
    page_icon="🎬",
    layout="wide",
    initial_sidebar_state="collapsed" # 사이드바 숨김
)

# --- 2. CSS 매직: 와이드 콘솔 디자인 ---
# st.markdown("""
#     <style>
#     @import url('https://fonts.googleapis.com/css2?family=Rajdhani:wght@500;700&family=Roboto+Mono:wght@400;700&display=swap');

#     /* [1] 배경 및 폰트 */
#     .stApp {
#         background-color: #050505;
#         background-image: radial-gradient(#151515 1px, transparent 1px);
#         background-size: 30px 30px;
#         color: #e0e0e0;
#         font-family: 'Rajdhani', sans-serif;
#     }

#     /* [2] 상단 컨트롤 패널 (Dashboard) */
#     .dashboard-container {
#         background: linear-gradient(180deg, #161616 0%, #0a0a0a 100%);
#         border-bottom: 2px solid #333;
#         padding: 20px;
#         margin-top: -50px; /* Streamlit 기본 여백 제거 */
#         margin-left: -5rem; margin-right: -5rem; /* 좌우 꽉 채우기 */
#         padding-left: 5rem; padding-right: 5rem;
#         box-shadow: 0 10px 20px rgba(0,0,0,0.8);
#         margin-bottom: 20px;
#     }
#     .control-label {
#         color: #888;
#         font-size: 12px;
#         letter-spacing: 1px;
#         margin-bottom: 5px;
#     }
    
#     /* 입력 필드 커스텀 */
#     .stTextInput>div>div, .stSelectbox>div>div, .stNumberInput>div>div {
#         background-color: #222 !important;
#         border: 1px solid #444 !important;
#         color: #FFD700 !important; /* Gold Text */
#         border-radius: 4px;
#     }
    
#     /* [3] 메인 뷰포트 (중앙) */
#     .viewport-frame {
#         border: 2px solid #333;
#         border-radius: 12px;
#         background-color: #000;
#         min-height: 500px;
#         position: relative;
#         display: flex;
#         align-items: center;
#         justify-content: center;
#         box-shadow: 0 0 30px rgba(0, 255, 255, 0.05);
#     }
    
#     /* [4] 액션 버튼 (하단 중앙 배치) */
#     .stButton>button {
#         background: linear-gradient(90deg, #FFD700, #ffaa00) !important;
#         color: #000 !important;
#         border: none;
#         font-weight: bold;
#         font-size: 20px;
#         padding: 15px 40px;
#         text-transform: uppercase;
#         letter-spacing: 2px;
#         transition: all 0.3s;
#         width: 100%;
#         border-radius: 8px;
#     }
#     .stButton>button:hover {
#         box-shadow: 0 0 20px #FFD700;
#         transform: scale(1.02);
#     }

#     /* 필름 스트립 */
#     .film-strip {
#         display: flex;
#         gap: 10px;
#         overflow-x: auto;
#         padding: 20px 0;
#         border-top: 1px dashed #333;
#         margin-top: 30px;
#     }
    
#     /* 탭 스타일 재정의 (상단 패널용) */
#     .stTabs [data-baseweb="tab-list"] { background-color: transparent; }
#     .stTabs [data-baseweb="tab"] { color: #666; }
#     .stTabs [aria-selected="true"] { color: #FFD700 !important; border-bottom-color: #FFD700 !important; }
    
#     </style>
# """, unsafe_allow_html=True)

# =========================================================
# 2. 세션 상태 (데이터 저장소) 초기화
# =========================================================
if "step" not in st.session_state: 
    st.session_state.step = 1
if "generated_faces" not in st.session_state: 
    st.session_state.generated_faces = []
if "selected_face_url" not in st.session_state: 
    st.session_state.selected_face_url = None
if "final_character_url" not in st.session_state: 
    st.session_state.final_character_url = None
if "processing" not in st.session_state: 
    st.session_state.processing = False

# =========================================================
# [SECTION 1] CHARACTER PROFILE
# =========================================================

# st.markdown(f"### STEP 1 : 👤 CHARACTER PROFILE")

# tab1, tab2 = st.tabs(["EYES TYPE","LIPS TYPE"])

# pm_options = {}

# with tab1:
#     col_c, col_s = st.columns(2)

    # with col_c:
    #     pm_options["EYES TYPE"] = st.selectbox("Eyes Color", ["Albino", "Amber", "Blue", "Brown", "Green", "Gray", "Hazel", "Heterochromia", "Red", "Violet"])
    #     pm_options["EYES TYPE"] = st.selectbox("Eyes Shape", ["Almond Eyes Shape","Asian Eyes Shape","Close-Set Eyes Shape","Deep Set Eyes Shape","Downturned Eyes Shape","Double Eyelid Eyes Shape","Hooded Eyes Shape","Monolid Eyes Shape","Oval Eyes Shape","Protruding Eyes Shape","Round Eyes Shape","Upturned Eyes Shape"])


# col1, col2, col3, col4, col5 = st.columns(5)

# with col1:
#     st.markdown(
#         """
#         <div style="margin-bottom:0px; font-weight:600;">
#             Gender & Nationality
#         </div>
#         <hr style="margin-top:4px; margin-bottom:8px;">
#         """,
#         unsafe_allow_html=True
#     )
#     pm_options["Face Shape"] = st.selectbox("Gender", ["Man","Woman"])
#     pm_options["Face Shape"] = st.selectbox("Nationality", ["Chinese","Japanese","Korean","South Korean","Indian","Saudi","British","French","German","Italian","Spanish","American","Canadian","Brazilian","Mexican","Argentine","Egyptian","South African","Nigerian","Kenyan","Moroccan","Australian","New Zealander","Fijian","Samoan","Tongan"])

# with col2:
#     st.markdown(
#         """
#         <div style="margin-bottom:0px; font-weight:600;">
#             Eyes Type
#         </div>
#         <hr style="margin-top:4px; margin-bottom:8px;">
#         """,
#         unsafe_allow_html=True
#     )
#     pm_options["Eyes Color"] = st.selectbox("Eyes Color", ["Albino", "Amber", "Blue", "Brown", "Green", "Gray", "Hazel", "Heterochromia", "Red", "Violet"])
#     pm_options["Eyes Shape"] = st.selectbox("Eyes Shape", ["Almond Eyes Shape","Asian Eyes Shape","Close-Set Eyes Shape","Deep Set Eyes Shape","Downturned Eyes Shape","Double Eyelid Eyes Shape","Hooded Eyes Shape","Monolid Eyes Shape","Oval Eyes Shape","Protruding Eyes Shape","Round Eyes Shape","Upturned Eyes Shape"])

# with col3:
#     st.markdown(
#         """
#         <div style="margin-bottom:0px; font-weight:600;">
#             Lips Type
#         </div>
#         <hr style="margin-top:4px; margin-bottom:8px;">
#         """,
#     unsafe_allow_html=True
#     )

#     pm_options["Lips Color"] = st.selectbox("Lips Color", ["Berry Lips","Black Lips","Blue Lips","Brown Lips","Burgundy Lips","Coral Lips","Glossy Red Lips","Mauve Lips","Orange Lips","Peach Lips","Pink Lips","Plum Lips","Purple Lips","Red Lips","Yellow Lips"])
#     pm_options["Lips Shape"] = st.selectbox("Lips Shape", ["Full Lips","Thin Lips","Plump Lips","Small Lips","Large Lips","Wide Lips","Round Lips","Heart-shaped Lips","Cupid's Bow Lips"])

# with col4:
#     st.markdown(
#         """
#         <div style="margin-bottom:0px; font-weight:600;">
#             Face Type
#         </div>
#         <hr style="margin-top:4px; margin-bottom:8px;">
#         """,
#         unsafe_allow_html=True
#     )
#     pm_options["Face Shape"] = st.selectbox("Face Shape", ["Oval","Round","Square","Heart","Diamond","Triangle","Inverted Triangle","Pear","Rectangle","Oblong","Long"])

# with col5:
#     st.markdown(
#         """
#         <div style="margin-bottom:0px; font-weight:600;">
#             Hair Type
#         </div>
#         <hr style="margin-top:4px; margin-bottom:8px;">
#         """,
#         unsafe_allow_html=True
#     )
#     pm_options["Hair Style"] = st.selectbox("Hair Style", ["Bald","Buzz","Crew","Pixie","Bob","Long bob","Long straight","Wavy","Curly","Afro","Faded afro","Braided","Box braids","Cornrows","Dreadlocks","Pigtails","Ponytail","High ponytail","Bangs","Curtain bangs","Side-swept bangs","Mohawk","Faux hawk","Undercut","Pompadour","Quiff","Top Knot","Bun","Updo"])
#     pm_options["Hair Style"] = st.selectbox("Hair Color", ["Black","Jet Black","Blonde","Platinum","Brown","Chestnut","Auburn","Red","Strawberry","Gray","Silver","White","Salt and pepper"])
#     pm_options["Hair Style"] = st.selectbox("Hair Length", ["Short","Medium","Long"])

# =========================================================
# 4. 메인 화면 (탭 구성)
# =========================================================
st.header(f"🎬 Cinematic Storyboard AI")

tab1, tab2, tab3, tab4 = st.tabs([
    "Step1 | 👤 CHARACTER PROFILE", 
    "Step2 | 👗 CLOTHING TRANSLATE", 
    "Step3 | 🏞️ BACKGROUND GENERATION", 
    "Step4 | 📝 SCRIPT"])

pm_options = {}
base_prompt = "Gray background, White t-shirt, 8k, highly detailed, photorealistic" # 기본값 설정
width = 896
height = 1152

# ---------------------------------------------------------
# [TAB 1] 배우 캐스팅 (얼굴 생성)
# ---------------------------------------------------------
with tab1:
    # col_left, divider, col_right = st.columns([1, 0.3, 2]).
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
    
            # [ACTION] 생성 버튼
            st.markdown("<br>", unsafe_allow_html=True)
            if st.button("🚀 CASTING START (Generate Faces)", use_container_width=True):
                if not api_key or not deployment_id:
                    st.error("API Key와 ID를 확인해주세요!")
                else:
                    with st.spinner("Casting in progress... (Switch Mode: 1)"):
                        # [Backend] Switch=1 로 얼굴 생성 요청
                        imgs = backend.generate_faces(base_prompt, pm_options, api_key, deployment_id, 896, 1152)
                        if imgs:
                            st.session_state.generated_faces = imgs
                            st.rerun()
                
    
        with col_left:
            # [PREVIEW] 생성된 이미지 선택
            with col_preview:
                st.markdown("#### Casting Result")
                if st.session_state.generated_faces:
                    # 2열로 이미지 나열
                    cols = st.columns(2)
                    for i, img_url in enumerate(st.session_state.generated_faces):
                        with cols[i % 2]:
                            st.image(img_url, use_container_width=True)
                            if st.button(f"✅ Select Actor {i+1}", key=f"sel_{i}"):
                                st.session_state.selected_face_url = img_url
                                st.session_state.step = 2 # 다음 단계로 이동
                                st.rerun()
                else:
                    st.info("좌측 설정 후 'CASTING START'를 눌러주세요.")

    else:
        st.success("✅ Actor Selected")
        if st.session_state.selected_face_url:
            st.image(st.session_state.selected_face_url, width=150, caption="Main Actor")
            
        # st.markdown('<div class="viewport-frame">', unsafe_allow_html=True)
        
        # # 이미지 표시 로직
        # display_img = None
        # overlay_text = "STANDBY"

        # # 단계별 뷰포트 이미지 표시 로직
        # if st.session_state.step == 1:
        #      overlay_text = "READY TO CAST"
        # elif st.session_state.step == 2 and st.session_state.generated_faces:
        #     # 가장 마지막에 생성된 것 중 첫번째 보여주기 (임시)
        #     display_img = st.session_state.generated_faces[0]
        #     overlay_text = "REVIEWING..."
        # elif st.session_state.step == 3:
        #     display_img = st.session_state.selected_face_url
        #     overlay_text = "REFERENCE LOADED"
        # elif st.session_state.step == 4:
        #     display_img = st.session_state.final_character_url
        #     overlay_text = "FINAL RENDER"
        
        # # if st.session_state.step == 1 and st.session_state.generated_faces:
        # #     display_img = st.session_state.generated_faces[-1]
        # #     overlay_text = "CASTING COMPLETE"
        # # elif st.session_state.step == 3: # 의상 단계
        # #     display_img = st.session_state.selected_face_url
        # #     overlay_text = "REFERENCE LOADED"
        # # elif st.session_state.step == 4:
        # #     display_img = st.session_state.final_character_url
        # #     overlay_text = "FINAL RENDER"
    
        # if display_img:
        #     st.image(display_img, use_container_width=True)
        # else:
        #     st.markdown(f"<h2 style='color:#333'>{overlay_text}</h2>", unsafe_allow_html=True)
            
        # st.markdown('</div>', unsafe_allow_html=True)

# ---------------------------------------------------------
# [TAB 2] 의상 피팅 (전신 생성)
# ---------------------------------------------------------
with tab2:
    if st.session_state.step == 2:
        st.markdown("### 2. Wardrobe & Styling")
        
        col_face, col_outfit, col_result = st.columns([1, 1, 1])
        
        with col_face:
            st.markdown("#### Reference Actor")
            st.image(st.session_state.selected_face_url, use_container_width=True)
            st.caption("이 얼굴을 유지하며 의상을 입힙니다.")
            
        with col_outfit:
            st.markdown("#### Outfit Description")
            outfit_prompt = st.text_area("Describe the outfit", 
                                       "White t-shirt, blue jeans, yellow sneakers, standing pose, full body shot", 
                                       height=200)
            
            st.markdown("<br>", unsafe_allow_html=True)
            if st.button("👗 APPLY OUTFIT", use_container_width=True):
                with st.spinner("Fitting room... (Switch Mode: 2)"):
                    # [Backend] Switch=2 로 의상 합성 요청
                    res = backend.generate_full_body(st.session_state.selected_face_url, outfit_prompt, api_key, deployment_id)
                    if res:
                        st.session_state.final_character_url = res[0]
                        st.rerun()
                        
        with col_result:
            st.markdown("#### Fitted Result")
            if st.session_state.final_character_url:
                st.image(st.session_state.final_character_url, use_container_width=True)
                if st.button("✨ CONFIRM & GO TO SET", use_container_width=True):
                    st.session_state.step = 3 # 다음 단계로 이동
                    st.rerun()
            else:
                st.info("의상 프롬프트를 입력하고 버튼을 누르세요.")
                
    elif st.session_state.step > 2:
         st.success("✅ Costume Fitted")
         if st.session_state.final_character_url:
            st.image(st.session_state.final_character_url, width=150, caption="Final Character")
    elif st.session_state.step < 2:
        st.warning("Step 1을 먼저 완료해주세요.")

# ---------------------------------------------------------
# [TAB 3] 씬 제작 (스토리보드)
# ---------------------------------------------------------
with tab3:
    if st.session_state.step == 3:
        st.markdown("### 3. Final Scene Composition")
        
        col_assets, col_prompt, col_final = st.columns([1, 1, 2])
        
        with col_assets:
            st.markdown("#### Assets")
            st.image(st.session_state.final_character_url, width=150, caption="Character 1")
            
            # 배경 이미지 입력 (URL 방식 - 데모용)
            bg_url = st.text_input("Background Image URL", 
                                 "https://images.unsplash.com/photo-1579546929518-9e396f3cc809?auto=format&fit=crop&w=1000&q=80",
                                 help="배경으로 쓸 이미지 주소를 넣으세요.")
            if bg_url:
                st.image(bg_url, width=150, caption="Background")
                
        with col_prompt:
            st.markdown("#### Director's Note")
            story_prompt = st.text_area("Scene Description", 
                                      "A boy and a girl are walking side by side to the right of the camera.",
                                      height=150)
            
            st.info("💡 Tip: Character 2가 없으면 Character 1이 복제되어 사용됩니다.")
            
            st.markdown("<br>", unsafe_allow_html=True)
            if st.button("🎬 ACTION! (Generate Scene)", use_container_width=True):
                with st.spinner("Shooting the scene... (Switch Mode: 3)"):
                    # [Backend] Switch=3 으로 스토리보드 요청
                    # Char 2는 현재 없으므로 None 전달 (백엔드에서 처리)
                    final_imgs = backend.final_storyboard(
                        st.session_state.final_character_url, # Char 1
                        None,                                 # Char 2 (None)
                        bg_url,                               # Background
                        story_prompt,
                        api_key,
                        deployment_id
                    )
                    
                    if final_imgs:
                        st.session_state.final_scene_url = final_imgs[0]
                        st.rerun()

        with col_final:
            st.markdown("#### 🏁 Final Cut")
            if st.session_state.final_scene_url:
                st.image(st.session_state.final_scene_url, use_container_width=True)
                st.balloons()
                st.success("Wokflow Complete!")
            else:
                st.info("배경과 지문을 입력하고 큐 사인을 주세요.")
                
    elif st.session_state.step < 3:
        st.warning("이전 단계를 먼저 완료해주세요.")


# # =========================================================
# # [ACTION AREA] 하단 컨트롤러
# # =========================================================
# st.markdown("---")
# st.markdown("### 🎬 ACTION")

# # Step 1: 생성하기
# if st.session_state.step == 1:
#     # st.info("Define character profile above and start casting.")
#     # if st.button("RUN CASTING\n(GENERATE)", use_container_width=True):
#     if st.button("🚀 캐릭터 얼굴 생성 시작", use_container_width=True):
#         # if not api_key:
#         #     st.error("⚠️ API KEY is missing! Check sidebar.")
#         # else:
#             # with st.spinner("CASTING ACTORS..."):
#         with st.spinner("ComfyUI가 열심히 그림을 그리고 있습니다... (약 20~40초 소요)"):

#             # backend 함수 호출
#             imgs = backend.generate_faces(base_prompt, 
#                                           pm_options, 
#                                           api_key, 
#                                           deployment_id, 
#                                           width=width, 
#                                           height=height, 
#                                           batch_size=batch_size)
#             if imgs:
#                 st.session_state.generated_faces = imgs
#                 st.session_state.step = 2
#                 st.rerun()
#             else:
#                 st.error("Failed to generate images. Check logs.")

# # Step 2: 선택하기 (새로 구현됨)
# elif st.session_state.step == 2:
#     st.success("Select an actor from the Film Strip below.")
#     # 이미지 갤러리 형태로 표시
#     if st.session_state.generated_faces:
#         cols = st.columns(len(st.session_state.generated_faces))
#         for idx, img_url in enumerate(st.session_state.generated_faces):
#             with cols[idx]:
#                 st.image(img_url, use_container_width=True)
#                 if st.button(f"✅ SELECT ACTOR #{idx+1}", key=f"sel_{idx}"):
#                     st.session_state.selected_face_url = img_url
#                     st.session_state.step = 3
#                     st.rerun()
                    
#     st.markdown("<br>", unsafe_allow_html=True)
#     if st.button("↺ RESTART CASTING", use_container_width=True):
#         st.session_state.step = 1
#         st.rerun()

#     # if st.button("↺ RESTART", use_container_width=True):
#     #     st.session_state.step = 1
#     #     st.rerun()

# # Step 3: 의상 입히기
# elif st.session_state.step == 3:
#     col_input, col_action = st.columns([3, 1])
#     with col_input:
#         outfit = st.text_area("WARDROBE DESCRIPTION", "White t-shirt, blue jeans, casual sneakers, standing pose")
#     with col_action:
#         st.markdown("<br>", unsafe_allow_html=True)
#         if st.button("APPLY COSTUME", use_container_width=True):
#             with st.spinner("FITTING... (Img2Img Processing)"):
#                 res = backend.generate_full_body(st.session_state.selected_face_url, outfit, api_key, deployment_id)
#                 if res:
#                     st.session_state.final_character_url = res[0] # 결과가 리스트라고 가정
#                     st.session_state.step = 4
#                     st.rerun()
    
#     # outfit = st.text_area("WARDROBE", "White t-shirt, jeans, sneakers")
#     # if st.button("APPLY COSTUME", use_container_width=True):
#     #     with st.spinner("FITTING..."):
#     #         res = backend.generate_full_body(st.session_state.selected_face_url, outfit, api_key, deployment_id)
#     #         if res:
#     #             st.session_state.final_character_url = res[-1]
#     #             st.session_state.step = 4
#     #             st.rerun()

# # Step 4: 완료
# elif st.session_state.step == 4:
#     st.balloons()
#     st.success("Scene generation complete!")
#     if st.button("🎬 START NEW PROJECT", use_container_width=True):
#         st.session_state.step = 1
#         st.session_state.generated_faces = []
#         st.session_state.selected_face_url = None
#         st.rerun()
    
#     # st.balloons()
#     # st.markdown("### ✅ SCENE CUT")
#     # if st.button("NEW PROJECT", use_container_width=True):
#     #     st.session_state.step = 1
#     #     st.rerun()

# # -------------------------------------------------


# # 1-2. 메인 컨트롤 패널 (여기가 사이드바를 대체함)
# st.markdown(f"### 🕹️ CONTROL CONSOLE | MODE: STEP {st.session_state.step}")

# # 탭을 사용하여 공간 절약
# tab1, tab2, tab3, tab4 = st.tabs(["👤 CHARACTER PROFILE", "👗 CLOTHING TRANSLATE", "🏞️ BACKGROUND GENERATION", "📝 SCRIPT"])

# pm_options = {}

# with tab1:
#     # 캐릭터 설정 (4열 배치)
#     col_g, col_a, col_n, col_b = st.columns(4)
    
#     with col_g: 
#         pm_options["gender"] = st.selectbox("GENDER", ["Man", "Woman"])
        
#     with col_a: 
#         pm_options["age"] = st.number_input("AGE", 10, 80, 25)
        
#     with col_n: 
#         pm_options["nationality"] = st.selectbox("ORIGIN", ["Korean", "American", "British", "French"])
        
#     with col_b: 
#         pm_options["body_type"] = st.selectbox("BODY", ["Fit", "Slim", "Muscular", "Average"])

# with tab2:
#     # 기술 설정 (3열 배치)
#     col_r, col_l, col_q = st.columns(3)
#     with col_r: 
#         ratio = st.selectbox("ASPECT RATIO", ["Cinematic (16:9)", "Portrait (9:16)", "Square (1:1)"])
#         if "16:9" in ratio: width, height = 1152, 896
#         elif "9:16" in ratio: width, height = 896, 1152
#         else: width, height = 1024, 1024
#     with col_l: st.select_slider("LIGHTING MOOD", ["Dark", "Cinematic", "Bright"], value="Cinematic")
#     with col_q: batch_size = st.slider("BATCH SIZE", 1, 4, 2)

# with tab3:
#     # 프롬프트 입력
#     base_prompt = st.text_input("LOGLINE / PROMPT", "Cinematic shot, highly detailed masterpiece, 8k resolution")

# st.markdown('</div>', unsafe_allow_html=True) # End Dashboard


# # =========================================================
# # [SECTION 2] MAIN VIEWPORT (중앙 화면)
# # =========================================================

# # 레이아웃: 왼쪽(뷰포트) - 오른쪽(작업 버튼)
# col_view, col_action = st.columns([3, 1])

# with col_view:
#     st.markdown('<div class="viewport-frame">', unsafe_allow_html=True)
    
#     # 이미지 표시 로직
#     display_img = None
#     overlay_text = "STANDBY"
    
#     if st.session_state.step == 1 and st.session_state.generated_faces:
#         display_img = st.session_state.generated_faces[-1]
#         overlay_text = "CASTING COMPLETE"
#     elif st.session_state.step == 3: # 의상 단계
#         display_img = st.session_state.selected_face_url
#         overlay_text = "REFERENCE LOADED"
#     elif st.session_state.step == 4:
#         display_img = st.session_state.final_character_url
#         overlay_text = "FINAL RENDER"

#     if display_img:
#         st.image(display_img, use_container_width=True)
#     else:
#         st.markdown(f"<h2 style='color:#333'>{overlay_text}</h2>", unsafe_allow_html=True)
        
#     st.markdown('</div>', unsafe_allow_html=True)

# with col_action:
#     st.markdown("### 🎬 ACTION")
#     st.markdown("---")
    
#     # 단계별 액션 버튼 로직
#     if st.session_state.step == 1:
#         st.info("Define character profile above and start casting.")
#         if st.button("RUN CASTING\n(GENERATE)", use_container_width=True):
#             if not api_key:
#                 st.error("API KEY REQUIRED")
#             else:
#                 with st.spinner("CASTING ACTORS..."):
#                     imgs = backend.generate_faces(base_prompt, pm_options, api_key, deployment_id, width, height, batch_size)
#                     if imgs:
#                         st.session_state.generated_faces = imgs
#                         st.session_state.step = 2
#                         st.rerun()

#     elif st.session_state.step == 2:
#         st.success("Select an actor from the Film Strip below.")
#         if st.button("↺ RESTART", use_container_width=True):
#             st.session_state.step = 1
#             st.rerun()

#     elif st.session_state.step == 3:
#         outfit = st.text_area("WARDROBE", "White t-shirt, jeans, sneakers")
#         if st.button("APPLY COSTUME", use_container_width=True):
#             with st.spinner("FITTING..."):
#                 res = backend.generate_full_body(st.session_state.selected_face_url, outfit, api_key, deployment_id)
#                 if res:
#                     st.session_state.final_character_url = res[-1]
#                     st.session_state.step = 4
#                     st.rerun()
                    
#     elif st.session_state.step == 4:
#         st.balloons()
#         st.markdown("### ✅ SCENE CUT")
#         if st.button("NEW PROJECT", use_container_width=True):
#             st.session_state.step = 1
#             st.rerun()

# # =========================================================
# # [SECTION 3] FILM STRIP (하단 갤러리)
# # =========================================================
# st.markdown("### 🎞️ RUSHES (FILM STRIP)")

# if st.session_state.generated_faces:
#     cols = st.columns(len(st.session_state.generated_faces))
#     for idx, img in enumerate(st.session_state.generated_faces):
#         with cols[idx]:
#             # 선택 효과
#             border = "2px solid #FFD700" if img == st.session_state.selected_face_url else "1px solid #333"
#             st.markdown(f"<div style='border:{border}; padding:2px'>", unsafe_allow_html=True)
#             st.image(img, use_container_width=True)
#             st.markdown("</div>", unsafe_allow_html=True)
            
#             if st.button(f"SELECT #{idx+1}", key=f"sel_{idx}"):
#                 st.session_state.selected_face_url = img
#                 st.session_state.step = 3
#                 st.rerun()
# else:
#     st.caption("No footage available.")
