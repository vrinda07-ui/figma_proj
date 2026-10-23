"""
FastAPI Server Adapter for Vista Slide POC / Figma-to-Dashboard Generator
Connects frontend to the real XGBoost ML pipeline and Vista page generation.
"""

import json
import os
import sys
import time
import uuid
from datetime import datetime
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

# History storage
HISTORY_DIR = ROOT / "outputs" / "history"
HISTORY_DIR.mkdir(parents=True, exist_ok=True)
HISTORY_INDEX_FILE = HISTORY_DIR / "index.json"

def load_history_index() -> List[Dict[str, Any]]:
    """Load history index from disk."""
    if HISTORY_INDEX_FILE.exists():
        try:
            with open(HISTORY_INDEX_FILE, encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return []
    return []

def save_history_index(index: List[Dict[str, Any]]):
    """Save history index to disk."""
    with open(HISTORY_INDEX_FILE, "w", encoding="utf-8") as f:
        json.dump(index, f, indent=2, ensure_ascii=False)

def add_history_entry(run_id: str, design_name: str, component_count: int, widget_count: int, tile_count: int, need_attention: int) -> Dict[str, Any]:
    """Add a new entry to history index."""
    index = load_history_index()
    entry = {
        "runId": run_id,
        "designName": design_name,
        "timestamp": datetime.utcnow().isoformat(),
        "componentCount": component_count,
        "widgetCount": widget_count,
        "tileCount": tile_count,
        "needAttention": need_attention,
        "status": "completed"
    }
    index.insert(0, entry)  # Add to beginning
    save_history_index(index)
    return entry


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
    runId: Optional[str] = None


# ============================================================================
# API ENDPOINTS
# ============================================================================

@app.get("/api/status")
def get_status():
    """Return backend health and ML model status."""
    model_path = ROOT / "models" / "xgboost_model.json"
    encoder_path = ROOT / "models" / "label_encoder.pkl"
    
    # Check if plugin has sent data
    active_figma = ROOT / "dataset" / "new_dashboard" / "figma_data.json"
    plugin_data_received = active_figma.exists()
    
    design_name = None
    if plugin_data_received:
        try:
            with open(active_figma, encoding="utf-8") as f:
                data = json.load(f)
            doc = data.get("document", {})
            first_child = doc.get("children", [{}])[0] if doc.get("children") else {}
            design_name = first_child.get("name") or doc.get("name") or "Unknown Design"
            design_name = design_name.replace("\ufffd", " - ").strip()
        except Exception:
            design_name = "Unknown Design"
    
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
        "pluginDataReceived": plugin_data_received,
        "designName": design_name,
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


@app.get("/api/load-plugin-data")
def load_plugin_data():
    """Load Figma data sent by plugin from dataset/new_dashboard/figma_data.json."""
    active_figma = ROOT / "dataset" / "new_dashboard" / "figma_data.json"
    if not active_figma.exists():
        raise HTTPException(status_code=404, detail="No plugin data found. Please send design from Figma plugin first.")
    
    try:
        with open(active_figma, encoding="utf-8") as f:
            figma_data = json.load(f)
        
        nodes, doc_name, dims = extract_nodes_from_figma_payload(figma_data)
        return {
            "success": True,
            "documentName": doc_name,
            "nodeCount": len(nodes),
            "dimensions": dims,
            "figmaJson": figma_data
        }
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Failed to load plugin data: {str(exc)}")


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
    """Run candidate generation stage only (Normalize)."""
    figma_data = request.figmaJson
    if not figma_data:
        active_figma = ROOT / "dataset" / "new_dashboard" / "figma_data.json"
        if not active_figma.exists():
            raise HTTPException(status_code=404, detail="No Figma data found. Please send from plugin first.")
        with open(active_figma, encoding="utf-8") as f:
            figma_data = json.load(f)

    nodes, doc_name, _ = extract_nodes_from_figma_payload(figma_data)
    candidates = run_candidate_generation(nodes, dashboard_name=doc_name)
    
    # Save to disk
    cand_file = ROOT / "dataset" / "new_candidates" / "new_dashboard_candidates.json"
    cand_file.parent.mkdir(parents=True, exist_ok=True)
    with open(cand_file, "w", encoding="utf-8") as f:
        json.dump({"dashboard": doc_name, "candidate_count": len(candidates), "candidates": candidates}, f, indent=2, ensure_ascii=False)
    
    return {
        "success": True,
        "stage": "normalize",
        "candidateCount": len(candidates),
        "documentName": doc_name,
        "normalizedJson": {
            "dashboard": doc_name,
            "candidate_count": len(candidates),
            "candidates": candidates
        }
    }


@app.post("/api/preprocess")
def preprocess_candidates(request: GenerateRequest):
    """Run preprocessing (feature extraction) on normalized candidates."""
    # Load candidates from normalize stage
    cand_file = ROOT / "dataset" / "new_candidates" / "new_dashboard_candidates.json"
    if not cand_file.exists():
        raise HTTPException(status_code=404, detail="No normalized candidates found. Please run Normalize first.")
    
    with open(cand_file, encoding="utf-8") as f:
        cand_data = json.load(f)
    
    candidates = cand_data.get("candidates", [])
    doc_name = cand_data.get("dashboard", "new_dashboard")
    
    # Feature extraction is part of classification, so we'll extract features here
    from src.features.extract_features import calculate_features
    import pandas as pd
    
    feature_rows = [calculate_features(c) for c in candidates]
    features_df = pd.DataFrame(feature_rows)
    
    return {
        "success": True,
        "stage": "preprocess",
        "candidateCount": len(candidates),
        "documentName": doc_name,
        "features": features_df.to_dict(orient="records")[:10],  # Return first 10 for preview
        "totalFeatures": len(feature_rows)
    }


@app.post("/api/classify")
def classify_components(request: GenerateRequest):
    """Run XGBoost classification and prediction cleaning only."""
    # Load candidates from normalize stage
    cand_file = ROOT / "dataset" / "new_candidates" / "new_dashboard_candidates.json"
    if not cand_file.exists():
        raise HTTPException(status_code=404, detail="No normalized candidates found. Please run Normalize first.")
    
    with open(cand_file, encoding="utf-8") as f:
        cand_data = json.load(f)
    
    candidates = cand_data.get("candidates", [])
    
    raw_predictions = run_classification(candidates)
    cleaned = run_prediction_cleaning(raw_predictions)
    
    # Save to disk
    clean_file = ROOT / "dataset" / "new_candidates" / "new_dashboard_clean_predictions.json"
    clean_file.parent.mkdir(parents=True, exist_ok=True)
    with open(clean_file, "w", encoding="utf-8") as f:
        json.dump({"dashboard": cand_data.get("dashboard", "new_dashboard"), "candidate_count": len(cleaned), "predictions": cleaned}, f, indent=2, ensure_ascii=False)

    return {
        "success": True,
        "stage": "classify",
        "candidateCount": len(cleaned),
        "classifierJson": {
            "candidate_count": len(cleaned),
            "predictions": cleaned
        }
    }


@app.post("/api/generate-layout")
def generate_layout(request: GenerateRequest):
    """Generate 12x12 grid layout and Vista page.json from predictions."""
    # Load predictions from classify stage
    pred_file = ROOT / "dataset" / "new_candidates" / "new_dashboard_clean_predictions.json"
    if not pred_file.exists():
        raise HTTPException(status_code=404, detail="No predictions found. Please run Classify first.")
    
    # Load figma data
    active_figma = ROOT / "dataset" / "new_dashboard" / "figma_data.json"
    if not active_figma.exists():
        raise HTTPException(status_code=404, detail="No Figma data found.")
    
    with open(active_figma, encoding="utf-8") as f:
        figma_data = json.load(f)
    
    with open(pred_file, encoding="utf-8") as f:
        pred_data = json.load(f)
    
    predictions = pred_data.get("predictions", [])
    
    # Generate grid layout
    grid_layout = run_grid_layout(figma_data, predictions)
    
    # Generate Vista page
    package_meta = request.packageDetails.dict() if request.packageDetails else None
    source_nodes, _, _ = extract_nodes_from_figma_payload(figma_data)

    vista_page = run_vista_page_generation(
        grid_layout,
        predictions,
        package_meta,
        source_nodes=source_nodes,
    )
    
    # Generate or use provided run ID
    run_id = request.runId or str(uuid.uuid4())[:8]
    
    # Save to history directory
    run_dir = HISTORY_DIR / run_id
    run_dir.mkdir(parents=True, exist_ok=True)
    
    # Save all outputs to history
    with open(run_dir / "figma_data.json", "w", encoding="utf-8") as f:
        json.dump(figma_data, f, indent=2, ensure_ascii=False)
    
    # Load raw predictions if available
    raw_pred_file = ROOT / "dataset" / "new_candidates" / "new_dashboard_predictions.json"
    if raw_pred_file.exists():
        with open(raw_pred_file, encoding="utf-8") as f:
            raw_predictions = json.load(f)
        with open(run_dir / "raw_predictions.json", "w", encoding="utf-8") as f:
            json.dump(raw_predictions, f, indent=2, ensure_ascii=False)
    
    with open(run_dir / "clean_predictions.json", "w", encoding="utf-8") as f:
        json.dump(pred_data, f, indent=2, ensure_ascii=False)
    
    with open(run_dir / "grid_layout.json", "w", encoding="utf-8") as f:
        json.dump(grid_layout, f, indent=2, ensure_ascii=False)
    
    with open(run_dir / "page.json", "w", encoding="utf-8") as f:
        json.dump(vista_page, f, indent=2, ensure_ascii=False)
    
    # Also save to standard locations for backward compatibility
    grid_file = ROOT / "outputs" / "dashboard_configs" / "new_dashboard" / "grid_layout.json"
    grid_file.parent.mkdir(parents=True, exist_ok=True)
    with open(grid_file, "w", encoding="utf-8") as f:
        json.dump(grid_layout, f, indent=2, ensure_ascii=False)
    
    page_file = ROOT / "outputs" / "vista_pages" / "new_dashboard" / "page.json"
    page_file.parent.mkdir(parents=True, exist_ok=True)
    with open(page_file, "w", encoding="utf-8") as f:
        json.dump(vista_page, f, indent=2, ensure_ascii=False)
    
    # Add to history index
    add_history_entry(
        run_id=run_id,
        design_name=vista_page["title"],
        component_count=len(predictions),
        widget_count=len(vista_page["widgets"]),
        tile_count=len(vista_page["tiles"]),
        need_attention=vista_page["validation"]["reviewRequired"]
    )
    
    return {
        "success": True,
        "stage": "generate-layout",
        "runId": run_id,
        "gridLayout": grid_layout,
        "pageJson": vista_page,
        "stats": {
            "widgets": len(vista_page["widgets"]),
            "tiles": len(vista_page["tiles"]),
            "needAttention": vista_page["validation"]["reviewRequired"]
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


# ============================================================================
# HISTORY API ENDPOINTS
# ============================================================================

@app.get("/api/history")
def get_history():
    """List all historical runs."""
    index = load_history_index()
    return {"runs": index}


@app.get("/api/history/{run_id}")
def get_history_run(run_id: str):
    """Get details for a specific historical run."""
    index = load_history_index()
    entry = next((e for e in index if e["runId"] == run_id), None)
    if not entry:
        raise HTTPException(status_code=404, detail="Run not found in history.")
    
    # Load the run's JSON files
    run_dir = HISTORY_DIR / run_id
    if not run_dir.exists():
        raise HTTPException(status_code=404, detail="Run data not found on disk.")
    
    result = dict(entry)
    
    # Load available JSON outputs
    json_files = {
        "figma_data": run_dir / "figma_data.json",
        "raw_predictions": run_dir / "raw_predictions.json",
        "clean_predictions": run_dir / "clean_predictions.json",
        "grid_layout": run_dir / "grid_layout.json",
        "page_json": run_dir / "page.json"
    }
    
    available_jsons = {}
    for key, path in json_files.items():
        if path.exists():
            available_jsons[key] = True
        else:
            available_jsons[key] = False
    
    result["availableOutputs"] = available_jsons
    return result


@app.get("/api/history/{run_id}/json/{json_type}")
def get_history_json(run_id: str, json_type: str):
    """Get a specific JSON output for a run."""
    run_dir = HISTORY_DIR / run_id
    if not run_dir.exists():
        raise HTTPException(status_code=404, detail="Run not found.")
    
    # Map json_type to file path
    file_map = {
        "figma_data": "figma_data.json",
        "raw_predictions": "raw_predictions.json",
        "clean_predictions": "clean_predictions.json",
        "grid_layout": "grid_layout.json",
        "page_json": "page.json"
    }
    
    if json_type not in file_map:
        raise HTTPException(status_code=400, detail=f"Invalid JSON type: {json_type}")
    
    file_path = run_dir / file_map[json_type]
    if not file_path.exists():
        raise HTTPException(status_code=404, detail=f"JSON file not found: {json_type}")
    
    with open(file_path, encoding="utf-8") as f:
        return json.load(f)


@app.get("/api/history/{run_id}/download/{json_type}")
def download_history_json(run_id: str, json_type: str):
    """Download a specific JSON output for a run."""
    run_dir = HISTORY_DIR / run_id
    if not run_dir.exists():
        raise HTTPException(status_code=404, detail="Run not found.")
    
    file_map = {
        "figma_data": "figma_data.json",
        "raw_predictions": "raw_predictions.json",
        "clean_predictions": "clean_predictions.json",
        "grid_layout": "grid_layout.json",
        "page_json": "page.json"
    }
    
    if json_type not in file_map:
        raise HTTPException(status_code=400, detail=f"Invalid JSON type: {json_type}")
    
    file_path = run_dir / file_map[json_type]
    if not file_path.exists():
        raise HTTPException(status_code=404, detail=f"JSON file not found: {json_type}")
    
    # Generate descriptive filename
    filename = f"{run_id}_{json_type}.json"
    
    return FileResponse(
        path=str(file_path),
        filename=filename,
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
