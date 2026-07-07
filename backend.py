import json
import time
import random
from copy import deepcopy
from pathlib import Path

import requests


RUNCOMFY_API_BASE = "https://api.runcomfy.net"

WORKFLOW_DIR = Path(__file__).parent / "workflows"
CSV_PARSER_TEST_WORKFLOW_PATH = WORKFLOW_DIR / "csv_parser_test_workflow_api.json"
FACE_WORKFLOW_PATH = WORKFLOW_DIR / "face_workflow_api.json"
BODY_WORKFLOW_PATH = WORKFLOW_DIR / "body_workflow_api.json"
SCENE_WORKFLOW_PATH = WORKFLOW_DIR / "scene_workflow_api.json"
CAMERA_REFINEMENT_WORKFLOW_PATH = WORKFLOW_DIR / "camera_refinement_workflow_api.json"


# =========================
# Common helpers
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
    poll_interval: int = 10,
    timeout_seconds: int = 1800,
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


# def extract_output_images(result: dict) -> list[dict]:
#     outputs = result.get("outputs", {})
#     images = []

#     for node_id, node_output in outputs.items():
#         if not isinstance(node_output, dict):
#             continue

#         for image_item in node_output.get("images", []):
#             if not isinstance(image_item, dict):
#                 continue

#             url = (
#                 image_item.get("url")
#                 or image_item.get("image_url")
#                 or image_item.get("file_url")
#                 or ""
#             )

#             images.append(
#                 {
#                     "node_id": node_id,
#                     "url": url,
#                     "image": url,
#                     "filename": image_item.get("filename", ""),
#                     "subfolder": image_item.get("subfolder", ""),
#                     "type": image_item.get("type", ""),
#                     "raw": image_item,
#                 }
#             )

#     return images

def extract_output_images(result: dict) -> list[dict]:
    """
    RunComfy 결과에서 이미지 URL을 최대한 안전하게 추출합니다.

    지원 구조:
    1. outputs -> node_id -> images -> url
    2. outputs -> node_id -> images -> image_url / file_url
    3. outputs -> node_id -> files / output_files
    4. result 전체를 재귀적으로 탐색해서 url이 있는 png/jpg/webp 파일 찾기
    """
    images = []

    def add_image_item(item: dict, node_id: str = ""):
        if not isinstance(item, dict):
            return

        url = (
            item.get("url")
            or item.get("image")
            or item.get("image_url")
            or item.get("file_url")
            or item.get("download_url")
            or item.get("path")
            or ""
        )

        filename = item.get("filename", "")

        # filename이 없으면 url에서 추정
        if not filename and isinstance(url, str) and "/" in url:
            filename = url.split("?")[0].rstrip("/").split("/")[-1]

        if not isinstance(url, str) or not url:
            return

        lower_url = url.lower()
        lower_filename = str(filename).lower()

        is_image = (
            lower_url.endswith((".png", ".jpg", ".jpeg", ".webp"))
            or ".png" in lower_url
            or ".jpg" in lower_url
            or ".jpeg" in lower_url
            or ".webp" in lower_url
            or lower_filename.endswith((".png", ".jpg", ".jpeg", ".webp"))
        )

        if not is_image:
            return

        images.append(
            {
                "node_id": node_id,
                "url": url,
                "image": url,
                "filename": filename,
                "subfolder": item.get("subfolder", ""),
                "type": item.get("type", ""),
                "raw": item,
            }
        )

    # 1차: RunComfy outputs 구조 우선 탐색
    outputs = result.get("outputs", {})

    if isinstance(outputs, dict):
        for node_id, node_output in outputs.items():
            if not isinstance(node_output, dict):
                continue

            for key in ["images", "files", "output_files"]:
                items = node_output.get(key, [])

                if isinstance(items, dict):
                    items = [items]

                if isinstance(items, list):
                    for item in items:
                        add_image_item(item, node_id=str(node_id))

    # 2차: 그래도 못 찾으면 result 전체 재귀 탐색
    if not images:
        def walk(obj, node_id: str = ""):
            if isinstance(obj, dict):
                add_image_item(obj, node_id=node_id)

                for key, value in obj.items():
                    next_node_id = node_id
                    if str(key).isdigit():
                        next_node_id = str(key)
                    walk(value, node_id=next_node_id)

            elif isinstance(obj, list):
                for value in obj:
                    walk(value, node_id=node_id)

        walk(result)

    # 중복 제거
    deduped = []
    seen = set()

    for item in images:
        key = item.get("url", "")
        if key and key not in seen:
            deduped.append(item)
            seen.add(key)

    return deduped


