import json
import random
import time
from copy import deepcopy
from pathlib import Path

import requests


RUNCOMFY_API_BASE = "https://api.runcomfy.net"

WORKFLOW_DIR = Path(__file__).parent / "workflows"

# 현재 프로젝트의 API-format workflow 파일명입니다.
CSV_PARSER_TEST_WORKFLOW_PATH = WORKFLOW_DIR / "csv_parser_test_workflow_api.json"
FACE_WORKFLOW_PATH = WORKFLOW_DIR / "Character_Appearance_Generation.json"
BODY_WORKFLOW_PATH = WORKFLOW_DIR / "Reference-based_Outfit_Change.json"
SCENE_WORKFLOW_PATH = WORKFLOW_DIR / "Reference-based_Scene_Generation.json"
CAMERA_REFINEMENT_WORKFLOW_PATH = WORKFLOW_DIR / "Camera_Refinement.json"


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
        raise FileNotFoundError(
            f"workflow_api_json file not found: {workflow_path}"
        )

    with workflow_path.open("r", encoding="utf-8") as f:
        workflow = json.load(f)

    # RunComfy dynamic workflow에는 ComfyUI API Format JSON이 필요합니다.
    if isinstance(workflow, dict) and isinstance(workflow.get("nodes"), list):
        raise ValueError(
            "The workflow is a ComfyUI UI-format JSON. "
            "Export it again with 'Save (API Format)' and save it as a workflow_api.json file."
        )

    return workflow


def submit_runcomfy_dynamic_workflow(
    api_key: str,
    deployment_id: str,
    workflow_api_json: dict,
) -> dict:
    if not deployment_id:
        raise ValueError("RunComfy deployment_id is missing.")

    url = f"{RUNCOMFY_API_BASE}/prod/v2/deployments/{deployment_id}/inference"

    response = requests.post(
        url,
        headers=_headers(api_key),
        json={"workflow_api_json": workflow_api_json},
        timeout=60,
    )

    if response.status_code >= 400:
        raise RuntimeError(
            "RunComfy dynamic workflow submit failed: "
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
                "RunComfy status check failed: "
                f"{status_response.status_code} / {status_response.text}"
            )

        status_data = status_response.json()
        status = status_data.get("status", "")

        if status == "completed":
            break

        if status in {"failed", "error", "cancelled", "canceled"}:
            raise RuntimeError(
                f"RunComfy request failed during polling: {status_data}"
            )

        if status not in {"in_queue", "in_progress"}:
            raise RuntimeError(
                f"Unexpected RunComfy status: {status_data}"
            )

        time.sleep(poll_interval)

    result_response = requests.get(
        result_url,
        headers=_headers(api_key, include_content_type=False),
        timeout=60,
    )

    if result_response.status_code >= 400:
        raise RuntimeError(
            "RunComfy result fetch failed: "
            f"{result_response.status_code} / {result_response.text}"
        )

    result_data = result_response.json()

    if result_data.get("status") != "succeeded":
        raise RuntimeError(
            f"RunComfy result is not succeeded: {result_data}"
        )

    return result_data


