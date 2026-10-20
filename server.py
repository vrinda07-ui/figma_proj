"""
FastAPI Server Adapter for Vista Slide POC / Figma-to-Dashboard Generator
Connects frontend to the real XGBoost ML pipeline and Vista page generation.
"""

import json
import os
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.pipeline import (
    execute_full_pipeline,
    extract_nodes_from_figma_payload,
    run_candidate_generation,
    run_classification,
    run_grid_layout,
    run_prediction_cleaning,
    run_vista_page_generation,
)

app = FastAPI(
    title="Vista Slide POC - Figma-to-Dashboard Generator",
    description="AI-powered pipeline transforming Figma designs into Vista dashboard page.json using XGBoost",
    version="1.0.0"
)

# Enable CORS for frontend development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Storage paths
STORAGE_DIR = ROOT / "outputs" / "designs"
STORAGE_DIR.mkdir(parents=True, exist_ok=True)


class PackageDetails(BaseModel):
    subjectArea: Optional[str] = "sales"
    topic: Optional[str] = "ecommerce"
    slideName: Optional[str] = "revenue-summary"
    slideId: Optional[str] = "CR001"
    title: Optional[str] = None


class GenerateRequest(BaseModel):
    figmaJson: Optional[Dict[str, Any]] = None
    designId: Optional[str] = None
    packageDetails: Optional[PackageDetails] = None
    reclassify: Optional[bool] = False
    includeChrome: Optional[bool] = False


# ============================================================================
# API ENDPOINTS
# ============================================================================

@app.get("/api/status")
def get_status():
    """Return backend health and ML model status."""
    model_path = ROOT / "models" / "xgboost_model.json"
    encoder_path = ROOT / "models" / "label_encoder.pkl"
    return {
        "status": "connected",
        "modelLoaded": model_path.exists() and encoder_path.exists(),
        "modelFile": str(model_path.name),
        "classes": ["CHART", "KPI_CARD", "OTHER", "TABLE"],
        "pipelineStages": [
            "Candidate Generation (gc)",
            "Semantic Feature Extraction (20 features)",
            "XGBoost Classifier",
            "Heuristic Prediction Cleaning",
            "12x12 CSS Grid Layout Mapping",
            "Vista Slide page.json Assembly"
        ],
        "timestamp": time.time()
    }


def list_sample_designs() -> List[Dict[str, Any]]:
    """Index preloaded sample designs and any saved user designs."""
    results = []

    # 1. Active design in new_dashboard
    active_figma = ROOT / "dataset" / "new_dashboard" / "figma_data.json"
    active_page = ROOT / "outputs" / "vista_pages" / "new_dashboard" / "page.json"
    if active_figma.exists():
        try:
            with open(active_figma, encoding="utf-8") as f:
                d = json.load(f)
            doc_name = "Design 03 — Appointment Operations"
            first_child = d.get("document", {}).get("children", [{}])[0]
            if first_child.get("type") == "PAGE" and first_child.get("children"):
                frame_child = first_child["children"][0]
                if frame_child.get("name"):
                    doc_name = frame_child.get("name")
            elif first_child.get("name"):
                doc_name = first_child.get("name")

            doc_name = doc_name.replace("\ufffd", " - ").strip()

            tile_count = 12
            if active_page.exists():
                try:
                    with open(active_page, encoding="utf-8") as pf:
                        pdata = json.load(pf)
                        tile_count = len(pdata.get("tiles", []))
                except Exception:
                    pass

            results.append({
                "id": "design-03-appointment-operations",
                "name": doc_name,
                "subtitle": "1607:2230 #03",
                "status": "Generated",
                "statusColor": "green",
                "tiles": tile_count,
                "lastRun": "just now",
                "isSample": True,
                "filePath": str(active_figma.relative_to(ROOT))
            })
        except Exception:
            pass

    # 2. Add reference dashboard designs
    reference_presets = [
        {"id": "design-02-pharmacy", "name": "Design 02 - Pharmacy Prescriptions", "subtitle": "6:157 #12", "status": "Generated", "tiles": 9, "lastRun": "just now"},
        {"id": "design-01-healthcare", "name": "Design 01 - Healthcare Analytics", "subtitle": "2:58 #11", "status": "Generated", "tiles": 10, "lastRun": "just now"},
        {"id": "design-ecommerce-rev", "name": "E-commerce Revenue Summary", "subtitle": "EC001 #01", "status": "Generated", "tiles": 11, "lastRun": "just now"},
        {"id": "health-08-care", "name": "Health 08 - Care Management", "subtitle": "2:18502 #09", "status": "Generated", "tiles": 9, "lastRun": "just now"},
        {"id": "health-07-ops", "name": "Health 07 - Clinical Operations", "subtitle": "3:4082 #07", "status": "3 need attention", "statusColor": "orange", "tiles": 12, "lastRun": "just now"}
    ]

    for p in reference_presets:
        if not any(r["id"] == p["id"] for r in results):
            results.append(p)

    return results


@app.get("/api/designs")
def get_designs():
    """List available designs for the gallery view."""
    return {"designs": list_sample_designs()}


@app.get("/api/designs/{design_id}")
def get_design_details(design_id: str):
    """Retrieve full pipeline results for a design."""
    active_figma = ROOT / "dataset" / "new_dashboard" / "figma_data.json"
    if not active_figma.exists():
        raise HTTPException(status_code=404, detail="No active design found.")

    try:
        with open(active_figma, encoding="utf-8") as f:
            figma_data = json.load(f)
        
        # Execute pipeline to ensure fresh state
        result = execute_full_pipeline(figma_data, sync_to_disk=False)
        return result
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@app.post("/api/upload")
async def upload_figma_file(file: UploadFile = File(...)):
    """Upload and validate a Figma JSON file."""
    if not file.filename.endswith(".json"):
        raise HTTPException(status_code=400, detail="Only .json files are supported.")

    try:
        content = await file.read()
        figma_data = json.loads(content.decode("utf-8"))
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Invalid JSON file: {str(exc)}")

    try:
        nodes, doc_name, dims = extract_nodes_from_figma_payload(figma_data)
        return {
            "success": True,
            "filename": file.filename,
            "documentName": doc_name,
            "nodeCount": len(nodes),
            "dimensions": dims,
            "figmaJson": figma_data
        }
    except Exception as exc:
        raise HTTPException(status_code=422, detail=f"Figma structure error: {str(exc)}")


