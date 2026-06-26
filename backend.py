import requests
import time


RUNCOMFY_API_BASE = "https://api.runcomfy.net/prod/v2"


def run_csv_parser_test(
    api_key: str,
    deployment_id: str,
    csv_node_id: str,
    csv_text: str,
    shot_filter: str = "ALL",
    custom_shot_ids: str = "",
):
    """
    Streamlit에서 업로드한 CSV 텍스트가 RunComfy Serverless workflow의
    CSVStoryboardParser 노드로 정상 전달되는지 테스트한다.
    """

    inference_url = f"{RUNCOMFY_API_BASE}/deployments/{deployment_id}/inference"

    payload = {
        "overrides": {
            str(csv_node_id): {
                "inputs": {
                    "input_mode": "text",
                    "csv_text": csv_text,
                    "shot_filter": shot_filter,
                    "custom_shot_ids": custom_shot_ids,
                }
            }
        }
    }

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }

    response = requests.post(
        inference_url,
        headers=headers,
        json=payload,
        timeout=120,
    )

    if response.status_code >= 400:
        raise RuntimeError(
            f"RunComfy inference failed. "
            f"status={response.status_code}, body={response.text}"
        )

    return response.json()
