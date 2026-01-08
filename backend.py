# backend.py
from __future__ import annotations

import time
import random
import requests
from typing import Any, Dict, List, Optional

BASE_URL = "https://api.runcomfy.net/prod/v1"


# -----------------------------
# RunComfy API (Queue) helpers
# -----------------------------
def _headers(api_key: str) -> Dict[str, str]:
    return {
        "Authorization": f"Bearer {api_key.strip()}",
        "Content-Type": "application/json",
    }


def submit_inference(
    api_key: str,
    deployment_id: str,
    overrides: Dict[str, Any],
) -> str:
    """
    Submit inference request to RunComfy.
    Returns request_id.
    If submission fails, raises RuntimeError with full response payload for debugging.
    """
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
    timeout_sec: int = 600,
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


def fetch_result(
    api_key: str,
    deployment_id: str,
    request_id: str,
) -> Dict[str, Any]:
    url = f"{BASE_URL}/deployments/{deployment_id}/requests/{request_id}/result"
    r = requests.get(url, headers=_headers(api_key), timeout=60)
    r.raise_for_status()
    return r.json()


def extract_image_urls(result_json: Dict[str, Any]) -> List[str]:
    """
    Extract all output image URLs from RunComfy result.
    """
    outputs = result_json.get("outputs", {}) or {}
    urls: List[str] = []

    for _, node_out in outputs.items():
        imgs = (node_out or {}).get("images") or []
        for img in imgs:
            u = img.get("url")
            if u:
                urls.append(u)

    # 중복 제거(순서 유지)
    seen = set()
    dedup = []
    for u in urls:
        if u not in seen:
            seen.add(u)
            dedup.append(u)
    return dedup


def run_workflow(
    api_key: str,
    deployment_id: str,
    overrides: Dict[str, Any],
) -> List[str]:
    request_id = submit_inference(api_key, deployment_id, overrides)
    poll_until_done(api_key, deployment_id, request_id)
    result = fetch_result(api_key, deployment_id, request_id)
    return extract_image_urls(result)


# -----------------------------
# High-level functions for app.py
# -----------------------------
def generate_faces(
    base_prompt: str,
    api_key: str,
    deployment_id: str,
    width: int,
    height: int,
    batch_size: int,
) -> List[str]:
    """
    Step1 (Switch=1): Portrait generation.
    - Node 56: ImpactSwitch.select = 1
    - Node 12: base portrait prompt
    - Node 13: latent size + batch
    - Node 11: sampler seed
    """
    seed = random.randint(1, 10**15)

    overrides: Dict[str, Any] = {
        # NODE_SWITCH
        "56": {"inputs": {"select": 1}},
        # NODE_BASE_PROMPT
        "12": {"inputs": {"text": base_prompt}},
        # NODE_LATENT
        "13": {"inputs": {"width": width, "height": height, "batch_size": batch_size}},
        # NODE_PORTRAIT_KSAMPLER
        "11": {"inputs": {"seed": seed}},
        # NODE_PORTRAIT_MASTER
        "3 ": {"inputs": {                                                               
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
    return run_workflow(api_key, deployment_id, overrides)


def generate_full_body(
    face_url: str,
    outfit_prompt: str,
    api_key: str,
    deployment_id: str,
) -> List[str]:
    """
    Step2 (Switch=2): Full body generation.
    - Node 56: select=2
    - Node 20: outfit keywords (Groq가 확장)
    - Node 58: LoadImageFromUrl (PuLID reference image)
    - Node 25: sampler seed
    """
    seed = random.randint(1, 10**15)

    overrides: Dict[str, Any] = {
        # NODE_SWITCH
        "56": {"inputs": {"select": 2}},
        # NODE_OUTFIT_PROMPT
        "20": {"inputs": {"text": outfit_prompt}},
        # NODE_FACE_URL
        "58": {"inputs": {"image": face_url}}, 
        # NODE_FULLBODY_KSAMPLER
        "25": {"inputs": {"seed": seed}},
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
    """
    Step3 (Switch=3): Final storyboard scene (Qwen edit).
    - Node 56: select=3
    - Node 59: LoadImageFromUrl (image1 = boy)
    - Node 61: LoadImageFromUrl (image2 = girl) -> if None, duplicate char1
    - Node 60: LoadImageFromUrl (image3 = background)
    - Node 48: GoogleTranslateTextNode.text (scene description)
    - Node 40: sampler seed
    """
    seed = random.randint(1, 10**15)
    if not char2_url:
        char2_url = char1_url

    overrides: Dict[str, Any] = {
        # NODE_SWITCH
        "56": {"inputs": {"select": 3}},
         # NODE_CHAR1_URL
        "59": {"inputs": {"image": char1_url}},
        # NODE_CHAR2_URL
        "61": {"inputs": {"image": char2_url}},
        # NODE_BG_URL
        "60": {"inputs": {"image": bg_url}},
        # NODE_SCENE_TEXT
        "48": {"inputs": {"text": story_prompt}},
        #  NODE_SCENE_KSAMPLER
        "40": {"inputs": {"seed": seed}},
    }
    return run_workflow(api_key, deployment_id, overrides)
