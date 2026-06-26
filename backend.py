import os
import re
import requests


def _safe_filename(filename: str) -> str:
    name = os.path.basename(filename)
    name = re.sub(r"[^a-zA-Z0-9._-]+", "_", name)

    if not name.lower().endswith(".csv"):
        name += ".csv"

    return name


def upload_csv_to_runcomfy_input(
    api_key: str,
    original_file_name: str,
    file_bytes: bytes,
    target_subdir: str = "storyboard_uploads",
):
    """
    Streamlit에서 받은 CSV를 RunComfy/ComfyUI input 폴더로 업로드하는 테스트 함수.

    주의:
    - COMFYUI_BASE_URL은 실행 중인 RunComfy ComfyUI backend URL이어야 함.
    - Serverless deployment_id만으로 바로 input 폴더에 업로드되는 구조가 아닐 수 있음.
    """

    safe_name = _safe_filename(original_file_name)

    # input 폴더 기준 상대 경로
    relative_path = f"{target_subdir}/{safe_name}"

    # 예: https://xxxx.runcomfy.com 또는 RunComfy에서 제공하는 ComfyUI backend base URL
    comfyui_base_url = os.getenv("COMFYUI_BASE_URL", "").rstrip("/")

    if not comfyui_base_url:
        raise RuntimeError(
            "COMFYUI_BASE_URL이 설정되지 않았습니다. "
            "RunComfy의 실행 중인 ComfyUI backend URL을 환경변수로 넣어야 합니다."
        )

    # 일반 ComfyUI Backend API에서는 보통 /upload/image 사용
    upload_url = f"{comfyui_base_url}/upload/image"

    files = {
        # endpoint 이름은 image지만, multipart 필드명도 image를 쓰는 경우가 많음
        "image": (
            safe_name,
            file_bytes,
            "text/csv"
        )
    }

    data = {
        "type": "input",
        "subfolder": target_subdir,
        "overwrite": "true",
    }

    headers = {}

    # RunComfy 환경에서 인증이 필요한 경우를 대비
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"

    response = requests.post(
        upload_url,
        headers=headers,
        files=files,
        data=data,
        timeout=60,
    )

    if response.status_code >= 400:
        raise RuntimeError(
            f"Upload failed. status={response.status_code}, body={response.text}"
        )

    return {
        "status_code": response.status_code,
        "response_text": response.text,
        "file_name": safe_name,
        "subfolder": target_subdir,
        "relative_path": relative_path,
    }
