# backend.py
from __future__ import annotations

import time
import random
import requests
from typing import Any, Dict, List, Optional

BASE_URL = "https://api.runcomfy.net/prod/v1"


# -----------------------------
# Low-level RunComfy API helpers
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
    POST /deployments/{deployment_id}/inference
    Returns request_id.
    """
    url = f"{BASE_URL}/deployments/{deployment_id}/inference"
    payload = {"overrides": overrides}

    r = requests.post(url, headers=_headers(api_key), json=payload, timeout=60)
    r.raise_for_status()
    data = r.json()

    # RunComfy returns request_id in response (per docs/examples)
    request_id = data.get("request_id")
    if not request_id:
        raise RuntimeError(f"Missing request_id in response: {data}")
    return request_id


def poll_status(
    api_key: str,
    deployment_id: str,
    request_id: str,
    *,
    poll_interval_sec: float = 1.5,
    timeout_sec: int = 600,
) -> str:
    """
    Polls GET /requests/{request_id}/status until completed or timeout.
    """
    url = f"{BASE_URL}/deployments/{deployment_id}/requests/{request_id}/status"
    start = time.time()

    while True:
        r = requests.get(url, headers=_headers(api_key), timeout=30)
        r.raise_for_status()
        data = r.json()

        status = data.get("status", "")
        # docs show: in_queue, in_progress, completed, cancelled
        if status in {"completed", "cancelled"}:
            return status

        if (time.time() - start) > timeout_sec:
            raise TimeoutError(f"Timeout waiting for request {request_id} (last status={status})")

        time.sleep(poll_interval_sec)


def fetch_result(
    api_key: str,
    deployment_id: str,
    request_id: str,
) -> Dict[str, Any]:
    """
    GET /requests/{request_id}/result
    """
    url = f"{BASE_URL}/deployments/{deployment_id}/requests/{request_id}/result"
    r = requests.get(url, headers=_headers(api_key), timeout=60)
    r.raise_for_status()
    return r.json()


def extract_image_urls(result_json: Dict[str, Any]) -> List[str]:
    """
    Extracts all image urls from RunComfy result format.
    Per docs, outputs are keyed by node id and include images list with url/filename/etc. :contentReference[oaicite:2]{index=2}
    """
    outputs = result_json.get("outputs", {}) or {}
    urls: List[str] = []

    for _node_id, node_out in outputs.items():
        imgs = (node_out or {}).get("images") or []
        for img in imgs:
            url = img.get("url")
            if url:
                urls.append(url)

    return urls


# -----------------------------
# High-level functions for app.py
# -----------------------------
def generate_faces(
    base_prompt: str,
    pm_options: Dict[str, Any],
    api_key: str,
    deployment_id: str,
    width: int,
    height: int,
    batch_size: int,
) -> List[str]:
    """
    Step1: Generate portrait faces (Switch Mode = 1).
    Returns list of image URLs.
    """
    # Randomize seed for variety unless you want deterministic behavior.
    seed = random.randint(1, 10**15)

    # Minimal + safe overrides:
    # - Switch select=1 (portrait branch)
    # - node12: Base portrait prompt
    # - node13: latent size & batch
    # - node11 seed (sampler seed) optionally
    overrides: Dict[str, Any] = {
        "56": {"inputs": {"select": 1}},  # ImpactSwitch -> Portrait output
        "12": {"inputs": {"text": base_prompt}},
        "13": {"inputs": {"width": width, "height": height, "batch_size": batch_size}},
        "11": {"inputs": {"seed": seed}},
    }

    # (Optional) If you want to reflect UI demographic into PortraitMaster node directly,
    # you can add these overrides, but keep in mind the node may expect specific enum strings.
    # We keep it conservative; base_prompt already carries identity constraints.
    # Example:
    # overrides["3"] = {"inputs": {"gender": pm_options.get("Gender", "-"), "nationality_1": pm_options.get("Nationality", "Korean")}}

    request_id = submit_inference(api_key, deployment_id, overrides)
    poll_status(api_key, deployment_id, request_id)
    result = fetch_result(api_key, deployment_id, request_id)
    return extract_image_urls(result)


def generate_full_body(
    selected_face_url: str,
    outfit_prompt: str,
    api_key: str,
    deployment_id: str,
) -> List[str]:
    """
    Step2: Full-body generation with identity preserved (Switch Mode = 2).
    Returns list of image URLs (usually batch_size=4 in your workflow node27).
    """
    seed = random.randint(1, 10**15)

    overrides: Dict[str, Any] = {
        "56": {"inputs": {"select": 2}},  # ImpactSwitch -> Full-body output
        "20": {"inputs": {"text": outfit_prompt}},  # Base_Full_body_Prompt
        "25": {"inputs": {"seed": seed}},  # Full_body_KSampler seed
        # PuLID reference image: LoadImage node32 "image" can be overridden with a public URL (docs allow URL). :contentReference[oaicite:3]{index=3}
        "32": {"inputs": {"image": selected_face_url}},
    }

    request_id = submit_inference(api_key, deployment_id, overrides)
    poll_status(api_key, deployment_id, request_id)
    result = fetch_result(api_key, deployment_id, request_id)
    return extract_image_urls(result)


def final_storyboard(
    char1_url: str,
    char2_url: Optional[str],
    bg_url: str,
    story_prompt: str,
    api_key: str,
    deployment_id: str,
) -> List[str]:
    """
    Step3: Final scene composition (Switch Mode = 3).
    - image1: character 1
    - image2: character 2 (if None, duplicate char1)
    - image3: background
    - prompt: story_prompt (your UI uses English; the translate node can pass through)
    Returns list of image URLs.
    """
    seed = random.randint(1, 10**15)

    if not char2_url:
        char2_url = char1_url

    overrides: Dict[str, Any] = {
        "56": {"inputs": {"select": 3}},  # ImpactSwitch -> Final scene output
        # LoadImage nodes for references (RunComfy allows overriding image inputs with URL). :contentReference[oaicite:4]{index=4}
        "42": {"inputs": {"image": char1_url}},   # image1
        "43": {"inputs": {"image": char2_url}},   # image2
        "44": {"inputs": {"image": bg_url}},      # background (goes into ImageScaleToTotalPixels)
        # Your pipeline: story_prompt -> GoogleTranslateTextNode(48) -> Groq(50) -> TextEncodeQwenImageEditPlus(52)
        # If story_prompt is already English, translate(auto->en) should keep it stable.
        "48": {"inputs": {"text": story_prompt}},
        "40": {"inputs": {"seed": seed}},  # Qwen edit KSampler seed
    }

    request_id = submit_inference(api_key, deployment_id, overrides)
    poll_status(api_key, deployment_id, request_id)
    result = fetch_result(api_key, deployment_id, request_id)
    return extract_image_urls(result)
