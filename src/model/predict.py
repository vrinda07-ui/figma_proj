
import json
import sys
import joblib
import pandas as pd

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from src.features.extract_features import calculate_features

# New dashboard candidates
CANDIDATE_FILE = (
    ROOT / "dataset" / "new_candidates" / "new_dashboard_candidates.json"
)

# Use the newly trained model bundle
MODEL_FILE = (
    ROOT / "src" / "model" / "models" / "component_classifier.joblib"
)

OUTPUT_FILE = (
    ROOT / "dataset" / "new_candidates" / "new_dashboard_predictions.json"
)

FEATURE_COLS = [
    "width", "height", "area", "aspect_ratio", "child_count",
    "text_count", "numeric_text_count", "text_density",
    "numeric_density", "vector_count", "line_count",
    "ellipse_count", "rectangle_count", "graphical_count",
    "has_percentage", "has_date_text", "has_chart_word",
    "has_table_word", "has_kpi_word", "has_filter_word",
]


def main():
    print("=" * 60)
    print("XGBOOST NEW DASHBOARD PREDICTION")
    print("=" * 60)

    if not CANDIDATE_FILE.exists():
        print(f"ERROR: Candidate file not found:\n{CANDIDATE_FILE}")
        return

    if not MODEL_FILE.exists():
        print(f"ERROR: Trained model bundle not found:\n{MODEL_FILE}")
        return

    with open(CANDIDATE_FILE, "r", encoding="utf-8") as f:
        candidate_data = json.load(f)

    if isinstance(candidate_data, list):
        candidates = candidate_data
    else:
        candidates = candidate_data.get("candidates", [])

    if not candidates:
        print("No candidates found. Check your candidate JSON structure.")
        return

    print(f"Candidates found: {len(candidates)}")

    print("\nLoading trained model and label encoder...")
    bundle = joblib.load(MODEL_FILE)

    model = bundle["model"]
    encoder = bundle["label_encoder"]
    medians = pd.Series(bundle["medians"])

    print("Classes:", list(encoder.classes_))

    print("\nExtracting features...")
    feature_rows = [
        calculate_features(candidate)
        for candidate in candidates
    ]

    features_df = pd.DataFrame(feature_rows)

    # Ensure all expected features exist and use training-time preprocessing.
    X_new = features_df.reindex(columns=FEATURE_COLS)
    X_new = X_new.apply(pd.to_numeric, errors="coerce")
    X_new = X_new.replace([float("inf"), float("-inf")], float("nan"))
    X_new = X_new.fillna(medians.reindex(FEATURE_COLS)).fillna(0)

    print(f"Feature matrix shape: {X_new.shape}")

    probabilities = model.predict_proba(X_new)
    predicted_ids = probabilities.argmax(axis=1)
    predictions = encoder.inverse_transform(predicted_ids)
    confidences = probabilities.max(axis=1)

    results = []

    for candidate, prediction, confidence in zip(
        candidates, predictions, confidences
    ):
        result = dict(candidate)
        result["predicted_type"] = str(prediction)
        result["confidence"] = round(float(confidence), 4)
        result["needs_review"] = bool(confidence < 0.70)
        results.append(result)

        print(
            f"{candidate.get('name', 'Unnamed')} | "
            f"{candidate.get('id', 'No ID')} | "
            f"{prediction} | confidence={confidence:.3f}"
        )

    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)

    output_data = {
        "source": str(CANDIDATE_FILE.relative_to(ROOT)),
        "candidate_count": len(results),
        "model": str(MODEL_FILE.relative_to(ROOT)),
        "predictions": results,
    }

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(output_data, f, indent=2, ensure_ascii=False)

    counts = pd.Series(predictions).value_counts()

    print("\nPredicted component counts:")
    print(counts.to_string())

    print(f"\nNeeds review: {sum(confidences < 0.70)} candidates")
    print("\nPREDICTION COMPLETE")
    print(f"Saved to: {OUTPUT_FILE}")


if __name__ == "__main__":
    main()