@app.post("/api/generate")
def generate_dashboard(request: GenerateRequest):
    """
    Main Generation Endpoint:
    Accepts Figma JSON or design ID + package details,
    executes candidate generation, XGBoost inference, grid mapping, and Vista page.json generation.
    """
    figma_data = request.figmaJson

    if not figma_data:
        active_figma = ROOT / "dataset" / "new_dashboard" / "figma_data.json"
        if active_figma.exists():
            with open(active_figma, encoding="utf-8") as f:
                figma_data = json.load(f)
        else:
            raise HTTPException(status_code=400, detail="No Figma JSON provided and no active design found.")

    package_meta = request.packageDetails.dict() if request.packageDetails else None

    try:
        result = execute_full_pipeline(
            figma_data=figma_data,
            package_metadata=package_meta,
            sync_to_disk=True
        )
        return result
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Generation failed: {str(exc)}")


@app.post("/api/normalize")
def normalize_candidates(request: GenerateRequest):
    """Run candidate generation stage only."""
    figma_data = request.figmaJson
    if not figma_data:
        active_figma = ROOT / "dataset" / "new_dashboard" / "figma_data.json"
        with open(active_figma, encoding="utf-8") as f:
            figma_data = json.load(f)

    nodes, doc_name, _ = extract_nodes_from_figma_payload(figma_data)
    candidates = run_candidate_generation(nodes, dashboard_name=doc_name)
    return {
        "success": True,
        "candidateCount": len(candidates),
        "normalizedJson": {
            "dashboard": doc_name,
            "candidate_count": len(candidates),
            "candidates": candidates
        }
    }


@app.post("/api/classify")
def classify_components(request: GenerateRequest):
    """Run XGBoost classification and prediction cleaning only."""
    figma_data = request.figmaJson
    if not figma_data:
        active_figma = ROOT / "dataset" / "new_dashboard" / "figma_data.json"
        with open(active_figma, encoding="utf-8") as f:
            figma_data = json.load(f)

    nodes, doc_name, _ = extract_nodes_from_figma_payload(figma_data)
    candidates = run_candidate_generation(nodes, dashboard_name=doc_name)
    raw_predictions = run_classification(candidates)
    cleaned = run_prediction_cleaning(raw_predictions)

    return {
        "success": True,
        "candidateCount": len(cleaned),
        "classifierJson": {
            "candidate_count": len(cleaned),
            "predictions": cleaned
        }
    }


@app.get("/api/download/page.json")
def download_page_json():
    """Download the generated Vista page.json file."""
    page_file = ROOT / "outputs" / "vista_pages" / "new_dashboard" / "page.json"
    if not page_file.exists():
        raise HTTPException(status_code=404, detail="No generated page.json found. Run generation first.")
    return FileResponse(
        path=str(page_file),
        filename="page.json",
        media_type="application/json"
    )


@app.get("/api/download/predictions.json")
def download_predictions_json():
    """Download the cleaned XGBoost predictions."""
    pred_file = ROOT / "dataset" / "new_candidates" / "new_dashboard_clean_predictions.json"
    if not pred_file.exists():
        raise HTTPException(status_code=404, detail="No predictions found.")
    return FileResponse(
        path=str(pred_file),
        filename="new_dashboard_clean_predictions.json",
        media_type="application/json"
    )


@app.post("/ingest")
async def plugin_ingest(file: UploadFile = File(None)):
    """Compatibility endpoint for Figma plugin."""
    try:
        active_figma = ROOT / "dataset" / "new_dashboard" / "figma_data.json"
        if file:
            content = await file.read()
            payload = json.loads(content.decode("utf-8"))
        else:
            raise HTTPException(status_code=400, detail="Missing payload")

        active_figma.parent.mkdir(parents=True, exist_ok=True)
        with open(active_figma, "w", encoding="utf-8") as f:
            json.dump(payload, f, indent=2)

        result = execute_full_pipeline(payload)
        return {
            "message": "Design received and Vista page.json generated.",
            "widgets": result["stats"]["widgets"],
            "tiles": result["stats"]["tiles"]
        }
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


# Serve dashboard_preview.html at /dashboard_preview.html
@app.get("/dashboard_preview.html")
def get_dashboard_preview():
    html_file = ROOT / "dashboard_preview.html"
    if html_file.exists():
        return FileResponse(str(html_file))
    return HTMLResponse("<h1>Preview file not found</h1>")


# Serve static frontend dist if it exists
FRONTEND_DIST = ROOT / "frontend" / "dist"
if FRONTEND_DIST.exists():
    app.mount("/assets", StaticFiles(directory=str(FRONTEND_DIST / "assets")), name="assets")

    @app.get("/{full_path:path}")
    def serve_frontend(full_path: str):
        file_path = FRONTEND_DIST / full_path
        if file_path.is_file():
            return FileResponse(str(file_path))
        return FileResponse(str(FRONTEND_DIST / "index.html"))


if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8000))
    print(f"Starting Vista POC Dashboard Generator server on http://127.0.0.1:{port}")
    uvicorn.run("server:app", host="0.0.0.0", port=port, reload=False)