def find_nodes_by_class_type(workflow: dict, class_type: str) -> list[str]:
    node_ids = []

    for node_id, node in workflow.items():
        if not isinstance(node, dict):
            continue

        if node.get("class_type") == class_type:
            node_ids.append(str(node_id))

    return node_ids


def find_first_node_by_class_type(workflow: dict, class_type: str) -> str:
    node_ids = find_nodes_by_class_type(workflow, class_type)

    if not node_ids:
        raise KeyError(f"Node with class_type='{class_type}' was not found.")

    return node_ids[0]


def character_filter_to_name(character_filter: str) -> str:
    if character_filter == "C1":
        return "boy"
    if character_filter == "C2":
        return "girl"
    return str(character_filter).lower().replace(" ", "_")


# =========================
# CSV Parser Test
# =========================
def patch_csv_parser_test_workflow(workflow: dict, storyboard_input_config: dict) -> dict:
    workflow = deepcopy(workflow)

    storyboard_input = storyboard_input_config.get("storyboard_input", storyboard_input_config)

    csv_text = storyboard_input.get("csv_text", "")
    shot_filter = storyboard_input.get("shot_filter", "ALL")
    custom_shot_ids = storyboard_input.get("custom_shot_ids", "")

    if not csv_text.strip():
        raise ValueError("csv_text is empty. Upload a CSV file first.")

    csv_parser_node_id = find_first_node_by_class_type(workflow, "CSVStoryboardParser")

    workflow[csv_parser_node_id]["inputs"]["csv_file"] = "CUSTOM"
    workflow[csv_parser_node_id]["inputs"]["csv_text"] = csv_text
    workflow[csv_parser_node_id]["inputs"]["shot_filter"] = shot_filter
    workflow[csv_parser_node_id]["inputs"]["custom_shot_ids"] = custom_shot_ids

    seed = random.randint(1, 4_294_967_295)
    filename_prefix = f"csv_parser_test_{seed}"

    for node_id in find_nodes_by_class_type(workflow, "KSampler"):
        inputs = workflow[node_id].get("inputs", {})
        if "seed" in inputs:
            inputs["seed"] = seed

    for node_id, node in workflow.items():
        if not isinstance(node, dict):
            continue

        inputs = node.get("inputs", {})
        if isinstance(inputs, dict) and "seed" in inputs and isinstance(inputs["seed"], int):
            inputs["seed"] = seed

    for node_id in find_nodes_by_class_type(workflow, "SaveImage"):
        inputs = workflow[node_id].get("inputs", {})
        if "filename_prefix" in inputs:
            inputs["filename_prefix"] = filename_prefix

    return workflow


def run_csv_parser_test(
    api_key: str,
    deployment_id: str,
    storyboard_input_config: dict,
    workflow_path: str | Path = CSV_PARSER_TEST_WORKFLOW_PATH,
    poll_interval: int = 10,
    timeout_seconds: int = 1800,
) -> dict:
    base_workflow = load_workflow_api_json(workflow_path)

    workflow = patch_csv_parser_test_workflow(
        workflow=base_workflow,
        storyboard_input_config=storyboard_input_config,
    )

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

    images = extract_output_images(result_data)

    return {
        "request": request_data,
        "result": result_data,
        "images": images,
        "workflow_api_json": workflow,
    }


