
import json
import math
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

FIGMA_FILE = ROOT / "dataset" / "new_dashboard" / "figma_data.json"
PREDICTIONS_FILE = (
    ROOT / "dataset" / "new_candidates"
    / "new_dashboard_clean_predictions.json"
)
OUTPUT_FILE = (
    ROOT / "outputs" / "dashboard_configs"
    / "new_dashboard" / "grid_layout.json"
)

GRID_COLUMNS = 12
GRID_ROWS = 12


def load_figma_nodes(document):
    """Flatten the Figma tree and remember each node's parent."""
    nodes = {}
    parents = {}

    def walk(node, parent_id=None):
        if not isinstance(node, dict):
            return

        node_id = node.get("id")

        if node_id is not None:
            node_id = str(node_id)
            nodes[node_id] = node
            parents[node_id] = parent_id

        for child in node.get("children", []):
            walk(child, node_id)

    walk(document)
    return nodes, parents


def get_bbox(node):
    """Return a valid absolute bounding box, if available."""
    bbox = node.get("absoluteBoundingBox")

    if not isinstance(bbox, dict):
        return None

    keys = ("x", "y", "width", "height")

    if not all(
        isinstance(bbox.get(key), (int, float))
        for key in keys
    ):
        return None

    if bbox["width"] <= 0 or bbox["height"] <= 0:
        return None

    return {key: float(bbox[key]) for key in keys}


def is_inside(inner, outer, tolerance=1.0):
    """Check whether inner is contained by outer."""
    return (
        inner["x"] >= outer["x"] - tolerance
        and inner["y"] >= outer["y"] - tolerance
        and inner["x"] + inner["width"]
        <= outer["x"] + outer["width"] + tolerance
        and inner["y"] + inner["height"]
        <= outer["y"] + outer["height"] + tolerance
    )


def find_dashboard(nodes, parents, predictions):
    """
    Find the smallest ancestor containing the largest number
    of predicted chart/KPI candidates.
    """
    candidate_ids = []

    for prediction in predictions:
        if prediction.get("predicted_type") not in {
            "CHART", "KPI_CARD"
        }:
            continue

        candidate_id = prediction.get("candidate_id")

        if candidate_id is not None and str(candidate_id) in nodes:
            if get_bbox(nodes[str(candidate_id)]) is not None:
                candidate_ids.append(str(candidate_id))

    if not candidate_ids:
        raise ValueError(
            "No predicted CHART/KPI candidates with bounding boxes "
            "were found in the Figma document."
        )

    # Count how many candidate nodes are descendants of each ancestor.
    coverage = {}

    for candidate_id in candidate_ids:
        current_id = parents.get(candidate_id)

        while current_id is not None:
            if get_bbox(nodes[current_id]) is not None:
                coverage[current_id] = (
                    coverage.get(current_id, 0) + 1
                )

            current_id = parents.get(current_id)

    if not coverage:
        raise ValueError(
            "Could not find a dashboard container with a bounding box."
        )

    # Prefer maximum candidate coverage, then the smallest container.
    max_coverage = max(coverage.values())

    possible = [
        node_id
        for node_id, count in coverage.items()
        if count == max_coverage
    ]

    dashboard_id = min(
        possible,
        key=lambda node_id: (
            get_bbox(nodes[node_id])["width"]
            * get_bbox(nodes[node_id])["height"]
        ),
    )

    return dashboard_id, nodes[dashboard_id]


