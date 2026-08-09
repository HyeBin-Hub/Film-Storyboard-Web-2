import json
import random
import time
from copy import deepcopy
from pathlib import Path

import requests


RUNCOMFY_API_BASE = "https://api.runcomfy.net"

WORKFLOW_DIR = Path(__file__).parent / "workflows"

# 기존 프로젝트 파일명을 유지합니다.
# 첨부한 최신 API-format workflow JSON을 아래 이름으로 workflows 폴더에 저장하세요.
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
    현재 첨부 workflow의 LoadImage 노드 image 값을 교체합니다.
    URL 문자열도 workflow JSON에서 이미 사용되고 있으므로 그대로 전달합니다.
    """
    node = _require_node(
        workflow,
        node_id,
        expected_class_type="LoadImage",
        description=f"Image input node {node_id}",
    )
    node.setdefault("inputs", {})["image"] = image_value


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
    Reference-based Outfit Change(1).json 기준:

    - 26: Character image
    - 33: Top reference
    - 7 : Bottom reference
    - 23: Shoes reference
    - 24: Single outfit reference
    - 29: easy ifElse
          False = Separate Garments (node 12)
          True  = Single Outfit Reference (node 27)
    - 19: KSampler
    - 17: SaveImage

    함수명 patch_body_workflow / run_body_generation은
    app.py와의 기존 연결을 유지하기 위해 그대로 사용합니다.
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

    character_image_url = (
        outfit_config.get("character_image_url")
        or outfit_config.get("face_image_url")
        or outfit_config.get("reference_image_url")
        or ""
    )

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

    # 26: Image 1 = character
    _set_image_input(
        workflow,
        "26",
        character_image_url,
    )

    # 29 branch selection
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
            "33",
            top_reference_url,
        )
        _set_image_input(
            workflow,
            "7",
            bottom_reference_url,
        )
        _set_image_input(
            workflow,
            "23",
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

        # 24 -> scale -> remove background -> ifElse true
        _set_image_input(
            workflow,
            "24",
            single_outfit_reference,
        )

        branch_node.setdefault("inputs", {})[
            "boolean"
        ] = True

    seed = random.randint(1, 4_294_967_295)
    filename_prefix = (
        f"outfit_{character_name}_{seed}"
    )

    # 19: KSampler
    sampler_node = _require_node(
        workflow,
        "19",
        "KSampler",
        "Step 2B KSampler",
    )
    sampler_node.setdefault("inputs", {})["seed"] = seed

    # 17: SaveImage
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

    - 1 : Image 1 - Boy character reference
    - 9 : Image 2 - Girl character reference
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

    # 1 / 9: Character references
    _set_image_input(
        workflow,
        "1",
        boy_body_image_url,
    )
    _set_image_input(
        workflow,
        "9",
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
    Camera Refinement(1).json 기준:

    - 13: Source scene image
    - 36: QwenMultiangleCameraNode
    - 12: KSampler
    - 11: SaveImage

    Step 1 CSV / ScenePromptBuilder / TwoWaySwitch는
    현재 Camera Refinement workflow에서 더 이상 사용하지 않습니다.
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

    scene_image_url = (
        input_scene.get("image")
        or camera_config.get("scene_image_url")
        or ""
    )

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
    zoom = int(
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

    # 13: Source Scene
    _set_image_input(
        workflow,
        "13",
        scene_image_url,
    )

    # 36: Qwen Multiangle Camera
    camera_node = _require_node(
        workflow,
        "36",
        "QwenMultiangleCameraNode",
        "Step 4 QwenMultiangleCameraNode",
    )
    camera_inputs = camera_node.setdefault(
        "inputs",
        {},
    )
    camera_inputs["horizontal_angle"] = horizontal_angle
    camera_inputs["vertical_angle"] = vertical_angle
    camera_inputs["zoom"] = zoom
    camera_inputs["default_prompts"] = default_prompts
    camera_inputs["camera_view"] = camera_view

    # 12: KSampler
    # steps=8 / cfg=1 / euler / simple 등은
    # 현재 workflow의 권장 고정값을 그대로 유지하고 seed만 변경합니다.
    sampler_node = _require_node(
        workflow,
        "12",
        "KSampler",
        "Step 4 KSampler",
    )
    sampler_node.setdefault("inputs", {})[
        "seed"
    ] = seed

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

# import csv
# import io
# import json
# import math
# import time
# import random
# from copy import deepcopy
# from pathlib import Path

# import requests


# RUNCOMFY_API_BASE = "https://api.runcomfy.net"

# WORKFLOW_DIR = Path(__file__).parent / "workflows"
# CSV_PARSER_TEST_WORKFLOW_PATH = WORKFLOW_DIR / "csv_parser_test_workflow_api.json"
# FACE_WORKFLOW_PATH = WORKFLOW_DIR / "face_workflow_api.json"
# BODY_WORKFLOW_PATH = WORKFLOW_DIR / "body_workflow_api.json"
# SCENE_WORKFLOW_PATH = WORKFLOW_DIR / "scene_workflow_api.json"
# CAMERA_REFINEMENT_WORKFLOW_PATH = WORKFLOW_DIR / "camera_refinement_workflow_api.json"


# # =========================
# # Common helpers
# # =========================
# def _headers(api_key: str, include_content_type: bool = True) -> dict:
#     if not api_key:
#         raise ValueError("RunComfy API key is missing.")

#     headers = {
#         "Authorization": f"Bearer {api_key}",
#     }

#     if include_content_type:
#         headers["Content-Type"] = "application/json"

#     return headers


# def load_workflow_api_json(workflow_path: str | Path) -> dict:
#     workflow_path = Path(workflow_path)

#     if not workflow_path.exists():
#         raise FileNotFoundError(f"workflow_api_json file not found: {workflow_path}")

#     with workflow_path.open("r", encoding="utf-8") as f:
#         workflow = json.load(f)

#     # ComfyUI의 일반 화면 저장 형식은 최상위에 nodes/list 구조를 사용합니다.
#     # RunComfy dynamic workflow에는 노드 ID를 key로 사용하는 API Format JSON이 필요합니다.
#     if isinstance(workflow, dict) and isinstance(workflow.get("nodes"), list):
#         raise ValueError(
#             "The workflow is a ComfyUI UI-format JSON. "
#             "Export it again with 'Save (API Format)' and save it as a workflow_api.json file."
#         )

#     return workflow


# def submit_runcomfy_dynamic_workflow(
#     api_key: str,
#     deployment_id: str,
#     workflow_api_json: dict,
# ) -> dict:
#     if not deployment_id:
#         raise ValueError("RunComfy deployment_id is missing.")

#     url = f"{RUNCOMFY_API_BASE}/prod/v2/deployments/{deployment_id}/inference"

#     payload = {
#         "workflow_api_json": workflow_api_json,
#     }

#     response = requests.post(
#         url,
#         headers=_headers(api_key),
#         json=payload,
#         timeout=60,
#     )

#     if response.status_code >= 400:
#         raise RuntimeError(
#             f"RunComfy dynamic workflow submit failed: "
#             f"{response.status_code} / {response.text}"
#         )

#     return response.json()


# def poll_runcomfy_result(
#     api_key: str,
#     status_url: str,
#     result_url: str,
#     poll_interval: int = 10,
#     timeout_seconds: int = 1800,
# ) -> dict:
#     start_time = time.time()

#     while True:
#         if time.time() - start_time > timeout_seconds:
#             raise TimeoutError("RunComfy request timed out.")

#         status_response = requests.get(
#             status_url,
#             headers=_headers(api_key, include_content_type=False),
#             timeout=60,
#         )

#         if status_response.status_code >= 400:
#             raise RuntimeError(
#                 f"RunComfy status check failed: "
#                 f"{status_response.status_code} / {status_response.text}"
#             )

#         status_data = status_response.json()
#         status = status_data.get("status", "")

#         if status == "completed":
#             break

#         if status in {"failed", "error", "cancelled", "canceled"}:
#             raise RuntimeError(f"RunComfy request failed during polling: {status_data}")

#         if status not in {"in_queue", "in_progress"}:
#             raise RuntimeError(f"Unexpected RunComfy status: {status_data}")

#         time.sleep(poll_interval)

#     result_response = requests.get(
#         result_url,
#         headers=_headers(api_key, include_content_type=False),
#         timeout=60,
#     )

#     if result_response.status_code >= 400:
#         raise RuntimeError(
#             f"RunComfy result fetch failed: "
#             f"{result_response.status_code} / {result_response.text}"
#         )

#     result_data = result_response.json()

#     if result_data.get("status") != "succeeded":
#         raise RuntimeError(f"RunComfy result is not succeeded: {result_data}")

#     return result_data


# # def extract_output_images(result: dict) -> list[dict]:
# #     outputs = result.get("outputs", {})
# #     images = []

# #     for node_id, node_output in outputs.items():
# #         if not isinstance(node_output, dict):
# #             continue

# #         for image_item in node_output.get("images", []):
# #             if not isinstance(image_item, dict):
# #                 continue

# #             url = (
# #                 image_item.get("url")
# #                 or image_item.get("image_url")
# #                 or image_item.get("file_url")
# #                 or ""
# #             )

# #             images.append(
# #                 {
# #                     "node_id": node_id,
# #                     "url": url,
# #                     "image": url,
# #                     "filename": image_item.get("filename", ""),
# #                     "subfolder": image_item.get("subfolder", ""),
# #                     "type": image_item.get("type", ""),
# #                     "raw": image_item,
# #                 }
# #             )

# #     return images

# def extract_output_images(result: dict) -> list[dict]:
#     """
#     RunComfy 결과에서 이미지 URL을 최대한 안전하게 추출합니다.

#     지원 구조:
#     1. outputs -> node_id -> images -> url
#     2. outputs -> node_id -> images -> image_url / file_url
#     3. outputs -> node_id -> files / output_files
#     4. result 전체를 재귀적으로 탐색해서 url이 있는 png/jpg/webp 파일 찾기
#     """
#     images = []

