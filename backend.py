# backend.py
from __future__ import annotations

import time
import random
import requests
from typing import Any, Dict, List, Optional

BASE_URL = "https://api.runcomfy.net/prod/v1"

# -----------------------------
# Seed helpers
# -----------------------------
def derive_seed(base_seed: int, index: int = 0) -> int:
    """
    Deterministically derive a per-index seed from base_seed.
    - Ensures stable but distinct seeds per character/step.
    - Keeps it within a reasonable 64-bit-ish range.
    """
    # 1) sanitize
    b = int(base_seed) if base_seed is not None else 0
    i = int(index) if index is not None else 0

    # 2) simple mixing (stable, reproducible)
    mixed = (b * 1000003) ^ (i * 9176) ^ 0x9E3779B97F4A7C15

    # 3) clamp to positive range used by your workflow (you used up to 10**15 before)
    mixed = abs(mixed) % (10**15)
    if mixed == 0:
        mixed = 1
    return mixed


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
    *,
    seed: Optional[int] = None,
    pm_options: Optional[Dict[str, Any]] = None,
) -> List[str]:
    """
    Step1 (Switch=1): Portrait generation.
    - Node 56: ImpactSwitch.select = 1
    - Node 12: base portrait prompt
    - Node 13: latent size + batch
    - Node 11: sampler seed
    """
    if seed is None:
        seed = random.randint(1, 10**15)

    pm_options = pm_options or {}

    overrides: Dict[str, Any] = {
                "3": {"inputs": { "age": pm_options.get("age", 25), 
                         "gender": pm_options.get("Gender", "Woman"), 
                         "nationality_1": pm_options.get("Nationality", "Korean"), 
                         "body_type": pm_options.get("Body Type", "Fit"), 
                         "eyes_color": pm_options.get("Eyes Color", "Brown"), 
                         "eyes_shape": pm_options.get("Eyes Shape", "Asian Eyes Shape"), 
                         "lips_color": pm_options.get("Lips Color", "Red Lips"), 
                         "lips_shape": pm_options.get("Lips Shape", "Round Lips"), 
                         "face_shape": pm_options.get("Face Shape", "Oval"), 
                         "hair_style": pm_options.get("Hair Style", "Buzz"), 
                         "hair_color": pm_options.get("Hair Color", "Black"), 
                         "hair_length": pm_options.get("Hair Length", "Long"), 
                         "shot": "Half-length portrait" }},
        "56": {"inputs": {"select": 1}},
        "12": {"inputs": {"text": base_prompt}},
        "13": {"inputs": {"width": width, "height": height, "batch_size": batch_size}},
        "11": {"inputs": {"seed": int(seed)}},  # ✅ seed 주입
    }
    return run_workflow(api_key, deployment_id, overrides)


def generate_full_body(
    face_url: str,
    outfit_prompt: str,
    api_key: str,
    deployment_id: str,
    *,
    seed: Optional[int] = None,
) -> List[str]:
    """
    Step2 (Switch=2): Full body generation.
    - Node 56: select=2
    - Node 20: outfit keywords (Groq가 확장)
    - Node 58: LoadImageFromUrl (PuLID reference image)
    - Node 25: sampler seed
    """
    if seed is None:
        seed = random.randint(1, 10**15)

    overrides: Dict[str, Any] = {
        "56": {"inputs": {"select": 2}},
        "20": {"inputs": {"text": outfit_prompt}},
        "58": {"inputs": {"image": face_url}},
        "25": {"inputs": {"seed": int(seed)}},  # ✅ seed 주입
    }
    return run_workflow(api_key, deployment_id, overrides)


def generate_scene(
    char1_url: str,
    char2_url: Optional[str],
    bg_url: str,
    story_prompt: str,
    api_key: str,
    deployment_id: str,
    *,
    seed: Optional[int] = None,
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
    if seed is None:
        seed = random.randint(1, 10**15)
            
    if not char2_url:
        char2_url = char1_url

    overrides: Dict[str, Any] = {
        "56": {"inputs": {"select": 3}},
        "59": {"inputs": {"image": char1_url}},
        "61": {"inputs": {"image": char2_url}},
        "60": {"inputs": {"image": bg_url}},
        "48": {"inputs": {"text": story_prompt}},
        "40": {"inputs": {"seed": int(seed)}},  # ✅ seed 주입
    }
    return run_workflow(api_key, deployment_id, overrides)