# =========================
# Face Generation
# =========================
def patch_face_workflow(workflow: dict, config: dict) -> dict:
    workflow = deepcopy(workflow)

    storyboard_input = config.get("storyboard_input", {})
    csv_config = config.get("csvstoryboardparser", {})
    character_config = config.get("character_registry_parser", {})
    base_prompt_config = config.get("base_background_clothing_prompt", {})
    base_character_config = config.get("portrait_master_base_character", {})
    skin_config = config.get("portrait_master_skin_details", {})

    csv_text = csv_config.get("csv_text") or storyboard_input.get("csv_text", "")
    shot_filter = csv_config.get("shot_filter") or storyboard_input.get("shot_filter", "ALL")
    custom_shot_ids = csv_config.get("custom_shot_ids") or storyboard_input.get("custom_shot_ids", "")

    if not csv_text.strip():
        raise ValueError("csv_text is empty. Upload a CSV file first.")

    character_filter = character_config.get("character_filter", "C2")
    character_name = character_filter_to_name(character_filter)

    seed = random.randint(1, 4_294_967_295)
    filename_prefix = f"face_{character_name}_{seed}"

    workflow["1002"]["inputs"]["csv_file"] = "CUSTOM"
    workflow["1002"]["inputs"]["csv_text"] = csv_text
    workflow["1002"]["inputs"]["shot_filter"] = shot_filter
    workflow["1002"]["inputs"]["custom_shot_ids"] = custom_shot_ids

    workflow["1000"]["inputs"]["character_filter"] = character_filter
    workflow["1000"]["inputs"]["custom_character_id"] = character_config.get("custom_character_id", "")
    workflow["1000"]["inputs"]["age"] = character_config.get("age", 9)
    workflow["1000"]["inputs"]["include_character_id"] = character_config.get("include_character_id", "false")

    workflow["1007"]["inputs"]["text"] = base_prompt_config.get(
        "text",
        "gray background, white t-shirt",
    )

    for key, value in base_character_config.items():
        if key in workflow["1003"]["inputs"]:
            workflow["1003"]["inputs"][key] = value

    for key, value in skin_config.items():
        if key in workflow["1004"]["inputs"]:
            workflow["1004"]["inputs"][key] = value

    if "999" in workflow and "seed" in workflow["999"]["inputs"]:
        workflow["999"]["inputs"]["seed"] = seed

    if "1014" in workflow and "seed" in workflow["1014"]["inputs"]:
        workflow["1014"]["inputs"]["seed"] = seed

    workflow["1018"]["inputs"]["seed"] = seed
    workflow["1019"]["inputs"]["filename_prefix"] = filename_prefix

    return workflow


def run_face_generation(
    api_key: str,
    deployment_id: str,
    config: dict,
    workflow_path: str | Path = FACE_WORKFLOW_PATH,
    poll_interval: int = 10,
    timeout_seconds: int = 1800,
) -> dict:
    base_workflow = load_workflow_api_json(workflow_path)

    workflow = patch_face_workflow(
        workflow=base_workflow,
        config=config,
    )

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

    character_filter = config.get("character_registry_parser", {}).get(
        "character_filter",
        "C2",
    )

    if character_filter == "C1":
        label_prefix = "Boy Face"
    elif character_filter == "C2":
        label_prefix = "Girl Face"
    else:
        label_prefix = "Face"

    images = []

    for idx, item in enumerate(raw_images, start=1):
        url = item.get("url") or item.get("image") or ""

        if not url:
            continue

        images.append(
            {
                "label": f"{label_prefix} {idx}",
                "image": url,
                "url": url,
                "filename": item.get("filename", ""),
                "node_id": item.get("node_id", ""),
                "raw": item.get("raw", {}),
            }
        )

    return {
        "request": request_data,
        "result": result_data,
        "images": images,
        "workflow_api_json": workflow,
    }


