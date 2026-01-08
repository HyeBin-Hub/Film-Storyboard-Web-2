# backend.py
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


def poll_until_terminal(
    api_key: str,
    deployment_id: str,
    request_id: str,
    *,
    poll_interval_sec: float = 1.5,
    timeout_sec: int = 1800,
) -> Dict[str, Any]:
    """
    RunComfy status endpoint를 폴링해서 terminal 상태가 될 때까지 기다립니다.
    terminal: completed / cancelled
    (주의) completed라고 해도 /result에서 failed가 나올 수 있어 result 검증이 필수입니다.
    """
    url = f"{BASE_URL}/deployments/{deployment_id}/requests/{request_id}/status"
    t0 = time.time()

    last_payload: Dict[str, Any] = {}
    while True:
        r = requests.get(url, headers=_headers(api_key), timeout=30)
        r.raise_for_status()
        data = r.json()
        last_payload = data

        status = data.get("status", "")
        if status == "completed":
            return data
        if status == "cancelled":
            raise RuntimeError(f"Request cancelled: {data}")

        if (time.time() - t0) > timeout_sec:
            raise TimeoutError(
                f"Timeout waiting for request_id={request_id}. Last status payload={last_payload}"
            )

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


def extract_images_from_target_node(outputs: Dict[str, Any], node_id: str) -> Tuple[List[str], Dict[str, Any]]:
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
    for img in imgs:
        if not isinstance(img, dict):
            continue
        u = img.get("url")
        if _looks_like_url(u) and _path_has_image_ext(u):
            urls.append(u)

    if not urls:
        debug["images_len"] = len(imgs)
        if imgs and isinstance(imgs[0], dict):
            debug["first_image_keys"] = list(imgs[0].keys())

    return _dedup_keep_order(urls), debug


def extract_images_from_outputs_any(outputs: Dict[str, Any]) -> List[str]:
    """
    fallback: outputs 전체를 순회하며 images[].url 수집
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


def extract_urls_recursive(result_json: Dict[str, Any]) -> List[str]:
    """
    마지막 fallback: result JSON 전체를 재귀 탐색해서 이미지 URL처럼 보이는 문자열을 수집
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
# Node IDs (ALIGNED WITH YOUR JSON)
# =========================================================
NODE_SWITCH = "56"
NODE_PREVIEW = "63"  # ✅ PreviewImage

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


# =========================================================
# Workflow runner (PreviewImage 우선)
# =========================================================
def run_workflow(
    api_key: str,
    deployment_id: str,
    overrides: Dict[str, Any],
    *,
    primary_image_node_id: str = NODE_PREVIEW,
) -> List[str]:
    request_id = submit_inference(api_key, deployment_id, overrides)

    status_payload = poll_until_terminal(api_key, deployment_id, request_id)
    # status_payload는 참고용. 진짜 성공/실패는 result를 봐야 함.
    result = fetch_result(api_key, deployment_id, request_id)

    # 1) result가 error를 포함하면 즉시 실패 처리
    if result.get("error"):
        raise RuntimeError(
            "RunComfy returned error in /result. "
            f"hint={{'request_id': '{request_id}', 'status_payload': {status_payload}, 'error': {result.get('error')}}}"
        )

    # 2) result.status 자체가 failed인 케이스
    if result.get("status") and result["status"] != "completed":
        raise RuntimeError(
            "RunComfy /result status is not completed. "
            f"hint={{'request_id': '{request_id}', 'result_status': '{result.get('status')}', 'status_payload': {status_payload}, 'result_keys': {list(result.keys())}}}"
        )

    outputs = result.get("outputs") or {}

    # ✅ 3) PreviewImage(63)에서 url 우선 추출
    urls, debug = extract_images_from_target_node(outputs, primary_image_node_id)
    if urls:
        return urls

    # 4) fallback: outputs 전체 스캔
    urls_any = extract_images_from_outputs_any(outputs)
    if urls_any:
        return urls_any

    # 5) last fallback: 재귀 탐색
    urls_recursive = extract_urls_recursive(result)
    if urls_recursive:
        return urls_recursive

    raise RuntimeError(
        "No image urls extracted. "
        f"hint={{'request_id': '{request_id}', "
        f"'keys': {list(result.keys())}, "
        f"'outputs_keys': {list(outputs.keys()) if isinstance(outputs, dict) else None}, "
        f"'primary_node_debug': {debug}, "
        f"'status_payload': {status_payload}}}"
    )


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
            "gender": pm_options.get("Gender", "Woman"),
            "age": pm_options.get("age", "25"),
            "nationality_1": pm_options.get("Nationality", "Korean"),
            "body_type": pm_options.get("Body Type", "Fit"),
            "eyes_color": pm_options.get("Eyes Color", "Brown"),
            "eyes_shape": pm_options.get("Eyes Shape", "Round Eyes Shape"),
            "lips_color": pm_options.get("Lips Color", "Red Lips"),
            "lips_shape": pm_options.get("Lips Shape", "Regulars"),
            "face_shape": pm_options.get("Face Shape", "Oval"),
            "hair_style": pm_options.get("Hair Style", "Long straight"),
            "hair_color": pm_options.get("Hair Color", "Black"),
            "hair_length": pm_options.get("Hair Length", "Short"),
        }},
    }

    return run_workflow(api_key, deployment_id, overrides, primary_image_node_id=NODE_PREVIEW)


def generate_full_body(
    face_url: str,
    outfit_prompt: str,
    api_key: str,
    deployment_id: str,
) -> List[str]:
    seed = random.randint(1, 10**15)

    overrides: Dict[str, Any] = {
        NODE_SWITCH: {"inputs": {"select": 2}},
        NODE_OUTFIT_PROMPT: {"inputs": {"text": outfit_prompt}},
        NODE_FACE_URL: {"inputs": {"image": face_url}},  # URL 주입
        NODE_FULLBODY_KSAMPLER: {"inputs": {"seed": seed}},
    }

    return run_workflow(api_key, deployment_id, overrides, primary_image_node_id=NODE_PREVIEW)


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

    return run_workflow(api_key, deployment_id, overrides, primary_image_node_id=NODE_PREVIEW)