#     def add_image_item(item: dict, node_id: str = ""):
#         if not isinstance(item, dict):
#             return

#         url = (
#             item.get("url")
#             or item.get("image")
#             or item.get("image_url")
#             or item.get("file_url")
#             or item.get("download_url")
#             or item.get("path")
#             or ""
#         )

#         filename = item.get("filename", "")

#         # filename이 없으면 url에서 추정
#         if not filename and isinstance(url, str) and "/" in url:
#             filename = url.split("?")[0].rstrip("/").split("/")[-1]

#         if not isinstance(url, str) or not url:
#             return

#         lower_url = url.lower()
#         lower_filename = str(filename).lower()

#         is_image = (
#             lower_url.endswith((".png", ".jpg", ".jpeg", ".webp"))
#             or ".png" in lower_url
#             or ".jpg" in lower_url
#             or ".jpeg" in lower_url
#             or ".webp" in lower_url
#             or lower_filename.endswith((".png", ".jpg", ".jpeg", ".webp"))
#         )

#         if not is_image:
#             return

#         images.append(
#             {
#                 "node_id": node_id,
#                 "url": url,
#                 "image": url,
#                 "filename": filename,
#                 "subfolder": item.get("subfolder", ""),
#                 "type": item.get("type", ""),
#                 "raw": item,
#             }
#         )

#     # 1차: RunComfy outputs 구조 우선 탐색
#     outputs = result.get("outputs", {})

#     if isinstance(outputs, dict):
#         for node_id, node_output in outputs.items():
#             if not isinstance(node_output, dict):
#                 continue

#             for key in ["images", "files", "output_files"]:
#                 items = node_output.get(key, [])

#                 if isinstance(items, dict):
#                     items = [items]

#                 if isinstance(items, list):
#                     for item in items:
#                         add_image_item(item, node_id=str(node_id))

#     # 2차: 그래도 못 찾으면 result 전체 재귀 탐색
#     if not images:
#         def walk(obj, node_id: str = ""):
#             if isinstance(obj, dict):
#                 add_image_item(obj, node_id=node_id)

#                 for key, value in obj.items():
#                     next_node_id = node_id
#                     if str(key).isdigit():
#                         next_node_id = str(key)
#                     walk(value, node_id=next_node_id)

#             elif isinstance(obj, list):
#                 for value in obj:
#                     walk(value, node_id=node_id)

#         walk(result)

#     # 중복 제거
#     deduped = []
#     seen = set()

#     for item in images:
#         key = item.get("url", "")
#         if key and key not in seen:
#             deduped.append(item)
#             seen.add(key)

#     return deduped


# def find_nodes_by_class_type(workflow: dict, class_type: str) -> list[str]:
#     node_ids = []

#     for node_id, node in workflow.items():
#         if not isinstance(node, dict):
#             continue

#         if node.get("class_type") == class_type:
#             node_ids.append(str(node_id))

#     return node_ids


# def find_first_node_by_class_type(workflow: dict, class_type: str) -> str:
#     node_ids = find_nodes_by_class_type(workflow, class_type)

#     if not node_ids:
#         raise KeyError(f"Node with class_type='{class_type}' was not found.")

#     return node_ids[0]


# def character_filter_to_name(character_filter: str) -> str:
#     if character_filter == "C1":
#         return "boy"
#     if character_filter == "C2":
#         return "girl"
#     return str(character_filter).lower().replace(" ", "_")


# # =========================
# # CSV Parser Test
# # =========================
# def patch_csv_parser_test_workflow(workflow: dict, storyboard_input_config: dict) -> dict:
#     workflow = deepcopy(workflow)

#     storyboard_input = storyboard_input_config.get("storyboard_input", storyboard_input_config)

#     csv_text = storyboard_input.get("csv_text", "")
#     shot_filter = storyboard_input.get("shot_filter", "ALL")
#     custom_shot_ids = storyboard_input.get("custom_shot_ids", "")

#     if not csv_text.strip():
#         raise ValueError("csv_text is empty. Upload a CSV file first.")

#     csv_parser_node_id = find_first_node_by_class_type(workflow, "CSVStoryboardParser")

#     workflow[csv_parser_node_id]["inputs"]["csv_file"] = "CUSTOM"
#     workflow[csv_parser_node_id]["inputs"]["csv_text"] = csv_text
#     workflow[csv_parser_node_id]["inputs"]["shot_filter"] = shot_filter
#     workflow[csv_parser_node_id]["inputs"]["custom_shot_ids"] = custom_shot_ids

#     seed = random.randint(1, 4_294_967_295)
#     filename_prefix = f"csv_parser_test_{seed}"

#     for node_id in find_nodes_by_class_type(workflow, "KSampler"):
#         inputs = workflow[node_id].get("inputs", {})
#         if "seed" in inputs:
#             inputs["seed"] = seed

#     for node_id, node in workflow.items():
#         if not isinstance(node, dict):
#             continue

#         inputs = node.get("inputs", {})
#         if isinstance(inputs, dict) and "seed" in inputs and isinstance(inputs["seed"], int):
#             inputs["seed"] = seed

#     for node_id in find_nodes_by_class_type(workflow, "SaveImage"):
#         inputs = workflow[node_id].get("inputs", {})
#         if "filename_prefix" in inputs:
#             inputs["filename_prefix"] = filename_prefix

#     return workflow


# def run_csv_parser_test(
#     api_key: str,
#     deployment_id: str,
#     storyboard_input_config: dict,
#     workflow_path: str | Path = CSV_PARSER_TEST_WORKFLOW_PATH,
#     poll_interval: int = 10,
#     timeout_seconds: int = 1800,
# ) -> dict:
#     base_workflow = load_workflow_api_json(workflow_path)

#     workflow = patch_csv_parser_test_workflow(
#         workflow=base_workflow,
#         storyboard_input_config=storyboard_input_config,
#     )

#     request_data = submit_runcomfy_dynamic_workflow(
#         api_key=api_key,
#         deployment_id=deployment_id,
#         workflow_api_json=workflow,
#     )

#     status_url = request_data.get("status_url")
#     result_url = request_data.get("result_url")

#     if not status_url or not result_url:
#         raise RuntimeError(
#             f"RunComfy response does not include status/result URL: {request_data}"
#         )

#     result_data = poll_runcomfy_result(
#         api_key=api_key,
#         status_url=status_url,
#         result_url=result_url,
#         poll_interval=poll_interval,
#         timeout_seconds=timeout_seconds,
#     )

#     images = extract_output_images(result_data)

#     return {
#         "request": request_data,
#         "result": result_data,
#         "images": images,
#         "workflow_api_json": workflow,
#     }


# # =========================
# # Face Generation
# # =========================
# def patch_face_workflow(workflow: dict, config: dict) -> dict:
#     workflow = deepcopy(workflow)

#     storyboard_input = config.get("storyboard_input", {})
#     csv_config = config.get("csvstoryboardparser", {})
#     character_config = config.get("character_registry_parser", {})
#     base_prompt_config = config.get("base_background_clothing_prompt", {})
#     base_character_config = config.get("portrait_master_base_character", {})
#     skin_config = config.get("portrait_master_skin_details", {})

#     csv_text = csv_config.get("csv_text") or storyboard_input.get("csv_text", "")
#     shot_filter = csv_config.get("shot_filter") or storyboard_input.get("shot_filter", "ALL")
#     custom_shot_ids = csv_config.get("custom_shot_ids") or storyboard_input.get("custom_shot_ids", "")

#     if not csv_text.strip():
#         raise ValueError("csv_text is empty. Upload a CSV file first.")

#     character_filter = character_config.get("character_filter", "C2")
#     character_name = character_filter_to_name(character_filter)

#     seed = random.randint(1, 4_294_967_295)
#     filename_prefix = f"face_{character_name}_{seed}"

#     workflow["1002"]["inputs"]["csv_file"] = "CUSTOM"
#     workflow["1002"]["inputs"]["csv_text"] = csv_text
#     workflow["1002"]["inputs"]["shot_filter"] = shot_filter
#     workflow["1002"]["inputs"]["custom_shot_ids"] = custom_shot_ids

#     workflow["1000"]["inputs"]["character_filter"] = character_filter
#     workflow["1000"]["inputs"]["custom_character_id"] = character_config.get("custom_character_id", "")
#     workflow["1000"]["inputs"]["age"] = character_config.get("age", 9)
#     workflow["1000"]["inputs"]["include_character_id"] = character_config.get("include_character_id", "false")

#     workflow["1007"]["inputs"]["text"] = base_prompt_config.get(
#         "text",
#         "gray background, white t-shirt",
#     )

#     for key, value in base_character_config.items():
#         if key in workflow["1003"]["inputs"]:
#             workflow["1003"]["inputs"][key] = value

#     for key, value in skin_config.items():
#         if key in workflow["1004"]["inputs"]:
#             workflow["1004"]["inputs"][key] = value

#     if "999" in workflow and "seed" in workflow["999"]["inputs"]:
#         workflow["999"]["inputs"]["seed"] = seed

#     if "1014" in workflow and "seed" in workflow["1014"]["inputs"]:
#         workflow["1014"]["inputs"]["seed"] = seed

#     workflow["1018"]["inputs"]["seed"] = seed
#     workflow["1019"]["inputs"]["filename_prefix"] = filename_prefix

#     return workflow


# def run_face_generation(
#     api_key: str,
#     deployment_id: str,
#     config: dict,
#     workflow_path: str | Path = FACE_WORKFLOW_PATH,
#     poll_interval: int = 10,
#     timeout_seconds: int = 1800,
# ) -> dict:
#     base_workflow = load_workflow_api_json(workflow_path)

#     workflow = patch_face_workflow(
#         workflow=base_workflow,
#         config=config,
#     )

#     request_data = submit_runcomfy_dynamic_workflow(
#         api_key=api_key,
#         deployment_id=deployment_id,
#         workflow_api_json=workflow,
#     )

#     status_url = request_data.get("status_url")
#     result_url = request_data.get("result_url")

