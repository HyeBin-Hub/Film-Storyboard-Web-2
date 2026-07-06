import json
import time
import random
from copy import deepcopy
from pathlib import Path

import requests


RUNCOMFY_API_BASE = "https://api.runcomfy.net"

WORKFLOW_DIR = Path(__file__).parent / "workflows"
FACE_WORKFLOW_PATH = WORKFLOW_DIR / "face_workflow_api.json"


# =========================
# Common
# =========================
def _headers(api_key: str, include_content_type: bool = True) -> dict:
    if not api_key:
        raise ValueError("RunComfy API key is missing.")

    headers = {
        "Authorization": f"Bearer {api_key}",
    }

    if include_content_type:
        headers["Content-Type"] = "application/json"

    return headers


def load_workflow_api_json(workflow_path: str | Path) -> dict:
    workflow_path = Path(workflow_path)

    if not workflow_path.exists():
        raise FileNotFoundError(f"workflow_api_json file not found: {workflow_path}")

    with workflow_path.open("r", encoding="utf-8") as f:
        return json.load(f)


def submit_runcomfy_dynamic_workflow(
    api_key: str,
    deployment_id: str,
    workflow_api_json: dict,
) -> dict:
    """
    RunComfy dynamic workflow 실행.

    문서 기준:
    POST /prod/v2/deployments/{deployment_id}/inference

    payload:
    {
        "workflow_api_json": { ... full workflow_api_json ... }
    }
    """
    if not deployment_id:
        raise ValueError("RunComfy deployment_id is missing.")

    url = f"{RUNCOMFY_API_BASE}/prod/v2/deployments/{deployment_id}/inference"

    payload = {
        "workflow_api_json": workflow_api_json,
    }

    response = requests.post(
        url,
        headers=_headers(api_key),
        json=payload,
        timeout=60,
    )

    if response.status_code >= 400:
        raise RuntimeError(
            f"RunComfy dynamic workflow submit failed: "
            f"{response.status_code} / {response.text}"
        )

    return response.json()


def poll_runcomfy_result(
    api_key: str,
    status_url: str,
    result_url: str,
    poll_interval: int = 5,
    timeout_seconds: int = 900,
) -> dict:
    start_time = time.time()

    while True:
        if time.time() - start_time > timeout_seconds:
            raise TimeoutError("RunComfy request timed out.")

        status_response = requests.get(
            status_url,
            headers=_headers(api_key, include_content_type=False),
            timeout=60,
        )

        if status_response.status_code >= 400:
            raise RuntimeError(
                f"RunComfy status check failed: "
                f"{status_response.status_code} / {status_response.text}"
            )

        status_data = status_response.json()
        status = status_data.get("status", "")

        if status == "completed":
            break

        if status in {"failed", "error", "cancelled", "canceled"}:
            raise RuntimeError(f"RunComfy request failed during polling: {status_data}")

        if status not in {"in_queue", "in_progress"}:
            raise RuntimeError(f"Unexpected RunComfy status: {status_data}")

        time.sleep(poll_interval)

    result_response = requests.get(
        result_url,
        headers=_headers(api_key, include_content_type=False),
        timeout=60,
    )

    if result_response.status_code >= 400:
        raise RuntimeError(
            f"RunComfy result fetch failed: "
            f"{result_response.status_code} / {result_response.text}"
        )

    result_data = result_response.json()

    if result_data.get("status") != "succeeded":
        raise RuntimeError(f"RunComfy result is not succeeded: {result_data}")

    return result_data


def extract_output_images(result: dict) -> list[dict]:
    outputs = result.get("outputs", {})
    images = []

    for node_id, node_output in outputs.items():
        if not isinstance(node_output, dict):
            continue

        for image_item in node_output.get("images", []):
            if not isinstance(image_item, dict):
                continue

            images.append(
                {
                    "node_id": node_id,
                    "url": image_item.get("url", ""),
                    "filename": image_item.get("filename", ""),
                    "subfolder": image_item.get("subfolder", ""),
                    "type": image_item.get("type", ""),
                }
            )

    return images


