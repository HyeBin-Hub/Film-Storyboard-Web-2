# AI Storyboard Pipeline

A Streamlit application for storyboard-driven image generation using ComfyUI workflows executed through RunComfy Serverless. The application combines CSV-driven shot data, character references, scene generation, and camera refinement.

## Features

- **Storyboard input:** Upload a CSV file and select shot IDs.
- **Step 2A — Face generation:** Generate character appearances from storyboard and character settings.
- **Step 2B — Body / outfit generation:** Use reference images and garment inputs to generate outfit variations.
- **Step 3 — Scene generation:** Compose a shot from selected character results and scene inputs.
- **Step 4 — Camera refinement:** Refine a generated scene with camera-angle controls.

The interface and workflow orchestration are implemented in **Streamlit and Python modules**. There is no separate FastAPI service.

## Architecture

```text
app.py                 # Streamlit entry point: UI and workflow orchestration
app_constants.py       # Feature flags, defaults, and widget choices
app_helpers.py         # CSV, upload, session-state, and workflow configuration helpers
ui_components.py       # Reusable image preview UI
backend.py             # ComfyUI workflow patching and RunComfy HTTP integration
preset_results.py      # Optional test/preset results
workflows/             # ComfyUI workflow JSON files and supporting assets
.devcontainer/         # GitHub Codespaces development environment
requirements.txt       # Python runtime dependencies
.streamlit/
  secrets.toml.example # Local configuration template (no credentials)
```

### Execution flow

```text
Storyboard CSV / image references
          |
      Streamlit UI (app.py)
          |
      Config helpers (app_helpers.py)
          |
      Python workflow client (backend.py)
          |
ComfyUI API-format workflow JSON
          |
RunComfy Serverless inference -> status polling -> generated image URLs
          |
      Streamlit results
```

`backend.py` acts as an **in-process Python module**, not a separately deployed backend service. It patches workflow inputs, submits inference requests, polls for results, and extracts output images.

## Requirements

- Python 3.11 recommended (Python 3.10 or later required by type annotations).
- A RunComfy Serverless deployment and a valid API key.
- ComfyUI nodes, model checkpoints, and workflow configuration compatible with the target deployment.
- Python packages listed in `requirements.txt`.

The repository includes workflow JSON definitions but **does not include model weights**. Some workflows depend on custom ComfyUI nodes; running the Streamlit UI alone does not make the remote deployment ready.

## Run locally

1. Clone the repository:

   ```bash
   git clone https://github.com/HyeBin-Hub/ai-storyboard-pipeline.git
   cd ai-storyboard-pipeline
   ```

2. Create and activate a virtual environment:

   ```bash
   python -m venv .venv
   # macOS / Linux
   source .venv/bin/activate
   # Windows PowerShell
   # .venv\Scripts\Activate.ps1
   ```

3. Install dependencies:

   ```bash
   pip install -r requirements.txt
   ```

4. Copy `.streamlit/secrets.toml.example` to `.streamlit/secrets.toml` and supply the credentials for **your** RunComfy deployment:

   ```toml
   RUNCOMFY_API_KEY = "your-api-key"
   DEPLOYMENT_ID = "your-deployment-id"
   ```

   Never commit `secrets.toml` or API keys.

5. Start the application:

   ```bash
   streamlit run app.py
   ```

6. Upload a storyboard CSV, select the desired character/shot inputs, and run the stages in order. Image generation requires a correctly configured, reachable RunComfy deployment.

## Workflows

The active workflow paths are declared in `backend.py`:

| Stage | Workflow |
| --- | --- |
| Character appearance | `workflows/Character_Appearance_Generation.json` |
| Reference-based outfit change | `workflows/Reference-based_Outfit_Change.json` |
| Reference-based scene generation | `workflows/Reference-based_Scene_Generation.json` |
| Camera refinement | `workflows/Camera_Refinement.json` |

**Important:** The `*_workflow_api.json` files and the active paths above are not interchangeable merely because of their names. Confirm that a workflow is exported with ComfyUI **Save (API Format)** and matches the node IDs and classes used by `backend.py` before replacing an active workflow. A UI-format file with a `nodes` list will be rejected by the loader.

## Deployment notes

The `.devcontainer/devcontainer.json` file is configured to launch `app.py` in Codespaces. For Streamlit Community Cloud, set **Main file path** to `app.py` and add `RUNCOMFY_API_KEY` and `DEPLOYMENT_ID` to the app's secrets settings. Do not disable authentication or publish credentials in logs.

## Validation status

- The four refactored application modules passed Python syntax compilation.
- Remote RunComfy inference, end-to-end generation, and deployment compatibility have **not** been verified in this repository update.
- Preset results are intended for UI testing and are not evidence of a successful current inference.

## License

No license is declared in this repository. Contact the author before reusing the source.
