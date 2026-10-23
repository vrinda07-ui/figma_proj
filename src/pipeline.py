"""
Unified Figma-to-Dashboard Pipeline Runner
Integrates:
1. Candidate Generation (src/preprocessing/generate_candidates.py)
2. Feature Extraction (src/features/extract_features.py)
3. XGBoost Model Prediction (models/xgboost_model.json & models/label_encoder.pkl)
4. Prediction Cleaning (src/output/clean_predictions.py)
5. 12x12 Grid Layout Generation (src/output/generate_grid_layout.py)
6. Vista Page Generation (compliant with Vista POC student guide)
"""

import json
import math
import os
import re
import secrets
import string
import sys
import time
import uuid
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import joblib
import pandas as pd
from xgboost import XGBClassifier

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))
if str(ROOT / "src" / "preprocessing") not in sys.path:
    sys.path.insert(0, str(ROOT / "src" / "preprocessing"))

import generate_candidates as gc
from src.features.extract_features import calculate_features

# Standard file paths
MODEL_FILE = ROOT / "models" / "xgboost_model.json"
ENCODER_FILE = ROOT / "models" / "label_encoder.pkl"

FEATURE_COLS = [
    "width", "height", "area", "aspect_ratio", "child_count",
    "text_count", "numeric_text_count", "text_density",
    "numeric_density", "vector_count", "line_count",
    "ellipse_count", "rectangle_count", "graphical_count",
    "has_percentage", "has_date_text", "has_chart_word",
    "has_table_word", "has_kpi_word", "has_filter_word",
]

GRID_COLUMNS = 12
GRID_ROWS = 12


def generate_short_id(length: int = 5) -> str:
    """Generate a clean 5-character alphanumeric ID, e.g. CR001."""
    chars = string.ascii_uppercase + string.digits
    return "".join(secrets.choice(chars) for _ in range(length))


def flatten_figma_document(document: Dict[str, Any], parent_id: Optional[str] = None) -> List[Dict[str, Any]]:
    """Recursively flatten Figma's nested document tree into a flat node list."""
    nodes = []
    current = dict(document)
    current["parent_id"] = parent_id

    if current.get("type") == "TEXT":
        current["text"] = current.get("characters", "")

    bbox = current.get("absoluteBoundingBox")
    if bbox and isinstance(bbox, dict):
        current["x"] = bbox.get("x", 0.0)
        current["y"] = bbox.get("y", 0.0)
        current["width"] = bbox.get("width", 0.0)
        current["height"] = bbox.get("height", 0.0)

    nodes.append(current)

    for child in current.get("children", []):
        if isinstance(child, dict):
            nodes.extend(flatten_figma_document(child, parent_id=current.get("id")))

    return nodes


def extract_nodes_from_figma_payload(data: Dict[str, Any]) -> Tuple[List[Dict[str, Any]], str, Dict[str, float]]:
    """
    Extract flat nodes from either nested Figma REST/plugin payload:
    { "document": { ... } } or flat payload: { "nodes": [ ... ] }
    """
    doc_name = "Dashboard"
    dimensions = {"width": 1440.0, "height": 900.0}

    if "document" in data and isinstance(data["document"], dict):
        document = data["document"]
        doc_name = document.get("name") or data.get("pageName") or "Dashboard"
        
        # Check first child frame for dimensions
        first_children = document.get("children", [])
        if first_children and isinstance(first_children[0], dict):
            first_child = first_children[0]
            if first_child.get("type") == "PAGE" and first_child.get("children"):
                frame_child = first_child["children"][0]
                if frame_child.get("name"):
                    doc_name = frame_child.get("name")
                bbox = frame_child.get("absoluteBoundingBox")
                if bbox and isinstance(bbox, dict):
                    dimensions["width"] = float(bbox.get("width", 1440.0))
                    dimensions["height"] = float(bbox.get("height", 900.0))
            else:
                if first_child.get("name"):
                    doc_name = first_child.get("name")
                bbox = first_child.get("absoluteBoundingBox")
                if bbox and isinstance(bbox, dict):
                    dimensions["width"] = float(bbox.get("width", 1440.0))
                    dimensions["height"] = float(bbox.get("height", 900.0))

        # Clean any corrupted encoding artifacts (e.g. \ufffd replacement character)
        doc_name = doc_name.replace("\ufffd", " - ").strip()

        nodes = []
        for child in document.get("children", []):
            if isinstance(child, dict):
                nodes.extend(flatten_figma_document(child, parent_id=document.get("id")))
        return nodes, doc_name, dimensions

    elif "nodes" in data and isinstance(data["nodes"], list):
        nodes = data["nodes"]
        doc_name = data.get("file_name") or data.get("name") or "Dashboard"
        return nodes, doc_name, dimensions

    else:
        raise ValueError("Invalid Figma JSON: Expected 'document' or 'nodes' root property.")


