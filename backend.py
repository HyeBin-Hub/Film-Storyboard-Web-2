# backend.py (HYBRID: SaveImage(15) 우선 + 전체 outputs fallback)
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

# =========================================================
# URL extraction helpers
# =========================================================
_IMAGE_EXTS = (".png", ".jpg", ".jpeg", ".webp", ".gif")

def _looks_like_url(x: Any) -> bool:
    return isinstance(x, str) and x.startswith(("http://", "https://"))

def _path_has_image_ext(url: str) -> bool:
    """
    https://.../image.png?X-Goog-... 처럼 query가 붙어도 path만 보고 확장자 판단
    """
    try:
        p = urlparse(url)
        path = (p.path or "").lower()
        return any(path.endswith(ext) for ext in _IMAGE_EXTS)
    except Exception:
        u = url.split("?", 1)[0].split("#", 1)[0].lower()
        return any(u.endswith(ext) for ext in _IMAGE_EXTS)

def _dedup_keep_order(urls: List[str]) -> List[str]:
    seen: Set[str] = set()
    out: List[str] = []
    for u in urls:
        if u not in seen:
            seen.add(u)
            out.append(u)
    return out

def extract_images_from_outputs_any(outputs: Dict[str, Any]) -> List[str]:
    """
    예전 방식과 동일: outputs 전체를 돌면서 node_out.images[*].url을 수집
    """
    if not isinstance(outputs, dict):
        return []

    urls: List[str] = []
    for _, node_out in outputs.items():
        if not isinstance(node_out, dict):
            continue
        imgs = node_out.get("images") or []
        if not isinstance(imgs, list):
            continue
        for img in imgs:
            if not isinstance(img, dict):
                continue
            u = img.get("url")
            if _looks_like_url(u) and _path_has_image_ext(u):
                urls.append(u)

    return _dedup_keep_order(urls)

def extract_images_from_target_node(outputs: Dict[str, Any], node_id: str) -> Tuple[List[str], Dict[str, Any]]:
    """
    특정 node_id(outputs[node_id])에서 images.url을 뽑는다.
    실패 시 debug 정보를 함께 반환한다.
    """
    node_id = str(node_id)
    debug: Dict[str, Any] = {
        "target_node_id": node_id,
        "available_output_keys": list(outputs.keys()) if isinstance(outputs, dict) else None,
    }

    if not isinstance(outputs, dict) or node_id not in outputs:
        debug["error"] = "target node not found in outputs"
        return [], debug

    node_out = outputs.get(node_id)
    if not isinstance(node_out, dict):
        debug["error"] = "node_out is not dict"
        debug["node_out_type"] = type(node_out).__name__
        return [], debug

    imgs = node_out.get("images")
    if not isinstance(imgs, list):
        debug["error"] = "node_out has no images list"
        debug["node_out_keys"] = list(node_out.keys())
        return [], debug

    urls: List[str] = []
    filenames: List[str] = []
    for img in imgs:
        if not isinstance(img, dict):
            continue
        u = img.get("url")
        if _looks_like_url(u) and _path_has_image_ext(u):
            urls.append(u)
        fn = img.get("filename")
        if isinstance(fn, str):
            filenames.append(fn)

    if not urls:
        debug["images_len"] = len(imgs)
        if imgs and isinstance(imgs[0], dict):
            debug["first_image_keys"] = list(imgs[0].keys())
        if filenames:
            debug["filenames_only"] = filenames

    return _dedup_keep_order(urls), debug

def extract_image_urls(result_json: Dict[str, Any]) -> List[str]:
    """
    (Fallback 2) 결과 JSON 전체를 재귀 탐색하며 URL 후보 수집
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
# Workflow runner (HYBRID)
#   1) SaveImage(15) 우선
#   2) outputs 전체 스캔 fallback (예전 방식)
#   3) JSON 전체 재귀 탐색 마지막 fallback
# =========================================================
def run_workflow(
    api_key: str,
    deployment_id: str,
    overrides: Dict[str, Any],
    *,
    primary_image_node_id: str = "15",
) -> List[str]:
    request_id = submit_inference(api_key, deployment_id, overrides)
    poll_until_done(api_key, deployment_id, request_id)
    result = fetch_result(api_key, deployment_id, request_id)

    # ✅ 1) RunComfy가 result에 error를 넣어주는 케이스를 최우선으로 잡아냄
    #    (status=completed 여도 error가 있으면 "실패"로 처리해야 함)
    err = result.get("error")
    if err:
        raise RuntimeError(
            "RunComfy workflow error returned in /result. "
            f"hint={{'request_id': '{request_id}', 'error': {err}}}"
        )

    outputs = result.get("outputs") or {}

    # 2) SaveImage(15) 우선
    urls, debug = extract_images_from_target_node(outputs, primary_image_node_id)
    if urls:
        return urls

    # 3) outputs 전체 스캔 (예전 방식)
    urls_any = extract_images_from_outputs_any(outputs)
    if urls_any:
        return urls_any

    # 4) JSON 전체 재귀 탐색
    urls_recursive = extract_image_urls(result)
    if urls_recursive:
        return urls_recursive

    # 모두 실패면 debug 포함해서 에러
    raise RuntimeError(
        "No image urls extracted. "
        f"hint={{'request_id': '{request_id}', "
        f"'keys': {list(result.keys())}, "
        f"'outputs_keys': {list(outputs.keys()) if isinstance(outputs, dict) else None}, "
        f"'primary_node_debug': {debug}}}"
    )


# =========================================================
# Node IDs (ALIGNED WITH YOUR JSON)
# =========================================================
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

# Primary output node (only SaveImage in JSON)
NODE_SAVE_IMAGE = "15"

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
    Step1 (Switch=1): Portrait generation.
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

    return run_workflow(api_key, deployment_id, overrides, primary_image_node_id=NODE_SAVE_IMAGE)

def generate_full_body(
    face_url: str,
    outfit_prompt: str,
    api_key: str,
    deployment_id: str,
) -> List[str]:
    """
    Step2 (Switch=2): Full body generation.
    """
    seed = random.randint(1, 10**15)

    overrides: Dict[str, Any] = {
        NODE_SWITCH: {"inputs": {"select": 2}},
        NODE_OUTFIT_PROMPT: {"inputs": {"text": outfit_prompt}},
        NODE_FACE_URL: {"inputs": {"image": face_url}},
        NODE_FULLBODY_KSAMPLER: {"inputs": {"seed": seed}},
    }

    return run_workflow(api_key, deployment_id, overrides, primary_image_node_id=NODE_SAVE_IMAGE)

def generate_scene(
    char1_url: str,
    char2_url: Optional[str],
    bg_url: str,
    story_prompt: str,
    api_key: str,
    deployment_id: str,
) -> List[str]:
    """
    Step3 (Switch=3): Final storyboard scene (Qwen edit).
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

    return run_workflow(api_key, deployment_id, overrides, primary_image_node_id=NODE_SAVE_IMAGE)