#     if not status_url or not result_url:
#         raise RuntimeError(
#             f"RunComfy response does not include status/result URL: {request_data}"
#         )

#     result_data = poll_runcomfy_result(
#         api_key=api_key,
#         status_url=status_url,
#         result_url=result_url,
#         poll_interval=poll_interval,
#         timeout_seconds=timeout_seconds,
#     )

#     raw_images = extract_output_images(result_data)
    
#     save_node_images = [
#         item
#         for item in raw_images
#         if str(item.get("node_id", "")) == "1019"
#     ]
    
#     typed_output_images = [
#         item
#         for item in save_node_images
#         if item.get("raw", {}).get("type") == "output"
#     ]
    
#     raw_images = typed_output_images or save_node_images

#     character_filter = config.get("character_registry_parser", {}).get(
#         "character_filter",
#         "C2",
#     )    

#     if character_filter == "C1":
#         label_prefix = "Boy Face"
#     elif character_filter == "C2":
#         label_prefix = "Girl Face"
#     else:
#         label_prefix = "Face"

#     images = []

#     for idx, item in enumerate(raw_images, start=1):
#         url = item.get("url") or item.get("image") or ""

#         if not url:
#             continue

#         images.append(
#             {
#                 "label": f"{label_prefix} {idx}",
#                 "image": url,
#                 "url": url,
#                 "filename": item.get("filename", ""),
#                 "node_id": item.get("node_id", ""),
#                 "raw": item.get("raw", {}),
#             }
#         )

#     return {
#         "request": request_data,
#         "result": result_data,
#         "images": images,
#         "workflow_api_json": workflow,
#     }


# # =========================
# # Body Generation
# # =========================
# def patch_body_workflow(workflow: dict, config: dict) -> dict:
#     """
#     Step 2B Full-Body Reference Generation workflow patch.

#     body_workflow_api.json 기준 주요 노드:
#     - 1239: LoadImageFromUrl
#     - 1238: body/outfit prompt text
#     - 1065: ThinkingLLM
#     - 1048: KSampler
#     - 1244: SaveImage
#     """
#     workflow = deepcopy(workflow)

#     body_config = config.get("body_generation", config)

#     character_filter = body_config.get("character_filter", "C1")
#     character_name = character_filter_to_name(character_filter)

#     face_image_url = (
#         body_config.get("face_image_url")
#         or body_config.get("face_reference_image")
#         or body_config.get("reference_image_url")
#         or ""
#     )

#     body_prompt = body_config.get("body_prompt", "")

#     if not face_image_url:
#         raise ValueError(
#             "face_image_url is empty. Generate a face reference first."
#         )

#     if not body_prompt.strip():
#         raise ValueError(
#             "body_prompt is empty. Enter a full-body outfit prompt first."
#         )

#     seed = random.randint(1, 4_294_967_295)
#     filename_prefix = f"body_{character_name}_{seed}"

#     # 1239: Load Image From URL
#     workflow["1239"]["inputs"]["image"] = face_image_url
#     workflow["1239"]["inputs"]["keep_alpha_channel"] = False
#     workflow["1239"]["inputs"]["output_mode"] = False

#     # 1238: text / outfit prompt
#     workflow["1238"]["inputs"]["text"] = body_prompt

#     # 1065: ThinkingLLM seed
#     if "1065" in workflow and "seed" in workflow["1065"]["inputs"]:
#         workflow["1065"]["inputs"]["seed"] = seed

#     # 1048: KSampler
#     workflow["1048"]["inputs"]["seed"] = seed

#     # 1244: SaveImage
#     workflow["1244"]["inputs"]["filename_prefix"] = filename_prefix

#     return workflow


# def run_body_generation(
#     api_key: str,
#     deployment_id: str,
#     config: dict,
#     workflow_path: str | Path = BODY_WORKFLOW_PATH,
#     poll_interval: int = 10,
#     timeout_seconds: int = 1800,
# ) -> dict:
#     base_workflow = load_workflow_api_json(workflow_path)

#     workflow = patch_body_workflow(
#         workflow=base_workflow,
#         config=config,
#     )

#     request_data = submit_runcomfy_dynamic_workflow(
#         api_key=api_key,
#         deployment_id=deployment_id,
#         workflow_api_json=workflow,
#     )

#     status_url = request_data.get("status_url")
#     result_url = request_data.get("result_url")

#     if not status_url or not result_url:
#         raise RuntimeError(
#             f"RunComfy response does not include status/result URL: {request_data}"
#         )

#     result_data = poll_runcomfy_result(
#         api_key=api_key,
#         status_url=status_url,
#         result_url=result_url,
#         poll_interval=poll_interval,
#         timeout_seconds=timeout_seconds,
#     )

#     raw_images = extract_output_images(result_data)

#     # Step 2B에서는 최종 SaveImage 노드인 1244 결과만 사용해야 함.
#     # 1239는 LoadImageFromUrl 입력 face reference라서 제외해야 함.
#     save_node_images = [
#         item
#         for item in raw_images
#         if str(item.get("node_id", "")) == "1244"
#     ]
    
#     typed_output_images = [
#         item
#         for item in save_node_images
#         if item.get("raw", {}).get("type") == "output"
#     ]
    
#     raw_images = typed_output_images or save_node_images
    
#     character_filter = config.get("body_generation", {}).get(
#         "character_filter",
#         "C1",
#     )

#     if character_filter == "C1":
#         label_prefix = "Boy Body"
#     elif character_filter == "C2":
#         label_prefix = "Girl Body"
#     else:
#         label_prefix = "Body"

#     images = []

#     for idx, item in enumerate(raw_images, start=1):
#         url = item.get("url") or item.get("image") or ""

#         if not url:
#             continue

#         images.append(
#             {
#                 "label": f"{label_prefix} {idx}",
#                 "image": url,
#                 "url": url,
#                 "filename": item.get("filename", ""),
#                 "node_id": item.get("node_id", ""),
#                 "raw": item.get("raw", {}),
#             }
#         )

#     return {
#         "request": request_data,
#         "result": result_data,
#         "images": images,
#         "workflow_api_json": workflow,
#     }

# # =========================
# # Scene Generation
# # =========================
# SCENE_STRUCTURED_DATA_MARKER = "[STRUCTURED_SHOT_DATA_JSON]"


# def _sanitize_scene_value(value):
#     """pandas/CSV 값을 JSON 직렬화 가능한 값으로 정리합니다."""
#     if value is None:
#         return None

#     if isinstance(value, float):
#         if math.isnan(value) or math.isinf(value):
#             return None
#         return value

#     if isinstance(value, dict):
#         return {
#             str(key): _sanitize_scene_value(item)
#             for key, item in value.items()
#         }

#     if isinstance(value, (list, tuple)):
#         return [_sanitize_scene_value(item) for item in value]

#     if isinstance(value, str):
#         stripped = value.strip()

#         # CSV 셀에 characters/camera 등이 JSON 문자열로 저장된 경우 복원합니다.
#         if (
#             len(stripped) >= 2
#             and stripped[0] in "[{"
#             and stripped[-1] in "]}"
#         ):
#             try:
#                 return _sanitize_scene_value(json.loads(stripped))
#             except (json.JSONDecodeError, TypeError):
#                 pass

#         return value

#     # numpy scalar 등은 item()으로 일반 Python 값으로 변환합니다.
#     item_method = getattr(value, "item", None)
#     if callable(item_method):
#         try:
#             return _sanitize_scene_value(item_method())
#         except Exception:
#             pass

#     return value


# def _parse_custom_shot_ids(custom_shot_ids) -> set[str]:
#     if isinstance(custom_shot_ids, (list, tuple, set)):
#         return {
#             str(item).strip()
#             for item in custom_shot_ids
#             if str(item).strip()
#         }

#     return {
#         item.strip()
#         for item in str(custom_shot_ids or "").split(",")
#         if item.strip()
#     }


# def _read_selected_scene_rows_from_csv(
#     csv_text: str,
#     shot_filter: str,
#     custom_shot_ids,
# ) -> list[dict]:
#     """selected_shot_data가 없을 때 CSV 원문에서 선택 샷을 복원합니다."""
#     reader = csv.DictReader(io.StringIO(csv_text))
#     rows = [dict(row) for row in reader]

#     if str(shot_filter).upper() != "CUSTOM":
#         return rows

#     selected_ids = _parse_custom_shot_ids(custom_shot_ids)
#     if not selected_ids:
#         return []

#     shot_id_candidates = {
#         "shot",
#         "shot_id",
#         "shot id",
#         "id",
#     }

#     filtered_rows = []

#     for row in rows:
#         shot_id_value = ""

#         for key, value in row.items():
#             if str(key).strip().lower() in shot_id_candidates:
#                 shot_id_value = str(value).strip()
#                 break

#         # 명시적인 shot id 컬럼이 없으면 첫 번째 컬럼을 사용합니다.
#         if not shot_id_value and row:
#             shot_id_value = str(next(iter(row.values()))).strip()

#         if shot_id_value in selected_ids:
#             filtered_rows.append(row)

#     return filtered_rows


# def _build_scene_structured_data(
#     storyboard_input: dict,
#     scene_config: dict,
# ) -> dict:
#     """Streamlit에서 받은 선택 샷을 Qwen 입력용 structured_shot_data로 구성합니다."""
#     selected_shot_data = (
#         scene_config.get("selected_shot_data")
#         or storyboard_input.get("selected_shot_data")
#         or []
#     )

#     if not selected_shot_data:
#         selected_shot_data = _read_selected_scene_rows_from_csv(
#             csv_text=storyboard_input.get("csv_text", ""),
#             shot_filter=(
#                 scene_config.get("shot_filter")
#                 or storyboard_input.get("shot_filter", "ALL")
#             ),
#             custom_shot_ids=(
#                 scene_config.get("custom_shot_ids")
#                 or storyboard_input.get("custom_shot_ids", "")
#             ),
#         )