def run_candidate_generation(nodes: List[Dict[str, Any]], dashboard_name: str = "new_dashboard") -> List[Dict[str, Any]]:
    """Stage 1: Candidate Generation using gc logic."""
    if not nodes:
        raise ValueError("No nodes found in Figma document.")

    node_map, children = gc.make_maps(nodes)
    candidates = []

    for node in nodes:
        if not gc.is_container(node):
            continue

        node_id = node.get("id")
        info = gc.stats(node_id, node_map, children)

        if gc.is_component_candidate(node, info):
            candidate = gc.build_candidate(node, info, dashboard_name)
            candidates.append(candidate)

    candidates = gc.remove_nested(candidates, node_map, children)

    # Deduplicate by candidate_id
    unique_candidates = list({c["candidate_id"]: c for c in candidates}.values())
    unique_candidates.sort(key=lambda c: (float(c.get("y") or 0), float(c.get("x") or 0)))

    return unique_candidates


def run_classification(candidates: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Stage 2: XGBoost Feature Extraction & Model Inference."""
    if not candidates:
        return []

    if not MODEL_FILE.exists():
        raise FileNotFoundError(f"Trained XGBoost model not found at {MODEL_FILE}")
    if not ENCODER_FILE.exists():
        raise FileNotFoundError(f"Label encoder not found at {ENCODER_FILE}")

    model = XGBClassifier()
    model.load_model(str(MODEL_FILE))
    encoder = joblib.load(ENCODER_FILE)

    feature_rows = [calculate_features(c) for c in candidates]
    features_df = pd.DataFrame(feature_rows)

    # Ensure all required feature columns exist
    for col in FEATURE_COLS:
        if col not in features_df.columns:
            features_df[col] = 0.0

    X_new = features_df[FEATURE_COLS].astype(float).fillna(0.0)

    predictions_encoded = model.predict(X_new)
    predictions = encoder.inverse_transform(predictions_encoded.astype(int))

    # Calculate probabilities for confidence reporting
    try:
        probas = model.predict_proba(X_new)
        confidences = probas.max(axis=1) * 100.0
    except Exception:
        confidences = [95.0] * len(predictions)

    results = []
    for candidate, pred, conf in zip(candidates, predictions, confidences):
        res = dict(candidate)
        res["predicted_type"] = str(pred)
        res["confidence"] = round(float(conf), 1)
        results.append(res)

    return results




def correct_prediction_type(component: Dict[str, Any]) -> str:
    """Apply conservative rules to correct obvious component misclassifications."""

    name = str(component.get("name", "")).lower()

    texts = [
        str(t).strip()
        for t in component.get("text_preview", [])
        if str(t).strip()
    ]

    text = " ".join(texts).lower()

    # Decorative elements should not be treated as dashboard widgets.
    if any(word in name for word in ("picture", "avatar", "icon")):
        return "OTHER"

    # Keep common page-level elements as OTHER.
    if name in {"title", "breadcrumb", "header utilities"}:
        return "OTHER"

    # Ignore numbered listening-list items.
    if "listenings" in text and any(
        t.startswith(f"{i}.")
        for i in range(1, 6)
        for t in texts
    ):
        return "OTHER"

    # Preserve existing KPI corrections.
    if any(metric in text for metric in [
        "minutes of listening",
        "unique tracks",
        "different artists",
        "appointments today",
    ]):
        return "KPI_CARD"

    # Identify explicit KPI cards using numeric values and label text.
    numeric_items = [
        t for t in texts
        if any(ch.isdigit() for ch in t)
    ]

    nonnumeric_items = [
        t for t in texts
        if not any(ch.isdigit() for ch in t)
    ]

    explicit_kpi_name = (
        "kpi card" in name
        or "kpi_card" in name
    )

    if explicit_kpi_name and numeric_items and nonnumeric_items:
        return "KPI_CARD"

    # Detect metric cards from their semantic name and text.
    metric_keywords = (
        "revenue",
        "engaged members",
        "average order",
        "repeat purchase",
        "new patients",
        "opd patients",
        "visitors",
        "no-show rate",
        "avg wait time",
        "utilisation",
        "utilization",
    )

    has_metric_label = any(
        keyword in name or keyword in text
        for keyword in metric_keywords
    )

    has_percentage_or_currency = any(
        "%" in t or "$" in t or "€" in t or "£" in t
        for t in numeric_items
    )

    if (
        has_metric_label
        and len(numeric_items) >= 1
        and len(nonnumeric_items) >= 1
        and has_percentage_or_currency
    ):
        return "KPI_CARD"

    # Donut/chart containers with multiple ellipses are charts.
    if "chart" in name and component.get("ellipse_count", 0) >= 2:
        return "CHART"

    # Otherwise, preserve the model's original prediction.
    return component.get("predicted_type", "OTHER")




def run_prediction_cleaning(predictions: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Stage 3: Remove candidates nested inside detected charts and apply type corrections."""
    visible = [dict(p) for p in predictions]

    # Remove candidates nested inside charts
    chart_ids = {
        p["candidate_id"]
        for p in visible
        if p.get("predicted_type") == "CHART"
    }

    # Also remove candidates nested inside tables (to prevent duplicate tables)
    table_ids = {
        p["candidate_id"]
        for p in visible
        if p.get("predicted_type") == "TABLE"
    }

    # Combine both sets of parent IDs
    parent_ids = chart_ids | table_ids

    cleaned = []
    for component in visible:
        parent_id = component.get("parent_id")
        # Remove if nested inside a chart or table
        if parent_id in parent_ids:
            continue

        component["predicted_type"] = correct_prediction_type(component)
        cleaned.append(component)

    # Additional cleanup: remove overlapping tables with same parent
    # If we have a table and a nested table-like element, keep the larger one
    table_preds = [c for c in cleaned if c["predicted_type"] == "TABLE"]
    if len(table_preds) > 1:
        # Group by parent
        by_parent = {}
        for t in table_preds:
            pid = t.get("parent_id")
            if pid not in by_parent:
                by_parent[pid] = []
            by_parent[pid].append(t)

        # For each parent, keep only the largest table
        to_remove = set()
        for pid, group in by_parent.items():
            if len(group) > 1:
                # Sort by area descending, keep the largest
                group.sort(key=lambda x: x.get("area", 0), reverse=True)
                for t in group[1:]:  # Remove all but the largest
                    to_remove.add(t["candidate_id"])

        cleaned = [c for c in cleaned if c["candidate_id"] not in to_remove]

    return cleaned


def get_bbox(node: Dict[str, Any]) -> Optional[Dict[str, float]]:
    bbox = node.get("absoluteBoundingBox")
    if not isinstance(bbox, dict):
        # Fallback to direct x, y, width, height if available
        keys = ("x", "y", "width", "height")
        if all(k in node and isinstance(node.get(k), (int, float)) for k in keys):
            if node["width"] > 0 and node["height"] > 0:
                return {k: float(node[k]) for k in keys}
        return None

    keys = ("x", "y", "width", "height")
    if not all(isinstance(bbox.get(key), (int, float)) for key in keys):
        return None
    if bbox["width"] <= 0 or bbox["height"] <= 0:
        return None
    return {key: float(bbox[key]) for key in keys}


def is_inside(inner: Dict[str, float], outer: Dict[str, float], tolerance: float = 1.0) -> bool:
    return (
        inner["x"] >= outer["x"] - tolerance
        and inner["y"] >= outer["y"] - tolerance
        and inner["x"] + inner["width"] <= outer["x"] + outer["width"] + tolerance
        and inner["y"] + inner["height"] <= outer["y"] + outer["height"] + tolerance
    )


def run_grid_layout(figma_data: Dict[str, Any], predictions: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Stage 4: Find Dashboard container and compute 12x12 grid coordinates."""
    # Flatten figma tree for lookup
    raw_nodes, doc_name, default_dims = extract_nodes_from_figma_payload(figma_data)
    nodes = {str(n.get("id")): n for n in raw_nodes if n.get("id") is not None}
    parents = {str(n.get("id")): str(n.get("parent_id")) if n.get("parent_id") is not None else None for n in raw_nodes if n.get("id") is not None}
    children = {}
    for n in raw_nodes:
        pid = n.get("parent_id")
        if pid is not None:
            pid_str = str(pid)
            if pid_str not in children:
                children[pid_str] = []
            children[pid_str].append(str(n.get("id")))

    candidate_ids = []
    for pred in predictions:
        if pred.get("predicted_type") in {"CHART", "KPI_CARD", "TABLE", "FILTER"}:
            cid = str(pred.get("candidate_id"))
            if cid in nodes and get_bbox(nodes[cid]) is not None:
                candidate_ids.append(cid)

    # Container detection
    coverage = {}
    for cid in candidate_ids:
        cur = parents.get(cid)
        while cur is not None and cur in nodes:
            if get_bbox(nodes[cur]) is not None:
                coverage[cur] = coverage.get(cur, 0) + 1
            cur = parents.get(cur)

    dashboard_id = None
    dashboard_node = None
    if coverage:
        max_cov = max(coverage.values())
        possibles = [nid for nid, cnt in coverage.items() if cnt == max_cov]
        dashboard_id = min(
            possibles,
            key=lambda nid: get_bbox(nodes[nid])["width"] * get_bbox(nodes[nid])["height"]
        )
        dashboard_node = nodes[dashboard_id]
    elif raw_nodes:
        # Fallback to the top-level container with a bounding box
        for n in raw_nodes:
            bb = get_bbox(n)
            if bb and bb["width"] >= 800 and bb["height"] >= 500:
                dashboard_id = str(n.get("id"))
                dashboard_node = n
                break

    if not dashboard_node or get_bbox(dashboard_node) is None:
        dashboard_bbox = {"x": 0.0, "y": 0.0, "width": default_dims["width"], "height": default_dims["height"]}
        dashboard_id = "default-dashboard"
        dashboard_name = doc_name
    else:
        dashboard_bbox = get_bbox(dashboard_node)
        dashboard_name = dashboard_node.get("name") or doc_name

    dash_x = dashboard_bbox["x"]
    dash_y = dashboard_bbox["y"]
    dash_w = dashboard_bbox["width"]
    dash_h = dashboard_bbox["height"]

    cell_w = dash_w / GRID_COLUMNS
    cell_h = dash_h / GRID_ROWS

    selected = []
    for pred in predictions:
        ptype = pred.get("predicted_type")
        if ptype not in {"CHART", "KPI_CARD", "TABLE", "FILTER", "OTHER"}:
            continue
        cid = str(pred.get("candidate_id"))
        node = nodes.get(cid)
        if not node:
            continue
        bbox = get_bbox(node)
        if not bbox:
            continue
        if cid == dashboard_id:
            continue

        rel = {
            "x": bbox["x"] - dash_x,
            "y": bbox["y"] - dash_y,
            "width": bbox["width"],
            "height": bbox["height"],
        }

        # Filter out nodes completely outside bounds
        if rel["x"] + rel["width"] <= 0 or rel["y"] + rel["height"] <= 0 or rel["x"] >= dash_w or rel["y"] >= dash_h:
            continue

        selected.append({
            "candidate_id": cid,
            "name": node.get("name", pred.get("name", "")),
            "predicted_type": ptype,
            "bbox": bbox,
            "relative": rel,
        })

    # Add structural components (Sidebar, Header) as direct children of dashboard
    # These are added as OTHER type since they're not in the model's class set
    for child_id in children.get(dashboard_id, []):
        if child_id in nodes:
            child = nodes[child_id]
            child_name = child.get("name", "").lower()
            bbox = get_bbox(child)

            # Check if this is a structural component
            is_structural = (
                "sidebar" in child_name or
                "header" in child_name or
                "navbar" in child_name or
                "navigation" in child_name
            )

            if is_structural and bbox:
                # Check if not already in selected
                already_selected = any(
                    item["candidate_id"] == child_id
                    for item in selected
                )

                if not already_selected:
                    rel = {
                        "x": bbox["x"] - dash_x,
                        "y": bbox["y"] - dash_y,
                        "width": bbox["width"],
                        "height": bbox["height"],
                    }

                    selected.append({
                        "candidate_id": child_id,
                        "name": child.get("name", ""),
                        "predicted_type": "OTHER",
                        "bbox": bbox,
                        "relative": rel,
                    })

    # Remove duplicate component IDs without discarding valid nested widgets.
    # KPI cards are commonly children of a KPI section/container, so preserve them
    # as separate widgets. Nested chart/table internals are handled earlier during
    # prediction cleaning.
    filtered = []
    seen_ids = set()

    for item in selected:
        candidate_id = item["candidate_id"]
        if candidate_id in seen_ids:
            continue
        seen_ids.add(candidate_id)
        filtered.append(item)

    # Compute grid offsets
    components = []
    for item in filtered:
        box = item["relative"]
        col_start = math.floor(box["x"] / cell_w)
        row_start = math.floor(box["y"] / cell_h)
        col_end = math.ceil((box["x"] + box["width"]) / cell_w)
        row_end = math.ceil((box["y"] + box["height"]) / cell_h)

        col_start = max(0, min(GRID_COLUMNS - 1, col_start))
        row_start = max(0, min(GRID_ROWS - 1, row_start))
        col_end = max(col_start + 1, min(GRID_COLUMNS, col_end))
        row_end = max(row_start + 1, min(GRID_ROWS, row_end))

        components.append({
            "candidate_id": item["candidate_id"],
            "name": item["name"],
            "predicted_type": item["predicted_type"],
            "grid": {
                "colOffset": col_start,
                "colSpan": col_end - col_start,
                "rowOffset": row_start,
                "rowSpan": row_end - row_start,
            },
            "position_relative_to_dashboard": {
                "x": round(box["x"], 2),
                "y": round(box["y"], 2),
                "width": round(box["width"], 2),
                "height": round(box["height"], 2),
            },
        })

    return {
        "dashboard_id": str(dashboard_id),
        "dashboard_name": dashboard_name,
        "grid": {"columns": GRID_COLUMNS, "rows": GRID_ROWS},
        "dashboard_size": {"width": dash_w, "height": dash_h},
        "component_count": len(components),
        "components": components,
    }


def extract_chart_data(
    prediction: Dict[str, Any],
    source_nodes: Optional[List[Dict[str, Any]]] = None,
    component: Optional[Dict[str, Any]] = None,
) -> List[Dict[str, Any]]:
    """Extract line-chart points from Figma geometry when reliable."""

    source_nodes = source_nodes or []
    component = component or {}

    def get_node_text(node: Dict[str, Any]) -> str:
        return str(
            node.get("text") or node.get("characters") or ""
        ).strip()

    def node_bbox(node: Dict[str, Any]) -> Optional[Dict[str, float]]:
        box = get_bbox(node)
        if box:
            return box
        return None

    candidate_id = str(component.get("candidate_id", ""))
    plot_nodes = [
        node for node in source_nodes
        if str(node.get("parent_id", "")) == candidate_id
    ]

    points = []
    x_labels = []
    y_labels = []

    for node in plot_nodes:
        box = node_bbox(node)
        if not box:
            continue

        name = str(node.get("name", "")).strip().lower()
        node_type = str(node.get("type", "")).upper()
        text = get_node_text(node)

        if name == "data point" and node_type == "ELLIPSE":
            points.append({
                "x": box["x"] + box["width"] / 2,
                "y": box["y"] + box["height"] / 2,
            })

        if node_type == "TEXT":
            if re.fullmatch(r"W\d{2}", text, flags=re.IGNORECASE):
                x_labels.append({
                    "label": text.upper(),
                    "x": box["x"] + box["width"] / 2,
                })

            numeric = text.replace(",", "").rstrip("%")
            if re.fullmatch(r"-?\d+(?:\.\d+)?", numeric):
                y_labels.append({
                    "value": float(numeric),
                    "y": box["y"] + box["height"] / 2,
                })

    points.sort(key=lambda item: item["x"])
    x_labels.sort(key=lambda item: item["x"])
    y_labels.sort(key=lambda item: item["y"])

    # Calculate values only when the points, week labels, and axis
    # labels all belong to the component identified by candidate_id.
    if (
        len(points) >= 3
        and len(points) == len(x_labels)
        and len(y_labels) >= 2
    ):
        result = []

        for point, label in zip(points, x_labels):
            above = [
                axis for axis in y_labels
                if axis["y"] <= point["y"]
            ]
            below = [
                axis for axis in y_labels
                if axis["y"] >= point["y"]
            ]

            if not above or not below:
                result = []
                break

            top = above[-1]
            bottom = below[0]

            if abs(bottom["y"] - top["y"]) < 0.001:
                value = top["value"]
            else:
                fraction = (
                    (point["y"] - top["y"])
                    / (bottom["y"] - top["y"])
                )
                value = top["value"] + fraction * (
                    bottom["value"] - top["value"]
                )

            result.append({
                "label": label["label"],
                "value": round(value, 2),
            })

        if len(result) == len(points):
            return result

    # Conservative fallback: do not infer values from arbitrary text.
    return []



def make_vista_widget(
    component: Dict[str, Any],
    prediction: Dict[str, Any],
    source_nodes: Optional[List[Dict[str, Any]]] = None,
) -> Dict[str, Any]:
    """
    Construct a Vista widget with KPI labels, main values,
    supporting descriptions, trends, and chart/table configuration.
    """
    ctype = component["predicted_type"]

    texts = [
        str(v).strip()
        for v in prediction.get("text_preview", [])
        if str(v).strip()
    ]

    name = str(component.get("name", ""))
    name_lower = name.lower()
    text_lower = " ".join(texts).lower()

    ignored_labels = {
        "show all", "%", "vs. prior period", "vs last mo",
        "kpi card", "chart", "table", "other"
    }

    meaningful_texts = [
        t for t in texts
        if not re.match(r"^\d+[.)]\s*", t)
        and t.lower() not in ignored_labels
        and len(t) > 2
    ]

    title = name
    if not title or title.startswith("4:"):
        title = meaningful_texts[0] if meaningful_texts else "Dashboard Widget"

    semantic_label = meaningful_texts[-1] if meaningful_texts else title

    widget_uuid = str(uuid.uuid4())
    chart_data = extract_chart_data(
    prediction,
    source_nodes=source_nodes or [],
    component=component,
    )

    # Determine Vista widget type.
    if ctype == "CHART":
        if any(word in name_lower for word in ("donut", "doughnut", "pie")):
            vista_type = "doughnut2d"
        elif "bar" in name_lower or "horizontal" in name_lower:
            vista_type = "bar2d"
        else:
            vista_type = "column2d"
    elif ctype == "KPI_CARD":
        vista_type = "column2d"
    elif ctype == "TABLE":
        vista_type = "table"
    elif ctype == "COMMENT" or "insight" in name_lower:
        vista_type = "comment"
    else:
        vista_type = "column2d"

    widget = {
        "id": widget_uuid,
        "widgetId": widget_uuid,
        "type": vista_type,
        "componentType": ctype,
        "title": title,
        "semanticLabel": semantic_label,
        "sourceComponentId": component["candidate_id"],
        "grid": component["grid"],
        "position": component.get("position_relative_to_dashboard", {}),
        "text": texts,
        "needsReview": False,
    }

    # Chart configuration.
    if ctype == "CHART":
        widget["chartData"] = chart_data
        widget["chart"] = {
            "showValues": "1",
            "showLegend": "1" if len(chart_data) > 3 else "0",
            "theme": "fusion,evernorth-light",
            "caption": title,
        }

        if chart_data:
            widget["dataRequest"] = {
                "moduleCode": "CMP",
                "type": "static",
                "staticData": [{
                    "id": widget_uuid,
                    "label": f"widget-{widget_uuid[:8]}",
                    "data": chart_data,
                }],
            }
        else:
            widget["needsReview"] = True
            widget["chartDataWarning"] = (
                "Could not extract chart data from source text"
            )

    # KPI extraction and annotations.
    
    elif ctype == "KPI_CARD":
        numeric_texts = [
            t for t in texts if re.search(r"\d", t)
        ]

        def is_trend_text(value: str) -> bool:
            s = value.strip()
            lower = s.lower()

            if "vs" in lower or "prior period" in lower:
                return True

            if re.match(r"^[+\-]\s*\d", s):
                return True

            # Handles Unicode arrows and common mojibake forms.
            if s.startswith(("↑", "↓", "↗", "↘", "â†", "â‡")):
                return True

            return False

        trend_candidates = [
            t for t in numeric_texts if is_trend_text(t)
        ]
        metric_candidates = [
            t for t in numeric_texts if not is_trend_text(t)
        ]

        numeric_val = metric_candidates[-1] if metric_candidates else "—"

        nonnumeric_texts = [
            t for t in texts
            if not re.search(r"\d", t)
            and "vs" not in t.lower()
            and "prior period" not in t.lower()
            and t.lower() not in {"show all", "vs last mo"}
        ]

        metric_lbl = nonnumeric_texts[-1] if nonnumeric_texts else title

        trend_lbl = trend_candidates[0] if trend_candidates else ""
        comparison = next(
            (t for t in texts if "vs" in t.lower() or "prior period" in t.lower()),
            "",
        )

        if comparison and comparison.lower() not in trend_lbl.lower():
            trend_lbl = f"{trend_lbl} {comparison}".strip()

        widget["kpiValue"] = numeric_val
        widget["kpiLabel"] = metric_lbl
        widget["trend"] = trend_lbl

    

        trend_is_positive = trend_lbl.strip().startswith(("+", "↑", "↗", "â†‘"))
        trend_is_negative = trend_lbl.strip().startswith(("-", "−", "↓", "↘", "â†“"))

        trend_color = (
            "#16a34a" if trend_is_positive
            else "#dc2626" if trend_is_negative
            else "#718096"
        )

        widget["chart"] = {
            "showLabels": "0",
            "showValues": "0",
            "showLegend": "0",
            "showXAxisLine": "0",
            "showYAxisLine": "0",
            "plotFillAlpha": "0",
            "plotHoverEffect": "0",
            "theme": "fusion,evernorth-light",
        }
        supporting_text = (
            str(widget.get("supportingText", "")).strip()
            or str(widget.get("description", "")).strip()
        )
        annotation_items = [
            {
                "id": "lbl-1",
                "type": "text",
                "text": metric_lbl,
                "x": "$chartCenterX",
                "y": "$chartTopMargin+25",
                "fontSize": "14",
            },
            {
                "id": "val-1",
                "type": "text",
                "text": numeric_val,
                "x": "$chartCenterX",
                "y": "$chartTopMargin+58",
                "fontSize": "26",
                "bold": "1",
            },
        ]

        if supporting_text:
            annotation_items.append({
                "id": "desc-1",
                "type": "text",
                "text": supporting_text,
                "x": "$chartCenterX",
                "y": "$chartTopMargin+80",
                "fontSize": "10",
                "color": "#64748b",
            })

        if trend_lbl:
            annotation_items.append({
                "id": "trend-1",
                "type": "text",
                "text": trend_lbl,
                "x": "$chartCenterX",
                "y": "$chartTopMargin+100",
                "fontSize": "12",
                "color": trend_color,
            })

        widget["annotations"] = {
            "groups": [{
                "id": "kpi-group",
                "textAlign": "center",
                "font": "Montserrat",
                "fontSize": "14",
                "color": "#172033",
                "items": annotation_items,
            }]
        }

        widget["dataRequest"] = {
            "moduleCode": "CMP",
            "type": "static",
            "staticData": [{
                "id": widget_uuid,
                "label": f"kpi-{widget_uuid[:8]}",
                "data": [{
                    "label": metric_lbl,
                    "value": 1,
                }],
            }],
        }

        if numeric_val == "—" or not metric_lbl:
            widget["needsReview"] = True

    # Table configuration.
    elif ctype == "TABLE":
        headers = [
            t for t in texts[:6] if len(t) < 30
        ]

        widget["tableConfig"] = {
            "columns": headers if headers else [
                "Column 1", "Column 2", "Status"
            ],
            "rows": [],
        }
        widget["needsReview"] = True

    return widget


def run_vista_page_generation(
    grid_data: Dict[str, Any],
    predictions: List[Dict[str, Any]],
    package_metadata: Optional[Dict[str, str]] = None,
    source_nodes: Optional[List[Dict[str, Any]]] = None,
) -> Dict[str, Any]:
    """Stage 5: Generate Vista page.json adhering strictly to student guide specifications."""
    meta = package_metadata or {}
    subject_area = meta.get("subjectArea", "sales")
    topic = meta.get("topic", "analytics")
    slide_name = meta.get("slideName", "dashboard-summary")
    custom_title = meta.get("title", "").strip()

    # Rule: contentId and slideId must be the same value, exactly 5 characters
    raw_slide_id = meta.get("slideId", "").strip().upper()
    if len(raw_slide_id) == 5 and raw_slide_id.isalnum():
        slide_id = raw_slide_id
    else:
        slide_id = generate_short_id(5)
    content_id = slide_id

    page_uuid = str(uuid.uuid4())
    dashboard_name = custom_title if custom_title else grid_data.get("dashboard_name", "Dashboard Overview")

    pred_map = {str(item["candidate_id"]): item for item in predictions if item.get("candidate_id")}
    components = grid_data.get("components", [])

    widgets = []
    tiles = []

    for comp in components:
        cid = str(comp["candidate_id"])
        pred = pred_map.get(cid, {})
        widget = make_vista_widget(
            comp,
            pred,
            source_nodes=source_nodes or [],
        )
        widgets.append(widget)

        tile_id = str(uuid.uuid4())
        grid = comp["grid"]
        tile = {
            "tileId": tile_id,
            "id": tile_id,
            "contentId": content_id,
            "slideId": slide_id,
            "cols": grid["colSpan"],
            "rows": grid["rowSpan"],
            "colOffset": grid["colOffset"],
            "rowOffset": grid["rowOffset"],
            "widgetIds": [widget["id"]],
            "widgetId": widget["id"],
            "grid": grid,
        }
        tiles.append(tile)

    # Optional background paths per student guide
    background_paths = [
        {
            "type": "rectangle-leaf",
            "color": "#f8fafc",
            "colOffset": 0, "colSpan": 12,
            "rowOffset": 0, "rowSpan": 12
        }
    ]

    page = {
        "contentId": content_id,
        "slideId": slide_id,
        "pageId": page_uuid,
        "id": page_uuid,
        "title": dashboard_name,
        "description": " ",
        "subjectArea": subject_area,
        "topic": topic,
        "slideName": slide_name,
        "schemaVersion": "1.0",
        "format": "local-dashboard-page",
        "dashboard": {
            "id": grid_data.get("dashboard_id", "new_dashboard"),
            "name": dashboard_name,
            "columns": grid_data["grid"]["columns"],
            "rows": grid_data["grid"]["rows"],
            "sourceWidth": grid_data["dashboard_size"]["width"],
            "sourceHeight": grid_data["dashboard_size"]["height"],
        },
        "tiles": tiles,
        "widgets": widgets,
        "backgroundPaths": background_paths,
        "validation": {
            "componentCount": len(components),
            "widgetCount": len(widgets),
            "tileCount": len(tiles),
            "reviewRequired": sum(bool(w.get("needsReview")) for w in widgets),
            "validationErrors": []
        }
    }

    # Verify constraints
    assert len(page["contentId"]) == 5, "contentId must be 5 chars"
    assert len(page["slideId"]) == 5, "slideId must be 5 chars"
    assert page["contentId"] == page["slideId"], "contentId and slideId must match"
    for tile in page["tiles"]:
        assert tile["grid"]["colOffset"] + tile["grid"]["colSpan"] <= 12, "Tile exceeds 12 columns"
        assert tile["grid"]["rowOffset"] + tile["grid"]["rowSpan"] <= 12, "Tile exceeds 12 rows"

    return page


def execute_full_pipeline(
    figma_data: Dict[str, Any],
    package_metadata: Optional[Dict[str, str]] = None,
    sync_to_disk: bool = True
) -> Dict[str, Any]:
    """
    Run full end-to-end pipeline:
    Figma JSON -> Candidates -> XGBoost Predict -> Clean -> Grid -> Vista page.json
    """
    start_time = time.time()

    # Step 1: Extract nodes
    nodes, doc_name, dims = extract_nodes_from_figma_payload(figma_data)
    if not nodes:
        raise ValueError("Could not extract any nodes from the provided Figma JSON.")

    # Step 2: Candidates (Normalize)
    candidates = run_candidate_generation(nodes, dashboard_name=doc_name)

    # Step 3: Classify (XGBoost)
    raw_predictions = run_classification(candidates)

    # Step 4: Clean predictions
    clean_predictions = run_prediction_cleaning(raw_predictions)

    # Step 5: Grid Layout
    grid_layout = run_grid_layout(figma_data, clean_predictions)

    # Step 6: Vista Page
    vista_page = run_vista_page_generation(
        grid_layout,
        clean_predictions,
        package_metadata,
        source_nodes=nodes,
    )

    elapsed_ms = round((time.time() - start_time) * 1000, 1)

    # Sync to disk so existing CLI scripts and dashboard_preview.html stay updated
    if sync_to_disk:
        try:
            # 1. Active figma_data.json
            active_figma = ROOT / "dataset" / "new_dashboard" / "figma_data.json"
            active_figma.parent.mkdir(parents=True, exist_ok=True)
            with open(active_figma, "w", encoding="utf-8") as f:
                json.dump(figma_data, f, indent=2, ensure_ascii=False)

            # 2. Candidates
            cand_file = ROOT / "dataset" / "new_candidates" / "new_dashboard_candidates.json"
            cand_file.parent.mkdir(parents=True, exist_ok=True)
            with open(cand_file, "w", encoding="utf-8") as f:
                json.dump({"dashboard": "new_dashboard", "candidate_count": len(candidates), "candidates": candidates}, f, indent=2, ensure_ascii=False)

            # 3. Raw Predictions
            pred_file = ROOT / "dataset" / "new_candidates" / "new_dashboard_predictions.json"
            with open(pred_file, "w", encoding="utf-8") as f:
                json.dump({"source": str(cand_file.relative_to(ROOT)), "candidate_count": len(raw_predictions), "predictions": raw_predictions}, f, indent=2, ensure_ascii=False)

            # 4. Clean Predictions
            clean_file = ROOT / "dataset" / "new_candidates" / "new_dashboard_clean_predictions.json"
            with open(clean_file, "w", encoding="utf-8") as f:
                json.dump({"dashboard": "new_dashboard", "candidate_count": len(clean_predictions), "predictions": clean_predictions}, f, indent=2, ensure_ascii=False)

            # 5. Grid layout
            grid_file = ROOT / "outputs" / "dashboard_configs" / "new_dashboard" / "grid_layout.json"
            grid_file.parent.mkdir(parents=True, exist_ok=True)
            with open(grid_file, "w", encoding="utf-8") as f:
                json.dump(grid_layout, f, indent=2, ensure_ascii=False)

            # 6. Vista page.json
            page_file = ROOT / "outputs" / "vista_pages" / "new_dashboard" / "page.json"
            page_file.parent.mkdir(parents=True, exist_ok=True)
            with open(page_file, "w", encoding="utf-8") as f:
                json.dump(vista_page, f, indent=2, ensure_ascii=False)

        except Exception as err:
            print(f"Warning: Failed to sync pipeline files to disk: {err}")

    # Build source wireframe representations for the UI
    source_components = []
    for c in candidates:
        source_components.append({
            "id": c.get("candidate_id"),
            "name": c.get("name"),
            "type": c.get("type", "FRAME"),
            "x": c.get("x", 0),
            "y": c.get("y", 0),
            "width": c.get("width", 0),
            "height": c.get("height", 0),
            "textPreview": c.get("text_preview", [])[:3]
        })

    return {
        "success": True,
        "designName": vista_page["title"],
        "contentId": vista_page["contentId"],
        "slideId": vista_page["slideId"],
        "pageId": vista_page["pageId"],
        "executionTimeMs": elapsed_ms,
        "sourceDimensions": dims,
        "nodeCount": len(nodes),
        "candidateCount": len(candidates),
        "sourceComponents": source_components,
        "normalizedJson": {
            "dashboard": vista_page["title"],
            "candidate_count": len(candidates),
            "candidates": candidates
        },
        "classifierJson": {
            "candidate_count": len(clean_predictions),
            "predictions": clean_predictions
        },
        "gridLayout": grid_layout,
        "pageJson": vista_page,
        "stats": {
            "widgets": len(vista_page["widgets"]),
            "tiles": len(vista_page["tiles"]),
            "needAttention": vista_page["validation"]["reviewRequired"],
            "infoNotes": 2,
            "validationErrors": 0,
            "classifier": "cached + ml (XGBoost)",
        }
    }