# =========================
# Body Generation
# =========================
def patch_body_workflow(workflow: dict, config: dict) -> dict:
    """
    Step 2B Full-Body Reference Generation workflow patch.

    body_workflow_api.json 기준 주요 노드:
    - 1239: LoadImageFromUrl
    - 1238: body/outfit prompt text
    - 1065: ThinkingLLM
    - 1048: KSampler
    - 1226: SaveImage
    """
    workflow = deepcopy(workflow)

    body_config = config.get("body_generation", config)

    character_filter = body_config.get("character_filter", "C1")
    character_name = character_filter_to_name(character_filter)

    face_image_url = (
        body_config.get("face_image_url")
        or body_config.get("face_reference_image")
        or body_config.get("reference_image_url")
        or ""
    )

    body_prompt = body_config.get("body_prompt", "")

    if not face_image_url:
        raise ValueError(
            "face_image_url is empty. Generate a face reference first."
        )

    if not body_prompt.strip():
        raise ValueError(
            "body_prompt is empty. Enter a full-body outfit prompt first."
        )

    seed = random.randint(1, 4_294_967_295)
    filename_prefix = f"body_{character_name}_{seed}"

    # 1239: Load Image From URL
    workflow["1239"]["inputs"]["image"] = face_image_url
    workflow["1239"]["inputs"]["keep_alpha_channel"] = False
    workflow["1239"]["inputs"]["output_mode"] = False

    # 1238: text / outfit prompt
    workflow["1238"]["inputs"]["text"] = body_prompt

    # 1065: ThinkingLLM seed
    if "1065" in workflow and "seed" in workflow["1065"]["inputs"]:
        workflow["1065"]["inputs"]["seed"] = seed

    # 1048: KSampler
    workflow["1048"]["inputs"]["seed"] = seed

    # 1226: SaveImage
    workflow["1226"]["inputs"]["filename_prefix"] = filename_prefix

    return workflow


def run_body_generation(
    api_key: str,
    deployment_id: str,
    config: dict,
    workflow_path: str | Path = BODY_WORKFLOW_PATH,
    poll_interval: int = 10,
    timeout_seconds: int = 1800,
) -> dict:
    base_workflow = load_workflow_api_json(workflow_path)

    workflow = patch_body_workflow(
        workflow=base_workflow,
        config=config,
    )

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

    # Step 2B에서는 최종 SaveImage 노드인 1226 결과만 사용해야 함.
    # 1239는 LoadImageFromUrl 입력 face reference라서 제외해야 함.
    raw_images = [
        item for item in raw_images
        if str(item.get("node_id", "")) == "1226"
        and item.get("raw", {}).get("type") == "output"
    ]

    character_filter = config.get("body_generation", {}).get(
        "character_filter",
        "C1",
    )

    if character_filter == "C1":
        label_prefix = "Boy Body"
    elif character_filter == "C2":
        label_prefix = "Girl Body"
    else:
        label_prefix = "Body"

    images = []

    for idx, item in enumerate(raw_images, start=1):
        url = item.get("url") or item.get("image") or ""

        if not url:
            continue

        images.append(
            {
                "label": f"{label_prefix} {idx}",
                "image": url,
                "url": url,
                "filename": item.get("filename", ""),
                "node_id": item.get("node_id", ""),
                "raw": item.get("raw", {}),
            }
        )

    return {
        "request": request_data,
        "result": result_data,
        "images": images,
        "workflow_api_json": workflow,
    }

