
import csv
import json
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]

CANDIDATE_DIR = ROOT / "dataset" / "candidates"
FEATURE_DIR = ROOT / "dataset" / "features"

FEATURE_DIR.mkdir(parents=True, exist_ok=True)


def safe_number(value, default=0.0):
    """Convert a value to a finite float, falling back safely."""
    try:
        number = float(value)
        return number if number == number and abs(number) != float("inf") else default
    except (TypeError, ValueError, OverflowError):
        return default


def safe_count(value):
    """Convert a count to a non-negative integer."""
    try:
        return max(0, int(float(value)))
    except (TypeError, ValueError, OverflowError):
        return 0


def get_text(candidate):
    """Normalize text_preview whether it is a list or a string."""
    text_preview = candidate.get("text_preview", [])

    if isinstance(text_preview, list):
        parts = [str(item) for item in text_preview if item is not None]
    elif text_preview is None:
        parts = []
    else:
        parts = [str(text_preview)]

    return " ".join(parts).strip().lower()


def contains_any(text, words):
    """Return 1 when any whole phrase/word is present."""
    return int(any(
        re.search(
            rf"(?<!\w){re.escape(word.lower())}(?!\w)",
            text
        )
        for word in words
    ))


def calculate_features(candidate):
    """Extract model features from one Figma candidate."""

    width = safe_number(candidate.get("width"))
    height = safe_number(candidate.get("height"))
    area = width * height

    aspect_ratio = width / height if height > 0 else 0.0

    child_count = safe_count(candidate.get("child_count"))
    text_count = safe_count(candidate.get("text_count"))
    numeric_text_count = safe_count(
        candidate.get("numeric_text_count")
    )

    vector_count = safe_count(candidate.get("vector_count"))
    line_count = safe_count(candidate.get("line_count"))
    ellipse_count = safe_count(candidate.get("ellipse_count"))
    rectangle_count = safe_count(candidate.get("rectangle_count"))

    text_density = (
        text_count / child_count if child_count > 0 else 0.0
    )
    numeric_density = (
        numeric_text_count / text_count if text_count > 0 else 0.0
    )

    graphical_count = vector_count + line_count + ellipse_count

    name = str(candidate.get("name", "") or "").strip().lower()
    all_text = get_text(candidate)
    combined_text = f"{name} {all_text}".strip()

    # Semantic indicators. These are supporting signals, not labels.
    has_chart_word = contains_any(combined_text, [
        "chart", "graph", "analytics", "trend", "statistics",
        "plot", "histogram", "donut", "scatter"
    ])

    has_table_word = contains_any(combined_text, [
        "table", "records", "data grid", "tabular"
    ])

    has_kpi_word = contains_any(combined_text, [
        "kpi", "metric", "total revenue", "total users",
        "total sales", "average", "conversion rate",
        "active users", "score"
    ])

    has_filter_word = contains_any(combined_text, [
        "filter", "dropdown", "select", "date range",
        "date picker", "choose category", "search filter"
    ])

    has_nav_word = contains_any(combined_text, [
        "navbar", "navigation", "nav menu",
        "sidebar menu", "breadcrumb"
    ])

    has_header_word = contains_any(combined_text, [
        "page title", "section title", "heading",
        "page header"
    ])

    # Preserve source-provided percentage information when available.
    raw_percentage = candidate.get("has_percentage", False)
    if isinstance(raw_percentage, str):
        has_percentage = int(
            raw_percentage.strip().lower() in {"1", "true", "yes"}
        )
    else:
        has_percentage = int(bool(raw_percentage))

    has_date_text = int(bool(re.search(
        r"\b(?:jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)"
        r"[a-z]*\b"
        r"|\b\d{1,2}[/-]\d{1,2}[/-]\d{2,4}\b"
        r"|\b\d{4}-\d{2}-\d{2}\b",
        combined_text,
        flags=re.IGNORECASE
    )))

    return {
        # Identifiers are retained for tracing, not model input.
        "dashboard_id": (
            candidate.get("dashboard_id")
            or candidate.get("dashboard")
        ),
        "candidate_id": candidate.get("candidate_id"),
        "name": candidate.get("name", ""),

        # Original 20 model features.
        "width": width,
        "height": height,
        "area": area,
        "aspect_ratio": aspect_ratio,
        "child_count": child_count,
        "text_count": text_count,
        "numeric_text_count": numeric_text_count,
        "text_density": text_density,
        "numeric_density": numeric_density,
        "vector_count": vector_count,
        "line_count": line_count,
        "ellipse_count": ellipse_count,
        "rectangle_count": rectangle_count,
        "graphical_count": graphical_count,
        "has_percentage": has_percentage,
        "has_date_text": has_date_text,
        "has_chart_word": has_chart_word,
        "has_table_word": has_table_word,
        "has_kpi_word": has_kpi_word,
        "has_filter_word": has_filter_word,

        # New features: update training and inference to use these.
        "has_nav_word": has_nav_word,
        "has_header_word": has_header_word,
    }


def main():
    files = sorted(CANDIDATE_DIR.glob("*_candidates.json"))

    if not files:
        print(f"No candidate files found in: {CANDIDATE_DIR}")
        print("Run generate_candidates.py first, or check the directory.")
        return

    rows = []

    for file_path in files:
        with file_path.open("r", encoding="utf-8") as f:
            data = json.load(f)

        dashboard = data.get("dashboard") or data.get("dashboard_id")

        for candidate in data.get("candidates", []):
            candidate_copy = dict(candidate)
            candidate_copy["dashboard"] = (
                candidate_copy.get("dashboard") or dashboard
            )
            rows.append(calculate_features(candidate_copy))

    if not rows:
        print("Candidate files were found, but they contained no candidates.")
        return

    output_file = FEATURE_DIR / "component_features.csv"
    fieldnames = list(rows[0].keys())

    with output_file.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    print("=" * 60)
    print("FEATURE EXTRACTION COMPLETE")
    print("=" * 60)
    print(f"Candidate files: {len(files)}")
    print(f"Candidates: {len(rows)}")
    print(f"Features per candidate: {len(fieldnames) - 3}")
    print(f"Output: {output_file}")


if __name__ == "__main__":
    main()
