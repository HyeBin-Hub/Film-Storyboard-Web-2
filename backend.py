import json
import time
import random
from copy import deepcopy
from pathlib import Path

import requests


RUNCOMFY_API_BASE = "https://api.runcomfy.net"

WORKFLOW_DIR = Path(__file__).parent / "workflows"
CSV_PARSER_TEST_WORKFLOW_PATH = WORKFLOW_DIR / "csv_parser_test_workflow_api.json"


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


# =========================
# CSV Parser Test
# =========================
def patch_csv_parser_test_workflow(workflow: dict, storyboard_input_config: dict) -> dict:
    """
    Step 1 검증용 workflow patch.

    목표:
    - Streamlit에서 업로드한 csv_text를 RunComfy의 CSVStoryboardParser에 넣는다.
    - shot_filter/custom_shot_ids도 같이 반영한다.
    - seed와 filename_prefix를 매번 바꿔서 caching/output 누락 가능성을 줄인다.
    """
    workflow = deepcopy(workflow)

    storyboard_input = storyboard_input_config.get("storyboard_input", storyboard_input_config)

    csv_text = storyboard_input.get("csv_text", "")
    shot_filter = storyboard_input.get("shot_filter", "ALL")
    custom_shot_ids = storyboard_input.get("custom_shot_ids", "")

    if not csv_text.strip():
        raise ValueError("csv_text is empty. Upload a CSV file first.")

    # CSVStoryboardParser 자동 탐색
    csv_parser_node_id = find_first_node_by_class_type(workflow, "CSVStoryboardParser")

    # input_mode은 건드리지 않음.
    # 커스텀 노드 dropdown 값이 workflow마다 다를 수 있어서 원본 유지가 안전함.
    workflow[csv_parser_node_id]["inputs"]["csv_file"] = "CUSTOM"
    workflow[csv_parser_node_id]["inputs"]["csv_text"] = csv_text
    workflow[csv_parser_node_id]["inputs"]["shot_filter"] = shot_filter
    workflow[csv_parser_node_id]["inputs"]["custom_shot_ids"] = custom_shot_ids

    seed = random.randint(1, 999_999_999_999_999)
    filename_prefix = f"csv_parser_test_{seed}"

    # 모든 KSampler seed 랜덤화
    for node_id in find_nodes_by_class_type(workflow, "KSampler"):
        inputs = workflow[node_id].get("inputs", {})
        if "seed" in inputs:
            inputs["seed"] = seed

    # rgthree Seed 노드 등 seed input이 있는 노드도 가능한 범위에서 랜덤화
    for node_id, node in workflow.items():
        if not isinstance(node, dict):
            continue

        inputs = node.get("inputs", {})
        if isinstance(inputs, dict) and "seed" in inputs:
            if isinstance(inputs["seed"], int):
                inputs["seed"] = seed

    # SaveImage filename_prefix 랜덤화
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
    poll_interval: int = 5,
    timeout_seconds: int = 900,
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
