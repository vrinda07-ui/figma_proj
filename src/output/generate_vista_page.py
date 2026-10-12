
import json
import re
import uuid
import secrets
import string
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

GRID_FILE = (
    ROOT / "outputs" / "dashboard_configs"
    / "new_dashboard" / "grid_layout.json"
)

PREDICTIONS_FILE = (
    ROOT / "dataset" / "new_candidates"
    / "new_dashboard_clean_predictions.json"
)

OUTPUT_FILE = (
    ROOT / "outputs" / "vista_pages"
    / "new_dashboard" / "page.json"
)

def short_id():
    """Generate a five-character alphanumeric identifier."""
    alphabet = string.ascii_lowercase + string.digits
    return "".join(secrets.choice(alphabet) for _ in range(5))


def read_json(path):
    if not path.exists():
        raise FileNotFoundError(f"Required file not found: {path}")

    with path.open(encoding="utf-8") as f:
        return json.load(f)


def get_text_values(prediction):
    values = prediction.get("text_preview", [])
    return [str(v).strip() for v in values if str(v).strip()]


def extract_chart_data(prediction):
    """
    Extract label/value pairs only when the Figma text
    contains an explicit numeric value.
    """
    data = []

    for text in get_text_values(prediction):
        match = re.match(
            r"^\s*(?:\d+[.)]\s*)?(.+?)\s*[-:]\s*"
            r"(-?\d+(?:\.\d+)?)\s*%?\s*$",
            text,
        )

        if match:
            label = match.group(1).strip()
            value = float(match.group(2))

            if label and label.lower() not in {"show all"}:
                data.append({
                    "label": label,
                    "value": value,
                })

    return data


def make_widget(component, prediction):
    component_type = component["predicted_type"]
    texts = get_text_values(prediction)

    # Prefer meaningful text rather than generic Figma layer names.
    title = component["name"]

    for text in texts:
        if not re.match(r"^\d+[.)]\s*", text):
            if text.lower() not in {"show all", "%"}:
                title = text
                break

    widget = {
        "id": str(uuid.uuid4()),
        "type": component_type,
        "title": title,
        "sourceComponentId": component["candidate_id"],
        "grid": component["grid"],
    }

    if component_type == "CHART":
        widget["chartData"] = extract_chart_data(prediction)
        widget["chartType"] = (
            "bar" if widget["chartData"] else "unconfigured"
        )
        widget["needsReview"] = not bool(widget["chartData"])

    elif component_type == "KPI_CARD":
        widget["text"] = texts
        widget["needsReview"] = True

    elif component_type == "TABLE":
        widget["text"] = texts
        widget["needsReview"] = True

    elif component_type == "FILTER":
        widget["text"] = texts
        widget["needsReview"] = True

    else:
        widget["text"] = texts
        widget["needsReview"] = True

    return widget


def main():
    grid_data = read_json(GRID_FILE)
    prediction_data = read_json(PREDICTIONS_FILE)

    predictions = {
        item["candidate_id"]: item
        for item in prediction_data.get("predictions", [])
        if item.get("candidate_id")
    }

    components = grid_data.get("components", [])

    if not components:
        raise ValueError("No grid components found. Run the grid generator first.")

    content_id = short_id()
    slide_id = short_id()

    widgets = []
    tiles = []

    for component in components:
        candidate_id = component["candidate_id"]
        prediction = predictions.get(candidate_id, {})

        widget = make_widget(component, prediction)
        widgets.append(widget)

        tiles.append({
            "id": str(uuid.uuid4()),
            "contentId": content_id,
            "slideId": slide_id,
            "widgetId": widget["id"],
            "grid": component["grid"],
        })

    page = {
        "schemaVersion": "1.0",
        "format": "local-dashboard-page",
        "id": str(uuid.uuid4()),
        "contentId": content_id,
        "slideId": slide_id,
        "dashboard": {
            "id": grid_data.get("dashboard_id", "new_dashboard"),
            "name": grid_data.get("dashboard_name", "Generated Dashboard"),
            "columns": grid_data["grid"]["columns"],
            "rows": grid_data["grid"]["rows"],
            "sourceWidth": grid_data["dashboard_size"]["width"],
            "sourceHeight": grid_data["dashboard_size"]["height"],
        },
        "tiles": tiles,
        "widgets": widgets,
        "validation": {
            "componentCount": len(components),
            "widgetCount": len(widgets),
            "reviewRequired": sum(
                bool(widget.get("needsReview"))
                for widget in widgets
            ),
        },
    }

    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)

    with OUTPUT_FILE.open("w", encoding="utf-8") as f:
        json.dump(page, f, indent=2, ensure_ascii=False)

    # Validate the written file and basic structural requirements.
    with OUTPUT_FILE.open(encoding="utf-8") as f:
        check = json.load(f)

    assert len(check["contentId"]) == 5
    assert len(check["slideId"]) == 5
    assert len(check["tiles"]) == len(check["widgets"])

    for tile in check["tiles"]:
        grid = tile["grid"]
        assert grid["colOffset"] >= 0
        assert grid["rowOffset"] >= 0
        assert grid["colOffset"] + grid["colSpan"] <= 12
        assert grid["rowOffset"] + grid["rowSpan"] <= 12

    print("Page generation successful.")
    print("Components:", len(components))
    print("Widgets:", len(widgets))
    print("Needs review:", check["validation"]["reviewRequired"])
    print("Output:", OUTPUT_FILE)


if __name__ == "__main__":
    main()
