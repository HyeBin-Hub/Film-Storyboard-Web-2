import streamlit as st


# =====================================
# Preset Results (Testing Only)
# =====================================

def apply_preset_2a_results():
    
    if not ENABLE_PRESET_2A_RESULTS:
        return

    preset_boy_url = (
        "https://serverless-api-storage.runcomfy.net/"
        "deployment_requests/e3b5d793-e111-49fe-850f-4b0e08424dd2/"
        "output/character_appearance_boy_3063348797_00001_.png"
    )

    preset_girl_url = (
        "https://serverless-api-storage.runcomfy.net/"
        "deployment_requests/94b10bea-a4e8-4f66-9d18-603ff35e325e/"
        "output/character_appearance_girl_667573668_00001_.png"
    )

    if not st.session_state.get("face_result_image_c1"):
        st.session_state["face_result_image_c1"] = preset_boy_url
        st.session_state["face_result_filename_c1"] = (
            "character_appearance_boy_3063348797_00001_.png"
        )

    if not st.session_state.get("face_result_image_c2"):
        st.session_state["face_result_image_c2"] = preset_girl_url
        st.session_state["face_result_filename_c2"] = (
            "character_appearance_girl_667573668_00001_.png"
        )
        
def apply_preset_2b_results():
    if not ENABLE_PRESET_2B_RESULTS:
        return

    preset_boy_outfit_url = (
        "https://cdn.phototourl.com/free/2026-08-10-cc0d90a8-b115-4c15-bd6f-57d30a16bbd9.png"
    )

    preset_girl_outfit_url = (
        "https://cdn.phototourl.com/free/2026-08-10-fa2ccad6-deec-4063-9bd5-b4c9f742c285.png"
    )

    if not st.session_state.get("body_result_image_c1"):
        st.session_state["body_result_image_c1"] = preset_boy_outfit_url
        st.session_state["body_result_filename_c1"] = "ComfyUI_01135_.png"

    if not st.session_state.get("body_result_image_c2"):
        st.session_state["body_result_image_c2"] = preset_girl_outfit_url
        st.session_state["body_result_filename_c2"] = "换装_00026_.png"


def apply_preset_step3_results():
    if not ENABLE_PRESET_STEP3_RESULTS:
        return

    if st.session_state.get("scene_candidates"):
        return

    preset_scene_urls = [
        (
            "Scene 1",
            "https://serverless-api-storage.runcomfy.net/"
            "deployment_requests/c48de276-8299-4f96-ba30-5f3deed58153/"
            "output/scene_3123289005_00001_.png",
            "scene_3123289005_00001_.png",
        ),
        (
            "Scene 2",
            "https://cdn.phototourl.com/free/2026-08-10-98c475bc-901c-4750-9b3d-fffeafd98a13.png",
            "scene2_custom.png",
        ),
        (
            "Scene 3",
            "https://serverless-api-storage.runcomfy.net/"
            "deployment_requests/c48de276-8299-4f96-ba30-5f3deed58153/"
            "output/scene_3123289005_00003_.png",
            "scene_3123289005_00003_.png",
        ),
    ]

    preset_candidates = [
        {
            "label": label,
            "image": image_url,
            "url": image_url,
            "filename": filename,
        }
        for label, image_url, filename in preset_scene_urls
    ]

    st.session_state["scene_candidates"] = preset_candidates

    first_scene = preset_candidates[0]
    st.session_state["scene_result_image"] = first_scene["image"]
    st.session_state["scene_result_filename"] = first_scene["filename"]
    st.session_state["scene_selected_label"] = first_scene["label"]


def apply_preset_step4_results():
    if not ENABLE_PRESET_STEP4_RESULTS:
        return

    if st.session_state.get("camera_refined_result_image"):
        return

    preset_step4_result_url = (
        "https://i.postimg.cc/XqnCWSTw/image-(7).png"
    )

    st.session_state["camera_refined_candidates"] = [
        {
            "label": "Camera Refined Scene 1",
            "image": preset_step4_result_url,
            "url": preset_step4_result_url,
            "filename": "step4_preset_image.png",
        }
    ]

    st.session_state["camera_refined_result_image"] = (
        preset_step4_result_url
    )
    st.session_state["camera_refined_result_filename"] = (
        "step4_preset_image.png"
    )
    st.session_state["camera_refined_selected_label"] = (
        "Camera Refined Scene 1"
    )
