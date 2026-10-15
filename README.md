# AI Storyboard Pipeline

Storyboard-based image generation with Streamlit, ComfyUI, and RunComfy Serverless.

## Workflow

1. Upload a storyboard CSV and select shots.
2. Generate character faces and outfits.
3. Generate scenes using character references.
4. Refine the camera angle.

## Project Structure

```text
app.py              Streamlit UI
app_constants.py    UI options and defaults
app_helpers.py      CSV, session state, and input helpers
ui_components.py    Image preview components
backend.py          ComfyUI workflow setup and RunComfy API calls
preset_results.py   Test result presets
workflows/          ComfyUI workflow JSON files
```

## Setup

Requires Python 3.11 and a RunComfy deployment configured with the required ComfyUI models and custom nodes.

```bash
git clone https://github.com/HyeBin-Hub/ai-storyboard-pipeline.git
cd ai-storyboard-pipeline
pip install -r requirements.txt
```

Copy `.streamlit/secrets.toml.example` to `.streamlit/secrets.toml` and set:

```toml
RUNCOMFY_API_KEY = "your-api-key"
DEPLOYMENT_ID = "your-deployment-id"
```

Run the app:

```bash
streamlit run app.py
```

The app sends ComfyUI API-format workflows to RunComfy Serverless. Model weights and deployment configuration are not included in this repository.