#     if not isinstance(selected_shot_data, list):
#         raise TypeError("selected_shot_data must be a list of shot records.")

#     shots = [
#         _sanitize_scene_value(row)
#         for row in selected_shot_data
#         if isinstance(row, dict)
#     ]

#     if not shots:
#         raise ValueError(
#             "No selected shot data was found. Check the CSV and shot selection in Step 1."
#         )

#     return {
#         "structured_shot_data": {
#             "shot_count": len(shots),
#             "shots": shots,
#         }
#     }


# def _build_scene_qwen_prompt(base_prompt: str, structured_data: dict) -> str:
#     """워크플로우에 저장된 고정 지침은 유지하고 샷 데이터 부분만 교체합니다."""
#     base_prompt = str(base_prompt or "").strip()

#     if not base_prompt:
#         raise ValueError("The Step 3 fixed Qwen prompt is empty.")

#     if SCENE_STRUCTURED_DATA_MARKER in base_prompt:
#         instruction = base_prompt.split(
#             SCENE_STRUCTURED_DATA_MARKER,
#             1,
#         )[0].rstrip()
#     else:
#         instruction = base_prompt

#     structured_json = json.dumps(
#         structured_data,
#         ensure_ascii=False,
#         indent=2,
#         allow_nan=False,
#     )

#     return (
#         f"{instruction}\n\n"
#         f"{SCENE_STRUCTURED_DATA_MARKER}\n\n"
#         f"{structured_json}"
#     )


# def _resolve_scene_node_id(
#     workflow: dict,
#     preferred_id: str,
#     class_types: tuple[str, ...],
#     description: str,
# ) -> str:
#     """선호 ID를 우선 사용하고, 없으면 class_type으로 노드를 찾습니다."""
#     preferred_id = str(preferred_id)

#     if preferred_id in workflow and isinstance(workflow[preferred_id], dict):
#         return preferred_id

#     for class_type in class_types:
#         node_ids = find_nodes_by_class_type(workflow, class_type)
#         if node_ids:
#             return node_ids[0]

#     raise KeyError(
#         f"{description} node was not found. "
#         f"Expected node id={preferred_id} or class_type in {class_types}."
#     )


# def _resolve_scene_reference_node_ids(workflow: dict) -> tuple[str, str]:
#     """Boy/Girl URL 입력 노드를 75, 76 순서로 찾습니다."""
#     preferred_ids = ["75", "76"]

#     if all(node_id in workflow for node_id in preferred_ids):
#         resolved = preferred_ids
#     else:
#         resolved = find_nodes_by_class_type(workflow, "LoadImageFromUrl")

#     if len(resolved) < 2:
#         load_image_ids = find_nodes_by_class_type(workflow, "LoadImage")

#         if load_image_ids:
#             raise ValueError(
#                 "Step 3 reference nodes are still LoadImage nodes. "
#                 "Replace the Boy/Girl reference nodes with LoadImageFromUrl, "
#                 "keep their IDs as 75 and 76, and export the workflow in API Format."
#             )

#         raise KeyError(
#             "Two LoadImageFromUrl nodes for the Boy and Girl references were not found."
#         )

#     boy_node_id, girl_node_id = resolved[:2]

#     for label, node_id in (
#         ("Boy", boy_node_id),
#         ("Girl", girl_node_id),
#     ):
#         class_type = workflow[node_id].get("class_type", "")
#         if class_type != "LoadImageFromUrl":
#             raise ValueError(
#                 f"Step 3 {label} reference node {node_id} uses "
#                 f"class_type='{class_type}'. Change it to LoadImageFromUrl."
#             )

#     return boy_node_id, girl_node_id


# def _resolve_scene_prompt_node_id(workflow: dict, qwen_node_id: str) -> str:
#     """Qwen custom_prompt에 연결된 Text Multiline 노드를 찾습니다."""
#     qwen_inputs = workflow[qwen_node_id].get("inputs", {})
#     custom_prompt_link = qwen_inputs.get("custom_prompt")

#     if (
#         isinstance(custom_prompt_link, (list, tuple))
#         and custom_prompt_link
#         and str(custom_prompt_link[0]) in workflow
#     ):
#         return str(custom_prompt_link[0])

#     return _resolve_scene_node_id(
#         workflow=workflow,
#         preferred_id="43",
#         class_types=("Text Multiline",),
#         description="Step 3 fixed prompt",
#     )


# def patch_scene_workflow(workflow: dict, config: dict) -> dict:
#     """
#     Step 3 Reference-Guided Scene Generation workflow patch.

#     새 scene_workflow_api.json 기준 주요 노드:
#     - 43: Text Multiline - 고정 프롬프트 + 동적 structured_shot_data
#     - 73: AILab_QwenVL
#     - 75: LoadImageFromUrl - Boy reference
#     - 76: LoadImageFromUrl - Girl reference
#     - 68: RandomNoise
#     - 52: SaveImage

#     주의:
#     - ComfyUI에서 Boy/Girl 입력 노드는 LoadImage가 아니라 LoadImageFromUrl이어야 합니다.
#     - 워크플로우 파일은 반드시 API Format으로 저장해야 합니다.
#     """
#     workflow = deepcopy(workflow)

#     storyboard_input = config.get("storyboard_input", {})
#     scene_config = config.get("scene_generation", {})

#     csv_text = storyboard_input.get("csv_text", "")
#     reference_images = scene_config.get("reference_images", {})

#     boy_body_image_url = (
#         reference_images.get("image_1_boy_body", {}).get("image")
#         or scene_config.get("boy_body_image_url")
#         or ""
#     )

#     girl_body_image_url = (
#         reference_images.get("image_2_girl_body", {}).get("image")
#         or scene_config.get("girl_body_image_url")
#         or ""
#     )

#     if not str(csv_text).strip():
#         raise ValueError("csv_text is empty. Upload a CSV file first.")

#     if not boy_body_image_url:
#         raise ValueError(
#             "boy_body_image_url is empty. "
#             "Generate Image 1 - Boy body reference first."
#         )

#     if not girl_body_image_url:
#         raise ValueError(
#             "girl_body_image_url is empty. "
#             "Generate Image 2 - Girl body reference first."
#         )

#     structured_data = _build_scene_structured_data(
#         storyboard_input=storyboard_input,
#         scene_config=scene_config,
#     )

#     seed = random.randint(1, 4_294_967_295)
#     filename_prefix = f"scene_{seed}"

#     boy_node_id, girl_node_id = _resolve_scene_reference_node_ids(workflow)

#     # 75/76: LoadImageFromUrl - Boy/Girl
#     for node_id, image_url in (
#         (boy_node_id, boy_body_image_url),
#         (girl_node_id, girl_body_image_url),
#     ):
#         inputs = workflow[node_id].setdefault("inputs", {})
#         inputs["image"] = image_url

#         if "keep_alpha_channel" in inputs:
#             inputs["keep_alpha_channel"] = False

#         if "output_mode" in inputs:
#             inputs["output_mode"] = False

#     # 73: AILab_QwenVL
#     qwen_node_id = _resolve_scene_node_id(
#         workflow=workflow,
#         preferred_id="73",
#         class_types=("AILab_QwenVL", "ThinkingLLM"),
#         description="Step 3 Qwen prompt generator",
#     )
#     qwen_inputs = workflow[qwen_node_id].setdefault("inputs", {})

#     if "seed" in qwen_inputs:
#         qwen_inputs["seed"] = seed

#     if "attention_mode" in qwen_inputs:
#         qwen_inputs["attention_mode"] = "auto"

#     if "max_tokens" in qwen_inputs:
#         shot_count = structured_data["structured_shot_data"]["shot_count"]
#         qwen_inputs["max_tokens"] = max(
#             1000,
#             min(4096, shot_count * 260),
#         )

#     # 43: 기존 고정 프롬프트 뒤의 샘플 JSON을 실제 선택 샷 JSON으로 교체
#     prompt_node_id = _resolve_scene_prompt_node_id(
#         workflow=workflow,
#         qwen_node_id=qwen_node_id,
#     )
#     prompt_inputs = workflow[prompt_node_id].setdefault("inputs", {})
#     prompt_inputs["text"] = _build_scene_qwen_prompt(
#         base_prompt=prompt_inputs.get("text", ""),
#         structured_data=structured_data,
#     )

#     # 68: RandomNoise
#     noise_node_id = _resolve_scene_node_id(
#         workflow=workflow,
#         preferred_id="68",
#         class_types=("RandomNoise",),
#         description="Step 3 noise",
#     )
#     noise_inputs = workflow[noise_node_id].setdefault("inputs", {})
#     if "noise_seed" in noise_inputs:
#         noise_inputs["noise_seed"] = seed

#     # 52: SaveImage
#     save_node_id = _resolve_scene_node_id(
#         workflow=workflow,
#         preferred_id="52",
#         class_types=("SaveImage",),
#         description="Step 3 final SaveImage",
#     )
#     save_inputs = workflow[save_node_id].setdefault("inputs", {})
#     save_inputs["filename_prefix"] = filename_prefix

#     return workflow


# def run_scene_generation(
#     api_key: str,
#     deployment_id: str,
#     config: dict,
#     workflow_path: str | Path = SCENE_WORKFLOW_PATH,
#     poll_interval: int = 10,
#     timeout_seconds: int = 1800,
# ) -> dict:
#     base_workflow = load_workflow_api_json(workflow_path)

#     workflow = patch_scene_workflow(
#         workflow=base_workflow,
#         config=config,
#     )

#     save_node_id = _resolve_scene_node_id(
#         workflow=workflow,
#         preferred_id="52",
#         class_types=("SaveImage",),
#         description="Step 3 final SaveImage",
#     )

#     request_data = submit_runcomfy_dynamic_workflow(
#         api_key=api_key,
#         deployment_id=deployment_id,
#         workflow_api_json=workflow,
#     )

#     status_url = request_data.get("status_url")
#     result_url = request_data.get("result_url")

#     if not status_url or not result_url:
#         raise RuntimeError(
#             f"RunComfy response does not include status/result URL: {request_data}"
#         )

