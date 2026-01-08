# backend.py (STABLE FINAL VERSION)
from __future__ import annotations

import time
import random
import base64
import mimetypes
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
    r = requests.post(url, headers=_headers(api_key), json={"overrides": overrides}, timeout=60)
    r.raise_for_status()
    data = r.json()
    if "request_id" not in data:
        raise RuntimeError(f"Missing request_id: {data}")
    return data["request_id"]

def poll_until_done(
    api_key: str,
    deployment_id: str,
    request_id: str,
    poll_interval_sec: float = 2.0,
    timeout_sec: int = 1800,
) -> None:
    url = f"{BASE_URL}/deployments/{deployment_id}/requests/{request_id}/status"
    t0 = time.time()

    while True:
        r = requests.get(url, headers=_headers(api_key), timeout=30)
        r.raise_for_status()
        data = r.json()
        status = data.get("status")

        if status == "completed":
            return
        if status == "cancelled":
            raise RuntimeError(f"Request cancelled: {data}")
        if time.time() - t0 > timeout_sec:
            raise TimeoutError(f"Timeout waiting for request_id={request_id}")

        time.sleep(poll_interval_sec)

def fetch_result(api_key: str, deployment_id: str, request_id: str) -> Dict[str, Any]:
    url = f"{BASE_URL}/deployments/{deployment_id}/requests/{request_id}/result"
    r = requests.get(url, headers=_headers(api_key), timeout=60)
    r.raise_for_status()
    return r.json()

# =========================================================
# Image helpers
# =========================================================
_IMAGE_EXTS = (".png", ".jpg", ".jpeg", ".webp")

def _looks_like_url(x: Any) -> bool:
    return isinstance(x, str) and x.startswith(("http://", "https://"))

def _path_has_image_ext(url: str) -> bool:
    p = urlparse(url)
    return any((p.path or "").lower().endswith(ext) for ext in _IMAGE_EXTS)

def url_to_data_uri(url: str) -> str:
    r = requests.get(url, timeout=30)
    r.raise_for_status()
    mime = r.headers.get("Content-Type") or mimetypes.guess_type(url)[0] or "application/octet-stream"
    b64 = base64.b64encode(r.content).decode("utf-8")
    return f"data:{mime};base64,{b64}"

def extract_images_from_saveimage(outputs: Dict[str, Any], node_id: str) -> List[str]:
    node = outputs.get(node_id)
    if not isinstance(node, dict):
        return []
    imgs = node.get("images")
    if not isinstance(imgs, list):
        return []
    urls = [img.get("url") for img in imgs if isinstance(img, dict) and _looks_like_url(img.get("url"))]
    return list(dict.fromkeys(urls))  # dedup keep order

# =========================================================
# Workflow runner
# =========================================================
def run_workflow(
    api_key: str,
    deployment_id: str,
    overrides: Dict[str, Any],
    primary_image_node_id: str = "15",
) -> List[str]:
    request_id = submit_inference(api_key, deployment_id, overrides)
    poll_until_done(api_key, deployment_id, request_id)
    result = fetch_result(api_key, deployment_id, request_id)

    status = result.get("status")
    if status != "completed":
        raise RuntimeError(f"Run failed: {result.get('error')}")

    outputs = result.get("outputs")
    if not isinstance(outputs, dict):
        raise RuntimeError("No outputs in result")

    urls = extract_images_from_saveimage(outputs, primary_image_node_id)
    if not urls:
        raise RuntimeError(f"No images written by SaveImage({primary_image_node_id})")

    return urls

# =========================================================
# Node IDs
# =========================================================
NODE_SWITCH = "56"
NODE_SAVE_IMAGE = "15"

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
# Public APIs
# =========================================================
def generate_faces(
    api_key: str,
    deployment_id: str,
    width: int,
    height: int,
    batch_size: int,
    pm_options: Dict[str, Any],
    base_prompt: Optional[str] = None,
) -> List[str]:
    seed = random.randint(1, 10**15)
    prefix = f"portrait_{seed}_{int(time.time())}"

    overrides = {
        NODE_SWITCH: {"inputs": {"select": 1}},
        NODE_BASE_PROMPT: {"inputs": {"text": base_prompt or "Grey background, portrait"}},
        NODE_LATENT: {"inputs": {"width": width, "height": height, "batch_size": batch_size}},
        NODE_PORTRAIT_SEED: {"inputs": {"seed": seed}},
        NODE_PORTRAIT_KSAMPLER: {"inputs": {"seed": seed}},
        NODE_SAVE_IMAGE: {"inputs": {"filename_prefix": prefix}},
        NODE_PORTRAIT_MASTER: {"inputs": pm_options},
    }
    return run_workflow(api_key, deployment_id, overrides)

def generate_full_body(face_url: str, outfit_prompt: str, api_key: str, deployment_id: str) -> List[str]:
    seed = random.randint(1, 10**15)
    prefix = f"fullbody_{seed}_{int(time.time())}"

    overrides = {
        NODE_SWITCH: {"inputs": {"select": 2}},
        NODE_OUTFIT_PROMPT: {"inputs": {"text": outfit_prompt}},
        NODE_FACE_URL: {"inputs": {"image": url_to_data_uri(face_url)}},
        NODE_FULLBODY_KSAMPLER: {"inputs": {"seed": seed}},
        NODE_SAVE_IMAGE: {"inputs": {"filename_prefix": prefix}},
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
    prefix = f"scene_{seed}_{int(time.time())}"

    overrides = {
        NODE_SWITCH: {"inputs": {"select": 3}},
        NODE_CHAR1_URL: {"inputs": {"image": url_to_data_uri(char1_url)}},
        NODE_CHAR2_URL: {"inputs": {"image": url_to_data_uri(char2_url or char1_url)}},
        NODE_BG_URL: {"inputs": {"image": url_to_data_uri(bg_url)}},
        NODE_SCENE_TEXT: {"inputs": {"text": story_prompt}},
        NODE_SCENE_KSAMPLER: {"inputs": {"seed": seed}},
        NODE_SAVE_IMAGE: {"inputs": {"filename_prefix": prefix}},
    }
    return run_workflow(api_key, deployment_id, overrides)