# =========================
# Scene Generation
# =========================
def patch_scene_workflow(workflow: dict, config: dict) -> dict:
    """
    Step 3 Reference-Guided Scene Generation workflow patch.

    scene_workflow_api.json 기준 주요 노드:
    - 26: CSVStoryboardParser
    - 27: LoadImageFromUrl - boy
    - 28: LoadImageFromUrl - girl
    - 10: KSampler
    - 11: SaveImage
    """
    workflow = deepcopy(workflow)

    storyboard_input = config.get("storyboard_input", {})
    scene_config = config.get("scene_generation", {})

    csv_text = storyboard_input.get("csv_text", "")
    shot_filter = scene_config.get("shot_filter") or storyboard_input.get("shot_filter", "ALL")
    custom_shot_ids = scene_config.get("custom_shot_ids") or storyboard_input.get("custom_shot_ids", "")

    reference_images = scene_config.get("reference_images", {})

    boy_body_image_url = (
        reference_images.get("image_1_boy_body", {}).get("image")
        or scene_config.get("boy_body_image_url")
        or ""
    )

    girl_body_image_url = (
        reference_images.get("image_2_girl_body", {}).get("image")
        or scene_config.get("girl_body_image_url")
        or ""
    )

    if not csv_text.strip():
        raise ValueError("csv_text is empty. Upload a CSV file first.")

    if not boy_body_image_url:
        raise ValueError("boy_body_image_url is empty. Generate Image 1 - Boy body reference first.")

    if not girl_body_image_url:
        raise ValueError("girl_body_image_url is empty. Generate Image 2 - Girl body reference first.")

    seed = random.randint(1, 4_294_967_295)
    filename_prefix = f"scene_{seed}"

    # 26: CSVStoryboardParser
    workflow["26"]["inputs"]["csv_file"] = "CUSTOM"
    workflow["26"]["inputs"]["csv_text"] = csv_text
    workflow["26"]["inputs"]["shot_filter"] = shot_filter
    workflow["26"]["inputs"]["custom_shot_ids"] = custom_shot_ids

    # 27: Load Image From URL - boy
    workflow["27"]["inputs"]["image"] = boy_body_image_url
    workflow["27"]["inputs"]["keep_alpha_channel"] = False
    workflow["27"]["inputs"]["output_mode"] = False

    # 28: Load Image From URL - girl
    workflow["28"]["inputs"]["image"] = girl_body_image_url
    workflow["28"]["inputs"]["keep_alpha_channel"] = False
    workflow["28"]["inputs"]["output_mode"] = False

    # 23: ThinkingLLM seed
    if "23" in workflow and "seed" in workflow["23"]["inputs"]:
        workflow["23"]["inputs"]["seed"] = seed

    # 10: KSampler
    workflow["10"]["inputs"]["seed"] = seed

    # 11: SaveImage
    workflow["11"]["inputs"]["filename_prefix"] = filename_prefix

    return workflow


def run_scene_generation(
    api_key: str,
    deployment_id: str,
    config: dict,
    workflow_path: str | Path = SCENE_WORKFLOW_PATH,
    poll_interval: int = 10,
    timeout_seconds: int = 1800,
) -> dict:
    base_workflow = load_workflow_api_json(workflow_path)

    workflow = patch_scene_workflow(
        workflow=base_workflow,
        config=config,
    )

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

    images = []

    for idx, item in enumerate(raw_images, start=1):
        url = item.get("url") or item.get("image") or ""

        if not url:
            continue

        images.append(
            {
                "label": f"Scene {idx}",
                "image": url,
                "url": url,
                "filename": item.get("filename", ""),
                "node_id": item.get("node_id", ""),
                "raw": item.get("raw", {}),
            }
        )

    return {
        "request": request_data,
        "result": result_data,
        "images": images,
        "workflow_api_json": workflow,
    }