#     result_data = poll_runcomfy_result(
#         api_key=api_key,
#         status_url=status_url,
#         result_url=result_url,
#         poll_interval=poll_interval,
#         timeout_seconds=timeout_seconds,
#     )

#     extracted_images = extract_output_images(result_data)

#     # Step 3에서는 최종 SaveImage 결과만 사용합니다.
#     save_node_images = [
#         item
#         for item in extracted_images
#         if str(item.get("node_id", "")) == str(save_node_id)
#     ]

#     # RunComfy 응답에 type='output'이 있으면 출력 파일만 우선 사용하고,
#     # type 필드가 없는 응답 구조에서는 SaveImage 결과 전체를 사용합니다.
#     typed_output_images = [
#         item
#         for item in save_node_images
#         if item.get("raw", {}).get("type") == "output"
#     ]
#     raw_images = typed_output_images or save_node_images

#     images = []

#     for idx, item in enumerate(raw_images, start=1):
#         url = item.get("url") or item.get("image") or ""

#         if not url:
#             continue

#         images.append(
#             {
#                 "label": f"Scene {idx}",
#                 "image": url,
#                 "url": url,
#                 "filename": item.get("filename", ""),
#                 "node_id": item.get("node_id", ""),
#                 "raw": item.get("raw", {}),
#             }
#         )

#     return {
#         "request": request_data,
#         "result": result_data,
#         "images": images,
#         "workflow_api_json": workflow,
#     }

# # =========================
# # Camera Refinement
# # =========================
# def patch_camera_refinement_workflow(workflow: dict, config: dict) -> dict:
#     """
#     Step 4 Camera Angle Refinement workflow patch.

#     New camera_refinement_workflow_api.json 기준 주요 노드:
#     - 8:  LoadImageFromUrl
#     - 16: CSVStoryboardParser
#     - 19: QwenMultiangleCameraNode
#     - 18: TwoWaySwitch
#     - 13: KSampler
#     - 17: SaveImage
#     """
#     workflow = deepcopy(workflow)

#     storyboard_input = config.get("storyboard_input", {})
#     camera_config = config.get("camera_angle_refinement", {})

#     input_scene = camera_config.get("input_scene", {})
#     camera_control = camera_config.get("camera_control", {})
#     prompt_source = camera_config.get("prompt_source", {})

#     csv_text = storyboard_input.get("csv_text", "")
#     shot_filter = storyboard_input.get("shot_filter", "ALL")
#     custom_shot_ids = storyboard_input.get("custom_shot_ids", "")

#     scene_image_url = (
#         input_scene.get("image")
#         or camera_config.get("scene_image_url")
#         or ""
#     )

#     if not csv_text.strip():
#         raise ValueError("csv_text is empty. Upload a CSV file first.")

#     if not scene_image_url:
#         raise ValueError("scene_image_url is empty. Generate a scene first.")

#     horizontal_angle = int(camera_control.get("horizontal_angle", 0))
#     vertical_angle = int(camera_control.get("vertical_angle", 0))
#     zoom = int(camera_control.get("zoom", 5))
#     default_prompts = bool(camera_control.get("default_prompts", True))
#     camera_view = bool(camera_control.get("camera_view", False))

#     switch_setting = int(prompt_source.get("two_way_switch_selection", 2))

#     if switch_setting not in [1, 2]:
#         switch_setting = 2

#     seed = random.randint(1, 4_294_967_295)
#     filename_prefix = f"camera_refined_{seed}"

#     # -------------------------------------------------
#     # 8: Load Image From URL
#     # -------------------------------------------------
#     workflow["8"]["inputs"]["image"] = scene_image_url
#     workflow["8"]["inputs"]["keep_alpha_channel"] = False
#     workflow["8"]["inputs"]["output_mode"] = False

#     # -------------------------------------------------
#     # 16: CSVStoryboardParser
#     # -------------------------------------------------
#     workflow["16"]["inputs"]["input_mode"] = "text"
#     workflow["16"]["inputs"]["csv_file"] = "CUSTOM"
#     workflow["16"]["inputs"]["csv_text"] = csv_text
#     workflow["16"]["inputs"]["shot_filter"] = shot_filter
#     workflow["16"]["inputs"]["custom_shot_ids"] = custom_shot_ids

#     # -------------------------------------------------
#     # 19: Qwen Multiangle Camera
#     # -------------------------------------------------
#     workflow["19"]["inputs"]["horizontal_angle"] = horizontal_angle
#     workflow["19"]["inputs"]["vertical_angle"] = vertical_angle
#     workflow["19"]["inputs"]["zoom"] = zoom
#     workflow["19"]["inputs"]["default_prompts"] = default_prompts
#     workflow["19"]["inputs"]["camera_view"] = camera_view

#     # -------------------------------------------------
#     # 18: TwoWaySwitch
#     # 1 = ScenePromptBuilder prompt
#     # 2 = Qwen Multiangle Camera prompt
#     # -------------------------------------------------
#     workflow["18"]["inputs"]["selection_setting"] = switch_setting

#     # -------------------------------------------------
#     # 13: KSampler
#     # -------------------------------------------------
#     workflow["13"]["inputs"]["seed"] = seed

#     # 현재 workflow 기본값이 steps=5, cfg=1이라 프롬프트 반영이 약할 수 있음.
#     # 우선 실행 안정성 중심으로 기본값만 보정.
#     workflow["13"]["inputs"]["steps"] = int(camera_control.get("steps", 15))
#     workflow["13"]["inputs"]["cfg"] = float(camera_control.get("cfg", 2.0))

#     # -------------------------------------------------
#     # 17: SaveImage
#     # -------------------------------------------------
#     workflow["17"]["inputs"]["filename_prefix"] = filename_prefix

#     return workflow


# def run_camera_refinement(
#     api_key: str,
#     deployment_id: str,
#     config: dict,
#     workflow_path: str | Path = CAMERA_REFINEMENT_WORKFLOW_PATH,
#     poll_interval: int = 10,
#     timeout_seconds: int = 1800,
# ) -> dict:
#     base_workflow = load_workflow_api_json(workflow_path)

#     workflow = patch_camera_refinement_workflow(
#         workflow=base_workflow,
#         config=config,
#     )

#     request_data = submit_runcomfy_dynamic_workflow(
#         api_key=api_key,
#         deployment_id=deployment_id,
#         workflow_api_json=workflow,
#     )

#     status_url = request_data.get("status_url")
#     result_url = request_data.get("result_url")

#     if not status_url or not result_url:
#         raise RuntimeError(
#             f"RunComfy response does not include status/result URL: {request_data}"
#         )

#     result_data = poll_runcomfy_result(
#         api_key=api_key,
#         status_url=status_url,
#         result_url=result_url,
#         poll_interval=poll_interval,
#         timeout_seconds=timeout_seconds,
#     )

#     raw_images = extract_output_images(result_data)

#     # Step 4에서는 최종 SaveImage 노드인 17번 결과만 사용
#     raw_images = [
#         item for item in raw_images
#         if str(item.get("node_id", "")) == "17"
#         and item.get("raw", {}).get("type") == "output"
#     ]

#     images = []

#     for idx, item in enumerate(raw_images, start=1):
#         url = item.get("url") or item.get("image") or ""

#         if not url:
#             continue

#         images.append(
#             {
#                 "label": f"Camera Refined Scene {idx}",
#                 "image": url,
#                 "url": url,
#                 "filename": item.get("filename", ""),
#                 "node_id": item.get("node_id", ""),
#                 "raw": item.get("raw", {}),
#             }
#         )

#     return {
#         "request": request_data,
#         "result": result_data,
#         "images": images,
#         "workflow_api_json": workflow,
#     }
#############################################

# import json
# import time
# import random
# from copy import deepcopy
# from pathlib import Path

# import requests


# RUNCOMFY_API_BASE = "https://api.runcomfy.net"

# WORKFLOW_DIR = Path(__file__).parent / "workflows"
# CSV_PARSER_TEST_WORKFLOW_PATH = WORKFLOW_DIR / "csv_parser_test_workflow_api.json"
# FACE_WORKFLOW_PATH = WORKFLOW_DIR / "face_workflow_api.json"
# BODY_WORKFLOW_PATH = WORKFLOW_DIR / "body_workflow_api.json"
# SCENE_WORKFLOW_PATH = WORKFLOW_DIR / "scene_workflow_api.json"
# CAMERA_REFINEMENT_WORKFLOW_PATH = WORKFLOW_DIR / "camera_refinement_workflow_api.json"


# # =========================
# # Common helpers
# # =========================
# def _headers(api_key: str, include_content_type: bool = True) -> dict:
#     if not api_key:
#         raise ValueError("RunComfy API key is missing.")

#     headers = {
#         "Authorization": f"Bearer {api_key}",
#     }

#     if include_content_type:
#         headers["Content-Type"] = "application/json"

#     return headers


# def load_workflow_api_json(workflow_path: str | Path) -> dict:
#     workflow_path = Path(workflow_path)

#     if not workflow_path.exists():
#         raise FileNotFoundError(f"workflow_api_json file not found: {workflow_path}")

#     with workflow_path.open("r", encoding="utf-8") as f:
#         return json.load(f)


# def submit_runcomfy_dynamic_workflow(
#     api_key: str,
#     deployment_id: str,
#     workflow_api_json: dict,
# ) -> dict:
#     if not deployment_id:
#         raise ValueError("RunComfy deployment_id is missing.")

#     url = f"{RUNCOMFY_API_BASE}/prod/v2/deployments/{deployment_id}/inference"

#     payload = {
#         "workflow_api_json": workflow_api_json,
#     }

#     response = requests.post(
#         url,
#         headers=_headers(api_key),
#         json=payload,
#         timeout=60,
#     )

#     if response.status_code >= 400:
#         raise RuntimeError(
#             f"RunComfy dynamic workflow submit failed: "
#             f"{response.status_code} / {response.text}"
#         )

#     return response.json()


