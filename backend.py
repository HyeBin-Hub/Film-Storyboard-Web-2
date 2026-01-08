# backend.py (JSON-aligned, robust)
from __future__ import annotations

import time
import random
import requests
from typing import Any, Dict, List, Optional, Set, Tuple
from urllib.parse import urlparse

BASE_URL = "https://api.runcomfy.net/prod/v1"

# =========================================================
# HTTP helpers
# =========================================================
def _headers(api_key: str) -> Dict[str, str]:
    return {
        "Authorization": f"Bearer {api_key.strip()}",
        "Content-Type": "application/json",
    }

def submit_inference(api_key: str, deployment_id: str, overrides: Dict[str, Any]) -> str:
    """
    POST /deployments/{deployment_id}/inference
    payload: {"overrides": {...}}
    returns: request_id
    """
    url = f"{BASE_URL}/deployments/{deployment_id}/inference"
    payload = {"overrides": overrides}

    r = requests.post(url, headers=_headers(api_key), json=payload, timeout=60)
    if not r.ok:
        try:
            detail = r.json()
        except Exception:
            detail = {"raw_text": r.text}
        raise RuntimeError(f"RunComfy inference error / HTTP {r.status_code} / {detail}")

    data = r.json()
    request_id = data.get("request_id")
    if not request_id:
        raise RuntimeError(f"Missing request_id in response: {data}")
    return request_id

def poll_until_done(
    api_key: str,
    deployment_id: str,
    request_id: str,
    *,
    poll_interval_sec: float = 1.5,
    timeout_sec: int = 1800,
) -> None:
    """
    GET /deployments/{deployment_id}/requests/{request_id}/status until completed
    """
    url = f"{BASE_URL}/deployments/{deployment_id}/requests/{request_id}/status"
    t0 = time.time()

    while True:
        r = requests.get(url, headers=_headers(api_key), timeout=30)
        r.raise_for_status()
        data = r.json()

        status = data.get("status", "")
        if status == "completed":
            return
        if status == "cancelled":
            raise RuntimeError(f"Request cancelled: {data}")

        if (time.time() - t0) > timeout_sec:
            raise TimeoutError(f"Timeout waiting for request_id={request_id}. Last status={data}")

        time.sleep(poll_interval_sec)

def fetch_result(api_key: str, deployment_id: str, request_id: str) -> Dict[str, Any]:
    """
    GET /deployments/{deployment_id}/requests/{request_id}/result
    """
    url = f"{BASE_URL}/deployments/{deployment_id}/requests/{request_id}/result"
    r = requests.get(url, headers=_headers(api_key), timeout=60)
    r.raise_for_status()
    return r.json()

# =========================================================
# URL extraction
#   - Primary: outputs[target_node_id].images[*].url (RunComfy export)
#   - Fallback: recursive scan for image URLs
# =========================================================
_IMAGE_EXTS = (".png", ".jpg", ".jpeg", ".webp", ".gif")

def _looks_like_url(x: Any) -> bool:
    return isinstance(x, str) and x.startswith(("http://", "https://"))

def _path_has_image_ext(url: str) -> bool:
    """
    https://.../image.png?X-Goog-... -> path만 보고 확장자 판별
    """
    try:
        p = urlparse(url)
        path = (p.path or "").lower()
        return any(path.endswith(ext) for ext in _IMAGE_EXTS)
    except Exception:
        u = url.split("?", 1)[0].split("#", 1)[0].lower()
        return any(u.endswith(ext) for ext in _IMAGE_EXTS)

