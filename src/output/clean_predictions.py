
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

INPUT_FILE = (
    ROOT / "dataset" / "new_candidates"
    / "new_dashboard_predictions.json"
)

OUTPUT_FILE = (
    ROOT / "dataset" / "new_candidates"
    / "new_dashboard_clean_predictions.json"
)


def correct_type(component):
    name = component.get("name", "").lower()
    text = " ".join(component.get("text_preview", [])).lower()

    # Profile images and headings are not KPI cards.
    if "picture" in name:
        return "OTHER"

    if name == "title":
        return "OTHER"

    # Ranked artist rows are list items, not KPI cards.
    if "listenings" in text and any(
        text.startswith(f"{i}.") for i in range(1, 6)
    ):
        return "OTHER"

    # Keep actual metric cards as KPI cards.
    if any(metric in text for metric in [
        "minutes of listening",
        "unique tracks",
        "different artists",
    ]):
        return "KPI_CARD"

    return component.get("predicted_type", "OTHER")


def main():
    with open(INPUT_FILE, encoding="utf-8") as f:
        data = json.load(f)

    predictions = data.get("predictions", [])

    # Keep displayed instance candidates rather than source definitions.
    # Keep all predictions from the current dashboard.
    visible = [dict(p) for p in predictions]

    visible_ids = {
        p["candidate_id"] for p in visible
    }

    # Remove candidates nested inside another detected chart.
    chart_ids = {
        p["candidate_id"]
        for p in visible
        if p.get("predicted_type") == "CHART"
    }

    cleaned = []

    for component in visible:
        parent_id = component.get("parent_id")

        if parent_id in chart_ids:
            continue

        component["predicted_type"] = correct_type(component)
        cleaned.append(component)

    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump({
            "dashboard": "new_dashboard",
            "source": str(INPUT_FILE.relative_to(ROOT)),
            "candidate_count": len(cleaned),
            "predictions": cleaned,
        }, f, indent=2, ensure_ascii=False)

    print("Cleaning complete.")
    print(f"Original predictions: {len(predictions)}")
    print(f"Displayed candidates: {len(visible)}")
    print(f"Cleaned candidates: {len(cleaned)}")
    print(f"Output: {OUTPUT_FILE}")

    print("\nCleaned components:")
    for c in cleaned:
        print(
            c.get("candidate_id"),
            "|", c.get("name"),
            "|", c.get("predicted_type")
        )


if __name__ == "__main__":
    main()