# def poll_runcomfy_result(
#     api_key: str,
#     status_url: str,
#     result_url: str,
#     poll_interval: int = 10,
#     timeout_seconds: int = 1800,
# ) -> dict:
#     start_time = time.time()

#     while True:
#         if time.time() - start_time > timeout_seconds:
#             raise TimeoutError("RunComfy request timed out.")

#         status_response = requests.get(
#             status_url,
#             headers=_headers(api_key, include_content_type=False),
#             timeout=60,
#         )

#         if status_response.status_code >= 400:
#             raise RuntimeError(
#                 f"RunComfy status check failed: "
#                 f"{status_response.status_code} / {status_response.text}"
#             )

#         status_data = status_response.json()
#         status = status_data.get("status", "")

#         if status == "completed":
#             break

#         if status in {"failed", "error", "cancelled", "canceled"}:
#             raise RuntimeError(f"RunComfy request failed during polling: {status_data}")

#         if status not in {"in_queue", "in_progress"}:
#             raise RuntimeError(f"Unexpected RunComfy status: {status_data}")

#         time.sleep(poll_interval)

#     result_response = requests.get(
#         result_url,
#         headers=_headers(api_key, include_content_type=False),
#         timeout=60,
#     )

#     if result_response.status_code >= 400:
#         raise RuntimeError(
#             f"RunComfy result fetch failed: "
#             f"{result_response.status_code} / {result_response.text}"
#         )

#     result_data = result_response.json()

#     if result_data.get("status") != "succeeded":
#         raise RuntimeError(f"RunComfy result is not succeeded: {result_data}")

#     return result_data


# # def extract_output_images(result: dict) -> list[dict]:
# #     outputs = result.get("outputs", {})
# #     images = []

# #     for node_id, node_output in outputs.items():
# #         if not isinstance(node_output, dict):
# #             continue

# #         for image_item in node_output.get("images", []):
# #             if not isinstance(image_item, dict):
# #                 continue

# #             url = (
# #                 image_item.get("url")
# #                 or image_item.get("image_url")
# #                 or image_item.get("file_url")
# #                 or ""
# #             )

# #             images.append(
# #                 {
# #                     "node_id": node_id,
# #                     "url": url,
# #                     "image": url,
# #                     "filename": image_item.get("filename", ""),
# #                     "subfolder": image_item.get("subfolder", ""),
# #                     "type": image_item.get("type", ""),
# #                     "raw": image_item,
# #                 }
# #             )

# #     return images

# def extract_output_images(result: dict) -> list[dict]:
#     """
#     RunComfy 결과에서 이미지 URL을 최대한 안전하게 추출합니다.

#     지원 구조:
#     1. outputs -> node_id -> images -> url
#     2. outputs -> node_id -> images -> image_url / file_url
#     3. outputs -> node_id -> files / output_files
#     4. result 전체를 재귀적으로 탐색해서 url이 있는 png/jpg/webp 파일 찾기
#     """
#     images = []

#     def add_image_item(item: dict, node_id: str = ""):
#         if not isinstance(item, dict):
#             return

#         url = (
#             item.get("url")
#             or item.get("image")
#             or item.get("image_url")
#             or item.get("file_url")
#             or item.get("download_url")
#             or item.get("path")
#             or ""
#         )

#         filename = item.get("filename", "")

#         # filename이 없으면 url에서 추정
#         if not filename and isinstance(url, str) and "/" in url:
#             filename = url.split("?")[0].rstrip("/").split("/")[-1]

#         if not isinstance(url, str) or not url:
#             return

#         lower_url = url.lower()
#         lower_filename = str(filename).lower()

#         is_image = (
#             lower_url.endswith((".png", ".jpg", ".jpeg", ".webp"))
#             or ".png" in lower_url
#             or ".jpg" in lower_url
#             or ".jpeg" in lower_url
#             or ".webp" in lower_url
#             or lower_filename.endswith((".png", ".jpg", ".jpeg", ".webp"))
#         )

#         if not is_image:
#             return

#         images.append(
#             {
#                 "node_id": node_id,
#                 "url": url,
#                 "image": url,
#                 "filename": filename,
#                 "subfolder": item.get("subfolder", ""),
#                 "type": item.get("type", ""),
#                 "raw": item,
#             }
#         )

#     # 1차: RunComfy outputs 구조 우선 탐색
#     outputs = result.get("outputs", {})

#     if isinstance(outputs, dict):
#         for node_id, node_output in outputs.items():
#             if not isinstance(node_output, dict):
#                 continue

#             for key in ["images", "files", "output_files"]:
#                 items = node_output.get(key, [])

#                 if isinstance(items, dict):
#                     items = [items]

#                 if isinstance(items, list):
#                     for item in items:
#                         add_image_item(item, node_id=str(node_id))

#     # 2차: 그래도 못 찾으면 result 전체 재귀 탐색
#     if not images:
#         def walk(obj, node_id: str = ""):
#             if isinstance(obj, dict):
#                 add_image_item(obj, node_id=node_id)

#                 for key, value in obj.items():
#                     next_node_id = node_id
#                     if str(key).isdigit():
#                         next_node_id = str(key)
#                     walk(value, node_id=next_node_id)

#             elif isinstance(obj, list):
#                 for value in obj:
#                     walk(value, node_id=node_id)

#         walk(result)

#     # 중복 제거
#     deduped = []
#     seen = set()

#     for item in images:
#         key = item.get("url", "")
#         if key and key not in seen:
#             deduped.append(item)
#             seen.add(key)

#     return deduped


# def find_nodes_by_class_type(workflow: dict, class_type: str) -> list[str]:
#     node_ids = []

#     for node_id, node in workflow.items():
#         if not isinstance(node, dict):
#             continue

#         if node.get("class_type") == class_type:
#             node_ids.append(str(node_id))

#     return node_ids


# def find_first_node_by_class_type(workflow: dict, class_type: str) -> str:
#     node_ids = find_nodes_by_class_type(workflow, class_type)

#     if not node_ids:
#         raise KeyError(f"Node with class_type='{class_type}' was not found.")

#     return node_ids[0]


# def character_filter_to_name(character_filter: str) -> str:
#     if character_filter == "C1":
#         return "boy"
#     if character_filter == "C2":
#         return "girl"
#     return str(character_filter).lower().replace(" ", "_")


# # =========================
# # CSV Parser Test
# # =========================
# def patch_csv_parser_test_workflow(workflow: dict, storyboard_input_config: dict) -> dict:
#     workflow = deepcopy(workflow)

#     storyboard_input = storyboard_input_config.get("storyboard_input", storyboard_input_config)

#     csv_text = storyboard_input.get("csv_text", "")
#     shot_filter = storyboard_input.get("shot_filter", "ALL")
#     custom_shot_ids = storyboard_input.get("custom_shot_ids", "")

#     if not csv_text.strip():
#         raise ValueError("csv_text is empty. Upload a CSV file first.")

#     csv_parser_node_id = find_first_node_by_class_type(workflow, "CSVStoryboardParser")

#     workflow[csv_parser_node_id]["inputs"]["csv_file"] = "CUSTOM"
#     workflow[csv_parser_node_id]["inputs"]["csv_text"] = csv_text
#     workflow[csv_parser_node_id]["inputs"]["shot_filter"] = shot_filter
#     workflow[csv_parser_node_id]["inputs"]["custom_shot_ids"] = custom_shot_ids

#     seed = random.randint(1, 4_294_967_295)
#     filename_prefix = f"csv_parser_test_{seed}"

#     for node_id in find_nodes_by_class_type(workflow, "KSampler"):
#         inputs = workflow[node_id].get("inputs", {})
#         if "seed" in inputs:
#             inputs["seed"] = seed

#     for node_id, node in workflow.items():
#         if not isinstance(node, dict):
#             continue

#         inputs = node.get("inputs", {})
#         if isinstance(inputs, dict) and "seed" in inputs and isinstance(inputs["seed"], int):
#             inputs["seed"] = seed

#     for node_id in find_nodes_by_class_type(workflow, "SaveImage"):
#         inputs = workflow[node_id].get("inputs", {})
#         if "filename_prefix" in inputs:
#             inputs["filename_prefix"] = filename_prefix

#     return workflow


# def run_csv_parser_test(
#     api_key: str,
#     deployment_id: str,
#     storyboard_input_config: dict,
#     workflow_path: str | Path = CSV_PARSER_TEST_WORKFLOW_PATH,
#     poll_interval: int = 10,
#     timeout_seconds: int = 1800,
# ) -> dict:
#     base_workflow = load_workflow_api_json(workflow_path)

#     workflow = patch_csv_parser_test_workflow(
#         workflow=base_workflow,
#         storyboard_input_config=storyboard_input_config,
#     )

#     request_data = submit_runcomfy_dynamic_workflow(
#         api_key=api_key,
#         deployment_id=deployment_id,
#         workflow_api_json=workflow,
#     )

#     status_url = request_data.get("status_url")
#     result_url = request_data.get("result_url")

#     if not status_url or not result_url:
#         raise RuntimeError(
#             f"RunComfy response does not include status/result URL: {request_data}"
#         )

#     result_data = poll_runcomfy_result(
#         api_key=api_key,
#         status_url=status_url,
#         result_url=result_url,
#         poll_interval=poll_interval,
#         timeout_seconds=timeout_seconds,
#     )

#     images = extract_output_images(result_data)

#     return {
#         "request": request_data,
#         "result": result_data,
#         "images": images,
#         "workflow_api_json": workflow,
#     }


# # =========================
# # Face Generation
# # =========================
# def patch_face_workflow(workflow: dict, config: dict) -> dict:
#     workflow = deepcopy(workflow)

#     storyboard_input = config.get("storyboard_input", {})
#     csv_config = config.get("csvstoryboardparser", {})
#     character_config = config.get("character_registry_parser", {})
#     base_prompt_config = config.get("base_background_clothing_prompt", {})
#     base_character_config = config.get("portrait_master_base_character", {})
#     skin_config = config.get("portrait_master_skin_details", {})