def extract_images_by_node(
    outputs: Dict[str, Any],
    target_node_id: str,
) -> Tuple[List[str], Dict[str, Any]]:
    """
    outputs[target_node_id]에서 images.url들을 추출.
    반환: (urls, debug_info)
    """
    target_node_id = str(target_node_id)
    debug: Dict[str, Any] = {
        "target_node_id": target_node_id,
        "available_output_keys": list(outputs.keys()) if isinstance(outputs, dict) else None,
    }

    if not isinstance(outputs, dict):
        debug["error"] = "outputs is not a dict"
        return [], debug

    if target_node_id not in outputs:
        debug["error"] = "target_node_id not in outputs"
        return [], debug

    node_out = outputs.get(target_node_id)
    debug["node_out_type"] = type(node_out).__name__

    if not isinstance(node_out, dict):
        debug["error"] = "node_out is not a dict"
        return [], debug

    images = node_out.get("images")
    if not isinstance(images, list):
        debug["error"] = "node_out has no images list"
        debug["node_out_keys"] = list(node_out.keys())
        return [], debug

    urls: List[str] = []
    for img in images:
        if not isinstance(img, dict):
            continue
        u = img.get("url")
        if _looks_like_url(u) and _path_has_image_ext(u):
            urls.append(u)

    # url이 없고 filename만 있는 경우 힌트 제공
    if not urls and images:
        debug["images_len"] = len(images)
        first = images[0] if images else None
        debug["first_image_keys"] = list(first.keys()) if isinstance(first, dict) else None
        filenames = []
        for img in images:
            if isinstance(img, dict) and isinstance(img.get("filename"), str):
                filenames.append(img["filename"])
        if filenames:
            debug["filenames_only"] = filenames

    return urls, debug

def extract_image_urls_fallback(result_json: Dict[str, Any]) -> List[str]:
    """
    결과 JSON 전체를 재귀 탐색하여 이미지 URL을 찾는 fallback.
    """
    urls: List[str] = []
    seen: Set[str] = set()

    def walk(x: Any) -> None:
        if isinstance(x, dict):
            for v in x.values():
                walk(v)
        elif isinstance(x, list):
            for it in x:
                walk(it)
        elif _looks_like_url(x) and _path_has_image_ext(x):
            if x not in seen:
                seen.add(x)
                urls.append(x)

    walk(result_json)
    return urls

# =========================================================
# Workflow Runner
# =========================================================
def run_workflow(
    api_key: str,
    deployment_id: str,
    overrides: Dict[str, Any],
    *,
    image_node_id: Optional[str] = None,
) -> List[str]:
    """
    1) submit -> poll -> fetch result
    2) image_node_id 지정 시 해당 노드에서만 images.url 추출
    3) 없으면 fallback 스캔
    """
    request_id = submit_inference(api_key, deployment_id, overrides)
    poll_until_done(api_key, deployment_id, request_id)
    result = fetch_result(api_key, deployment_id, request_id)

    outputs = result.get("outputs") or {}

    # (A) 지정 노드 우선 추출
    if image_node_id is not None:
        urls, debug = extract_images_by_node(outputs, image_node_id)
        if urls:
            return urls
        raise RuntimeError(
            "No image urls extracted from target node. "
            f"hint={{'request_id': '{request_id}', 'image_node_id': '{image_node_id}', "
            f"'outputs_keys': {list(outputs.keys())}, 'debug': {debug}}}"
        )

    # (B) fallback
    urls = extract_image_urls_fallback(result)
    if urls:
        return urls

    raise RuntimeError(
        "No image urls extracted. "
        f"hint={{'request_id': '{request_id}', 'keys': {list(result.keys())}, "
        f"'outputs_keys': {list(outputs.keys())}}}"
    )

# =========================================================
# Node IDs (ALIGNED WITH YOUR JSON)
# =========================================================
# Switch
NODE_SWITCH = "56"                 # ImpactSwitch (Any)

# Step1 (portrait)
NODE_BASE_PROMPT = "12"            # ttN text
NODE_PORTRAIT_MASTER = "3"         # PortraitMasterBaseCharacter
NODE_PORTRAIT_SEED = "4"           # Seed (rgthree)
NODE_LATENT = "13"                 # EmptySD3LatentImage
NODE_PORTRAIT_KSAMPLER = "11"      # KSampler

# Step2 (full body + PuLID)
NODE_OUTFIT_PROMPT = "20"          # ttN text
NODE_FACE_URL = "58"               # LoadImageFromUrl
NODE_FULLBODY_KSAMPLER = "25"      # KSampler

# Step3 (scene edit)
NODE_CHAR1_URL = "59"              # LoadImageFromUrl (char1)
NODE_CHAR2_URL = "61"              # LoadImageFromUrl (char2)
NODE_BG_URL = "60"                 # LoadImageFromUrl (bg)
NODE_SCENE_TEXT = "48"             # GoogleTranslateTextNode
NODE_SCENE_KSAMPLER = "40"         # KSampler