def main():
    with open(FIGMA_FILE, encoding="utf-8") as f:
        figma_data = json.load(f)

    with open(PREDICTIONS_FILE, encoding="utf-8") as f:
        prediction_data = json.load(f)

    nodes, parents = load_figma_nodes(
        figma_data.get("document", {})
    )
    predictions = prediction_data.get("predictions", [])

    dashboard_id, dashboard = find_dashboard(
        nodes, parents, predictions
    )

    dashboard_bbox = get_bbox(dashboard)

    if dashboard_bbox is None:
        raise ValueError("Detected dashboard has no bounding box.")

    dashboard_x = dashboard_bbox["x"]
    dashboard_y = dashboard_bbox["y"]
    dashboard_width = dashboard_bbox["width"]
    dashboard_height = dashboard_bbox["height"]

    cell_width = dashboard_width / GRID_COLUMNS
    cell_height = dashboard_height / GRID_ROWS

    print("Detected dashboard:", dashboard.get("name"))
    print("Detected dashboard ID:", dashboard_id)

    selected = []

    # Keep predicted charts and KPI cards inside the detected dashboard.
    for prediction in predictions:
        candidate_id = prediction.get("candidate_id")
        predicted_type = prediction.get("predicted_type")

        if predicted_type not in {"CHART", "KPI_CARD"}:
            continue

        if candidate_id is None:
            continue

        candidate_id = str(candidate_id)
        node = nodes.get(candidate_id)

        if node is None:
            print("Skipping missing node:", candidate_id)
            continue

        bbox = get_bbox(node)

        if bbox is None:
            print("Skipping node without bounding box:", candidate_id)
            continue

        # Exclude the dashboard container itself.
        if candidate_id == dashboard_id:
            continue

        # Require the candidate to be a descendant of the dashboard.
        current_id = parents.get(candidate_id)
        is_descendant = False

        while current_id is not None:
            if current_id == dashboard_id:
                is_descendant = True
                break
            current_id = parents.get(current_id)

        if not is_descendant:
            print("Skipping candidate outside dashboard:", candidate_id)
            continue

        relative = {
            "x": bbox["x"] - dashboard_x,
            "y": bbox["y"] - dashboard_y,
            "width": bbox["width"],
            "height": bbox["height"],
        }

        # Exclude nodes outside the dashboard bounds.
        if (
            relative["x"] + relative["width"] <= 0
            or relative["y"] + relative["height"] <= 0
            or relative["x"] >= dashboard_width
            or relative["y"] >= dashboard_height
        ):
            continue

        selected.append({
            "candidate_id": candidate_id,
            "name": node.get(
                "name", prediction.get("name", "")
            ),
            "predicted_type": predicted_type,
            "bbox": bbox,
            "relative": relative,
        })

    # Remove chart-like groups contained within larger chart containers.
    charts = [
        item for item in selected
        if item["predicted_type"] == "CHART"
    ]

    filtered = []

    for item in selected:
        if item["predicted_type"] == "CHART":
            nested = any(
                other["candidate_id"] != item["candidate_id"]
                and is_inside(item["bbox"], other["bbox"])
                and (
                    other["bbox"]["width"]
                    * other["bbox"]["height"]
                    > item["bbox"]["width"]
                    * item["bbox"]["height"]
                )
                for other in charts
            )

            if nested:
                print(
                    "Skipping nested chart:",
                    item["candidate_id"],
                    item["name"],
                )
                continue

        filtered.append(item)

    components = []

    for item in filtered:
        box = item["relative"]

        col_start = math.floor(box["x"] / cell_width)
        row_start = math.floor(box["y"] / cell_height)

        col_end = math.ceil(
            (box["x"] + box["width"]) / cell_width
        )
        row_end = math.ceil(
            (box["y"] + box["height"]) / cell_height
        )

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

    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)

    result = {
        "dashboard_id": dashboard_id,
        "dashboard_name": dashboard.get("name", ""),
        "grid": {
            "columns": GRID_COLUMNS,
            "rows": GRID_ROWS,
        },
        "dashboard_size": {
            "width": dashboard_width,
            "height": dashboard_height,
        },
        "component_count": len(components),
        "components": components,
    }

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(result, f, indent=2, ensure_ascii=False)

    print("\nGrid generation complete.")
    print("Dashboard size:", dashboard_width, "x", dashboard_height)
    print("Components:", len(components))
    print("Output:", OUTPUT_FILE)

    for item in components:
        print(
            item["candidate_id"],
            "|", item["name"],
            "|", item["predicted_type"],
            "|", item["grid"],
        )


if __name__ == "__main__":
    main()