#     csv_text = csv_config.get("csv_text") or storyboard_input.get("csv_text", "")
#     shot_filter = csv_config.get("shot_filter") or storyboard_input.get("shot_filter", "ALL")
#     custom_shot_ids = csv_config.get("custom_shot_ids") or storyboard_input.get("custom_shot_ids", "")

#     if not csv_text.strip():
#         raise ValueError("csv_text is empty. Upload a CSV file first.")

#     character_filter = character_config.get("character_filter", "C2")
#     character_name = character_filter_to_name(character_filter)

#     seed = random.randint(1, 4_294_967_295)
#     filename_prefix = f"face_{character_name}_{seed}"

#     workflow["1002"]["inputs"]["csv_file"] = "CUSTOM"
#     workflow["1002"]["inputs"]["csv_text"] = csv_text
#     workflow["1002"]["inputs"]["shot_filter"] = shot_filter
#     workflow["1002"]["inputs"]["custom_shot_ids"] = custom_shot_ids

#     workflow["1000"]["inputs"]["character_filter"] = character_filter
#     workflow["1000"]["inputs"]["custom_character_id"] = character_config.get("custom_character_id", "")
#     workflow["1000"]["inputs"]["age"] = character_config.get("age", 9)
#     workflow["1000"]["inputs"]["include_character_id"] = character_config.get("include_character_id", "false")

#     workflow["1007"]["inputs"]["text"] = base_prompt_config.get(
#         "text",
#         "gray background, white t-shirt",
#     )

#     for key, value in base_character_config.items():
#         if key in workflow["1003"]["inputs"]:
#             workflow["1003"]["inputs"][key] = value

#     for key, value in skin_config.items():
#         if key in workflow["1004"]["inputs"]:
#             workflow["1004"]["inputs"][key] = value

#     if "999" in workflow and "seed" in workflow["999"]["inputs"]:
#         workflow["999"]["inputs"]["seed"] = seed

#     if "1014" in workflow and "seed" in workflow["1014"]["inputs"]:
#         workflow["1014"]["inputs"]["seed"] = seed

#     workflow["1018"]["inputs"]["seed"] = seed
#     workflow["1019"]["inputs"]["filename_prefix"] = filename_prefix

#     return workflow


# def run_face_generation(
#     api_key: str,
#     deployment_id: str,
#     config: dict,
#     workflow_path: str | Path = FACE_WORKFLOW_PATH,
#     poll_interval: int = 10,
#     timeout_seconds: int = 1800,
# ) -> dict:
#     base_workflow = load_workflow_api_json(workflow_path)

#     workflow = patch_face_workflow(
#         workflow=base_workflow,
#         config=config,
#     )

#     request_data = submit_runcomfy_dynamic_workflow(
#         api_key=api_key,
#         deployment_id=deployment_id,
#         workflow_api_json=workflow,
#     )

#     status_url = request_data.get("status_url")
#     result_url = request_data.get("result_url")

#     if not status_url or not result_url:
#         raise RuntimeError(
#             f"RunComfy response does not include status/result URL: {request_data}"
#         )

#     result_data = poll_runcomfy_result(
#         api_key=api_key,
#         status_url=status_url,
#         result_url=result_url,
#         poll_interval=poll_interval,
#         timeout_seconds=timeout_seconds,
#     )

#     raw_images = extract_output_images(result_data)

#     character_filter = config.get("character_registry_parser", {}).get(
#         "character_filter",
#         "C2",
#     )

#     if character_filter == "C1":
#         label_prefix = "Boy Face"
#     elif character_filter == "C2":
#         label_prefix = "Girl Face"
#     else:
#         label_prefix = "Face"

#     images = []

#     for idx, item in enumerate(raw_images, start=1):
#         url = item.get("url") or item.get("image") or ""

#         if not url:
#             continue

#         images.append(
#             {
#                 "label": f"{label_prefix} {idx}",
#                 "image": url,
#                 "url": url,
#                 "filename": item.get("filename", ""),
#                 "node_id": item.get("node_id", ""),
#                 "raw": item.get("raw", {}),
#             }
#         )

#     return {
#         "request": request_data,
#         "result": result_data,
#         "images": images,
#         "workflow_api_json": workflow,
#     }


# # =========================
# # Body Generation
# # =========================
# def patch_body_workflow(workflow: dict, config: dict) -> dict:
#     """
#     Step 2B Full-Body Reference Generation workflow patch.

#     body_workflow_api.json 기준 주요 노드:
#     - 1239: LoadImageFromUrl
#     - 1238: body/outfit prompt text
#     - 1065: ThinkingLLM
#     - 1048: KSampler
#     - 1244: SaveImage
#     """
#     workflow = deepcopy(workflow)

#     body_config = config.get("body_generation", config)

#     character_filter = body_config.get("character_filter", "C1")
#     character_name = character_filter_to_name(character_filter)

#     face_image_url = (
#         body_config.get("face_image_url")
#         or body_config.get("face_reference_image")
#         or body_config.get("reference_image_url")
#         or ""
#     )

#     body_prompt = body_config.get("body_prompt", "")

#     if not face_image_url:
#         raise ValueError(
#             "face_image_url is empty. Generate a face reference first."
#         )

#     if not body_prompt.strip():
#         raise ValueError(
#             "body_prompt is empty. Enter a full-body outfit prompt first."
#         )

#     seed = random.randint(1, 4_294_967_295)
#     filename_prefix = f"body_{character_name}_{seed}"

#     # 1239: Load Image From URL
#     workflow["1239"]["inputs"]["image"] = face_image_url
#     workflow["1239"]["inputs"]["keep_alpha_channel"] = False
#     workflow["1239"]["inputs"]["output_mode"] = False

#     # 1238: text / outfit prompt
#     workflow["1238"]["inputs"]["text"] = body_prompt

#     # 1065: ThinkingLLM seed
#     if "1065" in workflow and "seed" in workflow["1065"]["inputs"]:
#         workflow["1065"]["inputs"]["seed"] = seed

#     # 1048: KSampler
#     workflow["1048"]["inputs"]["seed"] = seed

#     # 1244: SaveImage
#     workflow["1244"]["inputs"]["filename_prefix"] = filename_prefix

#     return workflow


# def run_body_generation(
#     api_key: str,
#     deployment_id: str,
#     config: dict,
#     workflow_path: str | Path = BODY_WORKFLOW_PATH,
#     poll_interval: int = 10,
#     timeout_seconds: int = 1800,
# ) -> dict:
#     base_workflow = load_workflow_api_json(workflow_path)

#     workflow = patch_body_workflow(
#         workflow=base_workflow,
#         config=config,
#     )

#     request_data = submit_runcomfy_dynamic_workflow(
#         api_key=api_key,
#         deployment_id=deployment_id,
#         workflow_api_json=workflow,
#     )

#     status_url = request_data.get("status_url")
#     result_url = request_data.get("result_url")

#     if not status_url or not result_url:
#         raise RuntimeError(
#             f"RunComfy response does not include status/result URL: {request_data}"
#         )

#     result_data = poll_runcomfy_result(
#         api_key=api_key,
#         status_url=status_url,
#         result_url=result_url,
#         poll_interval=poll_interval,
#         timeout_seconds=timeout_seconds,
#     )

#     raw_images = extract_output_images(result_data)

#     # Step 2B에서는 최종 SaveImage 노드인 1244 결과만 사용해야 함.
#     # 1239는 LoadImageFromUrl 입력 face reference라서 제외해야 함.
#     raw_images = [
#         item for item in raw_images
#         if str(item.get("node_id", "")) == "1244"
#         and item.get("raw", {}).get("type") == "output"
#     ]

#     character_filter = config.get("body_generation", {}).get(
#         "character_filter",
#         "C1",
#     )

#     if character_filter == "C1":
#         label_prefix = "Boy Body"
#     elif character_filter == "C2":
#         label_prefix = "Girl Body"
#     else:
#         label_prefix = "Body"

#     images = []

#     for idx, item in enumerate(raw_images, start=1):
#         url = item.get("url") or item.get("image") or ""

#         if not url:
#             continue

#         images.append(
#             {
#                 "label": f"{label_prefix} {idx}",
#                 "image": url,
#                 "url": url,
#                 "filename": item.get("filename", ""),
#                 "node_id": item.get("node_id", ""),
#                 "raw": item.get("raw", {}),
#             }
#         )

#     return {
#         "request": request_data,
#         "result": result_data,
#         "images": images,
#         "workflow_api_json": workflow,
#     }

# # =========================
# # Scene Generation
# # =========================
# def patch_scene_workflow(workflow: dict, config: dict) -> dict:
#     """
#     Step 3 Reference-Guided Scene Generation workflow patch.

#     scene_workflow_api.json 기준 주요 노드:
#     - 26: CSVStoryboardParser
#     - 27: LoadImageFromUrl - boy
#     - 28: LoadImageFromUrl - girl
#     - 10: KSampler
#     - 11: SaveImage
#     """
#     workflow = deepcopy(workflow)

#     storyboard_input = config.get("storyboard_input", {})
#     scene_config = config.get("scene_generation", {})

#     csv_text = storyboard_input.get("csv_text", "")
#     shot_filter = scene_config.get("shot_filter") or storyboard_input.get("shot_filter", "ALL")
#     custom_shot_ids = scene_config.get("custom_shot_ids") or storyboard_input.get("custom_shot_ids", "")

#     reference_images = scene_config.get("reference_images", {})

#     boy_body_image_url = (
#         reference_images.get("image_1_boy_body", {}).get("image")
#         or scene_config.get("boy_body_image_url")
#         or ""
#     )

#     girl_body_image_url = (
#         reference_images.get("image_2_girl_body", {}).get("image")
#         or scene_config.get("girl_body_image_url")
#         or ""
#     )

#     if not csv_text.strip():
#         raise ValueError("csv_text is empty. Upload a CSV file first.")

#     if not boy_body_image_url:
#         raise ValueError("boy_body_image_url is empty. Generate Image 1 - Boy body reference first.")