# =========================
# Camera Refinement
# =========================
def patch_camera_refinement_workflow(workflow: dict, config: dict) -> dict:
    """
    Step 4 Camera Angle Refinement workflow patch.

    camera_refinement_workflow_api.json 기준 주요 노드:
    - 1275: LoadImageFromUrl
    - 1269: CSVStoryboardParser
    - 1253: QwenMultiangleCameraNode
    - 1270: TwoWaySwitch
    - 1243: KSampler
    - 1263: SeedVR2VideoUpscaler
    - 1274: SaveImage
    """
    workflow = deepcopy(workflow)

    storyboard_input = config.get("storyboard_input", {})
    camera_config = config.get("camera_angle_refinement", {})

    input_scene = camera_config.get("input_scene", {})
    camera_control = camera_config.get("camera_control", {})
    prompt_source = camera_config.get("prompt_source", {})

    csv_text = storyboard_input.get("csv_text", "")
    shot_filter = storyboard_input.get("shot_filter", "ALL")
    custom_shot_ids = storyboard_input.get("custom_shot_ids", "")

    scene_image_url = (
        input_scene.get("image")
        or camera_config.get("scene_image_url")
        or ""
    )

    if not csv_text.strip():
        raise ValueError("csv_text is empty. Upload a CSV file first.")

    if not scene_image_url:
        raise ValueError("scene_image_url is empty. Generate a scene first.")

    horizontal_angle = camera_control.get("horizontal_angle", 0)
    vertical_angle = camera_control.get("vertical_angle", 0)
    zoom = camera_control.get("zoom", 5)
    default_prompts = camera_control.get("default_prompts", True)
    camera_view = camera_control.get("camera_view", False)

    switch_setting = prompt_source.get("two_way_switch_selection", 2)

    seed = random.randint(1, 4_294_967_295)
    filename_prefix = f"camera_refined_{seed}"

    # 1275: Load Image From URL
    workflow["1275"]["inputs"]["image"] = scene_image_url
    workflow["1275"]["inputs"]["keep_alpha_channel"] = False
    workflow["1275"]["inputs"]["output_mode"] = False

    # 1269: CSVStoryboardParser
    workflow["1269"]["inputs"]["csv_file"] = "CUSTOM"
    workflow["1269"]["inputs"]["csv_text"] = csv_text
    workflow["1269"]["inputs"]["shot_filter"] = shot_filter
    workflow["1269"]["inputs"]["custom_shot_ids"] = custom_shot_ids

    # 1253: Qwen Multiangle Camera
    workflow["1253"]["inputs"]["horizontal_angle"] = horizontal_angle
    workflow["1253"]["inputs"]["vertical_angle"] = vertical_angle
    workflow["1253"]["inputs"]["zoom"] = zoom
    workflow["1253"]["inputs"]["default_prompts"] = bool(default_prompts)
    workflow["1253"]["inputs"]["camera_view"] = bool(camera_view)

    # 1270: TwoWaySwitch
    # 1 = ScenePromptBuilder prompt
    # 2 = Qwen Multiangle Camera prompt
    workflow["1270"]["inputs"]["selection_setting"] = switch_setting

    # 1243: KSampler
    workflow["1243"]["inputs"]["seed"] = seed

    # 1263: SeedVR2VideoUpscaler
    if "1263" in workflow and "seed" in workflow["1263"]["inputs"]:
        workflow["1263"]["inputs"]["seed"] = seed

    # 1274: SaveImage
    workflow["1274"]["inputs"]["filename_prefix"] = filename_prefix

    return workflow


def run_camera_refinement(
    api_key: str,
    deployment_id: str,
    config: dict,
    workflow_path: str | Path = CAMERA_REFINEMENT_WORKFLOW_PATH,
    poll_interval: int = 10,
    timeout_seconds: int = 1800,
) -> dict:
    base_workflow = load_workflow_api_json(workflow_path)

    workflow = patch_camera_refinement_workflow(
        workflow=base_workflow,
        config=config,
    )

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

    images = []

    for idx, item in enumerate(raw_images, start=1):
        url = item.get("url") or item.get("image") or ""

        if not url:
            continue

        images.append(
            {
                "label": f"Camera Refined Scene {idx}",
                "image": url,
                "url": url,
                "filename": item.get("filename", ""),
                "node_id": item.get("node_id", ""),
                "raw": item.get("raw", {}),
            }
        )

    return {
        "request": request_data,
        "result": result_data,
        "images": images,
        "workflow_api_json": workflow,
    }

