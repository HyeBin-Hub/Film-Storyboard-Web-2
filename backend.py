import requests
import time
import base64 

BASE_URL = "https://api.runcomfy.net/prod/v1"
DUMMY_IMAGE = "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8/5+hHgAHggJ/PchI7wAAAABJRU5ErkJggg=="

def _url_to_base64(url):
    try:
        response = requests.get(url)
        response.raise_for_status()
        # 바이너리 데이터를 base64로 인코딩
        encoded_string = base64.b64encode(response.content).decode('utf-8')
        # ComfyUI가 이해하는 형식(prefix)을 붙여줌
        return f"data:image/png;base64,{encoded_string}"
      
    except Exception as e:
        print(f"❌ 이미지 변환 실패: {e}")
        return None

# 내부 함수도 api_key와 deployment_id를 인자로 받도록 수정
def _run_inference(overrides, api_key, deployment_id):
    
    if not api_key or not deployment_id:
        print("❌ API Key 또는 Deployment ID가 없습니다.")
        return None

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    
    payload = {"overrides": overrides}
    
    try:
      # 1. inference 요청
        print("🚀 Sending Inference Request...")
        res = requests.post(
            f"{BASE_URL}/deployments/{deployment_id}/inference",
            headers=headers,
            json=payload
        )
        res.raise_for_status()
        request_id = res.json().get("request_id")
        print(f"✅ Request Sent! ID: {request_id}")

        retry_count = 0
        max_retries = 120 # 약 6분 대기
      # 2. 상태 풀링
        while retry_count < max_retries:
            time.sleep(3)

            try:
                status_res = requests.get(f"{BASE_URL}/deployments/{deployment_id}/requests/{request_id}/status", headers=headers)
                status_res.raise_for_status()
                
                status_data = status_res.json() # [수정] 변수에 할당
                status = status_data.get("status", "").lower()
    
                print(f"⏳ Status: {status}")
                
                if status == "completed": 
                    break
                elif status in ["failed", "error"]: 
                    # [수정] status_data 변수 사용
                    print(f"❌ 생성 실패: {status_data.get('error_message', 'Unknown error')}")
                    return None
                    
            except Exception as e:
                print(f"⚠️ Polling connection issue: {e}, retrying...")
                time.sleep(2)
                continue
              
      # 3. 결과 가져오기 
        result_res = requests.get(f"{BASE_URL}/deployments/{deployment_id}/requests/{request_id}/result", headers=headers)
        result_res.raise_for_status()
      
        return result_res.json().get("outputs", {})

    except Exception as e:
        print(f"❌ API Error: {e}")
        return None
    retry_count += 1


def _extract_images(outputs, target_node_id):
  
    image_urls = []
  
    if target_node_id in outputs:
        for img in outputs[target_node_id].get("images", []):
            if img.get("url"): 
                image_urls.append(img["url"])
        return image_urls
      
    else:
        print(f"⚠️ 노드 {target_node_id}번의 결과물을 찾을 수 없습니다. (현재 노드: {list(outputs.keys())})")
        return []

# =========================================================
# [메인 기능 함수]
# =========================================================

# --- Step 1: Portrait Generation ---
def generate_faces(prompt_text, pm_options, api_key, deployment_id, width, height, batch_size=4):
    overrides = {        
        "56": { "inputs": { "select": 1 } },
        "12": {"inputs": {"text": prompt_text}},
        "3": {"inputs": {
            "age": pm_options.get("age", 25),
            "gender": pm_options.get("Gender", "Woman"), 
            "nationality_1": pm_options.get("Nationality", "Korean"),
            "body_type": pm_options.get("Body Type", "Fit"),
            "eyes_color": pm_options.get("Eyes Color", "Brown"),
            "eyes_shape": pm_options.get("Eyes Shape", "Round Eyes Shape"),
            "lips_color": pm_options.get("Lips Color", "Red Lips"),
            "lips_shape": pm_options.get("Lips Shape", "Regular"),
            "face_shape": pm_options.get("Face Shape", "Oval"),
            "hair_style": pm_options.get("Hair Style", "Long straight"),
            "hair_color": pm_options.get("Hair Color", "Black"),
            "hair_length": pm_options.get("Hair Length", "Long"),
        }},
        "13" : {"inputs":{"width": width, "height": height, "batch_size": batch_size}},

        # ✅ [핵심] Step 2, 3의 필수 입력 노드에 더미 이미지 주입 (에러 방지)
        "32": { "inputs": { "image": DUMMY_IMAGE } }, # Step 2 LoadImage
        "42": { "inputs": { "image": DUMMY_IMAGE } }, # Step 3 LoadImage 1
        "43": { "inputs": { "image": DUMMY_IMAGE } }, # Step 3 LoadImage 2
        "44": { "inputs": { "image": DUMMY_IMAGE } }, # Step 3 LoadImage 3 (배경)

        # "11": {"inputs": {"steps": 25}},
        # "85": {"inputs": {"image": DUMMY_IMAGE_BASE64}},
    }

    outputs = _run_inference(overrides, api_key, deployment_id)
  
    if not outputs: 
      return []

    return _extract_images(outputs, "15")
  
# --- Step 2: Clothing Translate ---
def generate_full_body(face_image_url, outfit_keywords, api_key, deployment_id):
    
    print("🔄 이미지를 서버로 전송하기 위해 변환 중...")
    base64_image = _url_to_base64(face_image_url)
    
    if not base64_image:
        print("❌ 이미지 변환에 실패하여 작업을 중단합니다.")
        return []

    overrides = {
        "56": { "inputs": { "select": 2 } },
        "20": {"inputs": {"text": outfit_keywords}},
        "32": { "inputs": { "image": base64_image } },
        "14": {"inputs": {"width": 896, "height": 1152, "batch_size": 1}}, 

        # ✅ Step 3의 필수 입력 노드에 더미 이미지 주입
        "42": { "inputs": { "image": DUMMY_IMAGE } },
        "43": { "inputs": { "image": DUMMY_IMAGE } },
        "44": { "inputs": { "image": DUMMY_IMAGE } },
      # "9": {"inputs": {"steps": 30, "seed": 793834637229542}} 
        }
    
    outputs = _run_inference(overrides, api_key, deployment_id)
  
    if not outputs: 
      return []

    return _extract_images(outputs, "15")

# --- Step 3: Final Storyboard ---
def final_storyboard(face_image_url_1, face_image_url_2, background_image_url_1, story_prompt, api_key, deployment_id):
    
    print("🔄 이미지를 서버로 전송하기 위해 변환 중...")
    base64_face_image_1 = _url_to_base64(face_image_url_1)
    base64_face_image_2 = _url_to_base64(face_image_url_2)
    base64_background_image_1 = _url_to_base64(background_image_url_1)
    
    if not all([base64_face_image_1, base64_face_image_2, b64_bg]):
        print("❌ 이미지 변환에 실패하여 작업을 중단합니다.")
        return []

    overrides = {
       # "15": {"inputs": {"steps": 25}}, 
        "56": { "inputs": { "select": 3 } },
        "42" : {"inputs": {"image": base64_face_image_1}},
        "43" : {"inputs": {"image": base64_face_image_2}},
        "44" : {"inputs": {"image": base64_background_image_1}},
        "48": {"inputs": {"text": story_prompt}},

        # ✅ Step 2의 필수 입력 노드에 더미 (Step 1은 보통 필수 아님)
        "32": { "inputs": { "image": DUMMY_IMAGE } },
    }
    
    outputs = _run_inference(overrides, api_key, deployment_id)
  
    if not outputs: 
      return []

    return _extract_images(outputs, "22")