def extract_output_images(result: dict) -> list[dict]:
    """
    RunComfy 결과에서 이미지 URL을 안전하게 추출합니다.

    지원 구조:
    1. outputs -> node_id -> images
    2. outputs -> node_id -> files / output_files
    3. 위 구조에서 찾지 못하면 result 전체를 재귀 탐색
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
                "node_id": str(node_id),
                "url": url,
                "image": url,
                "filename": filename,
                "subfolder": item.get("subfolder", ""),
                "type": item.get("type", ""),
                "raw": item,
            }
        )

    outputs = result.get("outputs", {})

    if isinstance(outputs, dict):
        for node_id, node_output in outputs.items():
            if not isinstance(node_output, dict):
                continue

            for key in ("images", "files", "output_files"):
                items = node_output.get(key, [])

                if isinstance(items, dict):
                    items = [items]

                if isinstance(items, list):
                    for item in items:
                        add_image_item(item, node_id=str(node_id))

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

    deduped = []
    seen = set()

    for item in images:
        url = item.get("url", "")
        if url and url not in seen:
            deduped.append(item)
            seen.add(url)

    return deduped


def find_nodes_by_class_type(workflow: dict, class_type: str) -> list[str]:
    return [
        str(node_id)
        for node_id, node in workflow.items()
        if isinstance(node, dict)
        and node.get("class_type") == class_type
    ]


def find_first_node_by_class_type(
    workflow: dict,
    class_type: str,
) -> str:
    node_ids = find_nodes_by_class_type(workflow, class_type)

    if not node_ids:
        raise KeyError(
            f"Node with class_type='{class_type}' was not found."
        )

    return node_ids[0]


def _require_node(
    workflow: dict,
    node_id: str,
    expected_class_type: str | None = None,
    description: str = "",
) -> dict:
    node_id = str(node_id)

    if node_id not in workflow or not isinstance(workflow[node_id], dict):
        label = description or f"node {node_id}"
        raise KeyError(f"{label} was not found in workflow.")

    node = workflow[node_id]

    if expected_class_type:
        actual_class_type = node.get("class_type", "")
        if actual_class_type != expected_class_type:
            label = description or f"node {node_id}"
            raise ValueError(
                f"{label} expected class_type='{expected_class_type}', "
                f"but found '{actual_class_type}'."
            )

    return node


def _set_image_input(
    workflow: dict,
    node_id: str,
    image_value: str,
) -> None:
    """
    LoadImageFromUrl 노드에 원격 이미지 URL을 주입합니다.
    """
    if not str(image_value or "").strip():
        raise ValueError(
            f"Image URL for node {node_id} is empty."
        )

    node = _require_node(
        workflow,
        node_id,
        expected_class_type="LoadImageFromUrl",
        description=f"Image input node {node_id}",
    )

    inputs = node.setdefault("inputs", {})
    inputs["image"] = str(image_value).strip()

    if "keep_alpha_channel" in inputs:
        inputs["keep_alpha_channel"] = False

    if "output_mode" in inputs:
        inputs["output_mode"] = False


def _extract_save_node_images(
    result_data: dict,
    save_node_id: str,
) -> list[dict]:
    extracted_images = extract_output_images(result_data)

    save_node_images = [
        item
        for item in extracted_images
        if str(item.get("node_id", "")) == str(save_node_id)
    ]

    # RunComfy 응답에 type='output'이 있으면 그것을 우선 사용합니다.
    # type 필드가 없는 응답도 지원합니다.
    typed_output_images = [
        item
        for item in save_node_images
        if item.get("raw", {}).get("type") == "output"
    ]

    return typed_output_images or save_node_images


def character_filter_to_name(character_filter: str) -> str:
    if character_filter == "C1":
        return "boy"
    if character_filter == "C2":
        return "girl"

    return str(character_filter).lower().replace(" ", "_")


def _run_workflow(
    api_key: str,
    deployment_id: str,
    workflow: dict,
    poll_interval: int,
    timeout_seconds: int,
) -> tuple[dict, dict]:
    request_data = submit_runcomfy_dynamic_workflow(
        api_key=api_key,
        deployment_id=deployment_id,
        workflow_api_json=workflow,
    )

    status_url = request_data.get("status_url")
    result_url = request_data.get("result_url")

    if not status_url or not result_url:
        raise RuntimeError(
            "RunComfy response does not include status/result URL: "
            f"{request_data}"
        )

    result_data = poll_runcomfy_result(
        api_key=api_key,
        status_url=status_url,
        result_url=result_url,
        poll_interval=poll_interval,
        timeout_seconds=timeout_seconds,
    )

    return request_data, result_data


# =========================
# Step 1. CSV Parser Test
# =========================
def patch_csv_parser_test_workflow(
    workflow: dict,
    storyboard_input_config: dict,
) -> dict:
    workflow = deepcopy(workflow)

    storyboard_input = storyboard_input_config.get(
        "storyboard_input",
        storyboard_input_config,
    )

    csv_text = storyboard_input.get("csv_text", "")
    shot_filter = storyboard_input.get("shot_filter", "ALL")
    custom_shot_ids = storyboard_input.get("custom_shot_ids", "")

    if not str(csv_text).strip():
        raise ValueError(
            "csv_text is empty. Upload a CSV file first."
        )

    csv_parser_node_id = find_first_node_by_class_type(
        workflow,
        "CSVStoryboardParser",
    )

    inputs = workflow[csv_parser_node_id].setdefault("inputs", {})
    inputs["input_mode"] = "text"
    inputs["csv_file"] = "CUSTOM"
    inputs["csv_text"] = csv_text
    inputs["shot_filter"] = shot_filter
    inputs["custom_shot_ids"] = custom_shot_ids

    seed = random.randint(1, 4_294_967_295)
    filename_prefix = f"csv_parser_test_{seed}"

    for node_id in find_nodes_by_class_type(workflow, "KSampler"):
        inputs = workflow[node_id].setdefault("inputs", {})
        if "seed" in inputs:
            inputs["seed"] = seed

    for node_id, node in workflow.items():
        if not isinstance(node, dict):
            continue

        inputs = node.get("inputs", {})
        if (
            isinstance(inputs, dict)
            and "seed" in inputs
            and isinstance(inputs["seed"], int)
        ):
            inputs["seed"] = seed

    for node_id in find_nodes_by_class_type(workflow, "SaveImage"):
        inputs = workflow[node_id].setdefault("inputs", {})
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

    request_data, result_data = _run_workflow(
        api_key=api_key,
        deployment_id=deployment_id,
        workflow=workflow,
        poll_interval=poll_interval,
        timeout_seconds=timeout_seconds,
    )

    return {
        "request": request_data,
        "result": result_data,
        "images": extract_output_images(result_data),
        "workflow_api_json": workflow,
    }


# ======================================
# Step 2A. Character Appearance
# ======================================
def patch_face_workflow(
    workflow: dict,
    config: dict,
) -> dict:
    """
    Character Appearance Generation(1).json 기준:

    - 11: CSVStoryboardParser
    - 17: CharacterRegistryParser
    - 19: PortraitMasterBaseCharacter
    - 18: PortraitMasterSkinDetails
    - 14: AILab_QwenVL
    - 15: KSampler
    - 16: SaveImage

    중요:
    app.py의 일부 legacy config에는
    shot='Head and shoulders portrait', weight=0 등이 남아 있습니다.
    그러나 현재 workflow는 Full body + workflow 고정 weight를 기준으로 하므로
    사용자 UI에서 실제 선택하는 appearance field만 patch하고
    shot/weight 등의 workflow 고정값은 덮어쓰지 않습니다.
    """
    workflow = deepcopy(workflow)

    storyboard_input = config.get("storyboard_input", {})
    csv_config = config.get("csvstoryboardparser", {})
    character_config = config.get("character_registry_parser", {})
    base_character_config = config.get(
        "portrait_master_base_character",
        {},
    )
    skin_config = config.get(
        "portrait_master_skin_details",
        {},
    )

    csv_text = (
        csv_config.get("csv_text")
        or storyboard_input.get("csv_text", "")
    )
    shot_filter = (
        csv_config.get("shot_filter")
        or storyboard_input.get("shot_filter", "ALL")
    )
    custom_shot_ids = (
        csv_config.get("custom_shot_ids")
        or storyboard_input.get("custom_shot_ids", "")
    )

    if not str(csv_text).strip():
        raise ValueError(
            "csv_text is empty. Upload a CSV file first."
        )

    character_filter = character_config.get(
        "character_filter",
        "C1",
    )
    character_name = character_filter_to_name(
        character_filter
    )

    seed = random.randint(1, 4_294_967_295)
    filename_prefix = (
        f"character_appearance_{character_name}_{seed}"
    )

    # 11: CSVStoryboardParser
    csv_node = _require_node(
        workflow,
        "11",
        "CSVStoryboardParser",
        "Step 2A CSVStoryboardParser",
    )
    csv_inputs = csv_node.setdefault("inputs", {})
    csv_inputs["input_mode"] = "text"
    csv_inputs["csv_file"] = "CUSTOM"
    csv_inputs["csv_text"] = csv_text
    csv_inputs["shot_filter"] = shot_filter
    csv_inputs["custom_shot_ids"] = custom_shot_ids

    # 17: CharacterRegistryParser
    registry_node = _require_node(
        workflow,
        "17",
        "CharacterRegistryParser",
        "Step 2A CharacterRegistryParser",
    )
    registry_inputs = registry_node.setdefault("inputs", {})
    registry_inputs["character_filter"] = character_filter
    registry_inputs["custom_character_id"] = (
        character_config.get("custom_character_id", "")
    )
    registry_inputs["age"] = character_config.get("age", 9)
    registry_inputs["include_character_id"] = (
        character_config.get("include_character_id", "false")
    )

    # 19: PortraitMasterBaseCharacter
    # UI에서 실제 선택 가능한 appearance 값만 반영합니다.
    appearance_keys = (
        "nationality_1",
        "body_type",
        "eyes_color",
        "eyes_shape",
        "lips_color",
        "lips_shape",
        "facial_expression",
        "face_shape",
        "hair_style",
        "hair_color",
        "hair_length",
    )

    base_node = _require_node(
        workflow,
        "19",
        "PortraitMasterBaseCharacter",
        "Step 2A PortraitMasterBaseCharacter",
    )
    base_inputs = base_node.setdefault("inputs", {})

    for key in appearance_keys:
        if (
            key in base_character_config
            and key in base_inputs
        ):
            base_inputs[key] = base_character_config[key]

    # PortraitMaster의 API Format에서는 UI의 "randomize" 문자열을
    # INT seed로 변환해야 RunComfy prompt validation을 통과합니다.
    if "seed" in base_inputs:
        base_inputs["seed"] = seed

    # 18: PortraitMasterSkinDetails
    skin_node = _require_node(
        workflow,
        "18",
        "PortraitMasterSkinDetails",
        "Step 2A PortraitMasterSkinDetails",
    )
    skin_inputs = skin_node.setdefault("inputs", {})

    for key, value in skin_config.items():
        if key in skin_inputs:
            skin_inputs[key] = value

    if "seed" in skin_inputs:
        skin_inputs["seed"] = seed

    # 14: QwenVL seed / attention
    qwen_node = _require_node(
        workflow,
        "14",
        "AILab_QwenVL",
        "Step 2A QwenVL",
    )
    qwen_inputs = qwen_node.setdefault("inputs", {})

    if "seed" in qwen_inputs:
        qwen_inputs["seed"] = seed

    if "attention_mode" in qwen_inputs:
        qwen_inputs["attention_mode"] = "auto"

    # 15: KSampler seed
    sampler_node = _require_node(
        workflow,
        "15",
        "KSampler",
        "Step 2A KSampler",
    )
    sampler_node.setdefault("inputs", {})["seed"] = seed

    # 16: SaveImage
    save_node = _require_node(
        workflow,
        "16",
        "SaveImage",
        "Step 2A SaveImage",
    )
    save_node.setdefault("inputs", {})[
        "filename_prefix"
    ] = filename_prefix

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

    request_data, result_data = _run_workflow(
        api_key=api_key,
        deployment_id=deployment_id,
        workflow=workflow,
        poll_interval=poll_interval,
        timeout_seconds=timeout_seconds,
    )

    raw_images = _extract_save_node_images(
        result_data,
        save_node_id="16",
    )

    character_filter = config.get(
        "character_registry_parser",
        {},
    ).get("character_filter", "C1")

    if character_filter == "C1":
        label_prefix = "Boy Appearance"
    elif character_filter == "C2":
        label_prefix = "Girl Appearance"
    else:
        label_prefix = "Character Appearance"

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


# ======================================
# Step 2B. Reference-based Outfit Change
# ======================================
def patch_body_workflow(
    workflow: dict,
    config: dict,
) -> dict:
    """
    Reference-based_Outfit_Change.json 기준:

    - 34: Source Character
    - 35: Top reference
    - 38: Bottom reference
    - 37: Shoes reference
    - 36: Single Outfit Reference
    - 29: easy ifElse
          False = Separate Garments
          True  = Single Outfit Reference
    - 19: KSampler
    - 17: SaveImage
    """
    workflow = deepcopy(workflow)

    outfit_config = config.get(
        "outfit_change",
        config.get("body_generation", config),
    )

    character_filter = outfit_config.get(
        "character_filter",
        "C1",
    )
    character_name = character_filter_to_name(
        character_filter
    )

    character_image_url = str(
        outfit_config.get("character_image_url")
        or outfit_config.get("face_image_url")
        or outfit_config.get("reference_image_url")
        or ""
    ).strip()

    input_mode = outfit_config.get(
        "input_mode",
        "Separate Garments",
    )

    garment_references = outfit_config.get(
        "garment_references",
        {},
    )

    top_reference_url = str(
        garment_references.get("top", "") or ""
    ).strip()
    bottom_reference_url = str(
        garment_references.get("bottom", "") or ""
    ).strip()
    shoes_reference_url = str(
        garment_references.get("shoes", "") or ""
    ).strip()

    single_outfit_reference = str(
        outfit_config.get(
            "single_outfit_reference",
            "",
        )
        or ""
    ).strip()

    if not character_image_url:
        raise ValueError(
            "character_image_url is empty. "
            "Generate the Step 2A character appearance first."
        )

    if input_mode not in {
        "Separate Garments",
        "Single Outfit Reference",
    }:
        raise ValueError(
            "Unsupported outfit input_mode: "
            f"{input_mode}"
        )

    # 34: Image 1 = Source Character
    _set_image_input(
        workflow,
        "34",
        character_image_url,
    )

    branch_node = _require_node(
        workflow,
        "29",
        "easy ifElse",
        "Step 2B Garment Input Mode switch",
    )

    if input_mode == "Separate Garments":
        missing = [
            name
            for name, url in (
                ("top", top_reference_url),
                ("bottom", bottom_reference_url),
                ("shoes", shoes_reference_url),
            )
            if not url
        ]

        if missing:
            raise ValueError(
                "Missing separate garment reference(s): "
                + ", ".join(missing)
            )

        # Stitch order = Top -> Bottom -> Shoes
        _set_image_input(
            workflow,
            "35",
            top_reference_url,
        )
        _set_image_input(
            workflow,
            "38",
            bottom_reference_url,
        )
        _set_image_input(
            workflow,
            "37",
            shoes_reference_url,
        )

        branch_node.setdefault("inputs", {})[
            "boolean"
        ] = False

    else:
        if not single_outfit_reference:
            raise ValueError(
                "single_outfit_reference is empty."
            )

        _set_image_input(
            workflow,
            "36",
            single_outfit_reference,
        )

        branch_node.setdefault("inputs", {})[
            "boolean"
        ] = True

    seed = random.randint(1, 4_294_967_295)
    filename_prefix = (
        f"outfit_{character_name}_{seed}"
    )

    sampler_node = _require_node(
        workflow,
        "19",
        "KSampler",
        "Step 2B KSampler",
    )
    sampler_node.setdefault("inputs", {})["seed"] = seed

    save_node = _require_node(
        workflow,
        "17",
        "SaveImage",
        "Step 2B SaveImage",
    )
    save_node.setdefault("inputs", {})[
        "filename_prefix"
    ] = filename_prefix

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

    request_data, result_data = _run_workflow(
        api_key=api_key,
        deployment_id=deployment_id,
        workflow=workflow,
        poll_interval=poll_interval,
        timeout_seconds=timeout_seconds,
    )

    raw_images = _extract_save_node_images(
        result_data,
        save_node_id="17",
    )

    outfit_config = config.get(
        "outfit_change",
        config.get("body_generation", {}),
    )

    character_filter = outfit_config.get(
        "character_filter",
        "C1",
    )

    if character_filter == "C1":
        label_prefix = "Boy Outfit Reference"
    elif character_filter == "C2":
        label_prefix = "Girl Outfit Reference"
    else:
        label_prefix = "Outfit Reference"

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


# ======================================
# Step 3. Reference-based Scene Generation
# ======================================
def patch_scene_workflow(
    workflow: dict,
    config: dict,
) -> dict:
    """
    Reference-based Scene Generation(1).json 기준:

    - 33: Image 1 - Boy character reference
    - 34: Image 2 - Girl character reference
    - 25: CSVStoryboardParser
    - 27: ScenePromptBuilder
    - 28: Fixed Qwen instruction
    - 31: AILab_QwenVL
    - 29: PromptLine
    - 15: RandomNoise
    - 32: SaveImage

    현재 workflow 내부에서
    CSVStoryboardParser -> ScenePromptBuilder -> fixed instruction -> QwenVL
    흐름을 구성하므로 backend에서 별도의 structured JSON prompt를
    다시 조립하지 않습니다.
    """
    workflow = deepcopy(workflow)

    storyboard_input = config.get(
        "storyboard_input",
        {},
    )
    scene_config = config.get(
        "scene_generation",
        {},
    )

    csv_text = storyboard_input.get(
        "csv_text",
        "",
    )
    shot_filter = (
        scene_config.get("shot_filter")
        or storyboard_input.get("shot_filter", "ALL")
    )
    custom_shot_ids = (
        scene_config.get("custom_shot_ids")
        or storyboard_input.get("custom_shot_ids", "")
    )

    reference_images = scene_config.get(
        "reference_images",
        {},
    )

    boy_body_image_url = (
        reference_images
        .get("image_1_boy_body", {})
        .get("image")
        or scene_config.get("boy_body_image_url")
        or ""
    )

    girl_body_image_url = (
        reference_images
        .get("image_2_girl_body", {})
        .get("image")
        or scene_config.get("girl_body_image_url")
        or ""
    )

    if not str(csv_text).strip():
        raise ValueError(
            "csv_text is empty. Upload a CSV file first."
        )

    if not boy_body_image_url:
        raise ValueError(
            "boy_body_image_url is empty. "
            "Generate Image 1 - Boy outfit reference first."
        )

    if not girl_body_image_url:
        raise ValueError(
            "girl_body_image_url is empty. "
            "Generate Image 2 - Girl outfit reference first."
        )

    # 33 / 34: Character references
    _set_image_input(
        workflow,
        "33",
        boy_body_image_url,
    )
    _set_image_input(
        workflow,
        "34",
        girl_body_image_url,
    )

    # 25: CSVStoryboardParser
    csv_node = _require_node(
        workflow,
        "25",
        "CSVStoryboardParser",
        "Step 3 CSVStoryboardParser",
    )
    csv_inputs = csv_node.setdefault("inputs", {})
    csv_inputs["input_mode"] = "text"
    csv_inputs["csv_file"] = "CUSTOM"
    csv_inputs["csv_text"] = csv_text
    csv_inputs["shot_filter"] = shot_filter
    csv_inputs["custom_shot_ids"] = custom_shot_ids

    seed = random.randint(1, 4_294_967_295)
    filename_prefix = f"scene_{seed}"

    # 31: QwenVL
    qwen_node = _require_node(
        workflow,
        "31",
        "AILab_QwenVL",
        "Step 3 QwenVL",
    )
    qwen_inputs = qwen_node.setdefault("inputs", {})

    if "seed" in qwen_inputs:
        qwen_inputs["seed"] = seed

    if "attention_mode" in qwen_inputs:
        qwen_inputs["attention_mode"] = "auto"

    # 15: RandomNoise
    noise_node = _require_node(
        workflow,
        "15",
        "RandomNoise",
        "Step 3 RandomNoise",
    )
    noise_node.setdefault("inputs", {})[
        "noise_seed"
    ] = seed

    # 32: SaveImage
    save_node = _require_node(
        workflow,
        "32",
        "SaveImage",
        "Step 3 SaveImage",
    )
    save_node.setdefault("inputs", {})[
        "filename_prefix"
    ] = filename_prefix

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

    request_data, result_data = _run_workflow(
        api_key=api_key,
        deployment_id=deployment_id,
        workflow=workflow,
        poll_interval=poll_interval,
        timeout_seconds=timeout_seconds,
    )

    raw_images = _extract_save_node_images(
        result_data,
        save_node_id="32",
    )

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


# ======================================
# Step 4. Camera Refinement
# ======================================
def patch_camera_refinement_workflow(
    workflow: dict,
    config: dict,
) -> dict:
    """
    Camera_Refinement.json 기준:

    - 26: LoadImageFromUrl (Source Scene)
    - 27: QwenMultiangleCameraNode
    - 14: TextEncodeQwenImageEditPlusAdvance_lrzjason
    - 12: KSampler
    - 11: SaveImage

    QwenMultiangleCameraNode는 workflow JSON에 이미 존재하므로
    backend에서 새 노드를 생성하지 않고 기존 27번 노드의 입력값만 수정합니다.
    """
    workflow = deepcopy(workflow)

    camera_config = config.get(
        "camera_angle_refinement",
        {},
    )
    input_scene = camera_config.get(
        "input_scene",
        {},
    )
    camera_control = camera_config.get(
        "camera_control",
        {},
    )

    scene_image_url = str(
        input_scene.get("image")
        or camera_config.get("scene_image_url")
        or ""
    ).strip()

    if not scene_image_url:
        raise ValueError(
            "scene_image_url is empty. "
            "Generate and select a Step 3 scene first."
        )

    horizontal_angle = int(
        camera_control.get(
            "horizontal_angle",
            0,
        )
    )
    vertical_angle = int(
        camera_control.get(
            "vertical_angle",
            0,
        )
    )
    zoom = float(
        camera_control.get(
            "zoom",
            5,
        )
    )
    default_prompts = bool(
        camera_control.get(
            "default_prompts",
            True,
        )
    )
    camera_view = bool(
        camera_control.get(
            "camera_view",
            False,
        )
    )

    seed = random.randint(1, 4_294_967_295)
    filename_prefix = f"camera_refined_{seed}"

    # 26: Source Scene URL
    _set_image_input(
        workflow,
        "26",
        scene_image_url,
    )

    # LoadImageFromUrl 구현에 따라 image/url 어느 입력을 참조하더라도
    # 동일한 source scene을 사용하도록 둘 다 설정합니다.
    source_node = _require_node(
        workflow,
        "26",
        "LoadImageFromUrl",
        "Step 4 Source Scene",
    )
    source_inputs = source_node.setdefault("inputs", {})
    source_inputs["image"] = scene_image_url
    if "url" in source_inputs:
        source_inputs["url"] = scene_image_url

    # 27: 기존 Qwen Multiangle Camera 노드 값만 patch
    camera_node = _require_node(
        workflow,
        "27",
        "QwenMultiangleCameraNode",
        "Step 4 Qwen Multiangle Camera",
    )
    camera_inputs = camera_node.setdefault("inputs", {})
    camera_inputs["horizontal_angle"] = horizontal_angle
    camera_inputs["vertical_angle"] = vertical_angle
    camera_inputs["zoom"] = zoom
    camera_inputs["default_prompts"] = default_prompts
    camera_inputs["camera_view"] = camera_view
    camera_inputs["image"] = ["26", 0]

    # 14: 기존 연결을 명시적으로 유지
    encode_node = _require_node(
        workflow,
        "14",
        "TextEncodeQwenImageEditPlusAdvance_lrzjason",
        "Step 4 Qwen Image Edit Text Encoder",
    )
    encode_inputs = encode_node.setdefault("inputs", {})
    encode_inputs["prompt"] = ["27", 0]
    encode_inputs["vl_resize_image1"] = ["26", 0]

    # 12: workflow의 고정 sampling 설정은 유지하고 seed만 변경
    sampler_node = _require_node(
        workflow,
        "12",
        "KSampler",
        "Step 4 KSampler",
    )
    sampler_node.setdefault("inputs", {})["seed"] = seed

    # 11: SaveImage
    save_node = _require_node(
        workflow,
        "11",
        "SaveImage",
        "Step 4 SaveImage",
    )
    save_node.setdefault("inputs", {})[
        "filename_prefix"
    ] = filename_prefix

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

    request_data, result_data = _run_workflow(
        api_key=api_key,
        deployment_id=deployment_id,
        workflow=workflow,
        poll_interval=poll_interval,
        timeout_seconds=timeout_seconds,
    )

    raw_images = _extract_save_node_images(
        result_data,
        save_node_id="11",
    )

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