#     if not girl_body_image_url:
#         raise ValueError("girl_body_image_url is empty. Generate Image 2 - Girl body reference first.")

#     seed = random.randint(1, 4_294_967_295)
#     filename_prefix = f"scene_{seed}"

#     # 57: CSVStoryboardParser
#     workflow["57"]["inputs"]["input_mode"] = "text"
#     workflow["57"]["inputs"]["csv_file"] = "CUSTOM"
#     workflow["57"]["inputs"]["csv_text"] = csv_text
#     workflow["57"]["inputs"]["shot_filter"] = shot_filter
#     workflow["57"]["inputs"]["custom_shot_ids"] = custom_shot_ids
    
#     # 50: Load Image From URL - boy
#     workflow["50"]["inputs"]["image"] = boy_body_image_url
#     workflow["50"]["inputs"]["keep_alpha_channel"] = False
#     workflow["50"]["inputs"]["output_mode"] = False
    
#     # 51: Load Image From URL - girl
#     workflow["51"]["inputs"]["image"] = girl_body_image_url
#     workflow["51"]["inputs"]["keep_alpha_channel"] = False
#     workflow["51"]["inputs"]["output_mode"] = False
    
#     # 58: ThinkingLLM / AILab_QwenVL
#     if "58" in workflow:
#         inputs = workflow["58"].get("inputs", {})
    
#         if "seed" in inputs:
#             inputs["seed"] = seed
    
#         if "attention_mode" in inputs:
#             inputs["attention_mode"] = "auto"
    
#     # 68: RandomNoise
#     if "68" in workflow and "noise_seed" in workflow["68"]["inputs"]:
#         workflow["68"]["inputs"]["noise_seed"] = seed
    
#     # 52: SaveImage
#     workflow["52"]["inputs"]["filename_prefix"] = filename_prefix

#     return workflow


# def run_scene_generation(
#     api_key: str,
#     deployment_id: str,
#     config: dict,
#     workflow_path: str | Path = SCENE_WORKFLOW_PATH,
#     poll_interval: int = 10,
#     timeout_seconds: int = 1800,
# ) -> dict:
#     base_workflow = load_workflow_api_json(workflow_path)

#     workflow = patch_scene_workflow(
#         workflow=base_workflow,
#         config=config,
#     )

#     request_data = submit_runcomfy_dynamic_workflow(
#         api_key=api_key,
#         deployment_id=deployment_id,
#         workflow_api_json=workflow,
#     )

#     status_url = request_data.get("status_url")
#     result_url = request_data.get("result_url")

#     if not status_url or not result_url:
#         raise RuntimeError(
#             f"RunComfy response does not include status/result URL: {request_data}"
#         )

#     result_data = poll_runcomfy_result(
#         api_key=api_key,
#         status_url=status_url,
#         result_url=result_url,
#         poll_interval=poll_interval,
#         timeout_seconds=timeout_seconds,
#     )

#     raw_images = extract_output_images(result_data)
    
#     # Step 3에서는 최종 SaveImage 노드인 52번 결과만 사용
#     raw_images = [
#         item for item in raw_images
#         if str(item.get("node_id", "")) == "52"
#         and item.get("raw", {}).get("type") == "output"
#     ]
    
#     images = []
    
#     for idx, item in enumerate(raw_images, start=1):
#         url = item.get("url") or item.get("image") or ""
    
#         if not url:
#             continue
    
#         images.append(
#             {
#                 "label": f"Scene {idx}",
#                 "image": url,
#                 "url": url,
#                 "filename": item.get("filename", ""),
#                 "node_id": item.get("node_id", ""),
#                 "raw": item.get("raw", {}),
#             }
#         )

#     return {
#         "request": request_data,
#         "result": result_data,
#         "images": images,
#         "workflow_api_json": workflow,
#     }

# # =========================
# # Camera Refinement
# # =========================
# def patch_camera_refinement_workflow(workflow: dict, config: dict) -> dict:
#     """
#     Step 4 Camera Angle Refinement workflow patch.

#     New camera_refinement_workflow_api.json 기준 주요 노드:
#     - 8:  LoadImageFromUrl
#     - 16: CSVStoryboardParser
#     - 19: QwenMultiangleCameraNode
#     - 18: TwoWaySwitch
#     - 13: KSampler
#     - 17: SaveImage
#     """
#     workflow = deepcopy(workflow)

#     storyboard_input = config.get("storyboard_input", {})
#     camera_config = config.get("camera_angle_refinement", {})

#     input_scene = camera_config.get("input_scene", {})
#     camera_control = camera_config.get("camera_control", {})
#     prompt_source = camera_config.get("prompt_source", {})

#     csv_text = storyboard_input.get("csv_text", "")
#     shot_filter = storyboard_input.get("shot_filter", "ALL")
#     custom_shot_ids = storyboard_input.get("custom_shot_ids", "")

#     scene_image_url = (
#         input_scene.get("image")
#         or camera_config.get("scene_image_url")
#         or ""
#     )

#     if not csv_text.strip():
#         raise ValueError("csv_text is empty. Upload a CSV file first.")

#     if not scene_image_url:
#         raise ValueError("scene_image_url is empty. Generate a scene first.")

#     horizontal_angle = int(camera_control.get("horizontal_angle", 0))
#     vertical_angle = int(camera_control.get("vertical_angle", 0))
#     zoom = int(camera_control.get("zoom", 5))
#     default_prompts = bool(camera_control.get("default_prompts", True))
#     camera_view = bool(camera_control.get("camera_view", False))

#     switch_setting = int(prompt_source.get("two_way_switch_selection", 2))

#     if switch_setting not in [1, 2]:
#         switch_setting = 2

#     seed = random.randint(1, 4_294_967_295)
#     filename_prefix = f"camera_refined_{seed}"

#     # -------------------------------------------------
#     # 8: Load Image From URL
#     # -------------------------------------------------
#     workflow["8"]["inputs"]["image"] = scene_image_url
#     workflow["8"]["inputs"]["keep_alpha_channel"] = False
#     workflow["8"]["inputs"]["output_mode"] = False

#     # -------------------------------------------------
#     # 16: CSVStoryboardParser
#     # -------------------------------------------------
#     workflow["16"]["inputs"]["input_mode"] = "text"
#     workflow["16"]["inputs"]["csv_file"] = "CUSTOM"
#     workflow["16"]["inputs"]["csv_text"] = csv_text
#     workflow["16"]["inputs"]["shot_filter"] = shot_filter
#     workflow["16"]["inputs"]["custom_shot_ids"] = custom_shot_ids

#     # -------------------------------------------------
#     # 19: Qwen Multiangle Camera
#     # -------------------------------------------------
#     workflow["19"]["inputs"]["horizontal_angle"] = horizontal_angle
#     workflow["19"]["inputs"]["vertical_angle"] = vertical_angle
#     workflow["19"]["inputs"]["zoom"] = zoom
#     workflow["19"]["inputs"]["default_prompts"] = default_prompts
#     workflow["19"]["inputs"]["camera_view"] = camera_view

#     # -------------------------------------------------
#     # 18: TwoWaySwitch
#     # 1 = ScenePromptBuilder prompt
#     # 2 = Qwen Multiangle Camera prompt
#     # -------------------------------------------------
#     workflow["18"]["inputs"]["selection_setting"] = switch_setting

#     # -------------------------------------------------
#     # 13: KSampler
#     # -------------------------------------------------
#     workflow["13"]["inputs"]["seed"] = seed

#     # 현재 workflow 기본값이 steps=5, cfg=1이라 프롬프트 반영이 약할 수 있음.
#     # 우선 실행 안정성 중심으로 기본값만 보정.
#     workflow["13"]["inputs"]["steps"] = int(camera_control.get("steps", 15))
#     workflow["13"]["inputs"]["cfg"] = float(camera_control.get("cfg", 2.0))

#     # -------------------------------------------------
#     # 17: SaveImage
#     # -------------------------------------------------
#     workflow["17"]["inputs"]["filename_prefix"] = filename_prefix

#     return workflow


# def run_camera_refinement(
#     api_key: str,
#     deployment_id: str,
#     config: dict,
#     workflow_path: str | Path = CAMERA_REFINEMENT_WORKFLOW_PATH,
#     poll_interval: int = 10,
#     timeout_seconds: int = 1800,
# ) -> dict:
#     base_workflow = load_workflow_api_json(workflow_path)

#     workflow = patch_camera_refinement_workflow(
#         workflow=base_workflow,
#         config=config,
#     )

#     request_data = submit_runcomfy_dynamic_workflow(
#         api_key=api_key,
#         deployment_id=deployment_id,
#         workflow_api_json=workflow,
#     )

#     status_url = request_data.get("status_url")
#     result_url = request_data.get("result_url")

#     if not status_url or not result_url:
#         raise RuntimeError(
#             f"RunComfy response does not include status/result URL: {request_data}"
#         )

#     result_data = poll_runcomfy_result(
#         api_key=api_key,
#         status_url=status_url,
#         result_url=result_url,
#         poll_interval=poll_interval,
#         timeout_seconds=timeout_seconds,
#     )

#     raw_images = extract_output_images(result_data)

#     # Step 4에서는 최종 SaveImage 노드인 17번 결과만 사용
#     raw_images = [
#         item for item in raw_images
#         if str(item.get("node_id", "")) == "17"
#         and item.get("raw", {}).get("type") == "output"
#     ]

#     images = []

#     for idx, item in enumerate(raw_images, start=1):
#         url = item.get("url") or item.get("image") or ""

#         if not url:
#             continue

#         images.append(
#             {
#                 "label": f"Camera Refined Scene {idx}",
#                 "image": url,
#                 "url": url,
#                 "filename": item.get("filename", ""),
#                 "node_id": item.get("node_id", ""),
#                 "raw": item.get("raw", {}),
#             }
#         )

#     return {
#         "request": request_data,
#         "result": result_data,
#         "images": images,
#         "workflow_api_json": workflow,
#     }

