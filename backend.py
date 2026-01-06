import requests
import time
import base64 

BASE_URL = "https://api.runcomfy.net/prod/v1"
DUMMY_IMAGE_BASE64 = "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8/5+hHgAHggJ/PchI7wAAAABJRU5ErkJggg=="

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
        res = requests.post(
            f"{BASE_URL}/deployments/{deployment_id}/inference",
            headers=headers,
            json=payload
        )
        res.raise_for_status()
        request_id = res.json()["request_id"]

      # 2. 상태 풀링
        while True:
            time.sleep(3)
            status_res = requests.get(f"{BASE_URL}/deployments/{deployment_id}/requests/{request_id}/status", headers=headers)
            status_res.raise_for_status()
            status = status_res.json().get("status", "").lower()
            
            if status == "completed": 
                break
            elif status in ["failed", "error"]: 
                print(f"❌ 생성 실패: {status_data.get('error_message', 'Unknown error')}")
                return None
              
      # 3. 결과 가져오기 
        result_res = requests.get(f"{BASE_URL}/deployments/{deployment_id}/requests/{request_id}/result", headers=headers)
        result_res.raise_for_status()
      
        return result_res.json().get("outputs", {})

    except Exception as e:
        print(f"❌ API Error: {e}")
        return None


def _extract_images(outputs, target_node_id):
  
    image_urls = []
  
    if target_node_id in outputs:
        for img in outputs[target_node_id].get("images", []):
            if img.get("url"): image_urls.append(img["url"])
        return image_urls
      
    else:
        print(f"⚠️ 노드 {target_id_str}번의 결과물을 찾을 수 없습니다. (현재 노드: {list(outputs.keys())})")
        return []

# --- Step 1: Portrait Generation ---
def generate_faces(prompt_text, pm_options, api_key, deployment_id, width, height, batch_size=4):
    overrides = {        
        "12": {"inputs": {"text": prompt_text}},
        "3": {"inputs": {
              "gender": pm_options.get("gender", "Woman"), 
              "nationality_1": pm_options.get("nationality_1", "Korean"),
              "body_type": pm_options.get("body_type", "Fit"),
              "eyes_color": pm_options.get("eyes_color", "Brown"),
              "eyes_shape": pm_options.get("eyes_shape", "Round Eyes Shape"),
              "lips_color": pm_options.get("lips_color", "Red Lips"),
              "lips_shape": pm_options.get("lips_shape", "Regular"),
              "face_shape": pm_options.get("face_shape", "Oval"),
              "hair_style": pm_options.get("hair_style", "Long straight"),
              "hair_color": pm_options.get("hair_color", "Black"),
              "hair_length": pm_options.get("hair_length", "Long"),
              "beard": pm_options.get("beard", "Clean Shaven"), 
              "beard_color": pm_options.get("beard_color", "Black")
        }},
        "13" : {"inputs":{"width": width, "height": height, "batch_size": batch_size}},
        "11": {"inputs": {"steps": 25}},
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
      "12": {"inputs": {"text": outfit_keywords}}, 
      "6": {"inputs": {"image": base64_image}},
      "14": {"inputs": {"width": 896, "height": 1152, "batch_size": 1}}, 
      "9": {"inputs": {"steps": 30, "seed": 793834637229542}} 
        }
    
    outputs = _run_inference(overrides, api_key, deployment_id)
  
    if not outputs: 
      return []

    return _extract_images(outputs, "11")

# --- Step 3: Final Storyboard ---
def final_storyboard(face_image_url_1, face_image_url_2, background_image_url_1, story_prompt, api_key, deployment_id):
    
    print("🔄 이미지를 서버로 전송하기 위해 변환 중...")
    base64_face_image_1 = _url_to_base64(face_image_url_1)
    base64_face_image_2 = _url_to_base64(face_image_url_2)
    base64_background_image_1 = _url_to_base64(background_image_url_1)
    
    if not all([b64_face1, b64_face2, b64_bg]):
        print("❌ 이미지 변환에 실패하여 작업을 중단합니다.")
        return []

    overrides = {
        "15": {"inputs": {"steps": 25}}, 
        "4" : {"inputs": {"image": base64_face_image_1}},
        "5" : {"inputs": {"image": base64_face_image_2}},
        "3" : {"inputs": {"image": base64_background_image_1}},
        "19": {"inputs": {"text": story_prompt}},
    }
    
    outputs = _run_inference(overrides, api_key, deployment_id)
  
    if not outputs: 
      return []

    return _extract_images(outputs, "22")
