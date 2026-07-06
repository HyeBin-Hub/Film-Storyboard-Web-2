import time
import random
import requests


RUNCOMFY_API_BASE = "https://api.runcomfy.net"


# =========================
# RunComfy Common API
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


def submit_runcomfy_inference(
    api_key: str,
    deployment_id: str,
    overrides: dict,
) -> dict:
    """
    RunComfy Async Queue에 inference job을 제출합니다.

    문서 기준:
    POST /prod/v2/deployments/{deployment_id}/inference

    반환:
    {
        "request_id": "...",
        "status_url": "...",
        "result_url": "...",
        "cancel_url": "..."
    }
    """
    if not deployment_id:
        raise ValueError("RunComfy deployment_id is missing.")

    url = f"{RUNCOMFY_API_BASE}/prod/v2/deployments/{deployment_id}/inference"

    payload = {
        "overrides": overrides,
    }

    response = requests.post(
        url,
        headers=_headers(api_key),
        json=payload,
        timeout=60,
    )

    if response.status_code >= 400:
        raise RuntimeError(
            f"RunComfy submit failed: {response.status_code} / {response.text}"
        )

    return response.json()


def poll_runcomfy_result(
    api_key: str,
    status_url: str,
    result_url: str,
    poll_interval: int = 5,
    timeout_seconds: int = 900,
) -> dict:
    """
    status_url을 polling하다가 status == completed가 되면
    result_url에서 최종 결과를 가져옵니다.

    status endpoint 기준:
    - in_queue
    - in_progress
    - completed
    - cancelled

    result endpoint 기준:
    - succeeded
    - failed
    - cancelled
    """
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
    result_status = result_data.get("status", "")

    if result_status != "succeeded":
        raise RuntimeError(f"RunComfy result is not succeeded: {result_data}")

    return result_data


def extract_output_images(result: dict) -> list[dict]:
    """
    result endpoint의 outputs에서 image 결과를 추출합니다.
    """
    outputs = result.get("outputs", {})
    images = []

    for node_id, node_output in outputs.items():
        if not isinstance(node_output, dict):
            continue

        node_images = node_output.get("images", [])

        for image_item in node_images:
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
# Face Workflow Overrides
# =========================
def build_face_generation_overrides(config: dict) -> dict:
    """
    app.py의 build_face_ui_config() 결과를
    RunComfy overrides 형식으로 변환합니다.

    Face workflow node mapping:
    - 1002: CSVStoryboardParser
    - 1000: CharacterRegistryParser
    - 1007: Base Background & Clothing Prompt
    - 1003: PortraitMasterBaseCharacter
    - 1004: PortraitMasterSkinDetails
    - 1018: KSampler
    - 1019: SaveImage
    """
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

    overrides = {
        "1002": {
            "inputs": {
                "input_mode": "text",
                "csv_file": "CUSTOM",
                "csv_text": csv_config.get("csv_text", ""),
                "shot_filter": csv_config.get("shot_filter", "ALL"),
                "custom_shot_ids": csv_config.get("custom_shot_ids", ""),
            }
        },
        "1000": {
            "inputs": {
                "character_filter": character_config.get("character_filter", "C2"),
                "custom_character_id": character_config.get("custom_character_id", ""),
                "age": character_config.get("age", 9),
                "include_character_id": character_config.get(
                    "include_character_id",
                    "false",
                ),
            }
        },
        "1007": {
            "inputs": {
                "text": base_prompt_config.get(
                    "text",
                    "gray background, white t-shirt",
                )
            }
        },
        "1003": {
            "inputs": base_character_config
        },
        "1004": {
            "inputs": skin_config
        },
        "1018": {
            "inputs": {
                "seed": seed,
            }
        },
        "1019": {
            "inputs": {
                "filename_prefix": filename_prefix,
            }
        },
    }

    return overrides


def run_face_generation(
    api_key: str,
    deployment_id: str,
    config: dict,
    poll_interval: int = 5,
    timeout_seconds: int = 900,
) -> dict:
    overrides = build_face_generation_overrides(config)

    request_data = submit_runcomfy_inference(
        api_key=api_key,
        deployment_id=deployment_id,
        overrides=overrides,
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
        "overrides": overrides,
    }
