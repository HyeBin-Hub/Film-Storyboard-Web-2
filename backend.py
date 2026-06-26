# backend.py
import requests


RUNCOMFY_API_BASE = "https://api.runcomfy.net/prod/v2"


def _build_inference_url(deployment_id: str) -> str:
    if not deployment_id:
        raise ValueError("deployment_id is empty.")

    deployment_id = str(deployment_id).strip()

    if deployment_id.startswith("http://") or deployment_id.startswith("https://"):
        return deployment_id

    return f"{RUNCOMFY_API_BASE}/deployments/{deployment_id}/inference"


def test_csv_parser(
    api_key: str,
    deployment_id: str,
    csv_text: str,
    shot_filter: str = "ALL",
    custom_shot_ids: str = "",
):
    if not api_key:
        raise ValueError("api_key is empty.")

    if not deployment_id:
        raise ValueError("deployment_id is empty.")

    if not csv_text or not str(csv_text).strip():
        raise ValueError("csv_text is empty.")

    if shot_filter == "CUSTOM" and not custom_shot_ids.strip():
        raise ValueError("CUSTOM mode requires custom_shot_ids.")

    inference_url = _build_inference_url(deployment_id)

    payload = {
        "overrides": {
            "3": {
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

    try:
        return response.json()
    except Exception:
        return {
            "status_code": response.status_code,
            "text": response.text,
        }