# =========================
# Face workflow patch
# =========================
def patch_face_workflow(workflow: dict, config: dict) -> dict:
    """
    face_workflow_api.json 전체를 받아서
    app.py의 UI config 값으로 노드 input을 직접 수정합니다.

    첨부한 Face workflow 기준 node ID:
    - 1002: CSVStoryboardParser
    - 1000: CharacterRegistryParser
    - 1007: Base Background & Clothing Prompt
    - 1003: PortraitMasterBaseCharacter
    - 1004: PortraitMasterSkinDetails
    - 1018: KSampler
    - 1019: SaveImage
    """
    workflow = deepcopy(workflow)

    csv_config = config["csvstoryboardparser"]
    character_config = config["character_registry_parser"]
    base_prompt_config = config["base_background_clothing_prompt"]
    base_character_config = config["portrait_master_base_character"]
    skin_config = config["portrait_master_skin_details"]

    character_filter = character_config.get("character_filter", "C2")

    if character_filter == "C1":
        character_name = "boy"
    elif character_filter == "C2":
        character_name = "girl"
    else:
        character_name = character_filter.lower()

    seed = random.randint(1, 999_999_999_999_999)
    filename_prefix = f"face_{character_name}"

    # 1002: CSVStoryboardParser
    workflow["1002"]["inputs"]["input_mode"] = "text"
    workflow["1002"]["inputs"]["csv_file"] = "CUSTOM"
    workflow["1002"]["inputs"]["csv_text"] = csv_config.get("csv_text", "")
    workflow["1002"]["inputs"]["shot_filter"] = csv_config.get("shot_filter", "ALL")
    workflow["1002"]["inputs"]["custom_shot_ids"] = csv_config.get("custom_shot_ids", "")

    # 1000: CharacterRegistryParser
    workflow["1000"]["inputs"]["character_filter"] = character_config.get("character_filter", "C2")
    workflow["1000"]["inputs"]["custom_character_id"] = character_config.get("custom_character_id", "")
    workflow["1000"]["inputs"]["age"] = character_config.get("age", 9)
    workflow["1000"]["inputs"]["include_character_id"] = character_config.get("include_character_id", "false")

    # 1007: Base Background & Clothing Prompt
    workflow["1007"]["inputs"]["text"] = base_prompt_config.get(
        "text",
        "gray background, white t-shirt",
    )

    # 1003: PortraitMasterBaseCharacter
    for key, value in base_character_config.items():
        if key in workflow["1003"]["inputs"]:
            workflow["1003"]["inputs"][key] = value

    # 1004: PortraitMasterSkinDetails
    for key, value in skin_config.items():
        if key in workflow["1004"]["inputs"]:
            workflow["1004"]["inputs"][key] = value

    # 1018: KSampler
    workflow["1018"]["inputs"]["seed"] = seed

    # 1019: SaveImage
    workflow["1019"]["inputs"]["filename_prefix"] = filename_prefix

    return workflow


def run_face_generation(
    api_key: str,
    deployment_id: str,
    config: dict,
    workflow_path: str | Path = FACE_WORKFLOW_PATH,
    poll_interval: int = 5,
    timeout_seconds: int = 900,
) -> dict:
    base_workflow = load_workflow_api_json(workflow_path)
    workflow = patch_face_workflow(base_workflow, config)

    request_data = submit_runcomfy_dynamic_workflow(
        api_key=api_key,
        deployment_id=deployment_id,
        workflow_api_json=workflow,
    )

    status_url = request_data.get("status_url")
    result_url = request_data.get("result_url")

    if not status_url or not result_url:
        raise RuntimeError(
            f"RunComfy response does not include status/result URL: {request_data}"
        )

    result_data = poll_runcomfy_result(
        api_key=api_key,
        status_url=status_url,
        result_url=result_url,
        poll_interval=poll_interval,
        timeout_seconds=timeout_seconds,
    )

    raw_images = extract_output_images(result_data)

    character_filter = config["character_registry_parser"].get("character_filter", "C2")

    if character_filter == "C1":
        label_prefix = "Boy Face"
    elif character_filter == "C2":
        label_prefix = "Girl Face"
    else:
        label_prefix = "Face"

    images = []

    for idx, item in enumerate(raw_images, start=1):
        url = item.get("url", "")

        if not url:
            continue

        images.append(
            {
                "label": f"{label_prefix} {idx}",
                "image": url,
                "url": url,
                "filename": item.get("filename", ""),
                "node_id": item.get("node_id", ""),
            }
        )

    return {
        "request": request_data,
        "result": result_data,
        "images": images,
        "workflow_api_json": workflow,
    }
