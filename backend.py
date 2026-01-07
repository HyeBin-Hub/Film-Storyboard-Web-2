# backend.py
import time
import random
import requests
from typing import Any, Dict, List, Optional

BASE_URL = "https://api.runcomfy.net/prod/v1"


def _headers(api_key: str) -> Dict[str, str]:
    return {
        "Authorization": "Bearer " + api_key.strip(),
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
    poll_interval_sec: float = 1.5,
    timeout_sec: int = 1800,
) -> bool:
    url = f"{BASE_URL}/deployments/{deployment_id}/requests/{request_id}/status"
    t0 = time.time()

    while True:
        r = requests.get(url, headers=_headers(api_key), timeout=30)
        r.raise_for_status()
        data = r.json()

        status = data.get("status", "")
        if status == "completed":
            return True
        if status == "cancelled":
            raise RuntimeError(f"Request cancelled: {data}")

        if (time.time() - t0) > timeout_sec:
            return False

        time.sleep(poll_interval_sec)


def fetch_result(api_key: str, deployment_id: str, request_id: str) -> Dict[str, Any]:
    url = f"{BASE_URL}/deployments/{deployment_id}/requests/{request_id}/result"
    r = requests.get(url, headers=_headers(api_key), timeout=60)
    r.raise_for_status()
    return r.json()


def extract_image_urls(result_json: Dict[str, Any]) -> List[str]:
    outputs = result_json.get("outputs") or {}
    urls: List[str] = []

    for _, node_out in outputs.items():
        imgs = (node_out or {}).get("images") or []
        for img in imgs:
            u = img.get("url")
            if u:
                urls.append(u)

    # dedup (stable)
    seen = set()
    dedup: List[str] = []
    for u in urls:
        if u not in seen:
            seen.add(u)
            dedup.append(u)
    return dedup


def run_workflow(api_key: str, deployment_id: str, overrides: Dict[str, Any]) -> List[str]:
    request_id = submit_inference(api_key, deployment_id, overrides)

    done = poll_until_done(api_key, deployment_id, request_id, timeout_sec=1800)
    if not done:
        # Streamlit에서 사용자에게 안내할 수 있도록 request_id를 메시지로 포함
        raise TimeoutError(
            f"Timeout waiting for request_id={request_id}. "
            f"Try increasing timeout or check status/result via RunComfy console."
        )

    result = fetch_result(api_key, deployment_id, request_id)
    return extract_image_urls(result)


# -----------------------------
# High-level functions for app.py
# -----------------------------
def generate_faces(
    api_key: str,
    deployment_id: str,
    width: int,
    height: int,
    batch_size: int,
    pm_options: Dict[str, Any],
    base_prompt: Optional[str] = None,
) -> List[str]:
    DEFAULT_BASE_PROMPT = "Grey background, white t-shirt, documentary photograph"
    prompt = base_prompt if base_prompt else DEFAULT_BASE_PROMPT

    seed = random.randint(1, 10**15)

    overrides: Dict[str, Any] = {
        "56": {"inputs": {"select": 1}},
        "12": {"inputs": {"text": prompt}},
        "13": {"inputs": {"width": width, "height": height, "batch_size": batch_size}},
        "11": {"inputs": {"seed": seed}},
        # PortraitMasterBaseCharacter (node 3) override
        "3": {"inputs": {
            "age": pm_options.get("age", "-"),
            "gender": pm_options.get("Gender", "-"),
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
            "shot": "Half-length portrait",
        }},
    }

    return run_workflow(api_key, deployment_id, overrides)


def generate_multiple_characters(
    api_key: str,
    deployment_id: str,
    width: int,
    height: int,
    shots_per_character: int,
    num_characters: int,
    pm_options_list: Optional[List[Dict[str, Any]]] = None,
    base_prompt: Optional[str] = None,
) -> List[List[str]]:
    """
    Returns: characters[i] = list of shot URLs for character i
    """
    results: List[List[str]] = []

    for i in range(num_characters):
        opts = pm_options_list[i] if pm_options_list else {}

        imgs = generate_faces(
            api_key=api_key,
            deployment_id=deployment_id,
            width=width,
            height=height,
            batch_size=shots_per_character,
            pm_options=opts,
            base_prompt=base_prompt,
        )
        results.append(imgs)

    return results


def generate_full_body(
    face_url: str,
    outfit_prompt: str,
    api_key: str,
    deployment_id: str,
) -> List[str]:
    seed = random.randint(1, 10**15)

    overrides: Dict[str, Any] = {
        "56": {"inputs": {"select": 2}},
        "20": {"inputs": {"text": outfit_prompt}},
        "58": {"inputs": {"image": face_url}},
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
    seed = random.randint(1, 10**15)
    if not char2_url:
        char2_url = char1_url

    overrides: Dict[str, Any] = {
        "56": {"inputs": {"select": 3}},
        "59": {"inputs": {"image": char1_url}},
        "61": {"inputs": {"image": char2_url}},
        "60": {"inputs": {"image": bg_url}},
        "48": {"inputs": {"text": story_prompt}},
        "40": {"inputs": {"seed": seed}},
    }
    return run_workflow(api_key, deployment_id, overrides)