# ✅ Only SaveImage in this workflow
NODE_SAVE_IMAGE = "15"             # SaveImage (images <- Switch output)

# =========================================================
# Public APIs used by app.py
# =========================================================
def generate_faces(
    api_key: str,
    deployment_id: str,
    width: int,
    height: int,
    batch_size: int,
    pm_options: Dict[str, Any],
    base_prompt: Optional[str] = None,
    seed: Optional[int] = None,
) -> List[str]:
    """
    Step1: select=1 => Switch input1(16) -> SaveImage(15)
    """
    if seed is None:
        seed = random.randint(1, 10**15)

    if base_prompt is None:
        base_prompt = "Grey background, white t-shirt, documentary photograph"

    overrides: Dict[str, Any] = {
        NODE_SWITCH: {"inputs": {"select": 1}},
        NODE_BASE_PROMPT: {"inputs": {"text": base_prompt}},
        NODE_LATENT: {"inputs": {"width": width, "height": height, "batch_size": batch_size}},
        NODE_PORTRAIT_SEED: {"inputs": {"seed": seed}},
        NODE_PORTRAIT_KSAMPLER: {"inputs": {"seed": seed}},
        NODE_PORTRAIT_MASTER: {"inputs": {
            "shot": "Half-length portrait",
            "gender": pm_options.get("Gender", "-"),
            "age": pm_options.get("age", "-"),
            "nationality_1": pm_options.get("Nationality", "Korean"),
            "body_type": pm_options.get("Body Type", "-"),
            "eyes_color": pm_options.get("Eyes Color", "Brown"),
            "eyes_shape": pm_options.get("Eyes Shape", "Monolid Eyes Shape"),
            "lips_color": pm_options.get("Lips Color", "Berry Lips"),
            "lips_shape": pm_options.get("Lips Shape", "Thin Lips"),
            "face_shape": pm_options.get("Face Shape", "Square with Soft Jaw"),
            "hair_style": pm_options.get("Hair Style", "-"),
            "hair_color": pm_options.get("Hair Color", "Black"),
            "hair_length": pm_options.get("Hair Length", "Short"),
        }},
    }

    # ✅ SaveImage(15)에서만 URL 추출
    return run_workflow(api_key, deployment_id, overrides, image_node_id=NODE_SAVE_IMAGE)

def generate_full_body(
    face_url: str,
    outfit_prompt: str,
    api_key: str,
    deployment_id: str,
) -> List[str]:
    """
    Step2: select=2 => Switch input2(26) -> SaveImage(15)
    """
    seed = random.randint(1, 10**15)

    overrides: Dict[str, Any] = {
        NODE_SWITCH: {"inputs": {"select": 2}},
        NODE_OUTFIT_PROMPT: {"inputs": {"text": outfit_prompt}},
        NODE_FACE_URL: {"inputs": {"image": face_url}},
        NODE_FULLBODY_KSAMPLER: {"inputs": {"seed": seed}},
    }

    return run_workflow(api_key, deployment_id, overrides, image_node_id=NODE_SAVE_IMAGE)

def generate_scene(
    char1_url: str,
    char2_url: Optional[str],
    bg_url: str,
    story_prompt: str,
    api_key: str,
    deployment_id: str,
) -> List[str]:
    """
    Step3: select=3 => Switch input3(41) -> SaveImage(15)
    """
    seed = random.randint(1, 10**15)
    if not char2_url:
        char2_url = char1_url

    overrides: Dict[str, Any] = {
        NODE_SWITCH: {"inputs": {"select": 3}},
        NODE_CHAR1_URL: {"inputs": {"image": char1_url}},
        NODE_CHAR2_URL: {"inputs": {"image": char2_url}},
        NODE_BG_URL: {"inputs": {"image": bg_url}},
        NODE_SCENE_TEXT: {"inputs": {"text": story_prompt}},
        NODE_SCENE_KSAMPLER: {"inputs": {"seed": seed}},
    }

    return run_workflow(api_key, deployment_id, overrides, image_node_id=NODE_SAVE_IMAGE)
