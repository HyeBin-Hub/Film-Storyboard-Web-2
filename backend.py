# backend.py (PATCH)
from __future__ import annotations

import time
import random
import requests
from typing import Any, Dict, List, Optional, Set
from urllib.parse import urlparse

BASE_URL = "https://api.runcomfy.net/prod/v1"

def _headers(api_key: str) -> Dict[str, str]:
    return {
        "Authorization": f"Bearer {api_key.strip()}",
        "Content-Type": "application/json",
    }

def submit_inference(api_key: str, deployment_id: str, overrides: Dict[str, Any]) -> str:
    url = f"{BASE_URL}/deployments/{deployment_id}/inference"
    payload = {"overrides": overrides}

    r = requests.post(url, headers=_headers(api_key), json=payload, timeout=60)
    if not r.ok:
        try:
            detail = r.json()
        except Exception:
            detail = {"raw_text": r.text}
        raise RuntimeError(f"ComfyUIQueuePromptError / HTTP {r.status_code} / {detail}")

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
    url = f"{BASE_URL}/deployments/{deployment_id}/requests/{request_id}/result"
    r = requests.get(url, headers=_headers(api_key), timeout=60)
    r.raise_for_status()
    return r.json()

# -----------------------------
# URL extraction (robust)
# -----------------------------
_IMAGE_EXTS = (".png", ".jpg", ".jpeg", ".webp", ".gif")

def _path_has_image_ext(url: str) -> bool:
    """
    https://.../image.png?X-Goog-... 처럼 query가 붙어도 path만 보고 확장자 판단
    """
    try:
        p = urlparse(url)
        path = (p.path or "").lower()
        return any(path.endswith(ext) for ext in _IMAGE_EXTS)
    except Exception:
        u = url.lower().split("?", 1)[0].split("#", 1)[0]
        return any(u.endswith(ext) for ext in _IMAGE_EXTS)

def _looks_like_url(s: str) -> bool:
    return s.startswith("http://") or s.startswith("https://")

def extract_image_urls(result_json: Dict[str, Any]) -> List[str]:
    """
    1) outputs->images->url 뿐 아니라
    2) result 전체를 재귀 탐색하며
    3) query 파라미터가 붙은 이미지 URL도 수집
    """
    urls: List[str] = []
    seen: Set[str] = set()

    # 1) 가장 흔한 구조 먼저 (있으면 이게 가장 정확)
    outputs = result_json.get("outputs") or {}
    if isinstance(outputs, dict):
        for _, node_out in outputs.items():
            if not isinstance(node_out, dict):
                continue
            imgs = node_out.get("images") or []
            if isinstance(imgs, list):
                for img in imgs:
                    if isinstance(img, dict):
                        u = img.get("url")
                        if isinstance(u, str) and _looks_like_url(u) and _path_has_image_ext(u):
                            if u not in seen:
                                seen.add(u)
                                urls.append(u)

    # 2) 그래도 없으면 전체 JSON 재귀 탐색
    def walk(x: Any) -> None:
        if isinstance(x, dict):
            for k, v in x.items():
                if isinstance(v, str) and _looks_like_url(v) and _path_has_image_ext(v):
                    if v not in seen:
                        seen.add(v)
                        urls.append(v)
                else:
                    walk(v)
        elif isinstance(x, list):
            for it in x:
                walk(it)
        elif isinstance(x, str):
            if _looks_like_url(x) and _path_has_image_ext(x) and x not in seen:
                seen.add(x)
                urls.append(x)

    walk(result_json)

    return urls

def run_workflow(api_key: str, deployment_id: str, overrides: Dict[str, Any]) -> List[str]:
    request_id = submit_inference(api_key, deployment_id, overrides)
    poll_until_done(api_key, deployment_id, request_id)
    result = fetch_result(api_key, deployment_id, request_id)

    urls = extract_image_urls(result)
    if not urls:
        outputs = result.get("outputs") or {}
        raise RuntimeError(
            "No image urls extracted. "
            f"hint={{'request_id': '{request_id}', "
            f"'keys': {list(result.keys())}, "
            f"'outputs_keys': {list(outputs.keys())}}}"
        )
    return urls

# -----------------------------
# Node IDs (YOUR WORKFLOW)
# -----------------------------
NODE_SWITCH = "56"

# Step1
NODE_BASE_PROMPT = "12"
NODE_PORTRAIT_MASTER = "3"
NODE_PORTRAIT_SEED = "4"
NODE_LATENT = "13"
NODE_PORTRAIT_KSAMPLER = "11"

# Step2
NODE_OUTFIT_PROMPT = "20"
NODE_FACE_URL = "58"
NODE_FULLBODY_KSAMPLER = "25"

# Step3
NODE_CHAR1_URL = "59"
NODE_CHAR2_URL = "61"
NODE_BG_URL = "60"
NODE_SCENE_TEXT = "48"
NODE_SCENE_KSAMPLER = "40"

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
    return run_workflow(api_key, deployment_id, overrides)

def generate_full_body(face_url: str, outfit_prompt: str, api_key: str, deployment_id: str) -> List[str]:
    seed = random.randint(1, 10**15)
    overrides: Dict[str, Any] = {
        NODE_SWITCH: {"inputs": {"select": 2}},
        NODE_OUTFIT_PROMPT: {"inputs": {"text": outfit_prompt}},
        NODE_FACE_URL: {"inputs": {"image": face_url}},
        NODE_FULLBODY_KSAMPLER: {"inputs": {"seed": seed}},
    }
    return run_workflow(api_key, deployment_id, overrides)

def generate_scene(
    char1_url: str,
    char2_url: Optional[str],
    bg_url: str,
    story_prompt: str,
    api_key: str,
    deployment_id: str,
) -> List[str]:
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
    return run_workflow(api_key, deployment_id, overrides)
